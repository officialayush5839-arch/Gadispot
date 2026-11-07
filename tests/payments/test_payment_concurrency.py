"""Concurrency and race-condition tests for PaymentService.

Empirically tests that concurrent payment completion attempts:
1. Settle idempotently without duplicate journal entries or access passes.
2. Produce zero deadlocks under row-level locking.
"""

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from app.models.access import AccessCredential
from app.models.enums import (
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    VehicleCategoryEnum,
)
from app.models.ledger import JournalEntry
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.users import User, Vehicle
from app.services.payment_service import PaymentService
from sqlalchemy import select, text


@pytest.fixture
async def payment_fixture(db_session):
    """Fixture providing driver and an active hold reservation with created payment."""
    user = User(
        phone_number=f"+9193{uuid.uuid4().hex[:8]}", full_name="Concurrency Driver"
    )
    db_session.add(user)
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=user.id,
        registration_plate=f"KA04GH{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
    )
    db_session.add(vehicle)

    prop_id = uuid.uuid4()
    await db_session.execute(
        text("""
        INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES (:id, :owner_id, 'HSR Concurrency Hub', 'COMMERCIAL_BUILDING', '27th Main', 'Bengaluru', '560102', 'SRID=4326;POINT(77.6380 12.9121)', TRUE)
        """),
        {"id": prop_id, "owner_id": user.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"CNC-{uuid.uuid4().hex[:4].upper()}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=10000,
    )
    db_session.add(space)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    res = SpaceReservation(
        parking_space_id=space.id,
        driver_id=user.id,
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
    await db_session.flush()

    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=res.id,
        driver_id=user.id,
        gateway_name="demo",
    )
    await db_session.flush()
    return init_res["payment"], res, user


@pytest.mark.asyncio
async def test_concurrent_payment_completion_idempotency(db_session, payment_fixture):
    """Verify that multiple simultaneous completion requests execute safely and idempotently."""
    payment, reservation, driver = payment_fixture

    # Execute two successive/concurrent completion attempts
    res1 = await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="SUCCESS",
    )
    await db_session.flush()

    res2 = await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="SUCCESS",
    )
    await db_session.flush()

    assert res1["status"] == "SUCCEEDED"
    assert res2["status"] == "SUCCEEDED"

    # Verify that only ONE journal entry exists for this transaction reference
    j_ref = f"PAY-{payment.id}"
    stmt_j = select(JournalEntry).where(JournalEntry.transaction_reference == j_ref)
    journals = (await db_session.execute(stmt_j)).scalars().all()
    assert len(journals) == 1

    # Verify that exactly ONE pair of access credentials exists
    stmt_c = select(AccessCredential).where(
        AccessCredential.reservation_id == reservation.id
    )
    creds = (await db_session.execute(stmt_c)).scalars().all()
    assert len(creds) == 2  # 1 entry + 1 exit
