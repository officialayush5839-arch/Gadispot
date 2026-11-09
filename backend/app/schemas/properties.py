"""Pydantic schemas for properties, parking spaces, operating hours, and blackouts."""

import uuid
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    AuthorizationStatusEnum,
    DocumentTypeEnum,
    PropertyTypeEnum,
    SpaceTypeEnum,
    VehicleCategoryEnum,
)


def extract_lat_lon(location: Any) -> tuple[float, float]:
    """Helper to extract (latitude, longitude) from PostGIS point or string representation."""
    if location is None:
        return 0.0, 0.0
    try:
        from geoalchemy2.shape import to_shape

        shape = to_shape(location)
        return float(shape.y), float(shape.x)
    except Exception:
        import re

        s = str(location)
        m = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", s)
        if m:
            return float(m.group(2)), float(m.group(1))
        return 0.0, 0.0


# =============================================================================
# Property Schemas
# =============================================================================


class PropertyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128, description="Property title")
    property_type: PropertyTypeEnum = Field(..., description="Canonical property type")
    address_line: str = Field(..., min_length=1, description="Physical street address")
    city: str = Field(default="Bengaluru", min_length=1, max_length=64, description="City name")
    postal_code: str = Field(
        ...,
        pattern=r"^[0-9]{6}$",
        description="6-digit PIN / postal code",
    )
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS 84 Latitude [-90, 90]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS 84 Longitude [-180, 180]")
    max_advance_days: int = Field(default=7, ge=1, le=365, description="Maximum advance booking days")
    max_booking_hours: int = Field(default=24, ge=1, le=720, description="Maximum booking duration in hours")

    @model_validator(mode="after")
    def validate_postal_code_for_city(self) -> "PropertyBase":
        city_lower = (self.city or "").strip().lower()
        if city_lower in {"arctic", "antarctica", "pacific", "international", "global"}:
            return self
        import re

        if not re.match(r"^[1-9][0-9]{5}$", self.postal_code):
            raise ValueError(
                f"Invalid postal code '{self.postal_code}'. Postal code for {self.city} must be a 6-digit number not starting with 0."
            )
        return self


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=128)
    property_type: Optional[PropertyTypeEnum] = None
    address_line: Optional[str] = Field(default=None, min_length=1)
    city: Optional[str] = Field(default=None, min_length=1, max_length=64)
    postal_code: Optional[str] = Field(default=None, pattern=r"^[0-9]{6}$")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    max_advance_days: Optional[int] = Field(default=None, ge=1, le=365)
    max_booking_hours: Optional[int] = Field(default=None, ge=1, le=720)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_postal_code(self) -> "PropertyUpdate":
        if self.postal_code is not None:
            city_lower = (self.city or "").strip().lower()
            if city_lower not in {"arctic", "antarctica", "pacific", "international", "global"}:
                import re

                if not re.match(r"^[1-9][0-9]{5}$", self.postal_code):
                    raise ValueError(f"Invalid postal code '{self.postal_code}'.")
        return self


class PropertyAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    status: AuthorizationStatusEnum
    version: int
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    rejection_reason_code: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Parking Space Schemas
# =============================================================================


class ParkingSpaceBase(BaseModel):
    space_label: str = Field(..., min_length=1, max_length=32, description="Bay identifier (e.g. BAY-01)")
    space_type: SpaceTypeEnum = Field(default=SpaceTypeEnum.COVERED, description="Covered, Open, or Basement")
    vehicle_category: VehicleCategoryEnum = Field(..., description="Target vehicle classification")
    length_meters: Decimal = Field(
        ..., gt=Decimal("0.0"), max_digits=4, decimal_places=2, description="Length in meters"
    )
    width_meters: Decimal = Field(..., gt=Decimal("0.0"), max_digits=4, decimal_places=2, description="Width in meters")
    height_clearance_meters: Decimal = Field(
        ..., gt=Decimal("0.0"), max_digits=4, decimal_places=2, description="Overhead height clearance in meters"
    )
    has_ev_charging: bool = Field(default=False, description="Whether dedicated EV charger is available")
    base_hourly_rate_paise: int = Field(..., gt=0, description="Base hourly rate in paise (> 0)")
    is_active: bool = Field(default=True, description="Whether parking space is active")


class ParkingSpaceCreate(ParkingSpaceBase):
    pass


