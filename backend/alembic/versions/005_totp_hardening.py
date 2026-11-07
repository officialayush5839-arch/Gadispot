"""Add TOTP two-factor authentication columns to users table.

Revision ID: 005_totp_hardening
Revises: 004_identity_and_sessions
Create Date: 2026-11-07 10:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_totp_hardening"
down_revision: str | None = "004_identity_and_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add TOTP columns to users table
    op.add_column(
        "users",
        sa.Column(
            "totp_secret_encrypted",
            sa.String(255),
            nullable=True,
            comment="AES-GCM encrypted Base32 TOTP secret key.",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether RFC 6238 TOTP 2FA is activated for this account.",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of initial successful TOTP code verification.",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_verified_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_encrypted")
