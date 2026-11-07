# Gadispot Demo Payment System — Testing Guide

**Target Audience:** Evaluators, Jury, QA Automation Engineers  
**Scope:** Interactive Checkout, Simulated Outcomes, Ledger Postings, and Payout Batches  

---

## 1. Quick Verification via Automated Test Suite

Run the complete payment test suite:

```bash
# Run all payment unit, integration, security, and concurrency tests
python -m pytest tests/payments/ -v
```

Expected output:
```
tests/payments/test_demo_adapter.py::test_demo_adapter_create_order PASSED
tests/payments/test_demo_adapter.py::test_demo_adapter_simulate_outcomes PASSED
tests/payments/test_demo_adapter.py::test_demo_adapter_refund_and_cancel PASSED
tests/payments/test_demo_adapter.py::test_demo_adapter_webhooks PASSED
tests/payments/test_payment_concurrency.py::test_concurrent_payment_completion_idempotency PASSED
tests/payments/test_payment_security.py::test_idor_payment_initiation_rejected PASSED
tests/payments/test_payment_security.py::test_idor_payment_completion_rejected PASSED
tests/payments/test_payment_security.py::test_production_environment_guard_blocks_simulation PASSED
tests/payments/test_payment_service.py::test_payment_creation_and_successful_demo_completion PASSED
tests/payments/test_payment_service.py::test_demo_payment_failure_scenario PASSED
tests/payments/test_payment_service.py::test_payment_idempotency_replay PASSED
tests/payments/test_payout_simulation.py::test_owner_payout_batch_and_double_pay_defense PASSED
tests/payments/test_youpi_adapter.py::test_youpi_adapter_disabled_by_default PASSED
tests/payments/test_youpi_adapter.py::test_youpi_adapter_disabled_calls_rejected PASSED
tests/payments/test_youpi_adapter.py::test_youpi_adapter_observer_event_never_confirms_directly PASSED
tests/payments/test_youpi_adapter.py::test_youpi_adapter_hmac_signature_verification PASSED
============================== 16 passed in 20s ==============================
```

---

## 2. Interactive REST API Walkthrough

### Step 1: Discover Active Payment Providers
```http
GET /api/v1/payments/providers
```
**Response:**
```json
{
  "active_mode": "demo",
  "demo_enabled": true,
  "supported_providers": ["demo", "razorpay", "cashfree", "hyperswitch"]
}
```

### Step 2: Create Checkout Payment Intent
```http
POST /api/v1/payments
Authorization: Bearer <driver_token>
Content-Type: application/json

{
  "reservation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "gateway": "demo",
  "idempotency_key": "client_intent_001"
}
```

### Step 3: Trigger Simulated Outcome
```http
POST /api/v1/payments/<payment_id>/demo/complete
Authorization: Bearer <driver_token>
Content-Type: application/json

{
  "outcome": "SUCCESS"
}
```
*Alternatives:* `"FAILURE"`, `"CANCEL"`, `"TIMEOUT"`.

### Step 4: Verify Minted Access Pass Tokens
```http
GET /api/v1/bookings/<reservation_id>
Authorization: Bearer <driver_token>
```
The booking is now `CONFIRMED` and entry/exit passes (`spx_ent_...`, `spx_ext_...`) are ready for gate validation.

### Step 5: Simulate Host Payout Batch
```http
POST /api/v1/payments/payouts/simulate
Authorization: Bearer <admin_or_owner_token>
```
**Response:**
```json
{
  "batch_id": "PB-8A2F",
  "amount_paise": 8230,
  "currency": "INR",
  "status": "SIMULATED_SETTLED",
  "settled_at": "2026-11-06T12:00:00Z",
  "utr": "UTR-DEMO-4A9B8C",
  "message": "Successfully disbursed ₹82.30 across owner balances"
}
```
A second immediate call to `/payouts/simulate` will return `0` paise disbursed, proving double-pay immunity.
