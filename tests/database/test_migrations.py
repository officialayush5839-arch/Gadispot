"""Database migration, schema integrity, and constraint verification tests (TSK-P7-002)."""

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
    )

    # Verify revision chain: 006 -> 005 -> 004 -> 003 -> 002 -> 001 -> None
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


@pytest.mark.asyncio
async def test_canonical_tables_exist(db_session):
    """Verify all canonical tables are present in the active PostgreSQL database."""
    expected_tables = {
        "users",
        "user_roles",
        "vehicles",
        "properties",
        "property_authorizations",
        "parking_spaces",
        "operating_schedules",
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
