"""Schedule Domain Service for Gadispot Phase 03 Supply Engine.

Handles operating schedule management (weekly recurring windows, non-overlapping interval validation)
and manual space blackouts (overlap prevention against existing blackouts and confirmed reservations, HTTP 409 conflict).
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authorization import verify_resource_ownership
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.enums import ReservationStatusEnum
from app.models.parking import ParkingSpace
from app.models.properties import OperatingSchedule, Property
from app.models.reservations import SpaceReservation
from app.models.schedules import BlackoutSchedule
from app.models.users import User
from app.schemas.properties import (
    BlackoutScheduleCreate,
    OperatingScheduleCreate,
)


class ScheduleService:
    """Domain service managing operational schedules and owner blackout windows."""

    # =========================================================================
    # Operating Schedules (Recurring Weekly Hours)
    # =========================================================================

    @classmethod
    async def add_operating_schedule(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        payload: OperatingScheduleCreate,
    ) -> OperatingSchedule:
        """Add weekly operating hours window with non-overlapping interval validation."""
        # 1. Fetch property and verify owner authorization
        prop_stmt = select(Property).where(Property.id == property_id)
        prop_res = await db.execute(prop_stmt)
        prop = prop_res.scalar_one_or_none()
        if not prop:
            raise EntityNotFoundException(
                detail=f"Property with ID '{property_id}' was not found.",
                code="PROPERTY_NOT_FOUND",
            )
        verify_resource_ownership(user, prop.owner_id)

        # 2. Validate time interval order
        if payload.start_time >= payload.end_time:
            raise ValidationException(
                detail="Operating hours start_time must be strictly before end_time.",
                code="INVALID_TIME_INTERVAL",
            )

        # 3. Check for overlapping schedule on the same day for the same property
        overlap_stmt = select(OperatingSchedule).where(
            OperatingSchedule.property_id == property_id,
            OperatingSchedule.day_of_week == payload.day_of_week,
            OperatingSchedule.is_active.is_(True),
            OperatingSchedule.start_time < payload.end_time,
            OperatingSchedule.end_time > payload.start_time,
        )
        overlap_res = await db.execute(overlap_stmt)
        if overlap_res.scalar_one_or_none() is not None:
            raise ConflictException(
                detail=f"Operating schedule window overlaps with an existing schedule for day {payload.day_of_week}.",
                code="SCHEDULE_OVERLAP_CONFLICT",
            )

        # 4. Create schedule
        schedule = OperatingSchedule(
            property_id=property_id,
            day_of_week=payload.day_of_week,
            start_time=payload.start_time,
            end_time=payload.end_time,
            is_active=payload.is_active,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @classmethod
    async def list_operating_schedules(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
    ) -> list[OperatingSchedule]:
        """List all active operating schedules for a property."""
        stmt = (
            select(OperatingSchedule)
            .where(
                OperatingSchedule.property_id == property_id,
                OperatingSchedule.is_active.is_(True),
            )
            .order_by(OperatingSchedule.day_of_week.asc(), OperatingSchedule.start_time.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def delete_operating_schedule(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        schedule_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete an operating schedule window with owner authorization."""
        stmt = (
            select(OperatingSchedule)
            .where(
                OperatingSchedule.id == schedule_id,
                OperatingSchedule.property_id == property_id,
            )
            .options(selectinload(OperatingSchedule.property))
        )
        res = await db.execute(stmt)
        schedule = res.scalar_one_or_none()
        if not schedule:
            raise EntityNotFoundException(
                detail=f"Operating schedule with ID '{schedule_id}' was not found.",
                code="SCHEDULE_NOT_FOUND",
            )
        verify_resource_ownership(user, schedule.property.owner_id)

        await db.delete(schedule)
        await db.commit()

    # =========================================================================
    # Blackout Schedules (Manual Bay / Property-Wide Blocks)
    # =========================================================================

    @classmethod
    async def add_blackout(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        payload: BlackoutScheduleCreate,
        parking_space_id: Optional[uuid.UUID] = None,
    ) -> BlackoutSchedule:
        """Add blackout schedule with conflict validation against existing blackouts and confirmed reservations."""
        # 1. Fetch property and verify owner authorization
        prop_stmt = select(Property).where(Property.id == property_id).options(selectinload(Property.parking_spaces))
        prop_res = await db.execute(prop_stmt)
        prop = prop_res.scalar_one_or_none()
        if not prop:
            raise EntityNotFoundException(
                detail=f"Property with ID '{property_id}' was not found.",
                code="PROPERTY_NOT_FOUND",
            )
        verify_resource_ownership(user, prop.owner_id)

        # 2. Determine target parking space ID
        target_space_id = parking_space_id or payload.parking_space_id
        if target_space_id:
            space_stmt = select(ParkingSpace).where(
                ParkingSpace.id == target_space_id,
                ParkingSpace.property_id == property_id,
            )
            space_res = await db.execute(space_stmt)
            if space_res.scalar_one_or_none() is None:
                raise EntityNotFoundException(
                    detail=f"Parking space '{target_space_id}' not found on this property.",
                    code="SPACE_NOT_FOUND",
                )

        # 3. Validate start_time < end_time
        if payload.start_time >= payload.end_time:
            raise ValidationException(
                detail="Blackout start_time must be strictly before end_time.",
                code="INVALID_TIME_INTERVAL",
            )

        # 4. Check for overlapping existing active blackouts
        # If bay-specific: overlaps if another blackout on the same bay OR a property-wide blackout overlaps
        # If property-wide: overlaps if ANY blackout on this property overlaps
        if target_space_id:
            bo_overlap_stmt = select(BlackoutSchedule).where(
                BlackoutSchedule.property_id == property_id,
                BlackoutSchedule.is_active.is_(True),
                (BlackoutSchedule.parking_space_id == target_space_id) | (BlackoutSchedule.parking_space_id.is_(None)),
                BlackoutSchedule.start_time < payload.end_time,
                BlackoutSchedule.end_time > payload.start_time,
            )
        else:
            bo_overlap_stmt = select(BlackoutSchedule).where(
                BlackoutSchedule.property_id == property_id,
                BlackoutSchedule.is_active.is_(True),
                BlackoutSchedule.start_time < payload.end_time,
                BlackoutSchedule.end_time > payload.start_time,
            )

        bo_overlap_res = await db.execute(bo_overlap_stmt)
        if bo_overlap_res.scalar_one_or_none() is not None:
            raise ConflictException(
                detail="Blackout window overlaps with an existing active blackout schedule.",
                code="BLACKOUT_OVERLAP_CONFLICT",
            )

        # 5. Check for overlapping confirmed or active hold reservations (HTTP 409 Conflict)
        target_space_ids: list[uuid.UUID] = []
        if target_space_id:
            target_space_ids = [target_space_id]
        else:
            target_space_ids = [s.id for s in (prop.parking_spaces or [])]

        if target_space_ids:
            resv_stmt = select(SpaceReservation).where(
                SpaceReservation.parking_space_id.in_(target_space_ids),
                SpaceReservation.status.in_(
                    [
                        ReservationStatusEnum.CONFIRMED,
                        ReservationStatusEnum.ACTIVE_HOLD,
                        ReservationStatusEnum.ACTIVE_SESSION,
                    ]
                ),
                func.lower(SpaceReservation.time_window) < payload.end_time,
                func.upper(SpaceReservation.time_window) > payload.start_time,
            )
            resv_res = await db.execute(resv_stmt)
            if resv_res.scalar_one_or_none() is not None:
                raise ConflictException(
                    detail="Blackout window conflicts with an existing confirmed or active hold reservation.",
                    code="RESERVATION_OVERLAP_CONFLICT",
                )

        # 6. Create blackout schedule
        blackout = BlackoutSchedule(
            property_id=property_id,
            parking_space_id=target_space_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            reason=payload.reason,
            is_active=payload.is_active,
        )
        db.add(blackout)
        await db.commit()
        await db.refresh(blackout)
        return blackout

    @classmethod
    async def list_blackouts(
        cls,
        db: AsyncSession,
        property_id: uuid.UUID,
        parking_space_id: Optional[uuid.UUID] = None,
    ) -> list[BlackoutSchedule]:
        """List active blackouts for a property or specific parking space."""
        stmt = select(BlackoutSchedule).where(
            BlackoutSchedule.property_id == property_id,
            BlackoutSchedule.is_active.is_(True),
        )
        if parking_space_id is not None:
            stmt = stmt.where(
                (BlackoutSchedule.parking_space_id == parking_space_id) | (BlackoutSchedule.parking_space_id.is_(None))
            )
        stmt = stmt.order_by(BlackoutSchedule.start_time.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def delete_blackout(
        cls,
        db: AsyncSession,
        blackout_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete / cancel a blackout schedule with owner authorization."""
        stmt = (
            select(BlackoutSchedule)
            .where(BlackoutSchedule.id == blackout_id)
            .options(selectinload(BlackoutSchedule.property))
        )
        res = await db.execute(stmt)
        blackout = res.scalar_one_or_none()
        if not blackout:
            raise EntityNotFoundException(
                detail=f"Blackout schedule with ID '{blackout_id}' was not found.",
                code="BLACKOUT_NOT_FOUND",
            )
        verify_resource_ownership(user, blackout.property.owner_id)

        await db.delete(blackout)
        await db.commit()
