"""Unit tests for DemoPaymentAdapter deterministic simulation behavior."""

import pytest
from app.core.exceptions import ValidationException
from app.integrations.payments.demo_adapter import DemoPaymentAdapter


@pytest.mark.asyncio
async def test_demo_adapter_create_order():
    """Verify DemoPaymentAdapter produces a valid simulated order."""
    adapter = DemoPaymentAdapter()
    result = await adapter.create_order(
        amount_paise=12000,
        receipt="rcpt_test_123",
        currency="INR",
        notes={"test_key": "test_val"},
    )

    assert result.gateway_name == "demo"
    assert result.amount_paise == 12000
    assert result.currency == "INR"
    assert result.status == "created"
    assert result.order_id.startswith("demo_ord_")


@pytest.mark.asyncio
async def test_demo_adapter_simulate_outcomes():
    """Verify deterministic outcomes: SUCCESS, FAILURE, CANCEL, TIMEOUT."""
    adapter = DemoPaymentAdapter()

    # Success outcome
    success = await adapter.simulate_outcome("order_sim_1", "SUCCESS")
    assert success["status"] == "SUCCEEDED"
    assert success["is_simulated"] is True
    assert success["payment_id"].startswith("demo_pay_")

    # Failure outcome
    failure = await adapter.simulate_outcome(
        "order_sim_2", "FAILURE", reason="Card declined"
    )
    assert failure["status"] == "FAILED"
    assert failure["failure_reason"] == "Card declined"

    # Cancel outcome
    cancel = await adapter.simulate_outcome("order_sim_3", "CANCEL")
    assert cancel["status"] == "CANCELLED"

    # Timeout outcome
    timeout = await adapter.simulate_outcome("order_sim_4", "TIMEOUT")
    assert timeout["status"] == "EXPIRED"

    # Invalid outcome raises ValidationException
    with pytest.raises(ValidationException):
        await adapter.simulate_outcome("order_sim_5", "INVALID_STATUS")


@pytest.mark.asyncio
async def test_demo_adapter_refund_and_cancel():
    """Verify refund simulation and payment cancellation."""
    adapter = DemoPaymentAdapter()

    refund = await adapter.process_refund(
        payment_id="pay_sim_123",
        amount_paise=5000,
        reason="Driver cancelled booking",
    )
    assert refund.gateway_name == "demo"
    assert refund.refund_id.startswith("demo_ref_")
    assert refund.amount_paise == 5000
    assert refund.status == "processed"
    assert refund.arn_utr is not None
    assert refund.arn_utr.startswith("SIM_UTR_")

    cancel_res = await adapter.cancel_payment("order_sim_123")
    assert cancel_res["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_demo_adapter_webhooks():
    """Verify webhook signature verification and parsing."""
    adapter = DemoPaymentAdapter()

    # Signature verification
    valid = adapter.verify_webhook_signature(
        b'{"test": 1}', {"x-demo-signature": "simulated_valid_signature"}
    )
    assert valid is True

    invalid = adapter.verify_webhook_signature(
        b'{"test": 1}', {"x-demo-signature": "wrong"}
    )
    assert invalid is False

    # Webhook parsing
    event = adapter.parse_webhook_event(
        {
            "event_id": "evt_123",
            "event_type": "payment.succeeded",
            "order_id": "order_sim_456",
            "payment_id": "pay_sim_789",
            "amount_paise": 15000,
        }
    )
    assert event.event_id == "evt_123"
    assert event.is_payment_success is True
    assert event.gateway_name == "demo"
    assert event.amount_paise == 15000
