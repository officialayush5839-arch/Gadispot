"""SQLAlchemy declarative model for parking spaces."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SpaceTypeEnum, VehicleCategoryEnum


class ParkingSpace(Base):
    __tablename__ = "parking_spaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    space_label: Mapped[str] = mapped_column(String(32), nullable=False)
    space_type: Mapped[SpaceTypeEnum] = mapped_column(
        ENUM(SpaceTypeEnum, name="space_type_enum", create_type=False),
        default=SpaceTypeEnum.COVERED,
        nullable=False,
    )
    vehicle_category: Mapped[VehicleCategoryEnum] = mapped_column(
        ENUM(VehicleCategoryEnum, name="vehicle_category_enum", create_type=False),
        nullable=False,
    )
    length_meters: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("4.80"), nullable=False)
    width_meters: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.40"), nullable=False)
    height_clearance_meters: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.10"), nullable=False)
    has_ev_charging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    base_hourly_rate_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship("Property", back_populates="parking_spaces")  # type: ignore # noqa: F821
    reservations: Mapped[list["SpaceReservation"]] = relationship(  # type: ignore # noqa: F821
        "SpaceReservation", back_populates="parking_space"
    )

    __table_args__ = (
        UniqueConstraint("property_id", "space_label", name="uq_parking_spaces_property_label"),
        CheckConstraint("base_hourly_rate_paise > 0", name="chk_base_hourly_rate_paise_positive"),
    )
