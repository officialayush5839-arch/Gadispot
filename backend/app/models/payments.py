"""SQLAlchemy declarative models for payment webhook events and outbox."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PaymentProviderEnum, PaymentStatusEnum


class Payment(Base):
    """Authoritative domain model for all payment transactions (simulated, live, and experimental)."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("space_reservations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    provider: Mapped[PaymentProviderEnum] = mapped_column(
        ENUM(PaymentProviderEnum, name="payment_provider_enum", create_type=False),
        nullable=False,
        index=True,
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[PaymentStatusEnum] = mapped_column(
        ENUM(PaymentStatusEnum, name="payment_status_enum", create_type=False),
        default=PaymentStatusEnum.CREATED,
        nullable=False,
        index=True,
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_experimental: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    experimental_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    simulation_scenario: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_name: Mapped[str] = mapped_column(String(32), nullable=False)
    gateway_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("gateway_name", "gateway_event_id", name="uq_gateway_event"),)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_outbox_pending",
            "status",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
    )
