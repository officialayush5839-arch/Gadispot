"""Unit tests verifying isolation, disabled default, and observer contracts of YoupiPaymentAdapter."""

import hashlib
import hmac

import pytest
from app.core.exceptions import ValidationException
from app.integrations.payments.youpi_adapter import YoupiPaymentAdapter


def test_youpi_adapter_disabled_by_default():
    """Verify YoupiPaymentAdapter is disabled by default and fails closed."""
    adapter = YoupiPaymentAdapter(is_enabled=False)
    assert adapter.is_enabled is False

    with pytest.raises(ValidationException) as exc:
        adapter._check_enabled()
    assert "disabled" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_youpi_adapter_disabled_calls_rejected():
    """All adapter operations must reject execution when disabled."""
    adapter = YoupiPaymentAdapter(is_enabled=False)

    with pytest.raises(ValidationException):
        await adapter.create_order(amount_paise=1000, receipt="rcpt_1")

    with pytest.raises(ValidationException):
        await adapter.get_payment_status("order_1")

    with pytest.raises(ValidationException):
        await adapter.process_refund("pay_1", 1000, "reason")


def test_youpi_adapter_observer_event_never_confirms_directly():
    """CRITICAL SECURITY INVARIANT: Observer events must NEVER set is_payment_success = True."""
    adapter = YoupiPaymentAdapter(is_enabled=True, webhook_secret="test_secret")

    payload = {
        "event_id": "evt_youpi_101",
        "order_id": "order_youpi_202",
        "transaction_id": "txn_303",
        "amount": 25000,
        "status": "SUCCESS",
        "observer_source": "SMS_OBSERVER",
    }

    event = adapter.parse_webhook_event(payload)
    assert event.event_id == "evt_youpi_101"
    assert event.gateway_name == "youpi"
    # Verification of zero bypass invariant:
    assert event.is_payment_success is False
    assert event.payload.get("experimental_observation_status") == "OBSERVED_SUCCESS"
    assert event.payload.get("requires_reconciliation") is True


def test_youpi_adapter_hmac_signature_verification():
    """Verify HMAC-SHA256 signature validation and forged signature rejection."""
    secret = "youpi_super_secret_key"
    adapter = YoupiPaymentAdapter(is_enabled=True, webhook_secret=secret)

    body = b'{"order_id": "yp_123", "status": "OBSERVED"}'
    valid_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    # Valid signature
    assert (
        adapter.verify_webhook_signature(body, {"x-youpi-signature": valid_sig}) is True
    )

    # Forged signature
    assert (
        adapter.verify_webhook_signature(
            body, {"x-youpi-signature": "forged_signature"}
        )
        is False
    )

    # Missing header
    assert adapter.verify_webhook_signature(body, {}) is False
