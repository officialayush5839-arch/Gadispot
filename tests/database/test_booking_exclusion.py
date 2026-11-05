"""
Tests for GiST Temporal Exclusion Booking Concurrency Constraints.
Verifies PostgreSQL 16 exclusion constraint prevent_overlapping_active_reservations
on (parking_space_id WITH =, time_window WITH &&) using canonical 14-table schema.
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from asyncpg.exceptions import ExclusionViolationError


async def create_test_driver(conn, phone="+919876543210"):
    row = await conn.fetchrow(
        """
        INSERT INTO users (phone_number, full_name, email)
        VALUES ($1, 'Test Driver', 'driver@test.com')
        ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
        RETURNING id
        """,
        phone,
    )
    driver_id = row["id"]
    await conn.execute(
        "INSERT INTO user_roles (user_id, role) VALUES ($1, 'DRIVER') ON CONFLICT DO NOTHING",
        driver_id,
    )
    return driver_id


async def create_test_vehicle(conn, driver_id, plate="KA01AB1234"):
    row = await conn.fetchrow(
        """
        INSERT INTO vehicles (driver_id, registration_plate, vehicle_category, make_model)
        VALUES ($1, $2, 'SEDAN', 'Test Honda City')
        ON CONFLICT (driver_id, registration_plate) DO UPDATE SET make_model = EXCLUDED.make_model
        RETURNING id
        """,
        driver_id,
        plate,
    )
    return row["id"]


async def create_test_owner_and_property(conn, phone="+919999999999"):
    row = await conn.fetchrow(
        """
        INSERT INTO users (phone_number, full_name, email)
        VALUES ($1, 'Test Owner', 'owner@test.com')
        ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
        RETURNING id
        """,
        phone,
    )
    owner_id = row["id"]
    await conn.execute(
        "INSERT INTO user_roles (user_id, role) VALUES ($1, 'OWNER') ON CONFLICT DO NOTHING",
        owner_id,
    )
    prop_row = await conn.fetchrow(
        """
        INSERT INTO properties (owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES ($1, 'Test Driveway', 'RESIDENTIAL_DRIVEWAY', '123 MG Road', 'Bengaluru', '560001', 'SRID=4326;POINT(77.5946 12.9716)', TRUE)
        RETURNING id
        """,
        owner_id,
    )
    return prop_row["id"]


async def create_parking_space(conn, property_id=None, label="Bay-A1"):
    if property_id is None:
        property_id = await create_test_owner_and_property(conn)
    row = await conn.fetchrow(
        """
        INSERT INTO parking_spaces (property_id, space_label, space_type, vehicle_category, base_hourly_rate_paise)
        VALUES ($1, $2, 'COVERED', 'SEDAN', 5000)
        ON CONFLICT (property_id, space_label) DO UPDATE SET base_hourly_rate_paise = EXCLUDED.base_hourly_rate_paise
        RETURNING id
        """,
        property_id,
        label,
    )
    return row["id"]


async def insert_reservation(
    conn,
    space_id,
    driver_id,
    vehicle_id,
    start_time,
    end_time,
    status="CONFIRMED",
    ref=None,
):
    if ref is None:
        ref = f"BK-{uuid.uuid4().hex[:8].upper()}"
    res_type = (
        "CONFIRMED_BOOKING"
        if status == "CONFIRMED"
        else ("TEMPORARY_HOLD" if status == "ACTIVE_HOLD" else "ACTIVE_SESSION")
    )
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(seconds=480))
        if status == "ACTIVE_HOLD"
        else None
    )
    await conn.execute(
        """
        INSERT INTO space_reservations (
            parking_space_id, driver_id, vehicle_id, time_window,
            reservation_type, status, hold_expires_at, booking_reference
        ) VALUES (
            $1, $2, $3, tstzrange($4, $5, '[)'),
            $6::reservation_type_enum, $7::reservation_status_enum, $8, $9
        )
        """,
        space_id,
        driver_id,
        vehicle_id,
        start_time,
        end_time,
        res_type,
        status,
        expires_at,
        ref,
    )


async def test_non_overlapping_bookings_succeed(pg_pool):
    """Adjacent, non-overlapping intervals on the same parking space must succeed."""
    async with pg_pool.acquire() as conn:
        prop_id = await create_test_owner_and_property(conn)
        space_id = await create_parking_space(conn, prop_id, "Bay-Adjacent")
        driver_id = await create_test_driver(conn, "+919876543201")
        vehicle_id = await create_test_vehicle(conn, driver_id, "KA01AB0001")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 11, 1, 14, 0, 0, tzinfo=timezone.utc)

        # Booking 1: [10:00, 12:00)
        await insert_reservation(
            conn, space_id, driver_id, vehicle_id, t1, t2, status="CONFIRMED"
        )

        # Booking 2: [12:00, 14:00) adjacent
        await insert_reservation(
            conn, space_id, driver_id, vehicle_id, t2, t3, status="ACTIVE_HOLD"
        )

        count = await conn.fetchval(
            "SELECT count(*) FROM space_reservations WHERE parking_space_id = $1",
            space_id,
        )
        assert count == 2


async def test_overlapping_bookings_same_space_fail(pg_pool):
    """Overlapping active holds or bookings on the same parking space must raise ExclusionViolationError."""
    async with pg_pool.acquire() as conn:
        prop_id = await create_test_owner_and_property(conn)
        space_id = await create_parking_space(conn, prop_id, "Bay-Overlap")
        driver_a = await create_test_driver(conn, "+919876543202")
        vehicle_a = await create_test_vehicle(conn, driver_a, "KA01AB0002")
        driver_b = await create_test_driver(conn, "+919876543203")
        vehicle_b = await create_test_vehicle(conn, driver_b, "KA01AB0003")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_mid = datetime(2026, 11, 1, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 11, 1, 13, 0, 0, tzinfo=timezone.utc)

        # Driver A holds [10:00, 12:00)
        await insert_reservation(
            conn, space_id, driver_a, vehicle_a, t1, t2, status="CONFIRMED"
        )

        # Driver B attempts to hold [11:00, 13:00) overlapping Driver A
        with pytest.raises(ExclusionViolationError) as exc_info:
            await insert_reservation(
                conn, space_id, driver_b, vehicle_b, t_mid, t3, status="ACTIVE_HOLD"
            )

        assert "prevent_overlapping_active_reservations" in str(exc_info.value)


async def test_overlapping_bookings_different_spaces_succeed(pg_pool):
    """Overlapping bookings on distinct parking spaces must not conflict."""
    async with pg_pool.acquire() as conn:
        prop_id = await create_test_owner_and_property(conn)
        space_1 = await create_parking_space(conn, prop_id, "Bay-1")
        space_2 = await create_parking_space(conn, prop_id, "Bay-2")
        driver_id = await create_test_driver(conn, "+919876543204")
        vehicle_id = await create_test_vehicle(conn, driver_id, "KA01AB0004")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        await insert_reservation(
            conn, space_1, driver_id, vehicle_id, t1, t2, status="CONFIRMED"
        )
        await insert_reservation(
            conn, space_2, driver_id, vehicle_id, t1, t2, status="CONFIRMED"
        )

        total = await conn.fetchval("SELECT count(*) FROM space_reservations")
        assert total == 2


async def test_cancelled_and_completed_reservations_do_not_block(pg_pool):
    """Inactive reservations (CANCELLED, EXPIRED_HOLD) must not block new bookings for the same window."""
    async with pg_pool.acquire() as conn:
        prop_id = await create_test_owner_and_property(conn)
        space_id = await create_parking_space(conn, prop_id, "Bay-Cancelled")
        driver_id = await create_test_driver(conn, "+919876543205")
        vehicle_id = await create_test_vehicle(conn, driver_id, "KA01AB0005")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 1. Expired hold
        await insert_reservation(
            conn, space_id, driver_id, vehicle_id, t1, t2, status="EXPIRED_HOLD"
        )

        # 2. Cancelled booking
        await insert_reservation(
            conn, space_id, driver_id, vehicle_id, t1, t2, status="CANCELLED_BY_DRIVER"
        )

        # 3. New confirmed booking on exact same window must succeed
        await insert_reservation(
            conn, space_id, driver_id, vehicle_id, t1, t2, status="CONFIRMED"
        )

        active_count = await conn.fetchval(
            "SELECT count(*) FROM space_reservations WHERE parking_space_id = $1 AND status = 'CONFIRMED'",
            space_id,
        )
        assert active_count == 1
