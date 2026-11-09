"""FastAPI endpoints for Operations Review Queue, Verification Dossier, TOTP step-up, and watermarking."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authorization import require_roles
from app.core.dependencies import get_db
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    UnauthorizedException,
)
from app.core.security import decrypt_totp_secret
from app.core.storage import StorageService
from app.models.audit import AuditEvent
from app.models.documents import PropertyDocument
from app.models.enums import AuthorizationStatusEnum, PropertyTypeEnum, UserRoleEnum
from app.models.properties import Property, PropertyAuthorization
from app.models.users import User
from app.schemas.properties import (
    OpsApproveRequest,
    OpsRejectRequest,
    OpsReviewDecisionResponse,
    OpsReviewQueueItem,
    OpsReviewQueueResponse,
    PropertyResponse,
)
from app.services.auth_service import verify_totp_code
from app.services.property_service import PropertyService

router = APIRouter()

# Strictly require OPERATIONS or OPS role for all operations review capabilities
require_ops_officer = require_roles(UserRoleEnum.OPERATIONS, "OPS")


def _verify_user_totp(user: User, code: str) -> None:
    """Validate RFC 6238 TOTP code against the officer's enrolled secret."""
    secret: Optional[str] = None
    if getattr(user, "totp_secret_encrypted", None):
        try:
            secret = decrypt_totp_secret(user.totp_secret_encrypted)
        except Exception:
            secret = None
    elif getattr(user, "totp_secret", None):
        secret = user.totp_secret

    if not secret or not verify_totp_code(secret, code):
        raise UnauthorizedException(
            detail="Invalid or expired TOTP step-up verification code.",
            code="INVALID_MFA_CODE",
        )


# =============================================================================
# Operations Review Queue & Dossier Endpoints
# =============================================================================


