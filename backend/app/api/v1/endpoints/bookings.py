"""Booking hold creation and reservation management endpoints."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import get_current_user
from app.core.dependencies import get_db
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.reservations import SpaceReservation
from app.schemas.bookings import (
    CreateHoldRequest,
    HoldResponse,
    ReservationDetailResponse,
)

router = APIRouter()


@router.post(
    "/hold",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an atomic 480-second checkout hold",
)
async def create_booking_hold(
    payload: CreateHoldRequest,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HoldResponse:
    """Create checkout hold. Enforces PostgreSQL GiST temporal exclusion and 480s lifespan."""
    if payload.end_time <= payload.start_time:
        raise ValidationException(
            detail="Reservation end_time must be strictly after start_time",
            code="INVALID_TIME_WINDOW",
        )

    now = datetime.now(timezone.utc)
    hold_expires_at = now + timedelta(seconds=480)
    booking_ref = f"BK-{secrets.token_hex(4).upper()}"
    reservation_id = uuid.uuid4()

    # Time window as asyncpg Range
    time_window = asyncpg.Range(
        payload.start_time,
        payload.end_time,
        lower_inc=True,
        upper_inc=False,
    )

    try:
        query = text(
            """
            INSERT INTO space_reservations (
                id, parking_space_id, driver_id, vehicle_id,
                time_window, reservation_type, status, booking_reference,
                hold_expires_at, idempotency_key
            )
            VALUES ($1, $2, $3, $4, $5, 'TEMPORARY_HOLD', 'ACTIVE_HOLD', $6, $7, $8)
            """
        )
        # Execute via connection or session
        conn = await db.connection()
        raw_conn = await conn.get_raw_connection()
        underlying = raw_conn.driver_connection

        await underlying.execute(
            """
            INSERT INTO space_reservations (
                id, parking_space_id, driver_id, vehicle_id,
                time_window, reservation_type, status, booking_reference,
                hold_expires_at, idempotency_key
            )
            VALUES ($1, $2, $3, $4, $5, 'TEMPORARY_HOLD', 'ACTIVE_HOLD', $6, $7, $8)
            """,
            reservation_id,
            payload.parking_space_id,
            current_user.id,
            payload.vehicle_id,
            time_window,
            booking_ref,
            hold_expires_at,
            payload.idempotency_key,
        )

        return HoldResponse(
            reservation_id=reservation_id,
            booking_reference=booking_ref,
            parking_space_id=payload.parking_space_id,
            driver_id=current_user.id,
            status="ACTIVE_HOLD",
            hold_expires_at=hold_expires_at,
        )

    except ExclusionViolationError:
        raise ConflictException(
            detail="The selected parking space was claimed by another driver for this time window.",
            code="SLOT_ALREADY_RESERVED",
        )
    except Exception as exc:
        if "prevent_overlapping_active_reservations" in str(exc):
            raise ConflictException(
                detail="The selected parking space was claimed by another driver for this time window.",
                code="SLOT_ALREADY_RESERVED",
            )
        raise exc


@router.get(
    "/{reservation_id}",
    response_model=ReservationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reservation details",
)
async def get_reservation_details(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReservationDetailResponse:
    """Retrieve reservation record."""
    stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id)
    result = await db.execute(stmt)
    res = result.scalar_one_or_none()
    if not res:
        raise EntityNotFoundException(
            detail=f"Reservation {reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    return ReservationDetailResponse(
        reservation_id=res.id,
        booking_reference=res.booking_reference,
        parking_space_id=res.parking_space_id,
        driver_id=res.driver_id,
        status=res.status.value,
        payment_order_id=res.payment_order_id,
        hold_expires_at=res.hold_expires_at,
        created_at=res.created_at,
    )