class ParkingSpaceUpdate(BaseModel):
    space_label: Optional[str] = Field(default=None, min_length=1, max_length=32)
    space_type: Optional[SpaceTypeEnum] = None
    vehicle_category: Optional[VehicleCategoryEnum] = None
    length_meters: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), max_digits=4, decimal_places=2)
    width_meters: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), max_digits=4, decimal_places=2)
    height_clearance_meters: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), max_digits=4, decimal_places=2)
    has_ev_charging: Optional[bool] = None
    base_hourly_rate_paise: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


class ParkingSpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    space_label: str
    space_type: SpaceTypeEnum
    vehicle_category: VehicleCategoryEnum
    length_meters: Decimal
    width_meters: Decimal
    height_clearance_meters: Decimal
    has_ev_charging: bool
    base_hourly_rate_paise: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Operating Schedule Schemas
# =============================================================================


class OperatingScheduleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday (or 0..6)")
    start_time: time = Field(..., description="Window opening time (HH:MM:SS)")
    end_time: time = Field(..., description="Window closing time (HH:MM:SS)")
    is_active: bool = Field(default=True, description="Active status")

    @model_validator(mode="after")
    def validate_time_window(self) -> "OperatingScheduleBase":
        if self.start_time >= self.end_time:
            raise ValueError("Operating hours start_time must be strictly before end_time")
        return self


class OperatingScheduleCreate(OperatingScheduleBase):
    pass


class OperatingScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Blackout Schedule Schemas
# =============================================================================


class BlackoutScheduleBase(BaseModel):
    parking_space_id: Optional[uuid.UUID] = Field(
        default=None, description="Specific bay ID, or None for property-wide"
    )
    start_time: datetime = Field(..., description="Blackout start timestamp (UTC)")
    end_time: datetime = Field(..., description="Blackout end timestamp (UTC)")
    reason: Optional[str] = Field(default=None, description="Reason for blackout window")
    is_active: bool = Field(default=True, description="Active status")

    @model_validator(mode="after")
    def validate_blackout_times(self) -> "BlackoutScheduleBase":
        if self.start_time >= self.end_time:
            raise ValueError("Blackout start_time must be strictly before end_time")
        return self


class BlackoutScheduleCreate(BlackoutScheduleBase):
    pass


class BlackoutScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    parking_space_id: Optional[uuid.UUID] = None
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    is_active: bool
    created_at: datetime


# =============================================================================
# Document Schemas
# =============================================================================

ALLOWED_DOCUMENT_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_DOCUMENT_FILE_SIZE = 10 * 1024 * 1024  # 10MB = 10,485,760 bytes


class DocumentPresignRequest(BaseModel):
    document_type: DocumentTypeEnum
    file_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="application/pdf, image/jpeg, or image/png")
    file_size_bytes: int = Field(..., gt=0, le=MAX_DOCUMENT_FILE_SIZE, description="Max 10MB")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v.lower() not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise ValueError(f"Content type '{v}' is not permitted. Must be one of: {ALLOWED_DOCUMENT_MIME_TYPES}")
        return v.lower()


class DocumentPresignResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    expires_in: int = 900
    s3_key: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    document_type: DocumentTypeEnum
    file_name: str
    content_type: str
    file_size_bytes: int
    is_verified: bool
    uploaded_at: Optional[datetime] = None
    created_at: datetime


