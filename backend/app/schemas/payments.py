"""Pydantic schemas for payment initiation, UPI QR codes, refunds, demo simulations, and webhooks."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    """Request to create a payment order with an integrated gateway."""

    reservation_id: uuid.UUID = Field(..., description="Target parking reservation ID")
    amount_paise: int = Field(..., gt=0, description="Monetary amount in Indian Paise (e.g. 10000 = ₹100.00)")
    gateway: str = Field("demo", description="Payment gateway: 'demo', 'razorpay', 'cashfree', 'hyperswitch', 'youpi'")
    currency: str = Field("INR", description="ISO 4217 3-letter currency code")


class CreateOrderResponse(BaseModel):
    """Payment order created by the gateway adapter."""

    order_id: str = Field(..., description="Gateway-generated order identifier")
    gateway: str = Field(..., description="Name of the executing gateway adapter")
    amount_paise: int = Field(..., description="Order amount in Paise")
    currency: str = Field("INR", description="Currency")
    status: str = Field(..., description="Order status ('created', 'pending')")


class InitiatePaymentRequest(BaseModel):
    """Request to initiate payment checkout for a reservation hold."""

    reservation_id: uuid.UUID = Field(..., description="Reservation ID under active hold")
    gateway: str = Field("demo", description="Payment gateway: 'demo', 'razorpay', 'cashfree', 'hyperswitch'")
    idempotency_key: str | None = Field(None, description="Optional client-generated idempotency key")


class InitiatePaymentResponse(BaseModel):
    """Payment intent response with pricing quote and provider order ID."""

    payment_id: uuid.UUID = Field(..., description="Unique internal payment transaction ID")
    reservation_id: uuid.UUID = Field(..., description="Target reservation ID")
    order_id: str = Field(..., description="Provider-specific order or intent ID")
    amount_paise: int = Field(..., description="Total payment amount in Paise")
    currency: str = Field("INR", description="Currency code")
    status: str = Field(..., description="Current payment status")
    gateway: str = Field(..., description="Selected gateway provider")
    is_simulated: bool = Field(..., description="Whether this is a simulated demo transaction")
    is_experimental: bool = Field(False, description="Whether this is an experimental gateway")
    quote: dict[str, Any] | None = Field(None, description="Detailed financial fee breakdown")


class DemoCompleteRequest(BaseModel):
    """Request to simulate a payment outcome in demo mode."""

    outcome: str = Field("SUCCESS", description="Simulation outcome: 'SUCCESS', 'FAILURE', 'CANCEL', 'TIMEOUT'")
    reason: str | None = Field(None, description="Optional diagnostic or cancellation reason")


class DemoCompleteResponse(BaseModel):
    """Result of the simulated payment completion."""

    payment_id: uuid.UUID = Field(..., description="Payment ID")
    reservation_id: uuid.UUID = Field(..., description="Reservation ID")
    status: str = Field(..., description="Updated payment status")
    is_simulated: bool = Field(..., description="Confirms simulated transaction")
    provider_payment_id: str | None = Field(None, description="Simulated UTR/payment ID")
    failure_reason: str | None = Field(None, description="Reason if simulation failed or timed out")
    message: str = Field(..., description="Human-readable result summary")


class PaymentDetailResponse(BaseModel):
    """Comprehensive payment record inspection."""

    id: uuid.UUID = Field(..., description="Payment ID")
    reservation_id: uuid.UUID = Field(..., description="Associated reservation ID")
    driver_id: uuid.UUID = Field(..., description="Driver user ID")
    amount_paise: int = Field(..., description="Amount in paise")
    currency: str = Field("INR", description="Currency")
    provider: str = Field(..., description="Payment provider name")
    provider_order_id: str | None = Field(None, description="Provider order ID")
    provider_payment_id: str | None = Field(None, description="Provider payment ID")
    status: str = Field(..., description="Payment lifecycle status")
    is_simulated: bool = Field(..., description="Simulated flag")
    is_experimental: bool = Field(False, description="Experimental flag")
    experimental_status: str | None = Field(None, description="Observer-derived status")
    idempotency_key: str | None = Field(None, description="Idempotency key")
    simulation_scenario: str | None = Field(None, description="Triggered simulation scenario")
    failure_reason: str | None = Field(None, description="Failure reason")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PayoutBatchResponse(BaseModel):
    """Simulated host earnings disbursement batch."""

    batch_id: str = Field(..., description="Batch identifier")
    amount_paise: int = Field(..., description="Disbursed amount in paise")
    currency: str = Field("INR", description="Currency")
    status: str = Field(..., description="Batch status ('SIMULATED_SETTLED')")
    settled_at: str = Field(..., description="Settlement ISO timestamp")
    utr: str | None = Field(None, description="Disbursement UTR reference")
    message: str = Field(..., description="Status summary message")


class ProviderListResponse(BaseModel):
    """List of active payment providers."""

    active_mode: str = Field(..., description="Active payment mode ('demo', 'live', 'hybrid')")
    demo_enabled: bool = Field(..., description="Whether demo simulation is permitted")
    supported_providers: list[str] = Field(..., description="List of available gateway identifiers")


class UpiQrRequest(BaseModel):
    """Request to generate a dynamic UPI QR code."""

    reservation_id: uuid.UUID = Field(..., description="Reservation ID associated with this payment")
    amount_rupees: float = Field(..., gt=0.0, description="Amount in INR (e.g. 91.80)")
    payee_vpa: str | None = Field(None, description="Optional custom VPA (defaults to system setting)")
    payee_name: str | None = Field(None, description="Optional custom Payee Name")
    note: str | None = Field(None, description="Payment note/description (max 50 chars)")


class UpiQrResponse(BaseModel):
    """Dynamic NPCI UPI URI and base64 PNG QR code representation."""

    upi_uri: str = Field(..., description="Canonical NPCI compliant upi://pay URI")
    qr_code_base64: str = Field(..., description="Data URL (base64 PNG) of the generated QR code")
    transaction_ref: str = Field(..., description="Deterministic transaction reference identifier")
    amount_rupees: float = Field(..., description="Payment amount in INR")


class RefundRequest(BaseModel):
    """Request to initiate a 6-stage refund for a cancelled or unfulfillable reservation."""

    reservation_id: uuid.UUID = Field(..., description="Reservation ID to refund")
    reason: str = Field(..., min_length=3, description="Cancellation or failure reason")
    amount_paise: int | None = Field(
        None, gt=0, description="Optional partial refund amount in Paise (defaults to full)"
    )


class RefundResponse(BaseModel):
    """Current refund state and gateway tracking identifiers."""

    reservation_id: uuid.UUID = Field(..., description="Reservation ID")
    refund_status: str = Field(..., description="Current status in the 6-stage refund state machine")
    refund_gateway_id: str | None = Field(None, description="Gateway refund ID if dispatched")
    refund_arn_utr: str | None = Field(None, description="Bank ARN/UTR settlement reference if available")
    message: str = Field(..., description="Summary status message")
