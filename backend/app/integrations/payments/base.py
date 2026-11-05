"""Payment Gateway Port: Abstract contract for runtime-swappable payment providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaymentOrderResult:
    """Result of order creation on the payment gateway."""

    order_id: str
    gateway_name: str
    amount_paise: int
    currency: str = "INR"
    status: str = "created"
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class RefundResult:
    """Result of refund dispatch on the payment gateway."""

    refund_id: str
    gateway_name: str
    amount_paise: int
    status: str  # e.g. "accepted", "processing", "settled", "failed"
    arn_utr: str | None = None
    failure_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayWebhookEvent:
    """Normalized payment gateway webhook event."""

    gateway_name: str
    event_id: str
    event_type: str
    order_id: str | None = None
    payment_id: str | None = None
    amount_paise: int | None = None
    is_payment_success: bool = False
    is_refund_update: bool = False
    refund_status: str | None = None
    refund_arn_utr: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class PaymentGatewayPort(ABC):
    """Abstract Base Class specifying common payment gateway contract."""

    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Return the unique gateway identifier ('razorpay', 'cashfree', 'hyperswitch')."""

    @abstractmethod
    async def create_order(
        self,
        amount_paise: int,
        receipt: str,
        currency: str = "INR",
        notes: dict[str, Any] | None = None,
    ) -> PaymentOrderResult:
        """Create an intent order at the payment gateway."""

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: dict[str, str],
        secret: str | None = None,
    ) -> bool:
        """Verify the cryptographic HMAC signature of incoming webhook requests."""

    @abstractmethod
    def parse_webhook_event(self, payload: dict[str, Any]) -> GatewayWebhookEvent:
        """Normalize raw provider webhook payload into standard GatewayWebhookEvent."""

    @abstractmethod
    async def process_refund(
        self,
        payment_id: str,
        amount_paise: int,
        reason: str,
        notes: dict[str, Any] | None = None,
    ) -> RefundResult:
        """Initiate or check refund status at the payment gateway."""
