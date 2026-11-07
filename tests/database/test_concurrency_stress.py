"""Concurrency and Deadlock Stress Testing Suite (TSK-P7-003).

Runs 50 concurrent booking hold attempts against the identical parking space and time window.
Verifies that:
1. Exactly 1 hold succeeds (HTTP 201 / active hold inserted).
2. Exactly 49 attempts are rejected by PostgreSQL 16 exclusion constraint (23P01).
3. Zero deadlocks occur under high load.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from asyncpg.exceptions import DeadlockDetectedError, ExclusionViolationError


@pytest.mark.asyncio
async def test_50_concurrent_holds_exactly_one_wins(pg_pool):
    """50 concurrent workers attempt to reserve the same space for [10:00, 12:00)."""
    async with pg_pool.acquire() as conn:
        # 1. Create property and space
        owner_row = await conn.fetchrow(
            """
            INSERT INTO users (phone_number, full_name, email)
            VALUES ($1, 'Stress Owner', 'stress_owner@test.com')
            ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
            RETURNING id
            """,
            "+919800000001",
        )
        owner_id = owner_row["id"]

        prop_row = await conn.fetchrow(
            """
            INSERT INTO properties (owner_id, title, property_type, address_line, city, postal_code, location)
            VALUES ($1, 'Stress Prop', 'RESIDENTIAL_DRIVEWAY', '123 Stress St', 'Bengaluru', '560001', 'SRID=4326;POINT(77.5946 12.9716)')
            RETURNING id
            """,
            owner_id,
        )
        prop_id = prop_row["id"]

        space_row = await conn.fetchrow(
            """
            INSERT INTO parking_spaces (property_id, space_label, space_type, vehicle_category, base_hourly_rate_paise)
            VALUES ($1, 'STRESS-BAY-01', 'COVERED', 'SEDAN', 4000)
            RETURNING id
            """,
            prop_id,
        )
        space_id = space_row["id"]

        # Create driver and vehicle
        driver_row = await conn.fetchrow(
            """
            INSERT INTO users (phone_number, full_name, email)
            VALUES ($1, 'Stress Driver', 'stress_driver@test.com')
            ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
            RETURNING id
            """,
            "+919800000002",
        )
        driver_id = driver_row["id"]

        veh_row = await conn.fetchrow(
            """
            INSERT INTO vehicles (driver_id, registration_plate, vehicle_category, make_model)
            VALUES ($1, 'KA01ST0001', 'SEDAN', 'Stress Vehicle')
            ON CONFLICT (driver_id, registration_plate) DO UPDATE SET make_model = EXCLUDED.make_model
            RETURNING id
            """,
            driver_id,
        )
        vehicle_id = veh_row["id"]

    start_time = datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
    time_window = asyncpg.Range(start_time, end_time, lower_inc=True, upper_inc=False)
    hold_expiry = datetime.now(timezone.utc) + timedelta(seconds=480)

    succeeded = []
    excluded = []
    deadlocks = []
    other_errors = []

    async def attempt_hold(worker_id: int):
        hold_uuid = uuid.uuid4()
        booking_ref = f"BK-STR-{worker_id}-{hold_uuid.hex[:6]}"
        try:
            async with pg_pool.acquire() as worker_conn:
                await worker_conn.execute(
                    """
                    INSERT INTO space_reservations (
                        id, parking_space_id, driver_id, vehicle_id,
                        time_window, reservation_type, status, booking_reference, hold_expires_at
                    )
                    VALUES ($1, $2, $3, $4, $5, 'TEMPORARY_HOLD', 'ACTIVE_HOLD', $6, $7)
                    """,
                    hold_uuid,
                    space_id,
                    driver_id,
                    vehicle_id,
                    time_window,
                    booking_ref,
                    hold_expiry,
                )
                succeeded.append(worker_id)
        except ExclusionViolationError:
            excluded.append(worker_id)
        except DeadlockDetectedError:
            deadlocks.append(worker_id)
        except Exception as exc:
            other_errors.append((worker_id, str(exc)))

    # Launch 50 workers concurrently
    tasks = [attempt_hold(i) for i in range(50)]
    await asyncio.gather(*tasks)

    # Invariants:
    # 1. Exactly 1 hold must succeed
    assert len(succeeded) == 1, f"Expected 1 winner, got {len(succeeded)}: {succeeded}"
    # 2. Exactly 49 holds must be excluded by GiST temporal constraint
    assert len(excluded) == 49, f"Expected 49 excluded, got {len(excluded)}"
    # 3. ZERO deadlocks
    assert len(deadlocks) == 0, f"Deadlocks detected: {deadlocks}"
    # 4. Zero unexpected errors
    assert len(other_errors) == 0, f"Unexpected errors: {other_errors}"
