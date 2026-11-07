"""Integration tests for PaymentService: booking confirmation, ledger balancing, and access pass issuance."""

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from app.models.access import AccessCredential
from app.models.enums import (
    JournalStatusEnum,
    PaymentProviderEnum,
    PaymentStatusEnum,
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    TokenStatusEnum,
    TokenTypeEnum,
    VehicleCategoryEnum,
)
from app.models.ledger import JournalEntry, JournalLine
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.users import User, Vehicle
from app.services.payment_service import PaymentService
from sqlalchemy import select, text


@pytest.fixture
async def reservation_fixture(db_session):
    """Fixture creating driver, vehicle, parking space, and active hold reservation."""
    user = User(
        phone_number=f"+9198{uuid.uuid4().hex[:8]}", full_name="Payment Svc Tester"
    )
    db_session.add(user)
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=user.id,
        registration_plate=f"KA02CD{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
    )
    db_session.add(vehicle)

    prop_id = uuid.uuid4()
    await db_session.execute(
        text("""
        INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES (:id, :owner_id, 'Koramangala Hub', 'COMMERCIAL_BUILDING', '80ft Road', 'Bengaluru', '560034', 'SRID=4326;POINT(77.6200 12.9352)', TRUE)
        """),
        {"id": prop_id, "owner_id": user.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"SLOT-{uuid.uuid4().hex[:4].upper()}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=15000,
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
    await db_session.commit()
    await db_session.refresh(res)
    return res, user


@pytest.mark.asyncio
async def test_payment_creation_and_successful_demo_completion(
    db_session, reservation_fixture
):
    """End-to-end test of payment creation, simulated success, ledger posting, and access credentials."""
    reservation, driver = reservation_fixture

    # 1. Initiate Payment
    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=reservation.id,
        driver_id=driver.id,
        gateway_name="demo",
        idempotency_key=f"idem_{uuid.uuid4().hex}",
    )

    payment = init_res["payment"]
    assert payment.status == PaymentStatusEnum.CREATED
    assert payment.is_simulated is True
    assert payment.provider == PaymentProviderEnum.DEMO
    assert init_res["amount_paise"] > 0
    assert init_res["quote"] is not None

    # 2. Complete Demo Payment with SUCCESS
    complete_res = await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="SUCCESS",
    )

    assert complete_res["status"] == "SUCCEEDED"
    assert complete_res["is_simulated"] is True
    assert complete_res["provider_payment_id"] is not None

    # 3. Assert reservation is confirmed
    await db_session.refresh(reservation)
    assert reservation.status == ReservationStatusEnum.CONFIRMED
    assert reservation.payment_transaction_id == complete_res["provider_payment_id"]

    # 4. Assert access credentials were generated
    stmt_creds = select(AccessCredential).where(
        AccessCredential.reservation_id == reservation.id
    )
    creds = (await db_session.execute(stmt_creds)).scalars().all()
    assert len(creds) == 2
    types = {c.token_type for c in creds}
    assert TokenTypeEnum.ENTRY in types
    assert TokenTypeEnum.EXIT in types
    for c in creds:
        assert c.status == TokenStatusEnum.ISSUED
        assert c.opaque_token.startswith("spx_")

    # 5. Assert General Ledger journal entry was posted and balances
    j_ref = f"PAY-{payment.id}"
    stmt_j = select(JournalEntry).where(JournalEntry.transaction_reference == j_ref)
    journal = (await db_session.execute(stmt_j)).scalar_one_or_none()
    assert journal is not None
    assert journal.posting_status == JournalStatusEnum.POSTED
    assert journal.posted_at is not None

    # Assert journal lines
    stmt_lines = select(JournalLine).where(JournalLine.journal_id == journal.id)
    lines = (await db_session.execute(stmt_lines)).scalars().all()
    assert len(lines) >= 2

    total_debits = sum(
        l.amount_in_paise for l in lines if l.entry_side.value == "DEBIT"
    )
    total_credits = sum(
        l.amount_in_paise for l in lines if l.entry_side.value == "CREDIT"
    )
    assert total_debits == total_credits
    assert total_debits == payment.amount_paise


@pytest.mark.asyncio
async def test_demo_payment_failure_scenario(db_session, reservation_fixture):
    """Test simulated failure marks payment as FAILED without confirming reservation."""
    reservation, driver = reservation_fixture

    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=reservation.id,
        driver_id=driver.id,
        gateway_name="demo",
    )
    payment = init_res["payment"]

    complete_res = await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="FAILURE",
        reason="Test simulated decline",
    )

    assert complete_res["status"] == "FAILED"
    await db_session.refresh(payment)
    assert payment.status == PaymentStatusEnum.FAILED
    assert payment.failure_reason == "Test simulated decline"

    # Reservation remains unconfirmed
    await db_session.refresh(reservation)
    assert reservation.status != ReservationStatusEnum.CONFIRMED


@pytest.mark.asyncio
async def test_payment_idempotency_replay(db_session, reservation_fixture):
    """Verify replaying SUCCESS on an already succeeded payment returns idempotent response."""
    reservation, driver = reservation_fixture

    init_res = await PaymentService.create_payment(
        db=db_session,
        reservation_id=reservation.id,
        driver_id=driver.id,
        gateway_name="demo",
    )
    payment = init_res["payment"]

    # First completion
    await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="SUCCESS",
    )

    # Replay completion
    replay_res = await PaymentService.complete_demo_payment(
        db=db_session,
        payment_id=payment.id,
        driver_id=driver.id,
        outcome="SUCCESS",
    )
    assert replay_res["status"] == "SUCCEEDED"
    assert "idempotent replay" in replay_res["message"]
