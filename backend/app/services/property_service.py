"""Property Domain Service for Gadispot Phase 03 Supply Engine.

Handles Property CRUD, WGS 84 Point spatial geometry persistence, owner authorization,
review submission workflow (DRAFT -> PENDING_REVIEW), and public discovery exclusion filtering.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authorization import verify_resource_ownership
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.core.storage import StorageService
from app.models.audit import AuditEvent
from app.models.documents import PropertyDocument
from app.models.enums import AuthorizationStatusEnum, UserRoleEnum
from app.models.properties import Property, PropertyAuthorization
from app.models.users import User
from app.schemas.properties import (
    DocumentPresignRequest,
    DocumentPresignResponse,
    PropertyCreate,
    PropertyUpdate,
)


class PropertyService:
    """Core domain service orchestrating property lifecycle and inventory boundaries."""

    @staticmethod
    def make_point_wkt(latitude: float, longitude: float) -> WKTElement:
        """Construct PostGIS WGS 84 Point geometry element (SRID 4326)."""
        return WKTElement(f"SRID=4326;POINT({longitude} {latitude})", srid=4326)

    @classmethod
    async def create_property(
        cls,
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: PropertyCreate,
    ) -> Property:
        """Create a new property listing in DRAFT status with initial authorization record."""
        point_geom = cls.make_point_wkt(payload.latitude, payload.longitude)

        property_obj = Property(
            owner_id=owner_id,
            title=payload.title,
            property_type=payload.property_type,
            address_line=payload.address_line,
            city=payload.city,
            postal_code=payload.postal_code,
            location=point_geom,
            max_advance_days=payload.max_advance_days,
            max_booking_hours=payload.max_booking_hours,
            is_active=False,
        )
        db.add(property_obj)
        await db.flush()

        # Automatically initialize linked PropertyAuthorization record with status=DRAFT, version=1
        auth_record = PropertyAuthorization(
            property_id=property_obj.id,
            status=AuthorizationStatusEnum.DRAFT,
            version=1,
        )
        db.add(auth_record)
        await db.commit()

        # Re-fetch with eager loaded relationships
        return await cls.get_property(db, property_obj.id)

    @classmethod
    async def get_property(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
    ) -> Property:
        """Retrieve property by ID with all child relationships loaded."""
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .options(
                selectinload(Property.authorization),
                selectinload(Property.parking_spaces),
                selectinload(Property.operating_schedules),
                selectinload(Property.blackouts),
                selectinload(Property.documents),
            )
        )
        res = await db.execute(stmt)
        prop = res.scalar_one_or_none()
        if not prop:
            raise EntityNotFoundException(
                detail=f"Property with ID '{property_id}' was not found.",
                code="PROPERTY_NOT_FOUND",
            )
        return prop

    @classmethod
    async def list_owner_properties(
        cls,
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> list[Property]:
        """List all properties registered by the given space owner."""
        stmt = (
            select(Property)
            .where(Property.owner_id == owner_id)
            .options(
                selectinload(Property.authorization),
                selectinload(Property.parking_spaces),
                selectinload(Property.operating_schedules),
                selectinload(Property.blackouts),
                selectinload(Property.documents),
            )
            .order_by(Property.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def update_property(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        payload: PropertyUpdate,
    ) -> Property:
        """Update property metadata with strict owner authorization."""
        prop = await cls.get_property(db, property_id)
        verify_resource_ownership(user, prop.owner_id)

        update_data = payload.model_dump(exclude_unset=True)

        # Handle coordinate updates if either latitude or longitude is provided
        new_lat = update_data.pop("latitude", None)
        new_lon = update_data.pop("longitude", None)
        if new_lat is not None or new_lon is not None:
            # If only one is provided, keep the other from current geometry
            from app.schemas.properties import extract_lat_lon

            curr_lat, curr_lon = extract_lat_lon(prop.location)
            target_lat = new_lat if new_lat is not None else curr_lat
            target_lon = new_lon if new_lon is not None else curr_lon
            prop.location = cls.make_point_wkt(target_lat, target_lon)

        for key, value in update_data.items():
            setattr(prop, key, value)

        await db.commit()
        return await cls.get_property(db, property_id)

    @classmethod
    async def submit_for_review(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
    ) -> Property:
        """Submit property dossier for operations verification (DRAFT / REJECTED -> PENDING_REVIEW).

        Validates prerequisites:
        - At least 1 configured parking space
        - At least 1 verified legal document
        """
        prop = await cls.get_property(db, property_id)
        verify_resource_ownership(user, prop.owner_id)

        auth = prop.authorization
        if not auth:
            auth = PropertyAuthorization(
                property_id=prop.id,
                status=AuthorizationStatusEnum.DRAFT,
                version=1,
            )
            db.add(auth)
            await db.flush()

        if auth.status == AuthorizationStatusEnum.PENDING_REVIEW:
            raise ConflictException(
                detail="Property is already in PENDING_REVIEW status.",
                code="ALREADY_SUBMITTED",
            )
        if auth.status == AuthorizationStatusEnum.APPROVED:
            raise ConflictException(
                detail="Property is already approved and active.",
                code="ALREADY_APPROVED",
            )

        # Prerequisite 1: At least 1 parking space
        if not prop.parking_spaces:
            raise ValidationException(
                detail="Property must have at least one parking space before review submission.",
                code="NO_SPACES_CONFIGURED",
            )

        # Prerequisite 2: At least 1 verified document
        verified_docs = [doc for doc in (prop.documents or []) if getattr(doc, "is_verified", False)]
        if not verified_docs:
            raise ValidationException(
                detail="Property must have at least one verified document before review submission.",
                code="NO_VERIFIED_DOCUMENTS",
            )

        # Transition status to PENDING_REVIEW
        auth.status = AuthorizationStatusEnum.PENDING_REVIEW

        # Emit immutable audit event
        audit_event = AuditEvent(
            actor_id=user.id,
            action="PROPERTY_SUBMITTED_FOR_REVIEW",
            resource_type="property",
            resource_id=str(prop.id),
            details={"version": auth.version, "status": "PENDING_REVIEW"},
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(auth)
        return prop

    @classmethod
    async def presign_document(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        payload: DocumentPresignRequest,
    ) -> DocumentPresignResponse:
        """Validate document payload, persist pending record, and return 15-minute presigned upload URL."""
        prop = await cls.get_property(db, property_id)
        if prop.owner_id != user.id and not user.has_role(UserRoleEnum.ADMIN):
            raise ForbiddenException(
                detail="You do not have permission to upload documents for this property.",
                code="FORBIDDEN",
            )

        if payload.file_size_bytes <= 0 or payload.file_size_bytes > 10 * 1024 * 1024:
            raise ValidationException(
                detail="File size exceeds maximum allowed 10MB limit (10485760 bytes).",
                code="FILE_TOO_LARGE",
            )

        doc_id = uuid.uuid4()
        s3_key = f"properties/{property_id}/documents/{doc_id}/{payload.file_name}"
        doc = PropertyDocument(
            id=doc_id,
            property_id=property_id,
            document_type=payload.document_type,
            file_name=payload.file_name,
            s3_key=s3_key,
            content_type=payload.content_type,
            file_size_bytes=payload.file_size_bytes,
            is_verified=False,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        upload_url = StorageService.generate_presigned_upload_url(
            s3_key=s3_key,
            content_type=payload.content_type,
            expires_in=900,
        )
        return DocumentPresignResponse(
            document_id=doc.id,
            upload_url=upload_url,
            expires_in=900,
            s3_key=s3_key,
        )

    @classmethod
    async def verify_document(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        document_id: uuid.UUID,
        user: User,
    ) -> PropertyDocument:
        """Verify document upload completion and mark record is_verified=True."""
        prop = await cls.get_property(db, property_id)
        if prop.owner_id != user.id and not user.has_role(UserRoleEnum.ADMIN):
            raise ForbiddenException(
                detail="You do not have permission to verify documents for this property.",
                code="FORBIDDEN",
            )

        stmt = select(PropertyDocument).where(
            PropertyDocument.id == document_id,
            PropertyDocument.property_id == property_id,
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise EntityNotFoundException(
                detail=f"Document with ID '{document_id}' was not found for this property.",
                code="DOCUMENT_NOT_FOUND",
            )

        doc.is_verified = True
        doc.uploaded_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(doc)
        return doc

    @classmethod
    async def list_documents(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
    ) -> list[PropertyDocument]:
        """List all authorization documents uploaded for this property."""
        prop = await cls.get_property(db, property_id)
        if (
            prop.owner_id != user.id
            and not user.has_role(UserRoleEnum.ADMIN)
            and not user.has_role(UserRoleEnum.OPERATIONS)
        ):
            raise ForbiddenException(
                detail="You do not have permission to view documents for this property.",
                code="FORBIDDEN",
            )

        stmt = (
            select(PropertyDocument)
            .where(PropertyDocument.property_id == property_id)
            .order_by(PropertyDocument.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_document(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        document_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete an unverified or obsolete property document."""
        prop = await cls.get_property(db, property_id)
        if prop.owner_id != user.id and not user.has_role(UserRoleEnum.ADMIN):
            raise ForbiddenException(
                detail="You do not have permission to delete documents for this property.",
                code="FORBIDDEN",
            )

        stmt = select(PropertyDocument).where(
            PropertyDocument.id == document_id,
            PropertyDocument.property_id == property_id,
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if doc:
            await db.delete(doc)
            await db.commit()

    @staticmethod
    def apply_public_discovery_filter(query: Select) -> Select:
        """Enforce strict gatekeeper filter for public driver discovery.

        Only properties with status == 'APPROVED' AND is_active == TRUE can be discovered.
        """
        return query.where(
            Property.is_active.is_(True),
            Property.authorization.has(PropertyAuthorization.status == AuthorizationStatusEnum.APPROVED),
        )

    @staticmethod
    def fuzz_coordinates(
        latitude: float,
        longitude: float,
        offset_meters: float = 100.0,
    ) -> tuple[float, float]:
        """Apply coordinate fuzzing for public driver discovery prior to booking confirmation."""
        # 1 deg latitude ~ 111,320m
        lat_offset = (offset_meters / 111320.0) * 0.5
        cos_lat = max(math.cos(math.radians(latitude)), 0.1)
        lon_offset = min((offset_meters / (111320.0 * cos_lat)) * 0.5, 0.004)
        return round(latitude + lat_offset, 4), round(longitude + lon_offset, 4)
