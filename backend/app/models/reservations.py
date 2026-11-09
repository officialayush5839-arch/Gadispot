"""SQLAlchemy declarative model for space reservations with GiST temporal exclusion."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, TSTZRANGE, UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    RefundStatusEnum,
    ReservationStatusEnum,
    ReservationTypeEnum,
)


class SpaceReservation(Base):
    __tablename__ = "space_reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parking_space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_spaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
    )

    time_window = mapped_column(TSTZRANGE, nullable=False)

    reservation_type: Mapped[ReservationTypeEnum] = mapped_column(
        ENUM(ReservationTypeEnum, name="reservation_type_enum", create_type=False),
        nullable=False,
    )
    status: Mapped[ReservationStatusEnum] = mapped_column(
        ENUM(ReservationStatusEnum, name="reservation_status_enum", create_type=False),
        nullable=False,
        index=True,
    )

    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    booking_reference: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, default=lambda: f"BK-{uuid.uuid4().hex[:8].upper()}"
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    @property
    def start_time(self) -> datetime | None:
        if self.time_window:
            return self.time_window.lower
        return None

    @start_time.setter
    def start_time(self, val: datetime) -> None:
        from asyncpg.types import Range

        end = self.time_window.upper if getattr(self, "time_window", None) else None
        self.time_window = Range(val, end, lower_inc=True, upper_inc=False)

    @property
    def end_time(self) -> datetime | None:
        if self.time_window:
            return self.time_window.upper
        return None

    @end_time.setter
    def end_time(self, val: datetime) -> None:
        from asyncpg.types import Range

        start = self.time_window.lower if getattr(self, "time_window", None) else None
        self.time_window = Range(start, val, lower_inc=True, upper_inc=False)

    @property
    def total_amount_paise(self) -> int:
        return 0

    @total_amount_paise.setter
    def total_amount_paise(self, val: int) -> None:
        pass

    refund_status: Mapped[RefundStatusEnum] = mapped_column(
        ENUM(RefundStatusEnum, name="refund_status_enum", create_type=False),
        default=RefundStatusEnum.NONE,
        nullable=False,
    )
    refund_gateway_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_arn_utr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parking_space: Mapped["ParkingSpace"] = relationship("ParkingSpace", back_populates="reservations")  # type: ignore # noqa: F821
    driver: Mapped["User"] = relationship("User")  # type: ignore # noqa: F821
    vehicle: Mapped["Vehicle"] = relationship("Vehicle")  # type: ignore # noqa: F821
    access_credentials: Mapped[list["AccessCredential"]] = relationship(  # type: ignore # noqa: F821
        "AccessCredential", back_populates="reservation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "(status != 'ACTIVE_HOLD') OR (hold_expires_at IS NOT NULL)",
            name="chk_hold_expiration",
        ),
        CheckConstraint(
            "lower(time_window) < upper(time_window)",
            name="chk_positive_time_window",
        ),
        ExcludeConstraint(
            ("parking_space_id", "="),
            ("time_window", "&&"),
            where=text(
                "status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT')"
            ),
            name="prevent_overlapping_active_reservations",
            using="gist",
        ),
        Index(
            "idx_reservations_space_time",
            "parking_space_id",
            "time_window",
            postgresql_using="gist",
        ),
        Index(
            "idx_reservations_hold_expiry",
            "hold_expires_at",
            postgresql_where=text("status = 'ACTIVE_HOLD'"),
        ),
    )
