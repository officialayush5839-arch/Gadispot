"""Milestone 1 Empirical Adversarial Test Suite.

Stress-tests the Phase 03 Milestone 1 database schema, constraints, stored functions,
and migration capabilities:
1. chk_blackout_time check constraint (start_time < end_time, start_time == end_time, start_time > end_time).
2. Optimistic concurrency locking (property_authorizations.version default, not-null, and race condition simulation).
3. rejection_reason_code boundary (null, 64 chars, 65 char overflow).
4. Foreign key cascades (Property -> Documents, Blackouts, Authorizations; ParkingSpace -> Blackouts) and orphan rejection.
5. Stored function fn_check_vehicle_bay_compatibility edge cases (EV charging requirement, exact dimensional boundaries).
6. 3D clearance margins (299mm vs 300mm length, 399mm vs 400mm width, 99mm vs 100mm height).
7. Programmatic migration downgrade/upgrade cycle with deep artifact inspection.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from app.models.enums import AuthorizationStatusEnum
from app.models.properties import PropertyAuthorization
from app.models.users import User
from app.services.compatibility_service import (
    CompatibilityService,
    SpaceDimensions,
    VehicleDimensions,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


async def _create_test_owner(db_session, suffix="adv") -> User:
    """Helper to insert an owner user."""
    owner = User(
        phone_number=f"+91987654{hash(suffix) % 900 + 100:03d}",
        full_name=f"Owner {suffix}",
        email=f"owner_{suffix}_{uuid.uuid4().hex[:6]}@test.com",
    )
    db_session.add(owner)
    await db_session.flush()
    return owner


async def _create_test_property(db_session, owner_id: uuid.UUID) -> uuid.UUID:
    """Helper to insert a property using raw SQL to support fallback domain."""
    prop_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO properties (
                id, owner_id, title, property_type, address_line, city, postal_code, location, is_active
            ) VALUES (
                :id, :owner_id, 'Adversarial Test Plaza', 'COMMERCIAL_BUILDING',
                '123 Adversarial Lane', 'Bengaluru', '560001',
                'SRID=4326;POINT(77.5946 12.9716)', FALSE
            )
            """
        ),
        {"id": prop_id, "owner_id": owner_id},
    )
    await db_session.flush()
    return prop_id


# =============================================================================
# 1. Check Constraint: chk_blackout_time
# =============================================================================


