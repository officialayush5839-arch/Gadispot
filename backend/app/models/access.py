"""SQLAlchemy declarative models for access credentials and offline manual admissions."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TokenStatusEnum, TokenTypeEnum


class AccessCredential(Base):
    __tablename__ = "access_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("space_reservations.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_type: Mapped[TokenTypeEnum] = mapped_column(
        ENUM(TokenTypeEnum, name="token_type_enum", create_type=False),
        nullable=False,
    )
    opaque_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[TokenStatusEnum] = mapped_column(
        ENUM(TokenStatusEnum, name="token_status_enum", create_type=False),
        default=TokenStatusEnum.ISSUED,
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_by_guard_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reservation: Mapped["SpaceReservation"] = relationship(  # type: ignore # noqa: F821
        "SpaceReservation", back_populates="access_credentials"
    )
    guard: Mapped[Optional["User"]] = relationship("User")  # type: ignore # noqa: F821

    __table_args__ = (Index("idx_access_credentials_res", "reservation_id", "token_type"),)


def generate_access_credentials(
    reservation_id: uuid.UUID,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> tuple[AccessCredential, AccessCredential]:
    """Generate cryptographically secure 128-bit CSPRNG Entry and Exit credentials with ingress window."""
    now = datetime.now(timezone.utc)
    v_from = valid_from or (now - timedelta(minutes=15))
    v_until = valid_until or (now + timedelta(hours=24))

    entry_cred = AccessCredential(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        token_type=TokenTypeEnum.ENTRY,
        opaque_token=f"spx_ent_{secrets.token_hex(16)}",
        status=TokenStatusEnum.ISSUED,
        valid_from=v_from,
        valid_until=v_until,
    )
    exit_cred = AccessCredential(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        token_type=TokenTypeEnum.EXIT,
        opaque_token=f"spx_ext_{secrets.token_hex(16)}",
        status=TokenStatusEnum.ISSUED,
        valid_from=v_from,
        valid_until=v_until,
    )
    return entry_cred, exit_cred


class OfflineManualAdmission(Base):
    __tablename__ = "offline_manual_admissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=False,
    )
    guard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    vehicle_plate: Mapped[str] = mapped_column(String(32), nullable=False)
    driver_phone_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    photo_s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    photo_purge_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(NOW() + INTERVAL '7 days')"),
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    device_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    event_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(32), default="PENDING_SYNC", nullable=False, index=True)
    matched_reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("space_reservations.id"), nullable=True
    )
    conflict_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    property: Mapped["Property"] = relationship("Property")  # type: ignore # noqa: F821
    guard: Mapped["User"] = relationship("User")  # type: ignore # noqa: F821
    matched_reservation: Mapped[Optional["SpaceReservation"]] = relationship("SpaceReservation")  # type: ignore # noqa: F821

    __table_args__ = (
        Index(
            "idx_offline_admissions_purge",
            "photo_purge_at",
            postgresql_where=text("reconciliation_status = 'RECONCILED'"),
        ),
    )
