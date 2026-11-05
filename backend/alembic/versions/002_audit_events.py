"""Add audit_events table for Phase 6 security baseline and audit trails.

Revision ID: 002_audit_events
Revises: 001_initial_schema
Create Date: 2026-11-05 14:30:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_audit_events"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        actor_id UUID,
        action VARCHAR(64) NOT NULL,
        resource_type VARCHAR(64) NOT NULL,
        resource_id VARCHAR(128) NOT NULL,
        details JSONB NOT NULL DEFAULT '{}'::jsonb,
        ip_address VARCHAR(45),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(resource_type, resource_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE;")
