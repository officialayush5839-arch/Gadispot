"""Razorpay Payment Gateway Adapter implementing PaymentGatewayPort."""

import hashlib
import hmac
import logging
import uuid
from typing import Any

import httpx
from app.core.config import get_settings
from app.integrations.payments.base import (
    GatewayWebhookEvent,
    PaymentGatewayPort,
    PaymentOrderResult,
    RefundResult,
)

logger = logging.getLogger("gadispot.payments.razorpay")


class RazorpayAdapter(PaymentGatewayPort):
    """Primary P0 Payment Gateway Adapter for Razorpay India."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ):
        settings = get_settings()
        self.key_id = key_id or settings.RAZORPAY_KEY_ID or "rzp_test_mock_key_id"
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET or "rzp_test_mock_secret"
        self.webhook_secret = webhook_secret or self.key_secret
        self.base_url = "https://api.razorpay.com/v1"

    @property
    def gateway_name(self) -> str:
        return "razorpay"

    async def create_order(
        self,
        amount_paise: int,
        receipt: str,
        currency: str = "INR",
        notes: dict[str, Any] | None = None,
    ) -> PaymentOrderResult:
        """Create an order via Razorpay Orders API."""
        settings = get_settings()

        # If live credentials available, dispatch real HTTPS request
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and not settings.is_testing:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/orders",
                        auth=(self.key_id, self.key_secret),
                        json={
                            "amount": amount_paise,
                            "currency": currency,
                            "receipt": receipt[:40],
                            "notes": notes or {},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return PaymentOrderResult(
                        order_id=data["id"],
                        gateway_name=self.gateway_name,
                        amount_paise=data["amount"],
                        currency=data["currency"],
                        status=data.get("status", "created"),
                        raw_response=data,
                    )
            except Exception as exc:
                logger.error("Razorpay API order creation failed: %s", exc)
                raise

        # Deterministic order generation for development/test
        generated_order_id = f"order_{uuid.uuid4().hex[:14]}"
        return PaymentOrderResult(
            order_id=generated_order_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            currency=currency,
            status="created",
            raw_response={
                "id": generated_order_id,
                "entity": "order",
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
            },
        )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: dict[str, str],
        secret: str | None = None,
    ) -> bool:
        """Verify HMAC-SHA256 signature from 'x-razorpay-signature' header."""
        signature = headers.get("x-razorpay-signature") or headers.get("X-Razorpay-Signature")
        if not signature:
            return False

        secret_key = secret or self.webhook_secret
        expected = hmac.new(
            secret_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify client-submitted payment signature: HMAC(order_id + '|' + payment_id)."""
        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected = hmac.new(
            self.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(razorpay_signature, expected)

    def parse_webhook_event(self, payload: dict[str, Any]) -> GatewayWebhookEvent:
        """Parse Razorpay webhook payload into standard GatewayWebhookEvent."""
        event_type = payload.get("event", "unknown")
        event_id = payload.get("id") or f"rzp_evt_{uuid.uuid4().hex[:12]}"

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})

        order_id = payment_entity.get("order_id") or order_entity.get("id")
        payment_id = payment_entity.get("id")
        amount = payment_entity.get("amount") or order_entity.get("amount") or refund_entity.get("amount")

        is_payment_success = event_type == "payment.captured"
        is_refund_update = event_type.startswith("refund.")

        refund_status = None
        arn_utr = None
        if is_refund_update:
            raw_status = refund_entity.get("status", "processed")
            refund_status = "REFUND_SETTLED" if raw_status == "processed" else "REFUND_PROCESSING"
            arn_utr = refund_entity.get("acquirer_data", {}).get("arn") or refund_entity.get("acquirer_data", {}).get(
                "rrn"
            )

        return GatewayWebhookEvent(
            gateway_name=self.gateway_name,
            event_id=event_id,
            event_type=event_type,
            order_id=order_id,
            payment_id=payment_id,
            amount_paise=amount,
            is_payment_success=is_payment_success,
            is_refund_update=is_refund_update,
            refund_status=refund_status,
            refund_arn_utr=arn_utr,
            payload=payload,
        )

    async def process_refund(
        self,
        payment_id: str,
        amount_paise: int,
        reason: str,
        notes: dict[str, Any] | None = None,
    ) -> RefundResult:
        """Dispatch refund to Razorpay."""
        settings = get_settings()

        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and not settings.is_testing:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/payments/{payment_id}/refund",
                        auth=(self.key_id, self.key_secret),
                        json={
                            "amount": amount_paise,
                            "notes": notes or {"reason": reason},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return RefundResult(
                        refund_id=data["id"],
                        gateway_name=self.gateway_name,
                        amount_paise=data["amount"],
                        status=data.get("status", "processed"),
                        arn_utr=data.get("acquirer_data", {}).get("arn"),
                        raw_response=data,
                    )
            except Exception as exc:
                logger.error("Razorpay refund execution failed: %s", exc)
                raise

        generated_refund_id = f"rfnd_{uuid.uuid4().hex[:14]}"
        return RefundResult(
            refund_id=generated_refund_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            status="processed",
            arn_utr=f"UTR{uuid.uuid4().hex[:10].upper()}",
            raw_response={
                "id": generated_refund_id,
                "payment_id": payment_id,
                "amount": amount_paise,
                "status": "processed",
            },
        )
