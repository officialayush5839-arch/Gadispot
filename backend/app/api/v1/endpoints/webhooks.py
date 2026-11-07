"""Payment webhook ingestion endpoint with durable idempotency and signature verification."""

from datetime import datetime, timezone
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.exceptions import UnauthorizedException, ValidationException
from app.integrations.payments.factory import PaymentGatewayFactory
from app.models.enums import PaymentStatusEnum, ReservationStatusEnum
from app.models.payments import Payment, PaymentWebhookEvent
from app.models.reservations import SpaceReservation
from app.services.refund_service import RefundService

logger = logging.getLogger("gadispot.webhooks")

router = APIRouter()


@router.post(
    "/{gateway}",
    status_code=status.HTTP_200_OK,
    summary="Ingest payment gateway webhook with durable deduplication",
)
async def handle_payment_webhook(
    gateway: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Ingest, verify, deduplicate, and process asynchronous payment gateway webhook events."""
    gateway_key = gateway.lower().strip()
    try:
        adapter = PaymentGatewayFactory.get_adapter(gateway_key)
    except ValidationException:
        raise ValidationException(
            detail=f"Unsupported payment gateway '{gateway}'. Supported: {PaymentGatewayFactory.get_supported_gateways()}",
            code="UNSUPPORTED_GATEWAY",
        )

    # 1. Read raw body bytes for cryptographic signature verification
    raw_body = await request.body()
    headers_dict = {k.lower(): v for k, v in request.headers.items()}

    # 2. Verify HMAC cryptographic signature
    # In test/dev environment, allow test header if no production secret is configured
    signature_valid = adapter.verify_webhook_signature(raw_body, headers_dict)
    if (
        not signature_valid
        and not settings.is_production
        and headers_dict.get("x-test-webhook-bypass") == "gadispot-test-secret"
    ):
        signature_valid = True

    if not signature_valid:
        logger.warning("Rejected webhook for %s: invalid HMAC signature", gateway_key)
        raise UnauthorizedException(
            detail=f"Cryptographic signature verification failed for {gateway_key} webhook.",
            code="INVALID_WEBHOOK_SIGNATURE",
        )

    # 3. Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise ValidationException(
            detail=f"Malformed JSON payload: {exc!s}",
            code="MALFORMED_JSON",
        )

    # 4. Normalize event
    event = adapter.parse_webhook_event(payload)

    # 5. Durable Deduplication: Check if (gateway_name, gateway_event_id) already exists
    stmt = select(PaymentWebhookEvent).where(
        PaymentWebhookEvent.gateway_name == adapter.gateway_name,
        PaymentWebhookEvent.gateway_event_id == event.event_id,
    )
    result = await db.execute(stmt)
    existing_event = result.scalar_one_or_none()

    if existing_event:
        logger.info(
            "Idempotent webhook received: %s event %s already processed. Returning 200.",
            adapter.gateway_name,
            event.event_id,
        )
        return {
            "status": "already_processed",
            "gateway": adapter.gateway_name,
            "event_id": event.event_id,
            "processed_at": existing_event.processed_at.isoformat() if existing_event.processed_at else None,
        }

    # 6. Record event in database
    now = datetime.now(timezone.utc)
    webhook_record = PaymentWebhookEvent(
        gateway_name=adapter.gateway_name,
        gateway_event_id=event.event_id,
        event_type=event.event_type,
        payload=payload,
        status="PROCESSED",
        processed_at=now,
    )
    db.add(webhook_record)

    # 7. Apply domain state transition
    if event.is_payment_success and event.order_id:
        # Locate reservation by payment_order_id or booking reference
        res_stmt = (
            select(SpaceReservation)
            .where(
                (SpaceReservation.payment_order_id == event.order_id)
                | (SpaceReservation.booking_reference == event.order_id)
            )
            .with_for_update()
        )
        res_result = await db.execute(res_stmt)
        reservation = res_result.scalar_one_or_none()
        if reservation and reservation.status == ReservationStatusEnum.ACTIVE_HOLD:
            reservation.status = ReservationStatusEnum.CONFIRMED
            reservation.payment_transaction_id = event.payment_id
            logger.info("Reservation %s confirmed via webhook", reservation.id)

        # Update payment table if exists
        stmt_pay = select(Payment).where(Payment.provider_order_id == event.order_id).with_for_update()
        pay_res = await db.execute(stmt_pay)
        payment = pay_res.scalar_one_or_none()
        if payment and payment.status != PaymentStatusEnum.SUCCEEDED:
            payment.status = PaymentStatusEnum.SUCCEEDED
            payment.provider_payment_id = event.payment_id

    elif event.is_refund_update and event.order_id:
        res_stmt = (
            select(SpaceReservation)
            .where(
                (SpaceReservation.payment_order_id == event.order_id)
                | (SpaceReservation.refund_gateway_id == event.payment_id)
            )
            .with_for_update()
        )
        res_result = await db.execute(res_stmt)
        reservation = res_result.scalar_one_or_none()
        if (
            reservation
            and event.refund_status
            and event.refund_status.upper() in ("REFUND_SETTLED", "SETTLED")
            and event.refund_arn_utr
        ):
            try:
                await RefundService.record_refund_settled(
                    db=db,
                    reservation_id=reservation.id,
                    arn_utr=event.refund_arn_utr,
                )
            except Exception as exc:
                logger.warning("Refund settlement update failed: %s", exc)

    await db.flush()

    return {
        "status": "processed",
        "gateway": adapter.gateway_name,
        "event_id": event.event_id,
        "event_type": event.event_type,
    }
