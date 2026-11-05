"""SQLAlchemy declarative models for users, roles, and vehicles."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRoleEnum, VehicleCategoryEnum


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    vehicles: Mapped[list["Vehicle"]] = relationship("Vehicle", back_populates="driver", cascade="all, delete-orphan")
    properties: Mapped[list["Property"]] = relationship(  # type: ignore # noqa: F821
        "Property", back_populates="owner"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[UserRoleEnum] = mapped_column(
        ENUM(UserRoleEnum, name="user_role_enum", create_type=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="roles")

    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_plate: Mapped[str] = mapped_column(String(32), nullable=False)
    vehicle_category: Mapped[VehicleCategoryEnum] = mapped_column(
        ENUM(VehicleCategoryEnum, name="vehicle_category_enum", create_type=False),
        nullable=False,
    )
    make_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_ev: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    driver: Mapped["User"] = relationship("User", back_populates="vehicles")

    __table_args__ = (UniqueConstraint("driver_id", "registration_plate", name="uq_vehicles_driver_plate"),)
