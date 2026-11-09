"""FastAPI endpoints for properties, parking spaces, schedules, and blackouts."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_roles
from app.core.dependencies import get_current_user, get_db
from app.models.enums import UserRoleEnum
from app.models.users import User
from app.schemas.properties import (
    BlackoutScheduleCreate,
    BlackoutScheduleResponse,
    DocumentPresignRequest,
    DocumentPresignResponse,
    DocumentResponse,
    OperatingScheduleCreate,
    OperatingScheduleResponse,
    ParkingSpaceCreate,
    ParkingSpaceResponse,
    ParkingSpaceUpdate,
    PropertyCreate,
    PropertyResponse,
    PropertyReviewSubmissionResponse,
    PropertyUpdate,
    VehicleCompatibilityCheckRequest,
    VehicleCompatibilityCheckResponse,
)
from app.services.parking_space_service import ParkingSpaceService
from app.services.property_service import PropertyService
from app.services.schedule_service import ScheduleService

router = APIRouter()
spaces_router = APIRouter()

# Role requirement for property administration: space owners and operators
require_space_owner = require_roles(UserRoleEnum.OWNER, "SPACE_OWNER")


# =============================================================================
# Property Management Endpoints (/api/v1/properties)
# =============================================================================


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property listing",
)
async def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Create a new property listing with WGS 84 spatial coordinates in DRAFT status."""
    prop = await PropertyService.create_property(db, current_user.id, payload)
    return PropertyResponse.model_validate(prop)


