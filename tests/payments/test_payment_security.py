"""Security and RBAC tests for PaymentService: production guards, IDOR protection, and tampering defense."""

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from app.core.config import settings
from app.core.exceptions import ForbiddenException
from app.models.enums import (
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.users import User, Vehicle
from app.services.payment_service import PaymentService
from sqlalchemy import text


@pytest.fixture
async def driver_and_reservation(db_session):
    """Fixture providing driver A and an active reservation."""
    driver_a = User(phone_number=f"+9191{uuid.uuid4().hex[:8]}", full_name="Driver A")
    driver_b = User(phone_number=f"+9192{uuid.uuid4().hex[:8]}", full_name="Driver B")
    db_session.add_all([driver_a, driver_b])
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=driver_a.id,
        registration_plate=f"KA03EF{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
    )
    db_session.add(vehicle)

    prop_id = uuid.uuid4()
    await db_session.execute(
        text("""
        INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES (:id, :owner_id, 'Indiranagar Secure Park', 'COMMERCIAL_BUILDING', '100ft Road', 'Bengaluru', '560038', 'SRID=4326;POINT(77.6413 12.9784)', TRUE)
        """),
        {"id": prop_id, "owner_id": driver_a.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"SEC-{uuid.uuid4().hex[:4].upper()}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=12000,
    )
    db_session.add(space)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    res = SpaceReservation(
        parking_space_id=space.id,
        driver_id=driver_a.id,
        vehicle_id=vehicle.id,
        time_window=asyncpg.Range(
            now, now + timedelta(hours=2), lower_inc=True, upper_inc=False
        ),
        reservation_type=ReservationTypeEnum.TEMPORARY_HOLD,
        status=ReservationStatusEnum.ACTIVE_HOLD,
        hold_expires_at=now + timedelta(seconds=480),
        booking_reference=f"GSP-{uuid.uuid4().hex[:8].upper()}",
    )
    db_session.add(res)
    await db_session.commit()
    await db_session.refresh(res)
    return driver_a, driver_b, res


@pytest.mark.asyncio
async def test_idor_payment_initiation_rejected(db_session, driver_and_reservation):
    """Driver B cannot initiate payment on Driver A's reservation."""
    _, driver_b, reservation = driver_and_reservation

    with pytest.raises(ForbiddenException):
        await PaymentService.create_payment(
            db=db_session,
            reservation_id=reservation.id,
            driver_id=driver_b.id,  # Wrong driver
            gateway_name="demo",
        )


@pytest.mark.asyncio
async def test_idor_payment_completion_rejected(db_session, driver_and_reservation):
    """Driver B cannot trigger simulation on Driver A's payment."""
    driver_a, driver_b, reservation = driver_and_reservation

    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=reservation.id,
        driver_id=driver_a.id,
        gateway_name="demo",
    )
    payment = init_res["payment"]

    with pytest.raises(ForbiddenException):
        await PaymentService.complete_demo_payment(
            db=db_session,
            payment_id=payment.id,
            driver_id=driver_b.id,  # Wrong driver
            outcome="SUCCESS",
        )


@pytest.mark.asyncio
async def test_production_environment_guard_blocks_simulation(
    db_session, driver_and_reservation, monkeypatch
):
    """CRITICAL SECURITY TEST: Demo simulation MUST fail-closed in production."""
    driver_a, _, reservation = driver_and_reservation

    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=reservation.id,
        driver_id=driver_a.id,
        gateway_name="demo",
    )
    payment = init_res["payment"]

    # Emulate production runtime
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    with pytest.raises(ForbiddenException) as exc:
        await PaymentService.complete_demo_payment(
            db=db_session,
            payment_id=payment.id,
            driver_id=driver_a.id,
            outcome="SUCCESS",
        )
    assert "production" in str(exc.value.detail).lower()
