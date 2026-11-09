"""Database migration, schema integrity, and constraint verification tests (TSK-P7-002)."""

import uuid

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text


def test_alembic_script_directory_and_head_revisions():
    """Verify Alembic configuration and revision history chain."""
    alembic_cfg = Config("backend/alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    # Verify heads
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] in (
        "003_demo_payments",
        "004_identity_and_sessions",
        "005_totp_hardening",
        "006_revocation_and_mfa",
        "007_phase03_inventory_and_documents",
    )

    # Verify revision chain: 007 -> 006 -> 005 -> 004 -> 003 -> 002 -> 001 -> None
    rev_007 = script.get_revision("007_phase03_inventory_and_documents")
    if rev_007 is not None:
        assert rev_007.down_revision == "006_revocation_and_mfa"

    rev_006 = script.get_revision("006_revocation_and_mfa")
    if rev_006 is not None:
        assert rev_006.down_revision == "005_totp_hardening"

    rev_005 = script.get_revision("005_totp_hardening")
    if rev_005 is not None:
        assert rev_005.down_revision == "004_identity_and_sessions"

    rev_004 = script.get_revision("004_identity_and_sessions")
    if rev_004 is not None:
        assert rev_004.down_revision == "003_demo_payments"

    rev_003 = script.get_revision("003_demo_payments")
    assert rev_003 is not None
    assert rev_003.down_revision == "002_audit_events"

    rev_002 = script.get_revision("002_audit_events")
    assert rev_002 is not None
    assert rev_002.down_revision == "001_initial_schema"

    rev_001 = script.get_revision("001_initial_schema")
    assert rev_001 is not None
    assert rev_001.down_revision is None


def test_alembic_migration_007_downgrade_and_upgrade_cycle():
    """Verify that migration 007 can be cleanly downgraded to 006 and upgraded back to head."""
    from alembic import command

    alembic_cfg = Config("backend/alembic.ini")

    # Cleanly downgrade 007 -> 006
    command.downgrade(alembic_cfg, "006_revocation_and_mfa")

    # Cleanly upgrade 006 -> 007 (head)
    command.upgrade(alembic_cfg, "head")


@pytest.mark.asyncio
async def test_canonical_tables_exist(db_session):
    """Verify all canonical tables are present in the active PostgreSQL database."""
    expected_tables = {
        "users",
        "user_roles",
        "vehicles",
        "properties",
        "property_authorizations",
        "property_documents",
        "parking_spaces",
        "operating_schedules",
        "blackout_schedules",
        "space_reservations",
        "ledger_accounts",
        "journal_entries",
        "journal_lines",
        "access_credentials",
        "offline_manual_admissions",
        "payment_webhook_events",
        "outbox_events",
        "audit_events",
        "payments",
        "user_sessions",
        "revoked_tokens",
    }

    result = await db_session.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
    )
    existing_tables = {row[0] for row in result.fetchall()}
    missing_tables = expected_tables - existing_tables
    assert not missing_tables, f"Missing canonical database tables: {missing_tables}"


@pytest.mark.asyncio
async def test_enum_types_registered(db_session):
    """Verify canonical enums exist in PostgreSQL pg_type."""
    expected_enums = {
        "user_role_enum",
        "property_type_enum",
        "authorization_status_enum",
        "document_type_enum",
        "vehicle_category_enum",
        "space_type_enum",
        "reservation_type_enum",
        "reservation_status_enum",
        "refund_status_enum",
        "token_type_enum",
        "token_status_enum",
        "account_type_enum",
        "journal_status_enum",
        "entry_side_enum",
        "payment_status_enum",
        "payment_provider_enum",
    }

    result = await db_session.execute(
        text(
            """
            SELECT typname
            FROM pg_type
            WHERE typtype = 'e'
            """
        )
    )
    existing_enums = {row[0] for row in result.fetchall()}
    missing_enums = expected_enums - existing_enums
    assert not missing_enums, f"Missing PostgreSQL enum types: {missing_enums}"


