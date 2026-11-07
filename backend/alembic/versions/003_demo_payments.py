"""Add payments table and enums for Dual-Mode Demo Payment System.

Revision ID: 003_demo_payments
Revises: 002_audit_events
Create Date: 2026-11-05 23:45:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_demo_payments"
down_revision: str | None = "002_audit_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create Enums if they do not exist
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE payment_status_enum AS ENUM (
            'CREATED', 'PENDING', 'SUCCEEDED', 'FAILED', 'CANCELLED',
            'EXPIRED', 'OBSERVED_SUCCESS', 'REQUIRES_RECONCILIATION', 'UNKNOWN'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute("""
    DO $$ BEGIN
        CREATE TYPE payment_provider_enum AS ENUM (
            'DEMO', 'RAZORPAY', 'CASHFREE', 'HYPERSWITCH', 'YOUPI'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    # 2. Create payments table
    op.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        reservation_id UUID NOT NULL REFERENCES space_reservations(id) ON DELETE RESTRICT,
        driver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        amount_paise BIGINT NOT NULL,
        currency VARCHAR(3) NOT NULL DEFAULT 'INR',
        provider payment_provider_enum NOT NULL,
        provider_payment_id VARCHAR(128),
        provider_order_id VARCHAR(128),
        status payment_status_enum NOT NULL DEFAULT 'CREATED',
        is_simulated BOOLEAN NOT NULL DEFAULT FALSE,
        is_experimental BOOLEAN NOT NULL DEFAULT FALSE,
        experimental_status VARCHAR(64),
        idempotency_key VARCHAR(64) UNIQUE,
        simulation_scenario VARCHAR(32),
        failure_reason TEXT,
        payment_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 3. Create Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_reservation ON payments(reservation_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_driver ON payments(driver_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider_payment_id ON payments(provider_payment_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider_order_id ON payments(provider_order_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments CASCADE;")
    op.execute("DROP TYPE IF EXISTS payment_provider_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS payment_status_enum CASCADE;")
