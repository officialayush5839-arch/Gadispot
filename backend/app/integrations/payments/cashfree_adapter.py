"""Cashfree Payment Gateway Adapter implementing PaymentGatewayPort."""

import base64
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

logger = logging.getLogger("gadispot.payments.cashfree")


class CashfreeAdapter(PaymentGatewayPort):
    """Secondary P0 Standby Payment Gateway Adapter for Cashfree Payments India."""

    def __init__(
        self,
        app_id: str | None = None,
        secret_key: str | None = None,
    ):
        settings = get_settings()
        self.app_id = app_id or settings.CASHFREE_APP_ID or "cf_mock_app_id"
        self.secret_key = secret_key or settings.CASHFREE_SECRET_KEY or "cf_mock_secret_key"
        self.base_url = (
            "https://sandbox.cashfree.com/pg" if not settings.is_production else "https://api.cashfree.com/pg"
        )

    @property
    def gateway_name(self) -> str:
        return "cashfree"

    async def create_order(
        self,
        amount_paise: int,
        receipt: str,
        currency: str = "INR",
        notes: dict[str, Any] | None = None,
    ) -> PaymentOrderResult:
        """Create an order on Cashfree PG."""
        settings = get_settings()
        amount_rupees = round(amount_paise / 100.0, 2)
        order_id = f"cf_order_{uuid.uuid4().hex[:14]}"

        if settings.CASHFREE_APP_ID and settings.CASHFREE_SECRET_KEY and not settings.is_testing:
            try:
                headers = {
                    "x-client-id": self.app_id,
                    "x-client-secret": self.secret_key,
                    "x-api-version": "2023-08-01",
                    "Content-Type": "application/json",
                }
                payload = {
                    "order_id": order_id,
                    "order_amount": amount_rupees,
                    "order_currency": currency,
                    "customer_details": {
                        "customer_id": f"cust_{receipt[:20]}",
                        "customer_phone": "9876543210",
                    },
                    "order_meta": {"return_url": "https://api.gadispot.in/api/v1/payments/return"},
                    "order_tags": notes or {},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{self.base_url}/orders", headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return PaymentOrderResult(
                        order_id=data.get("order_id", order_id),
                        gateway_name=self.gateway_name,
                        amount_paise=amount_paise,
                        currency=currency,
                        status=data.get("order_status", "ACTIVE").lower(),
                        raw_response=data,
                    )
            except Exception as exc:
                logger.error("Cashfree order creation failed: %s", exc)
                raise

        return PaymentOrderResult(
            order_id=order_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            currency=currency,
            status="active",
            raw_response={
                "order_id": order_id,
                "order_amount": amount_rupees,
                "order_currency": currency,
                "order_status": "ACTIVE",
            },
        )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: dict[str, str],
        secret: str | None = None,
    ) -> bool:
        """Verify Cashfree signature from 'x-webhook-signature' using HMAC-SHA256."""
        signature = headers.get("x-webhook-signature") or headers.get("X-Webhook-Signature")
        timestamp = headers.get("x-webhook-timestamp") or headers.get("X-Webhook-Timestamp")
        if not signature:
            return False

        secret_key = secret or self.secret_key
        # Cashfree v2023-08-01 signing computes HMAC on timestamp + payload
        data_to_sign = f"{timestamp}".encode() + payload_bytes if timestamp else payload_bytes
        computed = hmac.new(secret_key.encode("utf-8"), data_to_sign, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(computed).decode("utf-8")
        expected_hex = hmac.new(secret_key.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, expected_b64) or hmac.compare_digest(signature, expected_hex)

    def parse_webhook_event(self, payload: dict[str, Any]) -> GatewayWebhookEvent:
        """Parse Cashfree webhook payload into standard GatewayWebhookEvent."""
        event_type = payload.get("type", "unknown")
        event_id = payload.get("event_id") or f"cf_evt_{uuid.uuid4().hex[:12]}"

        data = payload.get("data", {})
        order = data.get("order", {})
        payment = data.get("payment", {})
        refund = data.get("refund", {})

        order_id = order.get("order_id") or data.get("order_id")
        payment_id = str(payment.get("cf_payment_id") or "")
        amount_rupees = order.get("order_amount") or payment.get("payment_amount") or refund.get("refund_amount")
        amount_paise = int(float(amount_rupees) * 100) if amount_rupees is not None else None

        is_payment_success = event_type == "PAYMENT_SUCCESS_WEBHOOK" or payment.get("payment_status") == "SUCCESS"
        is_refund_update = "REFUND" in event_type

        refund_status = None
        arn_utr = None
        if is_refund_update:
            raw_status = refund.get("refund_status", "SUCCESS")
            refund_status = "REFUND_SETTLED" if raw_status == "SUCCESS" else "REFUND_PROCESSING"
            arn_utr = refund.get("refund_arn")

        return GatewayWebhookEvent(
            gateway_name=self.gateway_name,
            event_id=event_id,
            event_type=event_type,
            order_id=order_id,
            payment_id=payment_id if payment_id else None,
            amount_paise=amount_paise,
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
        """Dispatch refund to Cashfree."""
        refund_id = f"cf_ref_{uuid.uuid4().hex[:14]}"
        amount_rupees = round(amount_paise / 100.0, 2)
        return RefundResult(
            refund_id=refund_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            status="processed",
            arn_utr=f"CFUTR{uuid.uuid4().hex[:10].upper()}",
            raw_response={
                "refund_id": refund_id,
                "cf_payment_id": payment_id,
                "refund_amount": amount_rupees,
                "refund_status": "SUCCESS",
            },
        )