@pytest.mark.asyncio
async def test_fn_check_vehicle_bay_compatibility_stored_function(db_session):
    """Verify stored function fn_check_vehicle_bay_compatibility executes correctly in PostgreSQL."""
    # EV requirement rejected if bay does not have EV
    res = await db_session.execute(
        text(
            """
            SELECT fn_check_vehicle_bay_compatibility(
                'EV_FOUR_WHEELER'::vehicle_category_enum,
                'SUV_BAY',
                5.0, 2.0, 2.2,
                false, -- bay has no ev
                true   -- driver requires ev
            )
            """
        )
    )
    assert res.scalar() is False

    # EV requirement satisfied
    res = await db_session.execute(
        text(
            """
            SELECT fn_check_vehicle_bay_compatibility(
                'EV_FOUR_WHEELER'::vehicle_category_enum,
                'SUV_BAY',
                5.0, 2.0, 2.2,
                true,  -- bay has ev
                true   -- driver requires ev
            )
            """
        )
    )
    assert res.scalar() is True

    # Hatchback dimension checks
    # Valid hatchback
    res = await db_session.execute(
        text(
            """
            SELECT fn_check_vehicle_bay_compatibility(
                'HATCHBACK'::vehicle_category_enum,
                'COMPACT_CAR',
                3.9, 1.8, 1.6,
                false, false
            )
            """
        )
    )
    assert res.scalar() is True

    # Too short for hatchback (< 3.8m)
    res = await db_session.execute(
        text(
            """
            SELECT fn_check_vehicle_bay_compatibility(
                'HATCHBACK'::vehicle_category_enum,
                'COMPACT_CAR',
                3.5, 1.8, 1.6,
                false, false
            )
            """
        )
    )
    assert res.scalar() is False

    # Two wheeler dimension checks
    res = await db_session.execute(
        text(
            """
            SELECT fn_check_vehicle_bay_compatibility(
                'TWO_WHEELER'::vehicle_category_enum,
                'TWO_WHEELER',
                2.1, 0.9, 1.2,
                false, false
            )
            """
        )
    )
    assert res.scalar() is True


@pytest.mark.asyncio
async def test_property_authorizations_new_columns(db_session):
    """Verify property_authorizations table contains Phase 03 columns."""
    res = await db_session.execute(
        text(
            """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'property_authorizations'
              AND column_name IN ('version', 'rejection_reason_code', 'updated_at')
            """
        )
    )
    cols = {row[0]: (row[1], row[2]) for row in res.fetchall()}
    assert "version" in cols
    assert "integer" in cols["version"][0]
    assert "rejection_reason_code" in cols
    assert "updated_at" in cols


@pytest.mark.asyncio
async def test_property_document_and_blackout_orm_models(db_session):
    """Verify PropertyDocument and BlackoutSchedule ORM relationships and persistence."""
    from datetime import datetime, timedelta, timezone

    from app.models.documents import PropertyDocument
    from app.models.enums import AuthorizationStatusEnum, DocumentTypeEnum
    from app.models.properties import PropertyAuthorization
    from app.models.schedules import BlackoutSchedule
    from app.models.users import User

    # Create Owner
    owner = User(
        phone_number="+919876543999",
        full_name="ORM Property Owner",
        email="owner_orm@test.com",
    )
    db_session.add(owner)
    await db_session.flush()

    # Create Property with raw SQL to support environments where PostGIS is a fallback domain
    prop_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
            VALUES (:id, :owner_id, 'Test ORM Plaza', 'COMMERCIAL_BUILDING', '100 Commercial Street', 'Bengaluru', '560025', 'SRID=4326;POINT(77.6000 12.9800)', FALSE)
            """
        ),
        {"id": prop_id, "owner_id": owner.id},
    )

    auth = PropertyAuthorization(
        property_id=prop_id,
        status=AuthorizationStatusEnum.DRAFT,
        version=1,
    )
    db_session.add(auth)

    # Add PropertyDocument via ORM
    doc = PropertyDocument(
        property_id=prop_id,
        document_type=DocumentTypeEnum.PROPERTY_TAX_RECEIPT,
        file_name="tax_receipt_2026.pdf",
        s3_key=f"documents/{prop_id}/tax_receipt.pdf",
        content_type="application/pdf",
        file_size_bytes=102400,
        is_verified=False,
    )
    db_session.add(doc)

    # Add BlackoutSchedule via ORM
    now = datetime.now(timezone.utc)
    blackout = BlackoutSchedule(
        property_id=prop_id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
        reason="Resurfacing parking lot",
        is_active=True,
    )
    db_session.add(blackout)
    await db_session.commit()

    # Query back using ORM models
    queried_doc = await db_session.get(PropertyDocument, doc.id)
    assert queried_doc is not None
    assert queried_doc.file_name == "tax_receipt_2026.pdf"
    assert queried_doc.document_type == DocumentTypeEnum.PROPERTY_TAX_RECEIPT
    assert queried_doc.is_verified is False

    queried_blackout = await db_session.get(BlackoutSchedule, blackout.id)
    assert queried_blackout is not None
    assert queried_blackout.reason == "Resurfacing parking lot"
    assert queried_blackout.is_active is True

    queried_auth = await db_session.get(PropertyAuthorization, auth.id)
    assert queried_auth is not None
    assert queried_auth.version == 1