@router.get(
    "/properties/queue",
    response_model=OpsReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="List properties waiting in operations verification queue",
)
async def list_review_queue(
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    city: Optional[str] = Query(None, description="Filter by property city"),
    property_type: Optional[PropertyTypeEnum] = Query(None, description="Filter by property type"),
    current_user: User = Depends(require_ops_officer),
    db: AsyncSession = Depends(get_db),
) -> OpsReviewQueueResponse:
    """Return paginated queue of properties in PENDING_REVIEW status with optional city and type filters."""
    query = (
        select(Property)
        .join(Property.authorization)
        .where(PropertyAuthorization.status == AuthorizationStatusEnum.PENDING_REVIEW)
        .options(selectinload(Property.authorization))
    )

    count_query = (
        select(func.count(Property.id))
        .join(Property.authorization)
        .where(PropertyAuthorization.status == AuthorizationStatusEnum.PENDING_REVIEW)
    )

    if city:
        query = query.where(Property.city == city)
        count_query = count_query.where(Property.city == city)
    if property_type:
        query = query.where(Property.property_type == property_type)
        count_query = count_query.where(Property.property_type == property_type)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(PropertyAuthorization.updated_at.desc()).offset(offset).limit(limit)
    properties = list((await db.execute(query)).scalars().all())

    items = [
        OpsReviewQueueItem(
            id=p.id,
            title=p.title,
            property_type=p.property_type,
            city=p.city,
            address_line=p.address_line,
            owner_id=p.owner_id,
            status=p.authorization.status if p.authorization else AuthorizationStatusEnum.PENDING_REVIEW,
            version=p.authorization.version if p.authorization else 1,
            submitted_at=p.authorization.updated_at if p.authorization else None,
            created_at=p.created_at,
        )
        for p in properties
    ]

    return OpsReviewQueueResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/properties/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete operations review dossier for property",
)
async def get_property_dossier(
    property_id: uuid.UUID,
    current_user: User = Depends(require_ops_officer),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Retrieve full property profile including parking spaces, schedules, and uploaded legal documents."""
    prop = await PropertyService.get_property(db, property_id)
    return PropertyResponse.model_validate(prop)


# =============================================================================
# Operations Step-Up Decisions (TOTP Required)
# =============================================================================


@router.post(
    "/properties/{property_id}/approve",
    response_model=OpsReviewDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve property listing with TOTP step-up authentication",
)
async def approve_property(
    property_id: uuid.UUID,
    payload: OpsApproveRequest,
    current_user: User = Depends(require_ops_officer),
    db: AsyncSession = Depends(get_db),
) -> OpsReviewDecisionResponse:
    """Approve property with TOTP step-up, optimistic concurrency lock, and audit logging."""
    _verify_user_totp(current_user, payload.totp_code)

    prop = await PropertyService.get_property(db, property_id)
    auth = prop.authorization
    if not auth:
        raise EntityNotFoundException(
            detail=f"Authorization record missing for property '{property_id}'.",
            code="AUTHORIZATION_RECORD_NOT_FOUND",
        )

    # Optimistic concurrency lock: prevent race condition if another operator already updated
    if auth.version != payload.version:
        raise ConflictException(
            detail=f"Optimistic lock conflict: dossier version is {auth.version}, but request specified {payload.version}.",
            code="VERSION_CONFLICT",
        )

    auth.status = AuthorizationStatusEnum.APPROVED
    auth.version += 1
    auth.reviewed_by = current_user.id
    auth.reviewed_at = datetime.now(timezone.utc)
    if payload.reviewer_notes:
        auth.reviewer_notes = payload.reviewer_notes
    prop.is_active = True

    # Emit immutable audit event
    audit_event = AuditEvent(
        actor_id=current_user.id,
        action="PROPERTY_APPROVED",
        resource_type="property",
        resource_id=str(prop.id),
        details={"version": auth.version, "status": "APPROVED"},
    )
    db.add(audit_event)

    await db.commit()
    await db.refresh(auth)
    return OpsReviewDecisionResponse(
        id=prop.id,
        status="APPROVED",
        is_active=True,
        version=auth.version,
        message="Property approved and activated for discovery.",
    )


@router.post(
    "/properties/{property_id}/reject",
    response_model=OpsReviewDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject property listing with TOTP step-up authentication",
)
async def reject_property(
    property_id: uuid.UUID,
    payload: OpsRejectRequest,
    current_user: User = Depends(require_ops_officer),
    db: AsyncSession = Depends(get_db),
) -> OpsReviewDecisionResponse:
    """Reject property with canonical rejection reason code, notes, and optimistic concurrency lock."""
    _verify_user_totp(current_user, payload.totp_code)

    prop = await PropertyService.get_property(db, property_id)
    auth = prop.authorization
    if not auth:
        raise EntityNotFoundException(
            detail=f"Authorization record missing for property '{property_id}'.",
            code="AUTHORIZATION_RECORD_NOT_FOUND",
        )

    # Optimistic concurrency lock
    if auth.version != payload.version:
        raise ConflictException(
            detail=f"Optimistic lock conflict: dossier version is {auth.version}, but request specified {payload.version}.",
            code="VERSION_CONFLICT",
        )

    auth.status = AuthorizationStatusEnum.REJECTED
    auth.version += 1
    auth.rejection_reason_code = payload.rejection_reason_code
    auth.reviewer_notes = payload.reviewer_notes
    auth.reviewed_by = current_user.id
    auth.reviewed_at = datetime.now(timezone.utc)
    prop.is_active = False

    # Emit immutable audit event
    audit_event = AuditEvent(
        actor_id=current_user.id,
        action="PROPERTY_REJECTED",
        resource_type="property",
        resource_id=str(prop.id),
        details={
            "version": auth.version,
            "status": "REJECTED",
            "rejection_reason_code": payload.rejection_reason_code,
        },
    )
    db.add(audit_event)

    await db.commit()
    await db.refresh(auth)
    return OpsReviewDecisionResponse(
        id=prop.id,
        status="REJECTED",
        is_active=False,
        version=auth.version,
        message="Property rejected with structured feedback.",
    )


# =============================================================================
# Watermarked Document Download
# =============================================================================


@router.get(
    "/documents/{document_id}/watermarked",
    status_code=status.HTTP_200_OK,
    summary="Download watermarked legal authorization document",
)
async def download_watermarked_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_ops_officer),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Operations officer downloads document stamped with tamper-evident 'For Gadispot Verification Only' watermark."""
    stmt = select(PropertyDocument).where(PropertyDocument.id == document_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise EntityNotFoundException(
            detail=f"Legal document with ID '{document_id}' was not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    watermarked_bytes = StorageService.generate_watermarked_content(
        content_type=doc.content_type,
        watermark_text="For Gadispot Verification Only",
    )

    return Response(
        content=watermarked_bytes,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'inline; filename="watermarked_{doc.file_name}"',
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
        },
    )