@router.get(
    "",
    response_model=list[PropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="List caller's properties",
)
async def list_properties(
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyResponse]:
    """Retrieve all properties owned by the authenticated caller."""
    props = await PropertyService.list_owner_properties(db, current_user.id)
    return [PropertyResponse.model_validate(p) for p in props]


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get property details",
)
async def get_property(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Retrieve detailed property profile including bays, schedules, and authorization status."""
    prop = await PropertyService.get_property(db, property_id)
    return PropertyResponse.model_validate(prop)


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update property metadata",
)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Update property metadata or spatial coordinates with owner authorization."""
    prop = await PropertyService.update_property(db, property_id, current_user, payload)
    return PropertyResponse.model_validate(prop)


@router.post(
    "/{property_id}/submit-review",
    response_model=PropertyReviewSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit property for operations verification",
)
@router.post(
    "/{property_id}/submit",
    response_model=PropertyReviewSubmissionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def submit_property_for_review(
    property_id: uuid.UUID,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> PropertyReviewSubmissionResponse:
    """Submit property for verification review, transitioning authorization status DRAFT -> PENDING_REVIEW."""
    prop = await PropertyService.submit_for_review(db, property_id, current_user)
    return PropertyReviewSubmissionResponse(
        property_id=prop.id,
        status="PENDING_REVIEW",
        message="Property submitted for review successfully.",
    )


# =============================================================================
# Document Management Endpoints (/api/v1/properties/{property_id}/documents/...)
# =============================================================================


@router.post(
    "/{property_id}/documents/presign",
    response_model=DocumentPresignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate presigned upload URL for property authorization document",
)
async def presign_property_document(
    property_id: uuid.UUID,
    payload: DocumentPresignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentPresignResponse:
    """Validate file metadata and return 15-minute S3 upload URL."""
    return await PropertyService.presign_document(db, property_id, current_user, payload)


@router.post(
    "/{property_id}/documents/{document_id}/verify",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm document upload completion and mark verified",
)
async def verify_property_document(
    property_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Verify document upload in storage and mark record verified."""
    doc = await PropertyService.verify_document(db, property_id, document_id, current_user)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{property_id}/documents",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List property authorization documents",
)
async def list_property_documents(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Retrieve all documents submitted for property verification."""
    docs = await PropertyService.list_documents(db, property_id, current_user)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.delete(
    "/{property_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property authorization document",
)
async def delete_property_document(
    property_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete unverified or rejected document."""
    await PropertyService.delete_document(db, property_id, document_id, current_user)


# =============================================================================
# Parking Spaces Management Endpoints (/api/v1/properties/{id}/spaces)
# =============================================================================


@router.post(
    "/{property_id}/spaces",
    response_model=ParkingSpaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add parking space to property",
)
async def create_parking_space(
    property_id: uuid.UUID,
    payload: ParkingSpaceCreate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> ParkingSpaceResponse:
    """Add a new parking bay with dimensions and EV charging capabilities."""
    space = await ParkingSpaceService.create_space(db, property_id, current_user, payload)
    return ParkingSpaceResponse.model_validate(space)


@router.get(
    "/{property_id}/spaces",
    response_model=list[ParkingSpaceResponse],
    status_code=status.HTTP_200_OK,
    summary="List parking spaces on property",
)
async def list_parking_spaces(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ParkingSpaceResponse]:
    """List all parking spaces associated with the property."""
    spaces = await ParkingSpaceService.list_spaces(db, property_id)
    return [ParkingSpaceResponse.model_validate(s) for s in spaces]


@router.put(
    "/{property_id}/spaces/{space_id}",
    response_model=ParkingSpaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update parking space",
)
async def update_property_parking_space(
    property_id: uuid.UUID,
    space_id: uuid.UUID,
    payload: ParkingSpaceUpdate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> ParkingSpaceResponse:
    """Update parking space dimensions, tariffs, or status."""
    space = await ParkingSpaceService.update_space(db, space_id, current_user, payload)
    return ParkingSpaceResponse.model_validate(space)


@router.post(
    "/{property_id}/spaces/{space_id}/compatibility",
    response_model=VehicleCompatibilityCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check vehicle compatibility for bay",
)
async def check_vehicle_compatibility_on_property(
    property_id: uuid.UUID,
    space_id: uuid.UUID,
    payload: VehicleCompatibilityCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VehicleCompatibilityCheckResponse:
    """Verify vehicle physical clearance and EV charging capability."""
    space = await ParkingSpaceService.get_space(db, space_id)
    return await ParkingSpaceService.check_compatibility(db, space, payload)


# =============================================================================
# Operating Hours Endpoints (/api/v1/properties/{id}/operating-hours)
# =============================================================================


@router.post(
    "/{property_id}/operating-hours",
    response_model=OperatingScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add operating schedule window",
)
async def add_operating_schedule(
    property_id: uuid.UUID,
    payload: OperatingScheduleCreate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> OperatingScheduleResponse:
    """Configure weekly recurring operating hours with non-overlapping window validation."""
    sch = await ScheduleService.add_operating_schedule(db, property_id, current_user, payload)
    return OperatingScheduleResponse.model_validate(sch)


@router.get(
    "/{property_id}/operating-hours",
    response_model=list[OperatingScheduleResponse],
    status_code=status.HTTP_200_OK,
    summary="List operating schedule windows",
)
async def list_operating_schedules(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OperatingScheduleResponse]:
    """List all active recurring operating schedules for the property."""
    schedules = await ScheduleService.list_operating_schedules(db, property_id)
    return [OperatingScheduleResponse.model_validate(s) for s in schedules]


@router.delete(
    "/{property_id}/operating-hours/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete operating schedule window",
)
async def delete_operating_schedule(
    property_id: uuid.UUID,
    schedule_id: uuid.UUID,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an operating schedule window with owner authorization."""
    await ScheduleService.delete_operating_schedule(db, property_id, schedule_id, current_user)


# =============================================================================
# Property Blackouts Endpoints (/api/v1/properties/{id}/blackouts)
# =============================================================================


@router.post(
    "/{property_id}/blackouts",
    response_model=BlackoutScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add property blackout window",
)
async def add_property_blackout(
    property_id: uuid.UUID,
    payload: BlackoutScheduleCreate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> BlackoutScheduleResponse:
    """Schedule property-level or bay blackout window with overlap conflict checks."""
    bo = await ScheduleService.add_blackout(
        db=db,
        property_id=property_id,
        user=current_user,
        payload=payload,
    )
    return BlackoutScheduleResponse.model_validate(bo)


@router.get(
    "/{property_id}/blackouts",
    response_model=list[BlackoutScheduleResponse],
    status_code=status.HTTP_200_OK,
    summary="List property blackout windows",
)
async def list_property_blackouts(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BlackoutScheduleResponse]:
    """List active blackout schedules for the property."""
    blackouts = await ScheduleService.list_blackouts(db, property_id)
    return [BlackoutScheduleResponse.model_validate(b) for b in blackouts]


@router.delete(
    "/{property_id}/blackouts/{blackout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property blackout window",
)
async def delete_property_blackout(
    property_id: uuid.UUID,
    blackout_id: uuid.UUID,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete / cancel a blackout schedule."""
    await ScheduleService.delete_blackout(db, blackout_id, current_user)


# =============================================================================
# Standalone Space Endpoints (/api/v1/spaces/{space_id}/...)
# =============================================================================


@spaces_router.get(
    "/{space_id}",
    response_model=ParkingSpaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get parking space details",
)
async def get_space_by_id(
    space_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParkingSpaceResponse:
    """Retrieve parking space details."""
    space = await ParkingSpaceService.get_space(db, space_id)
    return ParkingSpaceResponse.model_validate(space)


@spaces_router.put(
    "/{space_id}",
    response_model=ParkingSpaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update parking space",
)
async def update_space_by_id(
    space_id: uuid.UUID,
    payload: ParkingSpaceUpdate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> ParkingSpaceResponse:
    """Update parking space dimensions, tariffs, or status."""
    space = await ParkingSpaceService.update_space(db, space_id, current_user, payload)
    return ParkingSpaceResponse.model_validate(space)


@spaces_router.post(
    "/{space_id}/blackouts",
    response_model=BlackoutScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add space blackout window",
)
async def add_space_blackout(
    space_id: uuid.UUID,
    payload: BlackoutScheduleCreate,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> BlackoutScheduleResponse:
    """Add a blackout window dedicated to a specific parking bay."""
    space = await ParkingSpaceService.get_space(db, space_id)
    bo = await ScheduleService.add_blackout(
        db=db,
        property_id=space.property_id,
        user=current_user,
        payload=payload,
        parking_space_id=space_id,
    )
    return BlackoutScheduleResponse.model_validate(bo)


@spaces_router.delete(
    "/{space_id}/blackouts/{blackout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete space blackout window",
)
async def delete_space_blackout(
    space_id: uuid.UUID,
    blackout_id: uuid.UUID,
    current_user: User = Depends(require_space_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a blackout window for a parking bay."""
    await ScheduleService.delete_blackout(db, blackout_id, current_user)


@spaces_router.post(
    "/{space_id}/compatibility",
    response_model=VehicleCompatibilityCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check vehicle compatibility for bay",
)
async def check_vehicle_compatibility_standalone(
    space_id: uuid.UUID,
    payload: VehicleCompatibilityCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VehicleCompatibilityCheckResponse:
    """Verify vehicle physical clearance and EV charging capability."""
    space = await ParkingSpaceService.get_space(db, space_id)
    return await ParkingSpaceService.check_compatibility(db, space, payload)
