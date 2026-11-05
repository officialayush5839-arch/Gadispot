"""6-Stage Canonical Refund State Machine and Lifecycle Service.

Canonical States:
1. NONE: Initial state, no refund requested or eligible.
2. REFUND_ELIGIBLE: Driver cancelled within grace period or GPRP failed to find alternative space.
3. REFUND_REQUESTED: Refund initiated by platform service and enqueued for payment gateway dispatch.
4. GATEWAY_ACCEPTED: Payment gateway acknowledged refund request with a valid gateway refund ID.
5. REFUND_PROCESSING: Acquiring bank is processing refund batch.
6. REFUND_SETTLED: Bank ARN/UTR settlement confirmed; funds credited back to driver account.
(Terminal error: REFUND_FAILED - gateway rejection or bank routing error).
"""

import logging
import uuid
from datetime import datetime, timezone

from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.enums import RefundStatusEnum
from app.models.reservations import SpaceReservation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("gadispot.refunds")

# Directed acyclic graph of allowed refund status transitions
LEGAL_REFUND_TRANSITIONS: dict[RefundStatusEnum, list[RefundStatusEnum]] = {
    RefundStatusEnum.NONE: [
        RefundStatusEnum.REFUND_ELIGIBLE,
    ],
    RefundStatusEnum.REFUND_ELIGIBLE: [
        RefundStatusEnum.REFUND_REQUESTED,
        RefundStatusEnum.NONE,  # Driver uncancelled / administrative reversal
    ],
    RefundStatusEnum.REFUND_REQUESTED: [
        RefundStatusEnum.GATEWAY_ACCEPTED,
        RefundStatusEnum.REFUND_PROCESSING,
        RefundStatusEnum.REFUND_FAILED,
    ],
    RefundStatusEnum.GATEWAY_ACCEPTED: [
        RefundStatusEnum.REFUND_PROCESSING,
        RefundStatusEnum.REFUND_SETTLED,
        RefundStatusEnum.REFUND_FAILED,
    ],
    RefundStatusEnum.REFUND_PROCESSING: [
        RefundStatusEnum.REFUND_SETTLED,
        RefundStatusEnum.REFUND_FAILED,
    ],
    RefundStatusEnum.REFUND_SETTLED: [],  # Terminal immutable state
    RefundStatusEnum.REFUND_FAILED: [
        RefundStatusEnum.REFUND_REQUESTED,  # Allow retry by operations/worker
    ],
}


class RefundService:
    """Service managing the canonical 6-stage refund lifecycle with invariant validation."""

    @staticmethod
    def validate_transition(
        current_status: RefundStatusEnum,
        target_status: RefundStatusEnum,
    ) -> None:
        """Enforce state machine invariant preventing illegal refund transitions."""
        if current_status == target_status:
            return  # Idempotent no-op

        allowed = LEGAL_REFUND_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise ConflictException(
                detail=(
                    f"Illegal refund state transition from '{current_status.value}' "
                    f"to '{target_status.value}'. Permitted transitions: {[s.value for s in allowed]}."
                ),
                title="Invalid Refund State Transition",
                code="ILLEGAL_REFUND_TRANSITION",
            )

    @classmethod
    async def mark_refund_eligible(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        reason: str,
    ) -> SpaceReservation:
        """Mark a reservation as eligible for refund following cancellation or unfulfillable booking."""
        stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        result = await db.execute(stmt)
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        cls.validate_transition(reservation.refund_status, RefundStatusEnum.REFUND_ELIGIBLE)
        reservation.refund_status = RefundStatusEnum.REFUND_ELIGIBLE
        reservation.refund_failure_reason = None
        await db.flush()
        return reservation

    @classmethod
    async def request_refund(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        reason: str,
    ) -> SpaceReservation:
        """Transition refund status to REFUND_REQUESTED and record initiation timestamp."""
        stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        result = await db.execute(stmt)
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        cls.validate_transition(reservation.refund_status, RefundStatusEnum.REFUND_REQUESTED)
        now = datetime.now(timezone.utc)
        reservation.refund_status = RefundStatusEnum.REFUND_REQUESTED
        reservation.refund_initiated_at = now
        await db.flush()
        return reservation

    @classmethod
    async def record_gateway_acceptance(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        gateway_refund_id: str,
    ) -> SpaceReservation:
        """Record gateway acceptance of refund request."""
        stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        result = await db.execute(stmt)
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        cls.validate_transition(reservation.refund_status, RefundStatusEnum.GATEWAY_ACCEPTED)
        reservation.refund_status = RefundStatusEnum.GATEWAY_ACCEPTED
        reservation.refund_gateway_id = gateway_refund_id
        await db.flush()
        return reservation

    @classmethod
    async def record_refund_settled(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        arn_utr: str,
        gateway_refund_id: str | None = None,
    ) -> SpaceReservation:
        """Record terminal settlement of refund with verifiable bank ARN/UTR reference."""
        if not arn_utr or len(arn_utr.strip()) < 4:
            raise ValidationException(
                detail="Settlement requires a valid bank ARN/UTR reference identifier.",
                code="ARN_UTR_REQUIRED",
            )

        stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        result = await db.execute(stmt)
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        cls.validate_transition(reservation.refund_status, RefundStatusEnum.REFUND_SETTLED)
        now = datetime.now(timezone.utc)
        reservation.refund_status = RefundStatusEnum.REFUND_SETTLED
        reservation.refund_arn_utr = arn_utr.strip()
        reservation.refund_completed_at = now
        if gateway_refund_id:
            reservation.refund_gateway_id = gateway_refund_id
        await db.flush()
        return reservation

    @classmethod
    async def record_refund_failed(
        cls,
        db: AsyncSession,
        reservation_id: uuid.UUID,
        failure_reason: str,
    ) -> SpaceReservation:
        """Record refund failure with descriptive reason for operational investigation."""
        stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id).with_for_update()
        result = await db.execute(stmt)
        reservation = result.scalar_one_or_none()
        if not reservation:
            raise EntityNotFoundException(
                detail=f"Reservation {reservation_id} not found",
                code="RESERVATION_NOT_FOUND",
            )

        cls.validate_transition(reservation.refund_status, RefundStatusEnum.REFUND_FAILED)
        reservation.refund_status = RefundStatusEnum.REFUND_FAILED
        reservation.refund_failure_reason = failure_reason[:500]
        await db.flush()
        return reservation
