"""Parking Space Domain Service for Gadispot Phase 03 Supply Engine.

Handles parking space CRUD, physical dimensions, EV charging flags, and vehicle clearance compatibility
checks against CompatibilityService (3D margins) and PostgreSQL stored function fn_check_vehicle_bay_compatibility.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authorization import verify_resource_ownership
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
)
from app.models.parking import ParkingSpace
from app.models.properties import Property
from app.models.users import User
from app.schemas.properties import (
    ParkingSpaceCreate,
    ParkingSpaceUpdate,
    VehicleCompatibilityCheckRequest,
    VehicleCompatibilityCheckResponse,
)
from app.services.compatibility_service import (
    CompatibilityService,
    SpaceDimensions,
    VehicleDimensions,
)


class ParkingSpaceService:
    """Domain service managing parking bay inventory, dimensions, and clearance compatibility."""

    @classmethod
    async def create_space(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        payload: ParkingSpaceCreate,
    ) -> ParkingSpace:
        """Create a new parking bay under a property with owner verification and unique label enforcement."""
        # 1. Fetch parent property and verify owner authorization
        prop_stmt = select(Property).where(Property.id == property_id)
        prop_res = await db.execute(prop_stmt)
        prop = prop_res.scalar_one_or_none()
        if not prop:
            raise EntityNotFoundException(
                detail=f"Property with ID '{property_id}' was not found.",
                code="PROPERTY_NOT_FOUND",
            )
        verify_resource_ownership(user, prop.owner_id)

        # 2. Check for duplicate space label on this property
        dup_stmt = select(ParkingSpace).where(
            ParkingSpace.property_id == property_id,
            ParkingSpace.space_label == payload.space_label,
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise ConflictException(
                detail=f"A parking space with label '{payload.space_label}' already exists on this property.",
                code="DUPLICATE_SPACE_LABEL",
            )

        # 3. Create space
        space = ParkingSpace(
            property_id=property_id,
            space_label=payload.space_label,
            space_type=payload.space_type,
            vehicle_category=payload.vehicle_category,
            length_meters=payload.length_meters,
            width_meters=payload.width_meters,
            height_clearance_meters=payload.height_clearance_meters,
            has_ev_charging=payload.has_ev_charging,
            base_hourly_rate_paise=payload.base_hourly_rate_paise,
            is_active=payload.is_active,
        )
        db.add(space)
        await db.commit()
        await db.refresh(space)
        return space

    @classmethod
    async def get_space(
        cls,
        db: AsyncSession,
        space_id: uuid.UUID,
    ) -> ParkingSpace:
        """Retrieve parking space by ID with parent property eagerly loaded."""
        stmt = select(ParkingSpace).where(ParkingSpace.id == space_id).options(selectinload(ParkingSpace.property))
        res = await db.execute(stmt)
        space = res.scalar_one_or_none()
        if not space:
            raise EntityNotFoundException(
                detail=f"Parking space with ID '{space_id}' was not found.",
                code="SPACE_NOT_FOUND",
            )
        return space

    @classmethod
    async def list_spaces(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
    ) -> list[ParkingSpace]:
        """List all parking spaces belonging to a property."""
        stmt = (
            select(ParkingSpace).where(ParkingSpace.property_id == property_id).order_by(ParkingSpace.created_at.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def update_space(
        cls,
        db: AsyncSession,
        space_id: uuid.UUID,
        user: User,
        payload: ParkingSpaceUpdate,
    ) -> ParkingSpace:
        """Update parking bay metadata, dimensions, or tariff with owner authorization."""
        space = await cls.get_space(db, space_id)
        verify_resource_ownership(user, space.property.owner_id)

        update_data = payload.model_dump(exclude_unset=True)

        # If updating space_label, check for duplicate on the same property
        new_label = update_data.get("space_label")
        if new_label and new_label != space.space_label:
            dup_stmt = select(ParkingSpace).where(
                ParkingSpace.property_id == space.property_id,
                ParkingSpace.space_label == new_label,
                ParkingSpace.id != space.id,
            )
            dup_res = await db.execute(dup_stmt)
            if dup_res.scalar_one_or_none() is not None:
                raise ConflictException(
                    detail=f"A parking space with label '{new_label}' already exists on this property.",
                    code="DUPLICATE_SPACE_LABEL",
                )

        for key, value in update_data.items():
            setattr(space, key, value)

        await db.commit()
        await db.refresh(space)
        return space

    @classmethod
    async def check_compatibility(
        cls,
        db: AsyncSession,
        space: ParkingSpace,
        request: VehicleCompatibilityCheckRequest,
    ) -> VehicleCompatibilityCheckResponse:
        """Evaluate vehicle clearance compatibility using either 3D physical margins or stored PostgreSQL function."""
        has_exact_dimensions = (
            request.vehicle_length_mm is not None
            and request.vehicle_width_mm is not None
            and request.vehicle_height_mm is not None
        )

        if has_exact_dimensions:
            # Multi-dimensional clearance check (+300mm length, +400mm width, +100mm height)
            vehicle = VehicleDimensions(
                length_mm=request.vehicle_length_mm,  # type: ignore
                width_mm=request.vehicle_width_mm,  # type: ignore
                height_mm=request.vehicle_height_mm,  # type: ignore
                is_ev=request.is_ev or request.driver_requires_ev,
            )
            space_dims = SpaceDimensions(
                length_mm=int(space.length_meters * 1000),
                width_mm=int(space.width_meters * 1000),
                height_mm=int(space.height_clearance_meters * 1000),
                is_ev_charging=space.has_ev_charging,
            )
            result = CompatibilityService.evaluate_compatibility(vehicle, space_dims)
            return VehicleCompatibilityCheckResponse(
                is_compatible=result.is_compatible,
                method="3d_clearance",
                length_clearance_mm=result.length_clearance_mm,
                width_clearance_mm=result.width_clearance_mm,
                height_clearance_mm=result.height_clearance_mm,
                rejection_reasons=result.rejection_reasons,
            )

        # Database stored function check: fn_check_vehicle_bay_compatibility
        # Map space_type to standard bay type expected by the function
        bay_type_mapping = {
            "TWO_WHEELER": "TWO_WHEELER",
            "HATCHBACK": "COMPACT_CAR",
            "SEDAN": "STANDARD_CAR",
            "SUV": "SUV_BAY",
            "EV_FOUR_WHEELER": "LARGE_CAR",
            "EV_TWO_WHEELER": "BIKE_BAY",
        }
        bay_type = bay_type_mapping.get(space.vehicle_category.value, "STANDARD_CAR")

        fn_stmt = text("""
            SELECT fn_check_vehicle_bay_compatibility(
                CAST(:cat AS vehicle_category_enum),
                :bay_type,
                :l,
                :w,
                :h,
                :bay_ev,
                :req_ev
            )
        """)
        fn_res = await db.execute(
            fn_stmt,
            {
                "cat": request.vehicle_category.value,
                "bay_type": bay_type,
                "l": Decimal(str(space.length_meters)),
                "w": Decimal(str(space.width_meters)),
                "h": Decimal(str(space.height_clearance_meters)),
                "bay_ev": space.has_ev_charging,
                "req_ev": request.driver_requires_ev or request.is_ev,
            },
        )
        is_compat = bool(fn_res.scalar())
        rejection_reasons: list[str] = []
        if not is_compat:
            rejection_reasons.append(
                "Bay does not satisfy stored compatibility constraints for this vehicle category and EV requirement."
            )

        return VehicleCompatibilityCheckResponse(
            is_compatible=is_compat,
            method="stored_function",
            rejection_reasons=rejection_reasons,
        )
