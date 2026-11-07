"""Create revoked_tokens table and totp_pending_secret_encrypted column.

Revision ID: 006_revocation_and_mfa
Revises: 005_totp_hardening
Create Date: 2026-11-07 11:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_revocation_and_mfa"
down_revision: str | None = "005_totp_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add totp_pending_secret_encrypted to users table to protect re-enrollment
    op.add_column(
        "users",
        sa.Column(
            "totp_pending_secret_encrypted",
            sa.String(512),
            nullable=True,
            comment="Pending AES-GCM encrypted TOTP secret during re-enrollment.",
        ),
    )
    # Widen totp_secret_encrypted to 512 for larger ciphertext payloads
    op.alter_column(
        "users",
        "totp_secret_encrypted",
        existing_type=sa.String(255),
        type_=sa.String(512),
        existing_nullable=True,
    )

    # 2. Create revoked_tokens table for authoritative JTI revocation persistence
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(64), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_revoked_tokens_jti_expires_at",
        "revoked_tokens",
        ["jti", "expires_at"],
    )
    op.create_index(
        "ix_revoked_tokens_user_id",
        "revoked_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_revoked_tokens_family_id",
        "revoked_tokens",
        ["family_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_family_id", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_jti_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.alter_column(
        "users",
        "totp_secret_encrypted",
        existing_type=sa.String(512),
        type_=sa.String(255),
        existing_nullable=True,
    )
    op.drop_column("users", "totp_pending_secret_encrypted")
