"""Aggregated exports for all Gadispot SQLAlchemy domain models."""

from app.db.base import Base
from app.models.access import AccessCredential, OfflineManualAdmission
from app.models.enums import (
    AccountTypeEnum,
    AuthorizationStatusEnum,
    DocumentTypeEnum,
    EntrySideEnum,
    JournalStatusEnum,
    PaymentProviderEnum,
    PaymentStatusEnum,
    PropertyTypeEnum,
    RefundStatusEnum,
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    TokenStatusEnum,
    TokenTypeEnum,
    UserRoleEnum,
    VehicleCategoryEnum,
)
from app.models.ledger import JournalEntry, JournalLine, LedgerAccount
from app.models.parking import ParkingSpace
from app.models.payments import OutboxEvent, Payment, PaymentWebhookEvent
from app.models.properties import OperatingSchedule, Property, PropertyAuthorization
from app.models.reservations import SpaceReservation
from app.models.users import User, UserRole, Vehicle

__all__ = [
    "Base",
    # Enums
    "UserRoleEnum",
    "PropertyTypeEnum",
    "AuthorizationStatusEnum",
    "DocumentTypeEnum",
    "VehicleCategoryEnum",
    "SpaceTypeEnum",
    "ReservationTypeEnum",
    "ReservationStatusEnum",
    "RefundStatusEnum",
    "TokenTypeEnum",
    "TokenStatusEnum",
    "AccountTypeEnum",
    "JournalStatusEnum",
    "EntrySideEnum",
    "PaymentStatusEnum",
    "PaymentProviderEnum",
    # Models
    "User",
    "UserRole",
    "Vehicle",
    "Property",
    "PropertyAuthorization",
    "OperatingSchedule",
    "ParkingSpace",
    "SpaceReservation",
    "LedgerAccount",
    "JournalEntry",
    "JournalLine",
    "AccessCredential",
    "OfflineManualAdmission",
    "PaymentWebhookEvent",
    "Payment",
    "OutboxEvent",
]
