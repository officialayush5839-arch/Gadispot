"""Payment initiation, dynamic UPI QR generation, and refund management endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.integrations.payments.cashfree_adapter import CashfreeAdapter
from app.integrations.payments.hyperswitch_adapter import HyperswitchAdapter
from app.integrations.payments.razorpay_adapter import RazorpayAdapter
from app.integrations.payments.upi_qr_service import (
    build_upi_payment_uri,
    generate_upi_qr_base64,
)
from app.models.enums import RefundStatusEnum
from app.models.reservations import SpaceReservation
from app.schemas.payments import (
    CreateOrderRequest,
    CreateOrderResponse,
    RefundRequest,
    RefundResponse,
    UpiQrRequest,
    UpiQrResponse,
)
from app.services.refund_service import RefundService

router = APIRouter()

ADAPTERS = {
    "razorpay": RazorpayAdapter(),
    "cashfree": CashfreeAdapter(),
    "hyperswitch": HyperswitchAdapter(),
}


@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a payment intent order with selected gateway",
)
async def create_payment_order(
    payload: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateOrderResponse:
    """Create an order with the selected runtime gateway adapter and associate with reservation."""
    adapter = ADAPTERS.get(payload.gateway.lower())
    if not adapter:
        raise ValidationException(
            detail=f"Unsupported gateway '{payload.gateway}'. Supported: {list(ADAPTERS.keys())}",
            code="UNSUPPORTED_GATEWAY",
        )

    # 1. Verify reservation exists
    stmt = select(SpaceReservation).where(SpaceReservation.id == payload.reservation_id).with_for_update()
    result = await db.execute(stmt)
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise EntityNotFoundException(
            detail=f"Reservation {payload.reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    # 2. Invoke gateway adapter
    receipt_id = f"rcpt_{reservation.booking_reference}"
    order_result = await adapter.create_order(
        amount_paise=payload.amount_paise,
        receipt=receipt_id,
        currency=payload.currency,
        notes={"reservation_id": str(reservation.id), "booking_ref": reservation.booking_reference},
    )

    # 3. Store payment_order_id on reservation
    reservation.payment_order_id = order_result.order_id
    await db.flush()

    return CreateOrderResponse(
        order_id=order_result.order_id,
        gateway=order_result.gateway_name,
        amount_paise=order_result.amount_paise,
        currency=order_result.currency,
        status=order_result.status,
    )


@router.post(
    "/generate-upi-qr",
    response_model=UpiQrResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a dynamic NPCI-compliant UPI QR code",
)
async def generate_upi_qr(
    payload: UpiQrRequest,
    db: AsyncSession = Depends(get_db),
) -> UpiQrResponse:
    """Generate dynamic UPI payment URI and high-contrast base64 QR code image."""
    stmt = select(SpaceReservation).where(SpaceReservation.id == payload.reservation_id)
    result = await db.execute(stmt)
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise EntityNotFoundException(
            detail=f"Reservation {payload.reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    transaction_ref = f"GSP{reservation.booking_reference[:12]}"
    upi_uri = build_upi_payment_uri(
        amount_rupees=payload.amount_rupees,
        transaction_ref=transaction_ref,
        payee_vpa=payload.payee_vpa,
        payee_name=payload.payee_name,
        note=payload.note or f"Parking {reservation.booking_reference}",
    )
    qr_b64 = generate_upi_qr_base64(upi_uri)

    return UpiQrResponse(
        upi_uri=upi_uri,
        qr_code_base64=qr_b64,
        transaction_ref=transaction_ref,
        amount_rupees=payload.amount_rupees,
    )


@router.post(
    "/refund/request",
    response_model=RefundResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate a 6-stage refund for a reservation",
)
async def request_refund(
    payload: RefundRequest,
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Transition reservation into REFUND_REQUESTED and dispatch to gateway adapter."""
    # 1. Ensure reservation exists
    stmt = select(SpaceReservation).where(SpaceReservation.id == payload.reservation_id).with_for_update()
    result = await db.execute(stmt)
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise EntityNotFoundException(
            detail=f"Reservation {payload.reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    # 2. Advance through canonical state machine
    if reservation.refund_status == RefundStatusEnum.NONE:
        await RefundService.mark_refund_eligible(db, reservation.id, payload.reason)

    await RefundService.request_refund(db, reservation.id, payload.reason)

    # 3. Dispatch to primary gateway adapter (Razorpay default)
    adapter = ADAPTERS["razorpay"]
    refund_res = await adapter.process_refund(
        payment_id=reservation.payment_transaction_id or "pay_mock_default",
        amount_paise=payload.amount_paise or 10000,
        reason=payload.reason,
    )

    # 4. Advance to GATEWAY_ACCEPTED
    await RefundService.record_gateway_acceptance(db, reservation.id, refund_res.refund_id)

    # If gateway returned instantaneous settlement (or mock test UTR)
    if refund_res.arn_utr:
        await RefundService.record_refund_settled(db, reservation.id, refund_res.arn_utr, refund_res.refund_id)

    await db.flush()

    return RefundResponse(
        reservation_id=reservation.id,
        refund_status=reservation.refund_status.value,
        refund_gateway_id=reservation.refund_gateway_id,
        refund_arn_utr=reservation.refund_arn_utr,
        message="Refund request accepted and processed by gateway",
    )


@router.get(
    "/refund/{reservation_id}/status",
    response_model=RefundResponse,
    status_code=status.HTTP_200_OK,
    summary="Check current 6-stage refund status for a reservation",
)
async def get_refund_status(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Retrieve current refund status and settlement metadata."""
    stmt = select(SpaceReservation).where(SpaceReservation.id == reservation_id)
    result = await db.execute(stmt)
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise EntityNotFoundException(
            detail=f"Reservation {reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    return RefundResponse(
        reservation_id=reservation.id,
        refund_status=reservation.refund_status.value,
        refund_gateway_id=reservation.refund_gateway_id,
        refund_arn_utr=reservation.refund_arn_utr,
        message=f"Current refund status: {reservation.refund_status.value}",
    )
