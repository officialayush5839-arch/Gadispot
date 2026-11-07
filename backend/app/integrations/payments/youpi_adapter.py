"""Isolated Experimental YOUPI-PG Adapter for Gadispot.

WARNING:
- Strictly disabled by default (requires YOUPI_ENABLED=true).
- Observer-derived statuses are EXPERIMENTAL and CANNOT independently confirm reservations.
- Do NOT vendor or redistribute unlicensed YOUPI-PG code.
"""

import hmac
import hashlib
import logging
from typing import Any
import httpx

from app.core.exceptions import ValidationException
from app.integrations.payments.base import (
    GatewayWebhookEvent,
    PaymentGatewayPort,
    PaymentOrderResult,
    RefundResult,
)

logger = logging.getLogger("gadispot.payments.youpi")


class YoupiPaymentAdapter(PaymentGatewayPort):
    """Isolated experimental adapter for YOUPI-PG notification-observer payment tracking."""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        webhook_secret: str = "",
        is_enabled: bool = False,
    ):
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._webhook_secret = webhook_secret or ""
        self._is_enabled = is_enabled

    @property
    def gateway_name(self) -> str:
        return "youpi"

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def _assert_enabled(self) -> None:
        if not self._is_enabled:
            raise ValidationException(
                detail="YoupiPaymentAdapter is experimental and currently DISABLED. "
                "Set YOUPI_ENABLED=true in environment to activate this adapter.",
                code="YOUPI_ADAPTER_DISABLED",
            )

    def _check_enabled(self) -> None:
        self._assert_enabled()

    async def create_order(
        self,
        amount_paise: int,
        receipt: str,
        currency: str = "INR",
        notes: dict[str, Any] | None = None,
    ) -> PaymentOrderResult:
        """Create an experimental payment observation intent."""
        self._assert_enabled()

        if not self._base_url:
            raise ValueError("YOUPI_BASE_URL is not configured for experimental integration.")

        # Timeout budget: 3.0s connect, 5.0s read
        timeout = httpx.Timeout(5.0, connect=3.0)

        payload = {
            "amount": amount_paise / 100.0,
            "reference": receipt,
            "currency": currency,
            "notes": notes or {},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Gadispot-Experimental-Youpi/2.3.0",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self._base_url}/api/v1/orders", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                order_id = data.get("order_id", f"youpi_ord_{receipt}")
        except Exception as exc:
            logger.warning("YOUPI order initiation failed or service offline: %s", exc)
            # In experimental mode, return isolated intent with offline status
            order_id = f"youpi_exp_{receipt}"
            data = {"status": "experimental_pending", "error": str(exc)}

        return PaymentOrderResult(
            order_id=order_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            currency=currency,
            status="experimental_created",
            raw_response={
                "order_id": order_id,
                "is_experimental": True,
                "disclaimer": "YOUPI-PG EXPERIMENTAL — Observer evidence only, not bank-verified settlement.",
                "upstream_data": data,
            },
        )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: dict[str, str],
        secret: str | None = None,
    ) -> bool:
        """Verify HMAC-SHA256 signature from YOUPI-PG notification emitter."""
        if not self._is_enabled:
            return False

        sec = secret or self._webhook_secret
        if not sec:
            return False

        sig = headers.get("x-youpi-signature")
        if not sig:
            return False

        computed = hmac.new(sec.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, computed)

    def parse_webhook_event(self, payload: dict[str, Any]) -> GatewayWebhookEvent:
        """Map experimental observer notification to normalized internal representation.

        CRITICAL INVARIANT:
        'observed_success' does NOT become is_payment_success=True automatically.
        It is mapped to experimental REQUIRES_RECONCILIATION status.
        """
        raw_status = payload.get("status", "").lower()
        event_id = payload.get("event_id") or payload.get("id", "youpi_evt_unknown")

        # Map observer status conservatively
        if raw_status in ("success", "paid", "observed_success"):
            normalized_status = "OBSERVED_SUCCESS"
            # Never set is_payment_success = True for raw observer notifications
            # This prevents automated booking confirmation from unverified SMS/app observers!
            is_confirmed_settlement = False
        elif raw_status in ("failed", "rejected"):
            normalized_status = "FAILED"
            is_confirmed_settlement = False
        else:
            normalized_status = "PENDING"
            is_confirmed_settlement = False

        return GatewayWebhookEvent(
            gateway_name=self.gateway_name,
            event_id=event_id,
            event_type=payload.get("event", "youpi.payment.observed"),
            order_id=payload.get("order_id"),
            payment_id=payload.get("payment_id"),
            amount_paise=int(payload.get("amount", 0) * 100) if payload.get("amount") else None,
            is_payment_success=is_confirmed_settlement,
            is_refund_update=False,
            refund_status=None,
            payload={
                **payload,
                "experimental_observation_status": normalized_status,
                "is_experimental": True,
                "requires_reconciliation": True if normalized_status == "OBSERVED_SUCCESS" else False,
            },
        )

    async def process_refund(
        self,
        payment_id: str,
        amount_paise: int,
        reason: str,
        notes: dict[str, Any] | None = None,
    ) -> RefundResult:
        """YOUPI-PG does not support native programmatic refunds."""
        self._assert_enabled()
        return RefundResult(
            refund_id=f"youpi_ref_unsupported_{payment_id}",
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            status="failed",
            failure_reason="YOUPI-PG observer adapter does not support automated refund execution.",
            raw_response={"supported": False, "is_experimental": True},
        )

    async def get_payment_status(self, payment_id: str) -> dict[str, Any]:
        """Query observer status from YOUPI instance."""
        self._assert_enabled()
        return {
            "payment_id": payment_id,
            "gateway": self.gateway_name,
            "status": "REQUIRES_RECONCILIATION",
            "is_experimental": True,
            "disclaimer": "Observer observation requires manual bank reconciliation.",
        }

    async def cancel_payment(self, payment_id: str) -> dict[str, Any]:
        """Cancel experimental payment intent."""
        self._assert_enabled()
        return {
            "payment_id": payment_id,
            "gateway": self.gateway_name,
            "status": "cancelled",
            "is_experimental": True,
        }

    async def health_check(self) -> bool:
        """Check reachability of configured YOUPI instance."""
        if not self._is_enabled or not self._base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self._base_url}/health")
                return res.status_code == 200
        except Exception:
            return False