@pytest.mark.asyncio
async def test_blackout_schedule_time_check_constraint_valid(db_session):
    """Verify that start_time < end_time successfully persists in blackout_schedules."""
    owner = await _create_test_owner(db_session, "time_ok")
    prop_id = await _create_test_property(db_session, owner.id)

    now = datetime.now(timezone.utc)
    blackout_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO blackout_schedules (
                id, property_id, start_time, end_time, reason, is_active
            ) VALUES (
                :id, :prop_id, :st, :et, 'Valid interval', TRUE
            )
            """
        ),
        {
            "id": blackout_id,
            "prop_id": prop_id,
            "st": now,
            "et": now + timedelta(hours=2),
        },
    )
    await db_session.commit()

    res = await db_session.execute(
        text("SELECT COUNT(*) FROM blackout_schedules WHERE id = :id"),
        {"id": blackout_id},
    )
    assert res.scalar() == 1


@pytest.mark.asyncio
async def test_blackout_schedule_time_check_constraint_equal_times_rejected(db_session):
    """Verify chk_blackout_time rejects start_time == end_time."""
    owner = await _create_test_owner(db_session, "time_eq")
    prop_id = await _create_test_property(db_session, owner.id)

    now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO blackout_schedules (
                    id, property_id, start_time, end_time, reason, is_active
                ) VALUES (
                    gen_random_uuid(), :prop_id, :t, :t, 'Equal times', TRUE
                )
                """
            ),
            {"prop_id": prop_id, "t": now},
        )
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_blackout_schedule_time_check_constraint_inverted_times_rejected(
    db_session,
):
    """Verify chk_blackout_time rejects start_time > end_time."""
    owner = await _create_test_owner(db_session, "time_inv")
    prop_id = await _create_test_property(db_session, owner.id)

    now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO blackout_schedules (
                    id, property_id, start_time, end_time, reason, is_active
                ) VALUES (
                    gen_random_uuid(), :prop_id, :st, :et, 'Inverted times', TRUE
                )
                """
            ),
            {"prop_id": prop_id, "st": now + timedelta(hours=2), "et": now},
        )
        await db_session.commit()
    await db_session.rollback()


# =============================================================================
# 2. Optimistic Concurrency Locking: property_authorizations.version
# =============================================================================


@pytest.mark.asyncio
async def test_property_authorization_version_default_and_not_null(db_session):
    """Verify version defaults to 1 and cannot be set to NULL."""
    owner = await _create_test_owner(db_session, "ver_def")
    prop_id = await _create_test_property(db_session, owner.id)

    auth_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO property_authorizations (id, property_id, status)
            VALUES (:id, :prop_id, 'DRAFT')
            """
        ),
        {"id": auth_id, "prop_id": prop_id},
    )
    await db_session.commit()

    res = await db_session.execute(
        text("SELECT version FROM property_authorizations WHERE id = :id"),
        {"id": auth_id},
    )
    assert res.scalar() == 1

    # Setting version to NULL must violate NOT NULL constraint
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("UPDATE property_authorizations SET version = NULL WHERE id = :id"),
            {"id": auth_id},
        )
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_optimistic_locking_concurrency_race_simulation(db_session):
    """Adversarially simulate concurrent reviewers competing on the same property authorization version."""
    owner = await _create_test_owner(db_session, "ver_race")
    prop_id = await _create_test_property(db_session, owner.id)

    auth_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO property_authorizations (id, property_id, status, version)
            VALUES (:id, :prop_id, 'PENDING_REVIEW', 1)
            """
        ),
        {"id": auth_id, "prop_id": prop_id},
    )
    await db_session.commit()

    # Reviewer A and Reviewer B both read version = 1
    # Reviewer A successfully approves first
    res_a = await db_session.execute(
        text(
            """
            UPDATE property_authorizations
            SET status = 'APPROVED', version = version + 1
            WHERE id = :id AND version = 1
            """
        ),
        {"id": auth_id},
    )
    assert res_a.rowcount == 1
    await db_session.commit()

    # Reviewer B attempts rejection with stale version = 1 -> Must match 0 rows (triggers HTTP 409)
    res_b = await db_session.execute(
        text(
            """
            UPDATE property_authorizations
            SET status = 'REJECTED', version = version + 1, rejection_reason_code = 'BLURRY_DOC'
            WHERE id = :id AND version = 1
            """
        ),
        {"id": auth_id},
    )
    assert res_b.rowcount == 0
    await db_session.rollback()

    # Verify current database state reflects Reviewer A's decision with version = 2
    res_curr = await db_session.execute(
        text("SELECT status, version FROM property_authorizations WHERE id = :id"),
        {"id": auth_id},
    )
    row = res_curr.fetchone()
    assert row[0] == "APPROVED"
    assert row[1] == 2


# =============================================================================
# 3. Column Boundaries: rejection_reason_code
# =============================================================================


@pytest.mark.asyncio
async def test_rejection_reason_code_boundary_64_and_overflow(db_session):
    """Verify rejection_reason_code allows NULL, exactly 64 characters, and rejects 65 characters."""
    owner = await _create_test_owner(db_session, "rej_bnd")
    prop_id = await _create_test_property(db_session, owner.id)

    auth = PropertyAuthorization(
        property_id=prop_id,
        status=AuthorizationStatusEnum.DRAFT,
        version=1,
        rejection_reason_code=None,
    )
    db_session.add(auth)
    await db_session.commit()
    assert auth.rejection_reason_code is None

    # Exact boundary: 64 chars
    code_64 = "A" * 64
    auth.rejection_reason_code = code_64
    await db_session.commit()
    await db_session.refresh(auth)
    assert auth.rejection_reason_code == code_64

    # Overflow: 65 chars must fail
    code_65 = "A" * 65
    auth.rejection_reason_code = code_65
    with pytest.raises((DBAPIError, IntegrityError)):
        await db_session.commit()
    await db_session.rollback()


# =============================================================================
# 4. Foreign Key Cascades & Isolation
# =============================================================================


@pytest.mark.asyncio
async def test_property_cascade_delete_cleans_all_child_records(db_session):
    """Verify deleting a property cascades to documents, blackouts, and authorizations."""
    owner = await _create_test_owner(db_session, "casc_all")
    prop_id = await _create_test_property(db_session, owner.id)

    # 1. Insert authorization
    auth_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO property_authorizations (id, property_id, status, version)
            VALUES (:id, :prop_id, 'DRAFT', 1)
            """
        ),
        {"id": auth_id, "prop_id": prop_id},
    )

    # 2. Insert document
    doc_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO property_documents (
                id, property_id, document_type, file_name, s3_key, content_type, file_size_bytes, is_verified
            ) VALUES (
                :id, :prop_id, 'PROPERTY_TAX_RECEIPT', 'tax.pdf', 'docs/tax.pdf', 'application/pdf', 1024, FALSE
            )
            """
        ),
        {"id": doc_id, "prop_id": prop_id},
    )

    # 3. Insert blackout
    blackout_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db_session.execute(
        text(
            """
            INSERT INTO blackout_schedules (
                id, property_id, start_time, end_time, reason, is_active
            ) VALUES (
                :id, :prop_id, :st, :et, 'Holiday Block', TRUE
            )
            """
        ),
        {
            "id": blackout_id,
            "prop_id": prop_id,
            "st": now,
            "et": now + timedelta(days=1),
        },
    )
    await db_session.commit()

    # Delete property directly
    await db_session.execute(
        text("DELETE FROM properties WHERE id = :id"), {"id": prop_id}
    )
    await db_session.commit()

    # All three child records must be cascade deleted
    res_auth = await db_session.execute(
        text("SELECT COUNT(*) FROM property_authorizations WHERE id = :id"),
        {"id": auth_id},
    )
    assert res_auth.scalar() == 0

    res_doc = await db_session.execute(
        text("SELECT COUNT(*) FROM property_documents WHERE id = :id"), {"id": doc_id}
    )
    assert res_doc.scalar() == 0

    res_blk = await db_session.execute(
        text("SELECT COUNT(*) FROM blackout_schedules WHERE id = :id"),
        {"id": blackout_id},
    )
    assert res_blk.scalar() == 0


@pytest.mark.asyncio
async def test_orphaned_document_and_blackout_foreign_key_violations(db_session):
    """Verify inserting a document or blackout with non-existent property_id is rejected."""
    orphan_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Orphan document
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO property_documents (
                    id, property_id, document_type, file_name, s3_key, content_type, file_size_bytes
                ) VALUES (
                    gen_random_uuid(), :orphan, 'PROPERTY_TAX_RECEIPT', 'doc.pdf', 'key', 'application/pdf', 500
                )
                """
            ),
            {"orphan": orphan_id},
        )
        await db_session.commit()
    await db_session.rollback()

    # Orphan blackout
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO blackout_schedules (
                    id, property_id, start_time, end_time
                ) VALUES (
                    gen_random_uuid(), :orphan, :st, :et
                )
                """
            ),
            {"orphan": orphan_id, "st": now, "et": now + timedelta(hours=1)},
        )
        await db_session.commit()
    await db_session.rollback()


# =============================================================================
# 5. Stored Function: fn_check_vehicle_bay_compatibility
# =============================================================================


@pytest.mark.asyncio
async def test_stored_function_fn_check_vehicle_bay_compatibility_matrix(db_session):
    """Adversarially test fn_check_vehicle_bay_compatibility across all vehicle categories and edge boundaries."""

    async def check_compat(
        cat: str,
        bay_type: str,
        l: float,
        w: float,
        h: float,
        bay_ev: bool,
        req_ev: bool,
    ) -> bool:
        stmt = f"""
            SELECT fn_check_vehicle_bay_compatibility(
                '{cat}'::vehicle_category_enum,
                :bay_type,
                :l, :w, :h,
                :bay_ev, :req_ev
            )
        """
        res = await db_session.execute(
            text(stmt),
            {
                "bay_type": bay_type,
                "l": Decimal(str(l)),
                "w": Decimal(str(w)),
                "h": Decimal(str(h)),
                "bay_ev": bay_ev,
                "req_ev": req_ev,
            },
        )
        return bool(res.scalar())

    # 1. EV Requirement: If driver requires EV, bay MUST have EV
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 5.0, 2.0, 1.8, False, True) is False
    )
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 5.0, 2.0, 1.8, True, True) is True
    )
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 5.0, 2.0, 1.8, False, False) is True
    )
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 5.0, 2.0, 1.8, True, False) is True
    )

    # 2. TWO_WHEELER (min: L >= 2.0, W >= 0.8; bay_type in TWO_WHEELER, BIKE_BAY)
    assert (
        await check_compat("TWO_WHEELER", "TWO_WHEELER", 2.00, 0.80, 1.2, False, False)
        is True
    )
    assert (
        await check_compat("TWO_WHEELER", "BIKE_BAY", 2.00, 0.80, 1.2, False, False)
        is True
    )
    assert (
        await check_compat("TWO_WHEELER", "TWO_WHEELER", 1.99, 0.80, 1.2, False, False)
        is False
    )
    assert (
        await check_compat("TWO_WHEELER", "TWO_WHEELER", 2.00, 0.79, 1.2, False, False)
        is False
    )
    assert (
        await check_compat("TWO_WHEELER", "STANDARD_CAR", 2.50, 1.00, 1.2, False, False)
        is False
    )

    # 3. EV_TWO_WHEELER (same physical constraints as TWO_WHEELER + EV support)
    assert (
        await check_compat("EV_TWO_WHEELER", "BIKE_BAY", 2.00, 0.80, 1.2, True, True)
        is True
    )
    assert (
        await check_compat("EV_TWO_WHEELER", "BIKE_BAY", 2.00, 0.80, 1.2, False, True)
        is False
    )
    assert (
        await check_compat("EV_TWO_WHEELER", "BIKE_BAY", 1.99, 0.80, 1.2, True, False)
        is False
    )

    # 4. HATCHBACK (min: L >= 3.8, W >= 1.7; bay_type in COMPACT_CAR, STANDARD_CAR, LARGE_CAR, SUV_BAY)
    assert (
        await check_compat("HATCHBACK", "COMPACT_CAR", 3.80, 1.70, 1.5, False, False)
        is True
    )
    assert (
        await check_compat("HATCHBACK", "STANDARD_CAR", 3.80, 1.70, 1.5, False, False)
        is True
    )
    assert (
        await check_compat("HATCHBACK", "COMPACT_CAR", 3.79, 1.70, 1.5, False, False)
        is False
    )
    assert (
        await check_compat("HATCHBACK", "COMPACT_CAR", 3.80, 1.69, 1.5, False, False)
        is False
    )
    assert (
        await check_compat("HATCHBACK", "TWO_WHEELER", 4.00, 2.00, 1.5, False, False)
        is False
    )

    # 5. SEDAN (min: L >= 4.5, W >= 1.8; bay_type in STANDARD_CAR, LARGE_CAR, SUV_BAY)
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 4.50, 1.80, 1.5, False, False)
        is True
    )
    assert (
        await check_compat("SEDAN", "LARGE_CAR", 4.50, 1.80, 1.5, False, False) is True
    )
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 4.49, 1.80, 1.5, False, False)
        is False
    )
    assert (
        await check_compat("SEDAN", "STANDARD_CAR", 4.50, 1.79, 1.5, False, False)
        is False
    )
    assert (
        await check_compat("SEDAN", "COMPACT_CAR", 4.80, 2.00, 1.5, False, False)
        is False
    )  # COMPACT rejected

    # 6. SUV & EV_FOUR_WHEELER (min: L >= 4.8, W >= 1.9, H >= 2.0; bay_type in LARGE_CAR, SUV_BAY)
    assert await check_compat("SUV", "SUV_BAY", 4.80, 1.90, 2.00, False, False) is True
    assert (
        await check_compat("SUV", "LARGE_CAR", 4.80, 1.90, 2.00, False, False) is True
    )
    assert await check_compat("SUV", "SUV_BAY", 4.79, 1.90, 2.00, False, False) is False
    assert await check_compat("SUV", "SUV_BAY", 4.80, 1.89, 2.00, False, False) is False
    assert await check_compat("SUV", "SUV_BAY", 4.80, 1.90, 1.99, False, False) is False
    assert (
        await check_compat("SUV", "STANDARD_CAR", 5.00, 2.20, 2.20, False, False)
        is False
    )  # STANDARD rejected

    assert (
        await check_compat("EV_FOUR_WHEELER", "SUV_BAY", 4.80, 1.90, 2.00, True, True)
        is True
    )
    assert (
        await check_compat("EV_FOUR_WHEELER", "SUV_BAY", 4.80, 1.90, 2.00, False, True)
        is False
    )

    # 7. Non-positive dimensions rejected
    assert (
        await check_compat("HATCHBACK", "STANDARD_CAR", 0.0, 0.0, 0.0, False, False)
        is False
    )
    assert (
        await check_compat("HATCHBACK", "STANDARD_CAR", -4.0, -2.0, -1.5, False, False)
        is False
    )


# =============================================================================
# 6. Physical 3D Clearance Boundary Margins (CompatibilityService)
# =============================================================================


def test_clearance_margins_299mm_vs_300mm_length():
    """Verify length clearance boundary: 299mm fails, 300mm passes (+300mm required)."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)

    # 299mm clearance (space length 4799mm)
    space_299 = SpaceDimensions(length_mm=4799, width_mm=2300, height_mm=2000)
    res_299 = CompatibilityService.evaluate_compatibility(vehicle, space_299)
    assert res_299.is_compatible is False
    assert res_299.length_clearance_mm == 299
    assert any("Insufficient length clearance" in r for r in res_299.rejection_reasons)

    # 300mm clearance (space length 4800mm)
    space_300 = SpaceDimensions(length_mm=4800, width_mm=2300, height_mm=2000)
    res_300 = CompatibilityService.evaluate_compatibility(vehicle, space_300)
    assert res_300.is_compatible is True
    assert res_300.length_clearance_mm == 300


