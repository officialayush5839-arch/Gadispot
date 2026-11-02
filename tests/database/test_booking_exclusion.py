"""
Tests for GiST Temporal Exclusion Booking Concurrency Constraints.
Verifies PostgreSQL 16 exclusion constraint prevent_overlapping_active_reservations
on (parking_space_id WITH =, time_window WITH &&).
"""

from datetime import datetime, timezone
import pytest
from asyncpg.exceptions import ExclusionViolationError

async def create_parking_space(conn, name="Bay-A1"):
    row = await conn.fetchrow(
        "INSERT INTO parking_spaces (name) VALUES ($1) RETURNING id",
        name
    )
    return row["id"]

async def test_non_overlapping_bookings_succeed(pg_pool):
    """Adjacent, non-overlapping intervals on the same parking space must succeed."""
    async with pg_pool.acquire() as conn:
        space_id = await create_parking_space(conn, "Bay-Adjacent")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 11, 1, 14, 0, 0, tzinfo=timezone.utc)

        # Booking 1: [10:00, 12:00)
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CONFIRMED')
            """,
            space_id, t1, t2
        )

        # Booking 2: [12:00, 14:00) adjacent
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'ACTIVE_HOLD')
            """,
            space_id, t2, t3
        )

        count = await conn.fetchval(
            "SELECT count(*) FROM space_reservations WHERE parking_space_id = $1",
            space_id
        )
        assert count == 2

async def test_overlapping_bookings_same_space_fail(pg_pool):
    """Overlapping active holds or bookings on the same parking space must raise ExclusionViolationError."""
    async with pg_pool.acquire() as conn:
        space_id = await create_parking_space(conn, "Bay-Overlap")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_mid = datetime(2026, 11, 1, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 11, 1, 13, 0, 0, tzinfo=timezone.utc)

        # Driver A holds [10:00, 12:00)
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CONFIRMED')
            """,
            space_id, t1, t2
        )

        # Driver B attempts to hold [11:00, 13:00) overlapping Driver A
        with pytest.raises(ExclusionViolationError) as exc_info:
            await conn.execute(
                """
                INSERT INTO space_reservations (parking_space_id, time_window, status)
                VALUES ($1, tstzrange($2, $3, '[)'), 'ACTIVE_HOLD')
                """,
                space_id, t_mid, t3
            )

        assert "prevent_overlapping_active_reservations" in str(exc_info.value)

async def test_overlapping_bookings_different_spaces_succeed(pg_pool):
    """Overlapping bookings on distinct parking spaces must not conflict."""
    async with pg_pool.acquire() as conn:
        space_1 = await create_parking_space(conn, "Bay-1")
        space_2 = await create_parking_space(conn, "Bay-2")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CONFIRMED')
            """,
            space_1, t1, t2
        )

        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CONFIRMED')
            """,
            space_2, t1, t2
        )

        total = await conn.fetchval("SELECT count(*) FROM space_reservations")
        assert total == 2

async def test_cancelled_and_completed_reservations_do_not_block(pg_pool):
    """Inactive reservations (CANCELLED, RELEASED_EXPIRED) must not block new bookings for the same window."""
    async with pg_pool.acquire() as conn:
        space_id = await create_parking_space(conn, "Bay-Cancelled")

        t1 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 1. Expired hold
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'RELEASED_EXPIRED')
            """,
            space_id, t1, t2
        )

        # 2. Cancelled booking
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CANCELLED_BY_DRIVER')
            """,
            space_id, t1, t2
        )

        # 3. New confirmed booking on exact same window must succeed
        await conn.execute(
            """
            INSERT INTO space_reservations (parking_space_id, time_window, status)
            VALUES ($1, tstzrange($2, $3, '[)'), 'CONFIRMED')
            """,
            space_id, t1, t2
        )

        active_count = await conn.fetchval(
            "SELECT count(*) FROM space_reservations WHERE parking_space_id = $1 AND status = 'CONFIRMED'",
            space_id
        )
        assert active_count == 1
