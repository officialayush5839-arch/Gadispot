"""Automated tests for Phase 5 Payment Adapters, Dynamic UPI QR, Webhooks, and 6-Stage Refunds."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select


from app.core.exceptions import ConflictException, ValidationException
from app.integrations.payments.cashfree_adapter import CashfreeAdapter
from app.integrations.payments.hyperswitch_adapter import HyperswitchAdapter
from app.integrations.payments.razorpay_adapter import RazorpayAdapter
from app.integrations.payments.upi_qr_service import (
    build_upi_payment_uri,
    generate_upi_qr_base64,
    validate_vpa,
)
from app.main import app
from app.models.enums import (
    PropertyTypeEnum,
    RefundStatusEnum,
    ReservationStatusEnum,
    ReservationTypeEnum,
    SpaceTypeEnum,
    UserRoleEnum,
    VehicleCategoryEnum,
)
from app.models.parking import ParkingSpace
from app.models.payments import PaymentWebhookEvent
from app.models.properties import Property
from app.models.reservations import SpaceReservation
from app.models.users import User, UserRole, Vehicle
from app.services.refund_service import RefundService


@pytest.fixture
async def sample_reservation(db_session):
    """Fixture providing a persisted space reservation for payment tests."""
    user = User(phone_number=f"+9199{uuid.uuid4().hex[:8]}", full_name="Payment Test Driver")
    db_session.add(user)
    await db_session.flush()

    vehicle = Vehicle(
        driver_id=user.id,
        registration_plate=f"KA01AB{uuid.uuid4().hex[:4].upper()}",
        vehicle_category=VehicleCategoryEnum.HATCHBACK,
    )
    db_session.add(vehicle)

    prop_id = uuid.uuid4()
    from sqlalchemy import text
    await db_session.execute(
        text("""
        INSERT INTO properties (id, owner_id, title, property_type, address_line, city, postal_code, location, is_active)
        VALUES (:id, :owner_id, 'MG Road Test Plaza', 'COMMERCIAL_BUILDING', '123 MG Road', 'Bengaluru', '560001', 'SRID=4326;POINT(77.5946 12.9716)', TRUE)
        """),
        {"id": prop_id, "owner_id": user.id},
    )

    space = ParkingSpace(
        property_id=prop_id,
        space_label=f"BAY-{uuid.uuid4().hex[:4].upper()}",
        space_type=SpaceTypeEnum.COVERED,
        vehicle_category=VehicleCategoryEnum.HATCHBACK,
        base_hourly_rate_paise=10000,
    )
    db_session.add(space)
    await db_session.flush()


    now = datetime.now(timezone.utc)
    import asyncpg
    res = SpaceReservation(
        parking_space_id=space.id,
        driver_id=user.id,
        vehicle_id=vehicle.id,
        time_window=asyncpg.Range(now, now + timedelta(hours=2), lower_inc=True, upper_inc=False),
        reservation_type=ReservationTypeEnum.TEMPORARY_HOLD,
        status=ReservationStatusEnum.ACTIVE_HOLD,
        hold_expires_at=now + timedelta(seconds=480),
        booking_reference=f"GSP-{uuid.uuid4().hex[:8].upper()}",
    )
    db_session.add(res)
    await db_session.commit()
    await db_session.refresh(res)
    return res


@pytest.mark.asyncio
async def test_razorpay_adapter_order_and_signatures():
    """Verify Razorpay adapter order creation and HMAC-SHA256 signature verification."""
    adapter = RazorpayAdapter(key_id="rzp_test_mock", key_secret="rzp_secret_123")
    order = await adapter.create_order(amount_paise=10000, receipt="rcpt_test_01")
    assert order.gateway_name == "razorpay"
    assert order.amount_paise == 10000
    assert order.order_id.startswith("order_")

    # Verify payment signature
    order_id = "order_123456"
    payment_id = "pay_789012"
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    sig = hmac.new("rzp_secret_123".encode("utf-8"), msg, hashlib.sha256).hexdigest()
    assert adapter.verify_payment_signature(order_id, payment_id, sig) is True
    assert adapter.verify_payment_signature(order_id, payment_id, "forged_sig") is False


@pytest.mark.asyncio
async def test_cashfree_and_hyperswitch_adapters():
    """Verify Cashfree and Hyperswitch adapters conform to PaymentGatewayPort."""
    cf = CashfreeAdapter(app_id="cf_test", secret_key="cf_sec_123")
    cf_order = await cf.create_order(amount_paise=9180, receipt="rcpt_cf_01")
    assert cf_order.gateway_name == "cashfree"
    assert cf_order.amount_paise == 9180

    hs = HyperswitchAdapter(api_key="hs_api_key", webhook_secret="hs_sec_123")
    hs_order = await hs.create_order(amount_paise=9180, receipt="rcpt_hs_01")
    assert hs_order.gateway_name == "hyperswitch"
    assert hs_order.amount_paise == 9180


@pytest.mark.asyncio
async def test_dynamic_upi_qr_service():
    """Verify NPCI-compliant UPI URI generation and base64 QR generation."""
    assert validate_vpa("gadispot@icici") is True
    assert validate_vpa("invalid-vpa-format") is False

    uri = build_upi_payment_uri(
        amount_rupees=91.80,
        transaction_ref="TXN123456789",
        payee_vpa="gadispot.merchants@hdfcbank",
        payee_name="Gadispot Airport Plaza",
    )
    assert "upi://pay?" in uri
    assert "am=91.80" in uri
    assert "pa=gadispot.merchants%40hdfcbank" in uri

    qr_b64 = generate_upi_qr_base64(uri)
    assert qr_b64.startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_6_stage_refund_lifecycle_state_machine(db_session, sample_reservation):
    """Verify progression through the canonical 6-stage refund pipeline."""
    res_id = sample_reservation.id

    # Stage 1 -> 2: NONE to REFUND_ELIGIBLE
    res = await RefundService.mark_refund_eligible(db_session, res_id, "Driver cancelled")
    assert res.refund_status == RefundStatusEnum.REFUND_ELIGIBLE

    # Stage 2 -> 3: REFUND_ELIGIBLE to REFUND_REQUESTED
    res = await RefundService.request_refund(db_session, res_id, "Processing cancellation")
    assert res.refund_status == RefundStatusEnum.REFUND_REQUESTED
    assert res.refund_initiated_at is not None

    # Stage 3 -> 4: REFUND_REQUESTED to GATEWAY_ACCEPTED
    res = await RefundService.record_gateway_acceptance(db_session, res_id, "rfnd_rzp_12345")
    assert res.refund_status == RefundStatusEnum.GATEWAY_ACCEPTED
    assert res.refund_gateway_id == "rfnd_rzp_12345"

    # Stage 4 -> 6: GATEWAY_ACCEPTED to REFUND_SETTLED
    res = await RefundService.record_refund_settled(db_session, res_id, "UTR987654321")
    assert res.refund_status == RefundStatusEnum.REFUND_SETTLED
    assert res.refund_arn_utr == "UTR987654321"
    assert res.refund_completed_at is not None

    # Illegal transition: REFUND_SETTLED is terminal; attempting to mark eligible must fail
    with pytest.raises(ConflictException) as exc_info:
        await RefundService.mark_refund_eligible(db_session, res_id, "Try again")
    assert exc_info.value.code == "ILLEGAL_REFUND_TRANSITION"


@pytest.mark.asyncio
async def test_webhook_idempotency_and_deduplication(db_session, sample_reservation):
    """Verify that duplicate webhook deliveries return HTTP 200 without duplicate execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_mock_123",
                        "order_id": sample_reservation.booking_reference,
                        "amount": 10000,
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = hmac.new("rzp_test_mock_secret".encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        headers = {
            "x-razorpay-signature": sig,
            "Content-Type": "application/json",
        }

        # 1. First delivery -> processed
        resp1 = await client.post("/api/v1/webhooks/razorpay", content=body_bytes, headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        # 2. Second delivery with exact same (gateway, event_id) -> idempotent already_processed
        resp2 = await client.post("/api/v1/webhooks/razorpay", content=body_bytes, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_webhook_forged_signature_rejected():
    """Verify webhook endpoint rejects forged signatures with HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"id": "evt_fraud_01", "event": "payment.captured"}
        headers = {
            "x-razorpay-signature": "bad_signature_hash",
            "Content-Type": "application/json",
        }
        resp = await client.post("/api/v1/webhooks/razorpay", json=payload, headers=headers)
        assert resp.status_code == 401
        assert resp.json()["code"] == "INVALID_WEBHOOK_SIGNATURE"
