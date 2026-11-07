"""Automated tests for Phase 6 background workers: Hold Expiration and DPDPA Photo Purge."""

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from app.models.access import OfflineManualAdmission
from app.models.enums import (
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.reservations import SpaceReservation
from app.models.users import User, Vehicle
from app.workers.hold_cleanup_worker import (
    sweep_expired_holds_batch,
    sweep_expired_holds_for_space,
)
from app.workers.photo_purge_worker import purge_expired_gate_photos
from sqlalchemy import text


@pytest.fixture
async def worker_test_space(db_session):
    """Fixture providing a parking space and driver for worker tests."""
    user = User(
        phone_number=f"+9197{uuid.uuid4().hex[:8]}", full_name="Worker Test Driver"
    )
    db_session.add(user)
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=user.id,
        registration_plate=f"KA03CD{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.SEDAN,
    )
    db_session.add(vehicle)

    prop_id = uuid.uuid4()
    await db_session.execute(
        text("""
        INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES (:id, :owner_id, 'Koramangala Hub', 'COMMERCIAL_BUILDING', '80ft Road', 'Bengaluru', '560034', 'SRID=4326;POINT(77.6200 12.9350)', TRUE)
        """),
        {"id": prop_id, "owner_id": user.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"BAY-{uuid.uuid4().hex[:4].upper()}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.SEDAN,
        base_hourly_rate_paise=6000,
    )
    db_session.add(space)
    await db_session.commit()
    return user, vehicle, space


@pytest.mark.asyncio
async def test_two_tier_hold_expiration_engine(db_session, worker_test_space):
    """Verify Tier 1 batch sweep and Tier 2 inline opportunistic sweep."""
    user, vehicle, space = worker_test_space
    now = datetime.now(timezone.utc)

    # 1. Create an active hold that is NOT expired (expires in 400s)
    active_hold = SpaceReservation(
        parking_space_id=space.id,
        driver_id=user.id,
        vehicle_id=vehicle.id,
        time_window=asyncpg.Range(
            now, now + timedelta(hours=1), lower_inc=True, upper_inc=False
        ),
        reservation_type=ReservationTypeEnum.TEMPORARY_HOLD,
        status=ReservationStatusEnum.ACTIVE_HOLD,
        hold_expires_at=now + timedelta(seconds=400),
        booking_reference=f"GSP-{uuid.uuid4().hex[:8].upper()}",
    )
    db_session.add(active_hold)

    # 2. Create a stale hold that IS expired (expired 10s ago) on another space/ref
    stale_hold = SpaceReservation(
        parking_space_id=space.id,
        driver_id=user.id,
        vehicle_id=vehicle.id,
        time_window=asyncpg.Range(
            now + timedelta(hours=3),
            now + timedelta(hours=4),
            lower_inc=True,
            upper_inc=False,
        ),
        reservation_type=ReservationTypeEnum.TEMPORARY_HOLD,
        status=ReservationStatusEnum.ACTIVE_HOLD,
        hold_expires_at=now - timedelta(seconds=10),
        booking_reference=f"GSP-{uuid.uuid4().hex[:8].upper()}",
    )
    db_session.add(stale_hold)
    await db_session.commit()

    # 3. Execute Tier 1 batch sweep
    expired_count = await sweep_expired_holds_batch(db_session, batch_size=50)
    assert expired_count >= 1

    await db_session.refresh(active_hold)
    await db_session.refresh(stale_hold)

    # Active hold remains ACTIVE_HOLD
    assert active_hold.status == ReservationStatusEnum.ACTIVE_HOLD
    # Stale hold transitioned to EXPIRED_HOLD
    assert stale_hold.status == ReservationStatusEnum.EXPIRED_HOLD


@pytest.mark.asyncio
async def test_tier_2_inline_sweep_for_space(db_session, worker_test_space):
    """Verify Tier 2 inline sweep targets the specific parking space."""
    user, vehicle, space = worker_test_space
    now = datetime.now(timezone.utc)

    hold = SpaceReservation(
        parking_space_id=space.id,
        driver_id=user.id,
        vehicle_id=vehicle.id,
        time_window=asyncpg.Range(
            now, now + timedelta(hours=2), lower_inc=True, upper_inc=False
        ),
        reservation_type=ReservationTypeEnum.TEMPORARY_HOLD,
        status=ReservationStatusEnum.ACTIVE_HOLD,
        hold_expires_at=now - timedelta(seconds=5),
        booking_reference=f"GSP-{uuid.uuid4().hex[:8].upper()}",
    )
    db_session.add(hold)
    await db_session.commit()

    # Run Tier 2 inline sweep
    cleared = await sweep_expired_holds_for_space(db_session, space.id)
    assert cleared == 1

    await db_session.refresh(hold)
    assert hold.status == ReservationStatusEnum.EXPIRED_HOLD


@pytest.mark.asyncio
async def test_dpdpa_photo_purge_worker(db_session, worker_test_space):
    """Verify automated 7-day retention purge of gate proof photos under DPDPA 2023."""
    user, vehicle, space = worker_test_space
    now = datetime.now(timezone.utc)

    # 1. Fresh admission (taken today, expires in 7 days)
    fresh_admission = OfflineManualAdmission(
        property_id=space.property_id,
        guard_id=user.id,
        vehicle_plate="KA01AB1111",
        photo_s3_key="gate_photos/fresh_vehicle_photo.jpg",
        photo_purge_at=now + timedelta(days=7),
        reason_code="OFFLINE_NETWORK_OUTAGE",
        device_fingerprint="device_fp_01",
        event_signature="sig_01",
        admitted_at=now,
    )
    db_session.add(fresh_admission)

    # 2. Stale admission (taken 8 days ago, expired 1 day ago)
    stale_admission = OfflineManualAdmission(
        property_id=space.property_id,
        guard_id=user.id,
        vehicle_plate="KA01AB2222",
        photo_s3_key="gate_photos/stale_vehicle_photo_to_scrub.jpg",
        photo_purge_at=now - timedelta(days=1),
        reason_code="BARCODE_UNREADABLE",
        device_fingerprint="device_fp_02",
        event_signature="sig_02",
        admitted_at=now - timedelta(days=8),
    )
    db_session.add(stale_admission)
    await db_session.commit()

    # Execute DPDPA purge worker
    purged_count = await purge_expired_gate_photos(db_session, batch_size=50)
    assert purged_count >= 1

    await db_session.refresh(fresh_admission)
    await db_session.refresh(stale_admission)

    # Fresh admission preserves original key
    assert fresh_admission.photo_s3_key == "gate_photos/fresh_vehicle_photo.jpg"
    # Stale admission scrubbed with privacy tombstone
    assert stale_admission.photo_s3_key.startswith("PURGED:DPDPA_7DAY:")