def test_clearance_margins_399mm_vs_400mm_width():
    """Verify width clearance boundary: 399mm fails, 400mm passes (+400mm required)."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)

    # 399mm clearance (space width 2199mm)
    space_399 = SpaceDimensions(length_mm=4900, width_mm=2199, height_mm=2000)
    res_399 = CompatibilityService.evaluate_compatibility(vehicle, space_399)
    assert res_399.is_compatible is False
    assert res_399.width_clearance_mm == 399
    assert any("Insufficient width clearance" in r for r in res_399.rejection_reasons)

    # 400mm clearance (space width 2200mm)
    space_400 = SpaceDimensions(length_mm=4900, width_mm=2200, height_mm=2000)
    res_400 = CompatibilityService.evaluate_compatibility(vehicle, space_400)
    assert res_400.is_compatible is True
    assert res_400.width_clearance_mm == 400


def test_clearance_margins_99mm_vs_100mm_height():
    """Verify height clearance boundary: 99mm fails, 100mm passes (+100mm required)."""
    vehicle = VehicleDimensions(length_mm=4500, width_mm=1800, height_mm=1500)

    # 99mm clearance (space height 1599mm)
    space_99 = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=1599)
    res_99 = CompatibilityService.evaluate_compatibility(vehicle, space_99)
    assert res_99.is_compatible is False
    assert res_99.height_clearance_mm == 99
    assert any("Insufficient height clearance" in r for r in res_99.rejection_reasons)

    # 100mm clearance (space height 1600mm)
    space_100 = SpaceDimensions(length_mm=4900, width_mm=2300, height_mm=1600)
    res_100 = CompatibilityService.evaluate_compatibility(vehicle, space_100)
    assert res_100.is_compatible is True
    assert res_100.height_clearance_mm == 100


# =============================================================================
# 7. Programmatic Migration Downgrade/Upgrade Cycle with Deep Inspection
# =============================================================================


def test_programmatic_migration_downgrade_and_upgrade_cycle_with_artifact_inspection():
    """Verify clean downgrade to 006 removes M1 artifacts, and upgrade to 007 restores them."""
    import asyncio
    import os

    import asyncpg

    alembic_cfg = Config("backend/alembic.ini")

    # Step 1: Programmatic downgrade from 007 to 006
    command.downgrade(alembic_cfg, "006_revocation_and_mfa")

    # Async helper to inspect PostgreSQL schema at revision 006
    async def inspect_downgraded_state():
        test_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/gadispot_test",
        )
        conn = await asyncpg.connect(test_url)
        try:
            # 1. property_documents and blackout_schedules tables MUST NOT exist
            tables = await conn.fetch(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('property_documents', 'blackout_schedules')
                """
            )
            assert len(tables) == 0, f"Dangling tables found after downgrade: {tables}"

            # 2. version, rejection_reason_code, updated_at MUST NOT exist on property_authorizations
            cols = await conn.fetch(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'property_authorizations'
                  AND column_name IN ('version', 'rejection_reason_code', 'updated_at')
                """
            )
            assert len(cols) == 0, f"Dangling columns found after downgrade: {cols}"

            # 3. fn_check_vehicle_bay_compatibility MUST NOT exist
            funcs = await conn.fetch(
                """
                SELECT proname FROM pg_proc WHERE proname = 'fn_check_vehicle_bay_compatibility'
                """
            )
            assert len(funcs) == 0, (
                f"Dangling stored function found after downgrade: {funcs}"
            )
        finally:
            await conn.close()

    asyncio.run(inspect_downgraded_state())

    # Step 2: Programmatic upgrade back to head (007)
    command.upgrade(alembic_cfg, "head")

    # Async helper to inspect PostgreSQL schema at revision 007
    async def inspect_upgraded_state():
        test_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/gadispot_test",
        )
        conn = await asyncpg.connect(test_url)
        try:
            # 1. property_documents and blackout_schedules tables MUST exist
            tables = await conn.fetch(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('property_documents', 'blackout_schedules')
                """
            )
            found_tables = {r["table_name"] for r in tables}
            assert found_tables == {"property_documents", "blackout_schedules"}

            # 2. version, rejection_reason_code, updated_at MUST exist on property_authorizations
            cols = await conn.fetch(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'property_authorizations'
                  AND column_name IN ('version', 'rejection_reason_code', 'updated_at')
                """
            )
            found_cols = {r["column_name"] for r in cols}
            assert found_cols == {"version", "rejection_reason_code", "updated_at"}

            # 3. fn_check_vehicle_bay_compatibility MUST exist
            funcs = await conn.fetch(
                """
                SELECT proname FROM pg_proc WHERE proname = 'fn_check_vehicle_bay_compatibility'
                """
            )
            assert len(funcs) >= 1
        finally:
            await conn.close()

    asyncio.run(inspect_upgraded_state())
