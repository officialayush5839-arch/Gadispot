"""Payment initiation, dynamic UPI QR generation, simulation triggers, and refund management endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import (
    require_roles,
    verify_resource_ownership,
)
from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_current_user_optional, get_db
from app.core.exceptions import EntityNotFoundException
from app.integrations.payments.factory import PaymentGatewayFactory
from app.integrations.payments.upi_qr_service import (
    build_upi_payment_uri,
    generate_upi_qr_base64,
)
from app.models.enums import RefundStatusEnum, UserRoleEnum
from app.models.reservations import SpaceReservation
from app.models.users import User
from app.schemas.payments import (
    CreateOrderRequest,
    CreateOrderResponse,
    DemoCompleteRequest,
    DemoCompleteResponse,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentDetailResponse,
    PayoutBatchResponse,
    ProviderListResponse,
    RefundRequest,
    RefundResponse,
    UpiQrRequest,
    UpiQrResponse,
)
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService
from app.services.refund_service import RefundService

router = APIRouter()


@router.get(
    "/providers",
    response_model=ProviderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available payment gateways and active execution mode",
)
async def list_payment_providers() -> ProviderListResponse:
    """Retrieve supported payment gateways and system operation flags."""
    app_settings = get_settings()
    return ProviderListResponse(
        active_mode=app_settings.PAYMENT_MODE,
        demo_enabled=app_settings.DEMO_PAYMENTS_ENABLED,
        supported_providers=PaymentGatewayFactory.get_supported_gateways(),
    )


@router.post(
    "",
    response_model=InitiatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate payment checkout for an active reservation hold",
)
async def initiate_payment(
    payload: InitiatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InitiatePaymentResponse:
    """Create a verified payment intent, enforce pricing quote, and associate with reservation."""
    res = await PaymentService.create_payment(
        db=db,
        reservation_id=payload.reservation_id,
        driver_id=current_user.id,
        gateway_name=payload.gateway,
        idempotency_key=payload.idempotency_key,
    )
    payment = res["payment"]
    return InitiatePaymentResponse(
        payment_id=payment.id,
        reservation_id=payment.reservation_id,
        order_id=res["order_id"],
        amount_paise=res["amount_paise"],
        currency=res.get("currency", "INR"),
        status=payment.status.value,
        gateway=payload.gateway,
        is_simulated=res["is_simulated"],
        is_experimental=res.get("is_experimental", False),
        quote=res.get("quote"),
    )


@router.post(
    "/{payment_id}/demo/complete",
    response_model=DemoCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute simulated payment outcome (Strictly disabled in production)",
)
async def complete_demo_payment(
    payment_id: uuid.UUID,
    payload: DemoCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DemoCompleteResponse:
    """Simulate a deterministic payment outcome for hackathon evaluation and local testing."""
    res = await PaymentService.complete_demo_payment(
        db=db,
        payment_id=payment_id,
        driver_id=current_user.id,
        outcome=payload.outcome,
        reason=payload.reason,
    )
    return DemoCompleteResponse(
        payment_id=res["payment_id"],
        reservation_id=res["reservation_id"],
        status=res["status"],
        is_simulated=res["is_simulated"],
        provider_payment_id=res.get("provider_payment_id"),
        failure_reason=res.get("failure_reason"),
        message=res["message"],
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment details and status",
)
async def get_payment_details(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentDetailResponse:
    """Inspect payment state, simulation flags, and gateway identifiers."""
    payment = await PaymentService.get_payment(
        db=db,
        payment_id=payment_id,
        user_id=current_user.id,
    )
    return PaymentDetailResponse(
        id=payment.id,
        reservation_id=payment.reservation_id,
        driver_id=payment.driver_id,
        amount_paise=payment.amount_paise,
        currency=payment.currency,
        provider=payment.provider.value,
        provider_order_id=payment.provider_order_id,
        provider_payment_id=payment.provider_payment_id,
        status=payment.status.value,
        is_simulated=payment.is_simulated,
        is_experimental=payment.is_experimental,
        experimental_status=payment.experimental_status,
        idempotency_key=payment.idempotency_key,
        simulation_scenario=payment.simulation_scenario,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a pending payment intent",
)
async def cancel_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentDetailResponse:
    """Explicitly cancel a pending payment before checkout completion."""
    payment = await PaymentService.cancel_payment(
        db=db,
        payment_id=payment_id,
        user_id=current_user.id,
    )
    return PaymentDetailResponse(
        id=payment.id,
        reservation_id=payment.reservation_id,
        driver_id=payment.driver_id,
        amount_paise=payment.amount_paise,
        currency=payment.currency,
        provider=payment.provider.value,
        provider_order_id=payment.provider_order_id,
        provider_payment_id=payment.provider_payment_id,
        status=payment.status.value,
        is_simulated=payment.is_simulated,
        is_experimental=payment.is_experimental,
        experimental_status=payment.experimental_status,
        idempotency_key=payment.idempotency_key,
        simulation_scenario=payment.simulation_scenario,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.post(
    "/payouts/simulate",
    response_model=PayoutBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger simulated host earnings payout batch",
)
async def simulate_owner_payout(
    current_user: User = Depends(require_roles(UserRoleEnum.OPERATIONS, UserRoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PayoutBatchResponse:
    """Disburse accumulated host liability balances (Account 2010) in demo mode."""
    res = await PayoutService.simulate_owner_payout_batch(db=db)
    return PayoutBatchResponse(
        batch_id=res["batch_id"],
        amount_paise=res["amount_paise"],
        currency=res["currency"],
        status=res["status"],
        settled_at=res["settled_at"],
        utr=res.get("utr"),
        message=res["message"],
    )


@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a payment intent order with selected gateway (Legacy compatibility)",
)
async def create_payment_order(
    payload: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateOrderResponse:
    """Create an order with the selected runtime gateway adapter and associate with reservation."""
    adapter = PaymentGatewayFactory.get_adapter(payload.gateway)

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
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> RefundResponse:
    """Transition reservation into REFUND_REQUESTED and dispatch to gateway adapter."""
    stmt = select(SpaceReservation).where(SpaceReservation.id == payload.reservation_id).with_for_update()
    result = await db.execute(stmt)
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise EntityNotFoundException(
            detail=f"Reservation {payload.reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
        )

    if current_user:
        verify_resource_ownership(current_user, reservation.driver_id, allow_privileged=True)

    if reservation.refund_status == RefundStatusEnum.NONE:
        await RefundService.mark_refund_eligible(db, reservation.id, payload.reason)

    await RefundService.request_refund(db, reservation.id, payload.reason)

    app_settings = get_settings()
    adapter = PaymentGatewayFactory.get_adapter("demo" if app_settings.DEMO_PAYMENTS_ENABLED else "razorpay")
    refund_res = await adapter.process_refund(
        payment_id=reservation.payment_transaction_id or "pay_demo_default",
        amount_paise=payload.amount_paise or 10000,
        reason=payload.reason,
    )

    await RefundService.record_gateway_acceptance(db, reservation.id, refund_res.refund_id)

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
