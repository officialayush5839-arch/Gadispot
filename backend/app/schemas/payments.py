"""Pydantic schemas for payment initiation, UPI QR codes, refunds, and webhooks."""

import uuid

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    """Request to create a payment order with an integrated gateway."""

    reservation_id: uuid.UUID = Field(..., description="Target parking reservation ID")
    amount_paise: int = Field(..., gt=0, description="Monetary amount in Indian Paise (e.g. 10000 = ₹100.00)")
    gateway: str = Field("razorpay", description="Payment gateway: 'razorpay', 'cashfree', 'hyperswitch'")
    currency: str = Field("INR", description="ISO 4217 3-letter currency code")


class CreateOrderResponse(BaseModel):
    """Payment order created by the gateway adapter."""

    order_id: str = Field(..., description="Gateway-generated order identifier")
    gateway: str = Field(..., description="Name of the executing gateway adapter")
    amount_paise: int = Field(..., description="Order amount in Paise")
    currency: str = Field("INR", description="Currency")
    status: str = Field(..., description="Order status ('created', 'pending')")


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