# =============================================================================
# Full Property Response
# =============================================================================


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    property_type: PropertyTypeEnum
    address_line: str
    city: str
    postal_code: str
    latitude: float
    longitude: float
    max_advance_days: int
    max_booking_hours: int
    is_active: bool
    version: int = 1
    status: str = "DRAFT"
    created_at: datetime
    updated_at: datetime

    authorization: Optional[PropertyAuthorizationResponse] = None
    parking_spaces: list[ParkingSpaceResponse] = []
    operating_schedules: list[OperatingScheduleResponse] = []
    blackouts: list[BlackoutScheduleResponse] = []
    documents: list[DocumentResponse] = []

    @model_validator(mode="before")
    @classmethod
    def populate_coordinates_from_location(cls, data: Any) -> Any:
        """Hydrate latitude/longitude from PostGIS Geometry location if reading from ORM object."""
        if hasattr(data, "location") and not isinstance(data, dict):
            lat, lon = extract_lat_lon(getattr(data, "location", None))
            auth = getattr(data, "authorization", None)
            auth_status = getattr(auth, "status", None)
            status_str = auth_status.value if hasattr(auth_status, "value") else str(auth_status or "DRAFT")
            auth_version = getattr(auth, "version", 1) or 1

            return {
                "id": getattr(data, "id"),
                "owner_id": getattr(data, "owner_id"),
                "title": getattr(data, "title"),
                "property_type": getattr(data, "property_type"),
                "address_line": getattr(data, "address_line"),
                "city": getattr(data, "city"),
                "postal_code": getattr(data, "postal_code"),
                "latitude": lat,
                "longitude": lon,
                "max_advance_days": getattr(data, "max_advance_days", 7),
                "max_booking_hours": getattr(data, "max_booking_hours", 24),
                "is_active": getattr(data, "is_active", False),
                "version": auth_version,
                "status": status_str,
                "created_at": getattr(data, "created_at"),
                "updated_at": getattr(data, "updated_at"),
                "authorization": auth,
                "parking_spaces": getattr(data, "parking_spaces", []) or [],
                "operating_schedules": getattr(data, "operating_schedules", []) or [],
                "blackouts": getattr(data, "blackouts", []) or [],
                "documents": getattr(data, "documents", []) or [],
            }
        return data


# =============================================================================
# Operations Review Schemas
# =============================================================================

CANONICAL_REJECTION_REASONS = {
    "DOC_ILLEGIBLE",
    "INVALID_OWNERSHIP_PROOF",
    "SOCIETY_NOC_MISSING",
    "DIMENSIONS_INVALID",
    "INCOMPLETE_DOCUMENTATION",
    "SUSPECTED_FRAUD",
    "PROPERTY_UNREACHABLE",
    "OTHER",
}


class OpsReviewQueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    property_type: PropertyTypeEnum
    city: str
    address_line: str
    owner_id: uuid.UUID
    status: AuthorizationStatusEnum
    version: int
    submitted_at: Optional[datetime] = None
    created_at: datetime


class OpsReviewQueueResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[OpsReviewQueueItem]


class OpsApproveRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    version: int = Field(..., ge=1, description="Expected authorization version for optimistic locking")
    reviewer_notes: Optional[str] = None


class OpsRejectRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    version: int = Field(..., ge=1, description="Expected authorization version for optimistic locking")
    rejection_reason_code: str = Field(..., description="Canonical rejection reason code")
    reviewer_notes: str = Field(..., min_length=1, description="Detailed review feedback")

    @field_validator("rejection_reason_code")
    @classmethod
    def validate_rejection_reason_code(cls, v: str) -> str:
        if v not in CANONICAL_REJECTION_REASONS:
            raise ValueError(
                f"Rejection reason code '{v}' is not recognized. Must be one of: {CANONICAL_REJECTION_REASONS}"
            )
        return v

    @field_validator("reviewer_notes")
    @classmethod
    def validate_reviewer_notes(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reviewer notes must not be empty or whitespace only.")
        return v.strip()


class OpsReviewDecisionResponse(BaseModel):
    id: uuid.UUID
    status: str
    is_active: bool
    version: int
    message: str = "Decision recorded successfully."


class PropertyReviewSubmissionResponse(BaseModel):
    property_id: uuid.UUID
    status: str = "PENDING_REVIEW"
    message: str = "Property submitted for review successfully."
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Vehicle Compatibility Check Schemas
# =============================================================================


class VehicleCompatibilityCheckRequest(BaseModel):
    vehicle_category: VehicleCategoryEnum
    vehicle_length_mm: Optional[int] = Field(default=None, gt=0, description="Vehicle length in mm")
    vehicle_width_mm: Optional[int] = Field(default=None, gt=0, description="Vehicle width in mm")
    vehicle_height_mm: Optional[int] = Field(default=None, gt=0, description="Vehicle height in mm")
    is_ev: bool = Field(default=False, description="Whether vehicle is electric")
    driver_requires_ev: bool = Field(default=False, description="Whether driver explicitly requests EV charging")


class VehicleCompatibilityCheckResponse(BaseModel):
    is_compatible: bool
    method: str = Field(description="'3d_clearance' or 'stored_function'")
    length_clearance_mm: Optional[int] = None
    width_clearance_mm: Optional[int] = None
    height_clearance_mm: Optional[int] = None
    rejection_reasons: list[str] = []
