"""Add identity extension columns to users and create user_sessions table.

Revision ID: 004_identity_and_sessions
Revises: 003_demo_payments
Create Date: 2026-11-06 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_identity_and_sessions"
down_revision: str | None = "003_demo_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create account_status_enum
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE account_status_enum AS ENUM ('ACTIVE', 'DISABLED', 'SUSPENDED');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    # 2. Add columns to users table
    op.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128),
    ADD COLUMN IF NOT EXISTS status account_status_enum NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
    """)

    # 3. Create unique index on firebase_uid and index on status
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);")

    # 4. Create user_sessions table
    op.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
        family_id UUID,
        device_info VARCHAR(255),
        ip_address VARCHAR(64),
        is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
        expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        revoked_at TIMESTAMPTZ
    );
    """)

    # 5. Create indexes on user_sessions
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_hash ON user_sessions(refresh_token_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_family ON user_sessions(family_id);")


def downgrade() -> None:
    # 1. Drop user_sessions table
    op.execute("DROP TABLE IF EXISTS user_sessions CASCADE;")

    # 2. Drop indexes on users table
    op.execute("DROP INDEX IF EXISTS idx_users_firebase_uid;")
    op.execute("DROP INDEX IF EXISTS idx_users_status;")

    # 3. Drop columns from users table
    op.execute("""
    ALTER TABLE users
    DROP COLUMN IF EXISTS firebase_uid,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS last_login_at;
    """)

    # 4. Drop account_status_enum
    op.execute("DROP TYPE IF EXISTS account_status_enum CASCADE;")
