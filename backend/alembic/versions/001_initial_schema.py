"""Initial canonical schema migration for Gadispot (PostgreSQL 16 + PostGIS).

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-11-05 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. PostgreSQL 16 Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist";')
    op.execute("""
    DO $$ BEGIN
        CREATE EXTENSION IF NOT EXISTS "postgis";
    EXCEPTION
        WHEN undefined_file THEN
            RAISE NOTICE 'postgis extension not found on host, creating fallback geometry type';
        WHEN feature_not_supported THEN
            RAISE NOTICE 'postgis extension not supported on host, creating fallback geometry type';
    END $$;
    """)

    # 2. Domain Enums (14 Enums)
    enums = [
        "CREATE TYPE user_role_enum AS ENUM ('DRIVER', 'OWNER', 'GUARD', 'OPERATIONS', 'ADMIN')",
        "CREATE TYPE property_type_enum AS ENUM ('RESIDENTIAL_DRIVEWAY', 'APARTMENT_SOCIETY', 'COMMERCIAL_BUILDING', 'OPEN_PLOT')",
        "CREATE TYPE authorization_status_enum AS ENUM ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED')",
        "CREATE TYPE document_type_enum AS ENUM ('PROPERTY_TAX_RECEIPT', 'SALE_DEED', 'ELECTRICITY_BILL', 'SOCIETY_NOC', 'LEASE_AGREEMENT', 'COMMERCIAL_CONCESSION')",
        "CREATE TYPE vehicle_category_enum AS ENUM ('TWO_WHEELER', 'HATCHBACK', 'SEDAN', 'SUV', 'EV_FOUR_WHEELER', 'EV_TWO_WHEELER')",
        "CREATE TYPE space_type_enum AS ENUM ('COVERED', 'OPEN', 'BASEMENT')",
        "CREATE TYPE reservation_type_enum AS ENUM ('TEMPORARY_HOLD', 'CONFIRMED_BOOKING', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT')",
        "CREATE TYPE reservation_status_enum AS ENUM ('ACTIVE_HOLD', 'EXPIRED_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'COMPLETED', 'CANCELLED_BY_DRIVER', 'CANCELLED_BY_OWNER', 'NO_SHOW', 'ARRIVAL_FAILED', 'REPLACED', 'RELEASED_UNFULFILLABLE', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT')",
        "CREATE TYPE refund_status_enum AS ENUM ('NONE', 'REFUND_ELIGIBLE', 'REFUND_REQUESTED', 'GATEWAY_ACCEPTED', 'REFUND_PROCESSING', 'REFUND_SETTLED', 'REFUND_FAILED')",
        "CREATE TYPE token_type_enum AS ENUM ('ENTRY', 'EXIT')",
        "CREATE TYPE token_status_enum AS ENUM ('ISSUED', 'ACTIVE', 'CONSUMED', 'REVOKED', 'EXPIRED')",
        "CREATE TYPE account_type_enum AS ENUM ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
        "CREATE TYPE journal_status_enum AS ENUM ('DRAFT', 'POSTED', 'VOIDED')",
        "CREATE TYPE entry_side_enum AS ENUM ('DEBIT', 'CREDIT')",
    ]
    for enum_ddl in enums:
        op.execute(f"""
        DO $$ BEGIN
            {enum_ddl};
        EXCEPTION WHEN duplicate_object THEN null; END $$;
        """)

    # 3. Canonical Tables

    # Table 1: users
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        phone_number VARCHAR(16) NOT NULL UNIQUE,
        full_name VARCHAR(128) NOT NULL,
        email VARCHAR(255),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);")

    # Table 2: user_roles
    op.execute("""
    CREATE TABLE IF NOT EXISTS user_roles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role user_role_enum NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_user_roles_user_role UNIQUE(user_id, role)
    );
    """)

    # Table 3: vehicles
    op.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        driver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        registration_plate VARCHAR(32) NOT NULL,
        vehicle_category vehicle_category_enum NOT NULL,
        make_model VARCHAR(64),
        is_ev BOOLEAN NOT NULL DEFAULT FALSE,
        is_primary BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_vehicles_driver_plate UNIQUE(driver_id, registration_plate)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_driver ON vehicles(driver_id);")

    # Table 4: properties
    conn = op.get_bind()
    has_postgis = conn.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
    ).scalar()

    if has_postgis:
        op.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title VARCHAR(128) NOT NULL,
            property_type property_type_enum NOT NULL,
            address_line TEXT NOT NULL,
            city VARCHAR(64) NOT NULL DEFAULT 'Bengaluru',
            postal_code VARCHAR(16) NOT NULL,
            location GEOMETRY(Point, 4326) NOT NULL,
            max_advance_days INT NOT NULL DEFAULT 7,
            max_booking_hours INT NOT NULL DEFAULT 24,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_properties_location ON properties USING gist (location);")
    else:
        op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'geometry') THEN
                CREATE DOMAIN geometry AS TEXT;
            END IF;
        END $$;
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title VARCHAR(128) NOT NULL,
            property_type property_type_enum NOT NULL,
            address_line TEXT NOT NULL,
            city VARCHAR(64) NOT NULL DEFAULT 'Bengaluru',
            postal_code VARCHAR(16) NOT NULL,
            location geometry NOT NULL,
            max_advance_days INT NOT NULL DEFAULT 7,
            max_booking_hours INT NOT NULL DEFAULT 24,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_id);")

    # Table 5: property_authorizations
    op.execute("""
    CREATE TABLE IF NOT EXISTS property_authorizations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        property_id UUID NOT NULL UNIQUE REFERENCES properties(id) ON DELETE CASCADE,
        status authorization_status_enum NOT NULL DEFAULT 'DRAFT',
        pan_number VARCHAR(16),
        gstin VARCHAR(32),
        reviewer_notes TEXT,
        reviewed_by UUID REFERENCES users(id),
        reviewed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # Table 6: parking_spaces
    op.execute("""
    CREATE TABLE IF NOT EXISTS parking_spaces (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
        space_label VARCHAR(32) NOT NULL,
        space_type space_type_enum NOT NULL DEFAULT 'COVERED',
        vehicle_category vehicle_category_enum NOT NULL,
        length_meters NUMERIC(4,2) NOT NULL DEFAULT 4.80,
        width_meters NUMERIC(4,2) NOT NULL DEFAULT 2.40,
        height_clearance_meters NUMERIC(4,2) NOT NULL DEFAULT 2.10,
        has_ev_charging BOOLEAN NOT NULL DEFAULT FALSE,
        base_hourly_rate_paise BIGINT NOT NULL CHECK (base_hourly_rate_paise > 0),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_parking_spaces_property_label UNIQUE(property_id, space_label)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_spaces_property ON parking_spaces(property_id);")

    # Table 7: operating_schedules
    op.execute("""
    CREATE TABLE IF NOT EXISTS operating_schedules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
        day_of_week INT NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT chk_schedule_time CHECK (start_time < end_time)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_operating_schedules_property ON operating_schedules(property_id);")

    # Table 8: space_reservations (with GiST exclusion constraint)
    op.execute("""
    CREATE TABLE IF NOT EXISTS space_reservations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        parking_space_id UUID NOT NULL REFERENCES parking_spaces(id) ON DELETE RESTRICT,
        driver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
        time_window TSTZRANGE NOT NULL,
        reservation_type reservation_type_enum NOT NULL,
        status reservation_status_enum NOT NULL,
        hold_expires_at TIMESTAMPTZ,
        payment_order_id VARCHAR(64),
        payment_transaction_id VARCHAR(64),
        booking_reference VARCHAR(32) NOT NULL UNIQUE,
        idempotency_key VARCHAR(64) UNIQUE,
        refund_status refund_status_enum NOT NULL DEFAULT 'NONE',
        refund_gateway_id VARCHAR(64),
        refund_arn_utr VARCHAR(64),
        refund_initiated_at TIMESTAMPTZ,
        refund_completed_at TIMESTAMPTZ,
        refund_failure_reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT chk_hold_expiration CHECK (
            (status != 'ACTIVE_HOLD') OR (hold_expires_at IS NOT NULL)
        ),
        CONSTRAINT chk_positive_time_window CHECK (
            lower(time_window) < upper(time_window)
        ),
        CONSTRAINT prevent_overlapping_active_reservations
        EXCLUDE USING gist (
            parking_space_id WITH =,
            time_window WITH &&
        ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_reservations_space_time ON space_reservations USING gist (parking_space_id, time_window);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reservations_status ON space_reservations(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reservations_hold_expiry ON space_reservations(hold_expires_at) WHERE status = 'ACTIVE_HOLD';")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reservations_driver ON space_reservations(driver_id);")

    # Table 9: ledger_accounts
    op.execute("""
    CREATE TABLE IF NOT EXISTS ledger_accounts (
        account_code VARCHAR(16) PRIMARY KEY,
        account_name VARCHAR(128) NOT NULL,
        account_type account_type_enum NOT NULL,
        normal_balance VARCHAR(8) NOT NULL CHECK (normal_balance IN ('DEBIT', 'CREDIT')),
        description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("""
    INSERT INTO ledger_accounts (account_code, account_name, account_type, normal_balance, description) VALUES
        ('1010', 'Gateway Transit Asset', 'ASSET', 'DEBIT', 'In-transit gateway funds'),
        ('1020', 'Operating Bank Account', 'ASSET', 'DEBIT', 'Primary corporate current account'),
        ('2010', 'Owner Payable Liability', 'LIABILITY', 'CREDIT', 'Accumulated host earnings owed'),
        ('2020', 'Customer Refund Payable', 'LIABILITY', 'CREDIT', 'Queued refunds owed to drivers'),
        ('2030', 'GST Output Tax Payable', 'LIABILITY', 'CREDIT', '18% GST liability on commission'),
        ('3010', 'Platform Commission Revenue', 'REVENUE', 'CREDIT', '15% platform take-rate revenue'),
        ('3020', 'Driver Convenience Fee Revenue', 'REVENUE', 'CREDIT', 'Driver convenience fee'),
        ('4010', 'Payment Gateway MDR Expense', 'EXPENSE', 'DEBIT', 'Payment aggregator processing fee'),
        ('4020', 'GPRP Recovery Subsidy Expense', 'EXPENSE', 'DEBIT', 'Platform absorbed replacement fee')
    ON CONFLICT (account_code) DO NOTHING;
    """)

    # Table 10: journal_entries
    op.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        journal_number VARCHAR(32) NOT NULL UNIQUE,
        entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
        transaction_reference VARCHAR(64) NOT NULL,
        transaction_type VARCHAR(32) NOT NULL,
        currency VARCHAR(3) NOT NULL DEFAULT 'INR',
        posting_status journal_status_enum NOT NULL DEFAULT 'DRAFT',
        reversal_of_journal_id UUID REFERENCES journal_entries(id),
        description TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        posted_at TIMESTAMPTZ
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_journal_entries_reference ON journal_entries(transaction_reference);")

    # Table 11: journal_lines
    op.execute("""
    CREATE TABLE IF NOT EXISTS journal_lines (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        journal_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE RESTRICT,
        line_number INT NOT NULL,
        account_code VARCHAR(16) NOT NULL REFERENCES ledger_accounts(account_code),
        entry_side entry_side_enum NOT NULL,
        amount_in_paise BIGINT NOT NULL CHECK (amount_in_paise > 0),
        description TEXT,
        CONSTRAINT uq_journal_line UNIQUE (journal_id, line_number)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_journal_lines_journal ON journal_lines(journal_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON journal_lines(account_code);")

    # Table 12: access_credentials
    op.execute("""
    CREATE TABLE IF NOT EXISTS access_credentials (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        reservation_id UUID NOT NULL REFERENCES space_reservations(id) ON DELETE CASCADE,
        token_type token_type_enum NOT NULL,
        opaque_token VARCHAR(64) NOT NULL UNIQUE,
        status token_status_enum NOT NULL DEFAULT 'ISSUED',
        valid_from TIMESTAMPTZ NOT NULL,
        valid_until TIMESTAMPTZ NOT NULL,
        consumed_at TIMESTAMPTZ,
        consumed_by_guard_id UUID REFERENCES users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_credentials_lookup ON access_credentials(opaque_token);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_credentials_res ON access_credentials(reservation_id, token_type);")

    # Table 13: offline_manual_admissions
    op.execute("""
    CREATE TABLE IF NOT EXISTS offline_manual_admissions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        property_id UUID NOT NULL REFERENCES properties(id),
        guard_id UUID NOT NULL REFERENCES users(id),
        vehicle_plate VARCHAR(32) NOT NULL,
        driver_phone_last4 VARCHAR(4),
        photo_s3_key TEXT NOT NULL,
        photo_purge_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
        reason_code VARCHAR(32) NOT NULL,
        device_fingerprint VARCHAR(128) NOT NULL,
        event_signature VARCHAR(128) NOT NULL,
        admitted_at TIMESTAMPTZ NOT NULL,
        synced_at TIMESTAMPTZ,
        reconciliation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_SYNC',
        matched_reservation_id UUID REFERENCES space_reservations(id),
        conflict_details TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_offline_admissions_status ON offline_manual_admissions(reconciliation_status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_offline_admissions_purge ON offline_manual_admissions(photo_purge_at) WHERE reconciliation_status = 'RECONCILED';")

    # Table 14: payment_webhook_events
    op.execute("""
    CREATE TABLE IF NOT EXISTS payment_webhook_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        gateway_name VARCHAR(32) NOT NULL,
        gateway_event_id VARCHAR(128) NOT NULL,
        event_type VARCHAR(64) NOT NULL,
        payload JSONB NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
        processed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_gateway_event UNIQUE (gateway_name, gateway_event_id)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_status ON payment_webhook_events(status);")

    # Table 15: outbox_events
    op.execute("""
    CREATE TABLE IF NOT EXISTS outbox_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type VARCHAR(64) NOT NULL,
        payload JSONB NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        processed_at TIMESTAMPTZ
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_events(status, created_at) WHERE status = 'PENDING';")

    # 4. Trigger Functions & Triggers (Zero Child Lock Protocol)

    # Trigger Function 1: fn_verify_journal_balance
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_verify_journal_balance()
    RETURNS TRIGGER AS $$
    DECLARE
        v_total_debits BIGINT;
        v_total_credits BIGINT;
        v_line_count INT;
    BEGIN
        IF NEW.posting_status = 'POSTED' AND (OLD.posting_status IS NULL OR OLD.posting_status != 'POSTED') THEN
            -- CRITICAL CONCURRENCY FIX (P0-02): Zero Child Lock Protocol
            -- Balance verification computed via standard MVCC snapshot without child row locks
            SELECT 
                COALESCE(SUM(CASE WHEN entry_side = 'DEBIT' THEN amount_in_paise ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN entry_side = 'CREDIT' THEN amount_in_paise ELSE 0 END), 0),
                COUNT(*)
            INTO v_total_debits, v_total_credits, v_line_count
            FROM journal_lines
            WHERE journal_id = NEW.id;

            IF v_line_count < 2 THEN
                RAISE EXCEPTION 'Cannot post journal entry %: Must contain at least 2 lines (found %)', NEW.id, v_line_count;
            END IF;

            IF v_total_debits != v_total_credits THEN
                RAISE EXCEPTION 'Journal entry % does not balance! Total Debits: % paise, Total Credits: % paise',
                    NEW.id, v_total_debits, v_total_credits;
            END IF;

            NEW.posted_at := CLOCK_TIMESTAMP();
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_verify_journal_balance ON journal_entries;")
    op.execute("""
    CREATE TRIGGER trg_verify_journal_balance
    BEFORE UPDATE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION fn_verify_journal_balance();
    """)

    # Trigger Function 2: fn_prevent_posted_journal_modification
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_modification()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.posting_status = 'POSTED' THEN
            RAISE EXCEPTION 'Immutable Ledger Violation: Posted journal % cannot be updated or deleted. Post a reversing entry instead.', OLD.id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_modification ON journal_entries;")
    op.execute("""
    CREATE TRIGGER trg_prevent_posted_modification
    BEFORE UPDATE OR DELETE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_posted_journal_modification();
    """)

    # Trigger Function 3: fn_prevent_posted_lines_modification
    op.execute("""
    CREATE OR REPLACE FUNCTION fn_prevent_posted_lines_modification()
    RETURNS TRIGGER AS $$
    DECLARE
        v_status journal_status_enum;
    BEGIN
        IF TG_OP = 'INSERT' THEN
            SELECT posting_status INTO v_status FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
            IF v_status IS NULL THEN
                RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', NEW.journal_id;
            ELSIF v_status = 'POSTED' THEN
                RAISE EXCEPTION 'Immutable Ledger Violation: Cannot insert lines into POSTED journal %', NEW.journal_id;
            END IF;
            RETURN NEW;
        ELSIF TG_OP = 'DELETE' THEN
            SELECT posting_status INTO v_status FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
            IF v_status IS NULL THEN
                RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', OLD.journal_id;
            ELSIF v_status = 'POSTED' THEN
                RAISE EXCEPTION 'Immutable Ledger Violation: Cannot delete lines from POSTED journal %', OLD.journal_id;
            END IF;
            RETURN OLD;
        ELSIF TG_OP = 'UPDATE' THEN
            IF OLD.journal_id = NEW.journal_id THEN
                SELECT posting_status INTO v_status FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
                IF v_status IS NULL THEN
                    RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', NEW.journal_id;
                ELSIF v_status = 'POSTED' THEN
                    RAISE EXCEPTION 'Immutable Ledger Violation: Cannot update lines on POSTED journal %', NEW.journal_id;
                END IF;
            ELSE
                -- Deterministic locking order when moving lines across journals
                IF OLD.journal_id < NEW.journal_id THEN
                    PERFORM 1 FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
                    PERFORM 1 FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
                ELSE
                    PERFORM 1 FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
                    PERFORM 1 FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
                END IF;

                IF EXISTS (SELECT 1 FROM journal_entries WHERE id IN (OLD.journal_id, NEW.journal_id) AND posting_status = 'POSTED') THEN
                    RAISE EXCEPTION 'Immutable Ledger Violation: Cannot move line into or out of POSTED journal (% -> %)', OLD.journal_id, NEW.journal_id;
                END IF;
            END IF;
            RETURN NEW;
        END IF;

        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_lines_mod ON journal_lines;")
    op.execute("""
    CREATE TRIGGER trg_prevent_posted_lines_mod
    BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
    FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_posted_lines_modification();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_lines_mod ON journal_lines;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_modification ON journal_entries;")
    op.execute("DROP TRIGGER IF EXISTS trg_verify_journal_balance ON journal_entries;")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS fn_prevent_posted_lines_modification();")
    op.execute("DROP FUNCTION IF EXISTS fn_prevent_posted_journal_modification();")
    op.execute("DROP FUNCTION IF EXISTS fn_verify_journal_balance();")

    # Drop tables in reverse dependency order
    tables = [
        "outbox_events", "payment_webhook_events", "offline_manual_admissions",
        "access_credentials", "journal_lines", "journal_entries", "ledger_accounts",
        "space_reservations", "operating_schedules", "parking_spaces",
        "property_authorizations", "properties", "vehicles", "user_roles", "users"
    ]
    for tbl in tables:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")

    # Drop enums
    enums = [
        "entry_side_enum", "journal_status_enum", "account_type_enum",
        "token_status_enum", "token_type_enum", "refund_status_enum",
        "reservation_status_enum", "reservation_type_enum", "space_type_enum",
        "vehicle_category_enum", "document_type_enum", "authorization_status_enum",
        "property_type_enum", "user_role_enum"
    ]
    for e in enums:
        op.execute(f"DROP TYPE IF EXISTS {e} CASCADE;")
