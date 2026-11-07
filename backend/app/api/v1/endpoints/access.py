"""Gate admission access pass generation, verification, and single-use replay burning."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import verify_resource_ownership
from app.core.dependencies import get_current_user_optional, get_db
from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.models.access import AccessCredential, generate_access_credentials
from app.models.enums import (
    ReservationStatusEnum,
    TokenStatusEnum,
    TokenTypeEnum,
    UserRoleEnum,
)
from app.models.reservations import SpaceReservation
from app.models.users import User
from app.schemas.access import (
    IssueTokensRequest,
    IssueTokensResponse,
    ValidateScanRequest,
    ValidateScanResponse,
)

router = APIRouter()


@router.post(
    "/issue-tokens",
    response_model=IssueTokensResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue 128-bit CSPRNG ENTRY and EXIT access tokens for confirmed booking",
)
async def issue_access_tokens(
    payload: IssueTokensRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> IssueTokensResponse:
    """Generate separate entry and exit access passes for a confirmed reservation."""
    stmt = select(SpaceReservation).where(SpaceReservation.id == payload.reservation_id).with_for_update()
    result = await db.execute(stmt)
    res = result.scalar_one_or_none()
    if not res:
        raise EntityNotFoundException(
            detail=f"Reservation {payload.reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    if current_user:
        verify_resource_ownership(current_user, res.driver_id, allow_privileged=True)

    if res.status not in (
        ReservationStatusEnum.CONFIRMED,
        ReservationStatusEnum.ACTIVE_SESSION,
    ):
        raise ValidationException(
            detail=f"Cannot issue access passes for reservation in status {res.status.value}",
            code="INVALID_RESERVATION_STATUS",
        )

    now = datetime.now(timezone.utc)
    entry_cred, exit_cred = generate_access_credentials(reservation_id=res.id)
    entry_token = entry_cred.opaque_token
    exit_token = exit_cred.opaque_token

    db.add(entry_cred)
    db.add(exit_cred)
    await db.flush()

    return IssueTokensResponse(
        reservation_id=res.id,
        entry_token=entry_token,
        exit_token=exit_token,
        valid_from=entry_cred.valid_from,
        valid_until=entry_cred.valid_until,
    )


@router.post(
    "/validate-scan",
    response_model=ValidateScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate guard gate scan and burn token atomically",
)
async def validate_gate_scan(
    payload: ValidateScanRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> ValidateScanResponse:
    """Validate access pass, guard against replay attacks, and update session state."""
    guard_id = payload.guard_id
    if current_user:
        user_roles = set(current_user.canonical_role_names)
        allowed = {UserRoleEnum.GUARD.value, UserRoleEnum.ADMIN.value}
        if not user_roles.intersection(allowed):
            raise ForbiddenException(
                detail="Guard clearance required to validate gate scan.",
                title="Insufficient Permissions",
                code="GUARD_ROLE_REQUIRED",
            )
        guard_id = current_user.id

    stmt = select(AccessCredential).where(AccessCredential.opaque_token == payload.opaque_token).with_for_update()
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    if not cred:
        raise EntityNotFoundException(
            detail="Access pass token not found or invalid",
            code="INVALID_ACCESS_PASS",
        )

    # Replay check
    if cred.status == TokenStatusEnum.CONSUMED:
        raise ConflictException(
            detail="Access token has already been consumed (replay attempt detected)",
            code="TOKEN_ALREADY_CONSUMED",
        )

    now = datetime.now(timezone.utc)
    cred.status = TokenStatusEnum.CONSUMED
    cred.consumed_at = now
    cred.consumed_by_guard_id = guard_id

    # Update associated reservation state
    res_stmt = select(SpaceReservation).where(SpaceReservation.id == cred.reservation_id).with_for_update()
    res_result = await db.execute(res_stmt)
    res = res_result.scalar_one_or_none()

    if cred.token_type == TokenTypeEnum.ENTRY:
        if res:
            res.status = ReservationStatusEnum.ACTIVE_SESSION
        msg = "Entry gate scan verified; session activated"
    else:
        if res:
            res.status = ReservationStatusEnum.COMPLETED
        msg = "Exit gate scan verified; session completed"

    await db.flush()

    return ValidateScanResponse(
        status="SUCCESS",
        message=msg,
        token_type=cred.token_type.value,
        reservation_id=cred.reservation_id,
        consumed_at=now,
    )
