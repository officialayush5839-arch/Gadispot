"""SQLAlchemy declarative models for properties, authorizations, and operating schedules."""

import uuid
from datetime import datetime, time
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.documents import PropertyDocument
from app.models.enums import AuthorizationStatusEnum, PropertyTypeEnum
from app.models.schedules import BlackoutSchedule


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    property_type: Mapped[PropertyTypeEnum] = mapped_column(
        ENUM(PropertyTypeEnum, name="property_type_enum", create_type=False),
        nullable=False,
    )
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(64), default="Bengaluru", nullable=False)
    postal_code: Mapped[str] = mapped_column(String(16), nullable=False)
    location = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    max_advance_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    max_booking_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="properties")  # type: ignore # noqa: F821
    authorization: Mapped[Optional["PropertyAuthorization"]] = relationship(
        "PropertyAuthorization", back_populates="property", uselist=False, cascade="all, delete-orphan"
    )
    parking_spaces: Mapped[list["ParkingSpace"]] = relationship(  # type: ignore # noqa: F821
        "ParkingSpace", back_populates="property", cascade="all, delete-orphan"
    )
    operating_schedules: Mapped[list["OperatingSchedule"]] = relationship(
        "OperatingSchedule", back_populates="property", cascade="all, delete-orphan"
    )
    documents: Mapped[list["PropertyDocument"]] = relationship(  # type: ignore # noqa: F821
        "PropertyDocument", back_populates="property", cascade="all, delete-orphan"
    )
    blackouts: Mapped[list["BlackoutSchedule"]] = relationship(  # type: ignore # noqa: F821
        "BlackoutSchedule", back_populates="property", cascade="all, delete-orphan"
    )


class PropertyAuthorization(Base):
    __tablename__ = "property_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[AuthorizationStatusEnum] = mapped_column(
        ENUM(AuthorizationStatusEnum, name="authorization_status_enum", create_type=False),
        default=AuthorizationStatusEnum.DRAFT,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    pan_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship("Property", back_populates="authorization")


class OperatingSchedule(Base):
    __tablename__ = "operating_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship("Property", back_populates="operating_schedules")

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="chk_schedule_time"),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="chk_day_of_week"),
    )
