"""
Gadispot Database Test Fixtures & Schema Setup
Tests real PostgreSQL 16/18 triggers, GiST concurrency, and ledger immutability.
"""

import os
import asyncio
import pytest
import asyncpg

# Support test DB URL with fallback from port 5432 to 5433
PRIMARY_URL = "postgresql://postgres:postgres@127.0.0.1:5432/gadispot_test"
FALLBACK_URL = "postgresql://postgres:postgres@127.0.0.1:5433/gadispot_test"
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", PRIMARY_URL)

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

DO $$ BEGIN
    CREATE TYPE entry_side_enum AS ENUM ('DEBIT', 'CREDIT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE journal_status_enum AS ENUM ('DRAFT', 'POSTED', 'VOIDED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE reservation_status_enum AS ENUM (
        'ACTIVE_HOLD',
        'CONFIRMED',
        'ACTIVE_SESSION',
        'COMPLETED',
        'CANCELLED_BY_DRIVER',
        'CANCELLED_BY_HOST',
        'RELEASED_EXPIRED',
        'RELEASED_UNFULFILLABLE',
        'NO_SHOW',
        'MAINTENANCE_BLOCK',
        'OWNER_BLACKOUT'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1. Ledger Accounts Table
CREATE TABLE IF NOT EXISTS ledger_accounts (
    account_code VARCHAR(16) PRIMARY KEY,
    account_name VARCHAR(128) NOT NULL,
    account_type VARCHAR(32) NOT NULL
);

-- Seed standard accounts
INSERT INTO ledger_accounts (account_code, account_name, account_type) VALUES
    ('1010', 'Gateway Transit Asset', 'ASSET'),
    ('1020', 'Operating Bank Account', 'ASSET'),
    ('2010', 'Owner Payable Liability', 'LIABILITY'),
    ('2020', 'Customer Refund Payable', 'LIABILITY'),
    ('2030', 'GST Output Tax Payable', 'LIABILITY'),
    ('3010', 'Platform Commission Revenue', 'REVENUE'),
    ('3020', 'Driver Convenience Fee Revenue', 'REVENUE'),
    ('4010', 'Payment Gateway MDR Expense', 'EXPENSE'),
    ('4020', 'GPRP Recovery Subsidy Expense', 'EXPENSE')
ON CONFLICT (account_code) DO NOTHING;

-- 2. Journal Entries Table
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_reference VARCHAR(64) NOT NULL,
    description TEXT,
    posting_status journal_status_enum NOT NULL DEFAULT 'DRAFT',
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);

-- 3. Journal Lines Table
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

CREATE INDEX IF NOT EXISTS idx_journal_lines_journal ON journal_lines(journal_id);

-- 4. Parking Spaces & Reservations (GiST Concurrency)
CREATE TABLE IF NOT EXISTS parking_spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS space_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parking_space_id UUID NOT NULL REFERENCES parking_spaces(id),
    time_window TSTZRANGE NOT NULL,
    status reservation_status_enum NOT NULL DEFAULT 'ACTIVE_HOLD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    CONSTRAINT prevent_overlapping_active_reservations
    EXCLUDE USING gist (
        parking_space_id WITH =,
        time_window WITH &&
    )
    WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
);

-- ============================================================================
-- 5. TRIGGER FUNCTIONS (Zero Child Lock Protocol)
-- ============================================================================

-- Posting Balance Verification Trigger
CREATE OR REPLACE FUNCTION fn_verify_journal_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_total_debits BIGINT;
    v_total_credits BIGINT;
    v_line_count INT;
BEGIN
    IF NEW.posting_status = 'POSTED' AND (OLD.posting_status IS NULL OR OLD.posting_status != 'POSTED') THEN
        -- Zero Child Lock: No FOR UPDATE on journal_lines here!
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

DROP TRIGGER IF EXISTS trg_verify_journal_balance ON journal_entries;
CREATE TRIGGER trg_verify_journal_balance
BEFORE UPDATE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_verify_journal_balance();

-- Immutability of Posted Journals Trigger
CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.posting_status = 'POSTED' THEN
        RAISE EXCEPTION 'Immutable Ledger Violation: Posted journal % cannot be updated or deleted. Post a reversing entry instead.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_posted_modification ON journal_entries;
CREATE TRIGGER trg_prevent_posted_modification
BEFORE UPDATE OR DELETE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_journal_modification();

-- Immutability of Posted Journal Lines Trigger (Parent Serialization Lock)
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

DROP TRIGGER IF EXISTS trg_prevent_posted_lines_mod ON journal_lines;
CREATE TRIGGER trg_prevent_posted_lines_mod
BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_lines_modification();
"""

async def get_test_pool():
    # Try primary port 5432, fallback to 5433
    urls = [TEST_DB_URL, FALLBACK_URL]
    for url in urls:
        try:
            pool = await asyncpg.create_pool(url, min_size=5, max_size=20, timeout=3)
            # Test query
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return pool
        except Exception:
            continue
    raise RuntimeError("Could not connect to local PostgreSQL on port 5432 or 5433")

@pytest.fixture(scope="function")
async def pg_pool():
    pool = await get_test_pool()
    # Initialize schema
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    yield pool
    await pool.close()

@pytest.fixture(autouse=True)
async def clean_db(pg_pool):
    """Ensure tests run against a clean database state."""
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE space_reservations, journal_lines, journal_entries, parking_spaces CASCADE;
        """)
    yield
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE space_reservations, journal_lines, journal_entries, parking_spaces CASCADE;
        """)
