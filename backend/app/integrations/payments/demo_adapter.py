"""Zero-Cost Simulated Payment Gateway Adapter for Gadispot Demo Mode."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from app.core.exceptions import ValidationException
from app.integrations.payments.base import (
    GatewayWebhookEvent,
    PaymentGatewayPort,
    PaymentOrderResult,
    RefundResult,
)

logger = logging.getLogger("gadispot.payments.demo")


class DemoPaymentAdapter(PaymentGatewayPort):
    """Deterministic, zero-cost payment gateway adapter for hackathon demonstrations and local testing."""

    def __init__(self, is_enabled: bool = True):
        self._is_enabled = is_enabled

    @property
    def gateway_name(self) -> str:
        return "demo"

    async def create_order(
        self,
        amount_paise: int,
        receipt: str,
        currency: str = "INR",
        notes: dict[str, Any] | None = None,
    ) -> PaymentOrderResult:
        """Create a simulated payment intent order."""
        if not self._is_enabled:
            raise ValidationException(
                detail="DemoPaymentAdapter is disabled in the current environment.",
                code="DEMO_ADAPTER_DISABLED",
            )

        order_suffix = uuid.uuid4().hex[:12]
        order_id = f"demo_ord_{order_suffix}"

        return PaymentOrderResult(
            order_id=order_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            currency=currency,
            status="created",
            raw_response={
                "id": order_id,
                "entity": "demo_order",
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "is_simulated": True,
                "disclaimer": "DEMO PAYMENT — No real money transferred or bank accounts connected.",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "notes": notes or {},
            },
        )

    async def simulate_outcome(
        self,
        order_id: str,
        outcome: str = "SUCCESS",
        amount_paise: int | None = None,
        reason: str | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """Generate deterministic simulated outcome for an order."""
        target_scenario = (scenario or outcome or "SUCCESS").upper().strip()
        sim_suffix = uuid.uuid4().hex[:12]
        payment_id = f"demo_pay_{sim_suffix}"
        amt = amount_paise or 0

        if target_scenario == "SUCCESS":
            return {
                "status": "SUCCEEDED",
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_paise": amt,
                "is_simulated": True,
                "failure_reason": None,
                "error": None,
            }
        elif target_scenario == "FAILURE":
            return {
                "status": "FAILED",
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_paise": amt,
                "is_simulated": True,
                "failure_reason": reason or "SIMULATED_PAYMENT_FAILED_USER_DECLINED",
                "error": "SIMULATED_PAYMENT_FAILED_USER_DECLINED",
            }
        elif target_scenario == "CANCEL":
            return {
                "status": "CANCELLED",
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_paise": amt,
                "is_simulated": True,
                "failure_reason": reason or "SIMULATED_PAYMENT_CANCELLED_BY_USER",
                "error": "SIMULATED_PAYMENT_CANCELLED_BY_USER",
            }
        elif target_scenario == "TIMEOUT":
            return {
                "status": "EXPIRED",
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_paise": amt,
                "is_simulated": True,
                "failure_reason": reason or "SIMULATED_PAYMENT_WINDOW_EXPIRED",
                "error": "SIMULATED_PAYMENT_WINDOW_EXPIRED",
            }
        else:
            raise ValidationException(
                detail=f"Unsupported demo simulation scenario: {target_scenario}",
                code="INVALID_SIMULATION_SCENARIO",
            )

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: dict[str, str],
        secret: str | None = None,
    ) -> bool:
        """Verify webhook signature for demo simulation."""
        sig = headers.get("x-gadispot-demo-signature") or headers.get("x-demo-signature")
        return sig in ("demo-signature-verified", "simulated_valid_signature")

    def parse_webhook_event(self, payload: dict[str, Any]) -> GatewayWebhookEvent:
        """Parse simulated webhook payload into normalized event."""
        event_type = payload.get("event_type") or payload.get("event", "demo.payment.succeeded")
        event_data = payload.get("data", {})

        is_success = "succeeded" in event_type.lower() or event_type.lower() == "payment.succeeded"
        is_refund = "refund" in event_type.lower()

        event_id = payload.get("event_id") or payload.get("id", f"demo_evt_{uuid.uuid4().hex[:12]}")
        order_id = payload.get("order_id") or event_data.get("order_id")
        payment_id = payload.get("payment_id") or event_data.get("payment_id")
        amount_paise = payload.get("amount_paise") or event_data.get("amount_paise")

        return GatewayWebhookEvent(
            gateway_name=self.gateway_name,
            event_id=event_id,
            event_type=event_type,
            order_id=order_id,
            payment_id=payment_id,
            amount_paise=amount_paise,
            is_payment_success=is_success,
            is_refund_update=is_refund,
            refund_status="REFUND_SETTLED" if is_refund else None,
            refund_arn_utr=f"SIM_UTR_{uuid.uuid4().hex[:10].upper()}" if is_refund else None,
            payload=payload,
        )

    async def process_refund(
        self,
        payment_id: str,
        amount_paise: int,
        reason: str,
        notes: dict[str, Any] | None = None,
    ) -> RefundResult:
        """Generate deterministic simulated refund."""
        ref_id = f"demo_ref_{uuid.uuid4().hex[:12]}"
        mock_utr = f"SIM_UTR_{uuid.uuid4().hex[:10].upper()}"

        return RefundResult(
            refund_id=ref_id,
            gateway_name=self.gateway_name,
            amount_paise=amount_paise,
            status="processed",
            arn_utr=mock_utr,
            raw_response={
                "id": ref_id,
                "payment_id": payment_id,
                "amount": amount_paise,
                "currency": "INR",
                "status": "processed",
                "utr": mock_utr,
                "reason": reason,
                "is_simulated": True,
                "disclaimer": "SIMULATED REFUND — No real funds transferred.",
                "notes": notes or {},
            },
        )

    async def get_payment_status(self, payment_id: str) -> dict[str, Any]:
        """Return simulated payment status."""
        return {
            "payment_id": payment_id,
            "gateway": self.gateway_name,
            "status": "succeeded" if "pay" in payment_id else "created",
            "is_simulated": True,
        }

    async def cancel_payment(self, payment_id: str) -> dict[str, Any]:
        """Cancel a simulated payment."""
        return {
            "payment_id": payment_id,
            "gateway": self.gateway_name,
            "status": "CANCELLED",
            "is_simulated": True,
        }

    async def health_check(self) -> bool:
        """Demo adapter is always available when enabled."""
        return self._is_enabled
