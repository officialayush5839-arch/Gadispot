"""Revoked token model for authoritative persistent JTI revocation tracking."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class RevokedToken(Base):
    """Stores individually revoked access token JTIs to ensure authoritative revocation even during Redis failure."""

    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (Index("ix_revoked_tokens_jti_expires_at", "jti", "expires_at"),)
