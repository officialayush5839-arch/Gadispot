# Gadispot (formerly SmartPark Exchange) — Comprehensive Quality Assurance & Test Strategy (V2.3)

> **Document Version:** 2.3.0  
> **Date:** October 31, 2026  
> **Authors:** QA & Test Strategy Lead, Senior Backend Engineer, Mobile Test Architect  
> **Test Frameworks:** Pytest (Backend / DB), Flutter Test / Integration Test (Mobile), Locust (Performance)  
> **Status:** Authoritative Engineering Test Catalogue (Targeted Revision V2.3)  

---

## 1. Test Strategy Overview & Verification Pyramid

SmartPark Exchange validates software dependability through an automated multi-tier testing strategy. Given the financial and physical consequences of parking reservation failures, testing focuses heavily on **transactional concurrency**, **database exclusion integrity**, **durable webhook idempotency**, and **financial ledger balance invariants**.

```
                / \
               /   \       10% E2E Mobile User Journeys
              /     \      - Flutter integration_test on Android/iOS
             /-------\
            /         \    25% Concurrency, Race Condition & Chaos Tests
           /           \   - Multi-threaded booking races (asyncio / Locust)
          /             \  - Delayed webhook arrivals & late-payment recovery
         /---------------\
        /                 \ 25% API Contract & Integration Tests
       /                   \ - FastAPI TestClient, OpenAPI schema validation
      /---------------------\
     /                       \ 40% Unit & Pure Domain Logic Tests
    /                         \ - Pricing math, DPDPA data sanitizer, ledger balance
   /---------------------------\
```

---

## 2. The 20 Mandatory High-Risk Test Scenarios

### Scenario TS-01: Concurrent Booking Collision for Same Time Interval
- **Category:** Concurrency / Database Exclusion Constraint.
- **Preconditions:** Parking Bay `Slot 1` is available for `10:00 - 12:00`.
- **Test Execution:** Two async client workers simultaneously submit `POST /api/v1/bookings/hold` for `Slot 1` for `10:00 - 12:00` using identical microsecond timestamps.
- **Expected Outcome:**
  1. PostgreSQL GiST exclusion constraint (`prevent_overlapping_active_reservations`) serializes index lock.
  2. Exactly one transaction commits and returns HTTP 201 Created with `ACTIVE_HOLD` (480s countdown).
  3. The competing transaction catches `ExclusionViolation` (`23P01`), rolls back, and returns HTTP 409 Conflict with code `SLOT_INTERVAL_CONFLICT`.
  4. Querying `space_reservations` confirms exactly 1 active row exists for that interval.

### Scenario TS-02: Concurrent Booking for Non-Overlapping Time Intervals
- **Category:** Concurrency / Time-Window Independence.
- **Preconditions:** Parking Bay `Slot 1` is available for both `10:00 - 11:00` and `14:00 - 15:00`.
- **Test Execution:** Worker 1 requests `10:00 - 11:00`; Worker 2 requests `14:00 - 15:00` simultaneously for the same physical bay.
- **Expected Outcome:**
  1. Both interval ranges are evaluated as non-overlapping (`time_window && time_window` is `FALSE`).
  2. Both database inserts succeed and commit independently.
  3. Both workers receive HTTP 201 Created with active holds. Neither is blocked by the other.

### Scenario TS-03: Duplicate Hold Request (Idempotency Replay)
- **Category:** API Reliability / Network Jitter.
- **Preconditions:** Driver submits `POST /bookings/hold` with `Idempotency-Key: e4b2...`.
- **Test Execution:** Client network times out; client re-submits the identical request with the same `Idempotency-Key` 2 seconds later.
- **Expected Outcome:**
  1. Database and Redis return the cached JSON payload and HTTP 201 Created immediately without executing a second database insert.
  2. Only 1 record exists in `space_reservations`.

### Scenario TS-04: Expired Hold Followed by Late Payment Webhook (LPRP)
- **Category:** Asynchronous Webhook Race / Concurrency.
- **Preconditions:** Driver A's 480s hold expires (`EXPIRED_HOLD`). Driver B books and confirms the same bay.
- **Test Execution:** Razorpay delivers delayed `payment.captured` webhook for Driver A.
- **Expected Outcome:**
  1. Backend attempts to transition Driver A's reservation to `CONFIRMED`.
  2. PostgreSQL throws `ExclusionViolation (23P01)` because Driver B now holds the slot.
  3. Backend catches exception; transitions Driver A's reservation to `RELEASED_UNFULFILLABLE`.
  4. System enters multi-stage refund: `REFUND_PENDING` $\to$ calls gateway API $\to$ `REFUND_PROCESSING`.
  5. Driver A receives push notification of refund with banking settlement window (5–7 business days). Driver B's confirmed booking remains untouched.

### Scenario TS-05: Duplicate Payment Webhook Ingestion (Durable Idempotency)
- **Category:** Financial Idempotency.
- **Preconditions:** Webhook `payment.captured` for order `order_9821` is received and processed.
- **Test Execution:** Gateway retries and redelivers identical webhook payload with the same `x-razorpay-event-id` 30 seconds later.
- **Expected Outcome:**
  1. Database unique constraint on `payment_webhook_events(gateway_name, gateway_event_id)` detects duplicate.
  2. Webhook controller returns HTTP 200 OK immediately without re-processing.
  3. Zero duplicate rows are inserted into `journal_entries` or `space_reservations`.

### Scenario TS-06: Out-of-Order Webhook Delivery
- **Category:** Asynchronous State Ordering.
- **Preconditions:** A reservation is in `ACTIVE_HOLD`.
- **Test Execution:** Gateway delivers `refund.processed` webhook *before* the `payment.captured` webhook.
- **Expected Outcome:**
  1. System detects invalid state transition (`ACTIVE_HOLD -> REFUNDED` without `CONFIRMED`).
  2. Event is routed to Dead-Letter Queue (DLQ) with retry backoff; database transaction rolls back.
  3. Once `payment.captured` arrives and commits, DLQ worker re-evaluates refund successfully.

### Scenario TS-07: Payment Captured but Physical Booking Unfulfillable
- **Category:** Financial Reconciliation & Fallback.
- **Preconditions:** Driver completes payment, but bay experienced catastrophic physical obstruction (space marked `BLOCKED`).
- **Test Execution:** Webhook arrives while bay is `BLOCKED`.
- **Expected Outcome:**
  1. Booking engine detects bay status is `BLOCKED`.
  2. Transitions reservation to `ARRIVAL_FAILED`.
  3. GPRP protocol launches: searches alternative within 500m; if none available or driver declines, dispatches automated refund.

### Scenario TS-08: Duplicate Access QR Scan Within Session
- **Category:** Access Security / Double Scan.
- **Preconditions:** Guard scans driver QR code; entry is validated and session starts (`ACTIVE_SESSION`).
- **Test Execution:** Guard accidentally rescans the same QR code 15 seconds later.
- **Expected Outcome:**
  1. Backend detects that `space_reservations.status` is already `ACTIVE_SESSION` and `access_credentials.status` is `CONSUMED`.
  2. Guard scanner displays informative warning: "Vehicle already checked in at [Time]. Bay is Active."
  3. Session timestamp is not overwritten; no duplicate entry is created.

### Scenario TS-09: Access QR Replay After Physical Entry
- **Category:** Access Security / Screenshot Sharing.
- **Preconditions:** Driver A enters gate; Access QR token is burned (`CONSUMED`).
- **Test Execution:** Driver B presents a screenshot of Driver A's QR code at another gate.
- **Expected Outcome:**
  1. Backend detects token status is `CONSUMED`.
  2. Guard app screen flashes **BOLD RED** with haptic alert: "ACCESS REJECTED: QR code already used at [Timestamp]."
  3. Gate entry is denied. Failed scan logged in `access_scan_logs` with event `REPLAY_ATTEMPT`.

### Scenario TS-10: Access QR Presented at Wrong Property
- **Category:** Access Security / Gate Misdirection.
- **Preconditions:** Driver has valid confirmed booking for Property A.
- **Test Execution:** Driver presents QR code to Guard at Property B.
- **Expected Outcome:**
  1. Backend checks `property_id` in token against guard's assigned property ID.
  2. Guard scanner rejects scan: "WRONG PROPERTY: Pass is for Green Villa, 600m away."
  3. Gate remains closed.

### Scenario TS-11: Guard Attempts Unauthorized Cross-Property Access
- **Category:** Object-Level Authorization (IDOR).
- **Preconditions:** Guard is assigned to Property A.
- **Test Execution:** Guard attempts API call `POST /api/v1/access/validate-scan` passing `property_id = Property B`.
- **Expected Outcome:**
  1. RBAC authorization middleware queries `guard_assignments` for `guard_id` and target property.
  2. Call is rejected with HTTP 403 Forbidden ("You are not authorized for this property").

### Scenario TS-12: Space Owner Accesses Another Owner's Payout Ledger
- **Category:** Object-Level Authorization (IDOR).
- **Preconditions:** Owner 1 and Owner 2 are registered hosts.
- **Test Execution:** Owner 1 calls `GET /api/v1/payouts/owner-ledger` passing Owner 2's `owner_id`.
- **Expected Outcome:**
  1. Endpoint ignores query parameter; strictly extracts `owner_id` from authenticated JWT `sub` claim.
  2. Owner 1 receives only their own financial data.

### Scenario TS-13: GPRP Alternative Space Becomes Unavailable During Offer Creation
- **Category:** Concurrency / Failover.
- **Preconditions:** GPRP identifies Alternative Bay B; presents offer to driver.
- **Test Execution:** Another public driver reserves Alternative Bay B before the original driver taps "Accept".
- **Expected Outcome:**
  1. GPRP atomic hold acquisition on Alternative Bay B fails with `ExclusionViolation`.
  2. System detects conflict; automatically re-executes search for next closest alternative.
  3. If none found, dispatches full refund immediately without deadlocking.

### Scenario TS-14: Duplicate Refund Webhook Delivery
- **Category:** Financial Idempotency.
- **Preconditions:** Refund is processed; webhook `refund.processed` is delivered.
- **Test Execution:** Gateway re-delivers the identical refund webhook 1 hour later.
- **Expected Outcome:**
  1. Event ID check in `payment_webhook_events` rejects duplicate.
  2. Zero duplicate debit entries are posted to `journal_entries`.

### Scenario TS-15: Payout Transfer Network Timeout and Retry
- **Category:** Payout Settlement Idempotency.
- **Preconditions:** Weekly payout batch executes RazorpayX IMPS transfer.
- **Test Execution:** Network disconnects after gateway captures request but before returning HTTP response.
- **Expected Outcome:**
  1. Worker retries using the identical `payout_reference` as idempotency key.
  2. Gateway recognizes idempotency key; returns status without initiating duplicate bank transfer.

### Scenario TS-16: Financial Journal Double-Entry Balance Invariant Check
- **Category:** Accounting Mathematical Correctness.
- **Preconditions:** Any financial mutation is triggered (Booking, Extension, Refund, Overstay).
- **Test Execution:** Test injects an unbalanced journal entry into `journal_entries` and calls `POSTED`.
- **Expected Outcome:**
  1. PostgreSQL trigger `trg_verify_journal_balance` throws exception: `Journal entry does not balance!`.
  2. Database rolls back the transaction. Zero unbalanced rows are ever committed.

### Scenario TS-17: Cellular Network Disconnect During Guard Entry Scan (Controlled Manual Fallback)
- **Category:** Offline Mobile Resilience & Privacy.
- **Preconditions:** Guard is in an underground basement with 0 bars of reception.
- **Test Execution:** Guard attempts scan; API times out (>3s). Guard inputs plate, takes photo, signs locally.
- **Expected Outcome:**
  1. Guard app switches to Controlled Manual Fallback mode.
  2. Offline admission stored in encrypted SQLite (SQLCipher AES-256).
  3. Upon surface reconnection, record flushes to `/access/reconcile-offline-admissions`.
  4. S3 lifecycle policy purges photo within 7 days.

### Scenario TS-18: Driver Departs Property Without Guard Exit Scan
- **Category:** Session Exception Handling.
- **Preconditions:** Vehicle has departed, but guard forgot to scan exit.
- **Test Execution:** Session timer exceeds scheduled end time by 2 hours.
- **Expected Outcome:**
  1. System flags session as `STALE_ACTIVE`.
  2. Push notification sent to guard: "Vehicle KA-01-AB-1234 has not checked out. Please verify bay clearance."
  3. Guard verifies bay is physically empty and taps "Confirm Space Cleared".

### Scenario TS-19: Driver Overstays Into Subsequent Confirmed Booking
- **Category:** Overstay Conflict Resolution.
- **Preconditions:** Driver A is booked 10:00–12:00. Driver B is booked 12:15–14:00.
- **Test Execution:** Driver A fails to exit at 12:00. Clock reaches 12:15; Driver B arrives at the gate.
- **Expected Outcome:**
  1. Overstay billing triggers automatically for Driver A (1.5x hourly rate in 30-min blocks).
  2. Guard detects bay is still occupied; immediately triggers GPRP incident for Driver B.
  3. Driver B is rerouted to an alternative bay within 500m or issued a full refund.
  4. Driver A cannot extend reservation because subsequent slot is locked.

### Scenario TS-20: Property Authorization Revoked While Active Bookings Exist
- **Category:** Governance / Revocation Integrity.
- **Preconditions:** Property has confirmed future bookings. Ops revokes authorization due to fraud report.
- **Test Execution:** Admin sets property status to `SUSPENDED`.
- **Expected Outcome:**
  1. Property and bays are immediately hidden from future discovery searches.
  2. Existing confirmed bookings within next 24 hours are evaluated: if safe, honored; if compromised, cancelled with full refund.
  3. Space owner payouts are frozen pending fraud investigation.

---

## 3. Concrete Executable Pytest Implementations

### 3.1 Concurrency Race Test (`tests/concurrency/test_booking_exclusion.py`)
```python
import asyncio
import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_concurrent_booking_exclusion(app_client: AsyncClient, test_space_id: str, test_driver_tokens: list):
    """
    TS-01: Verifies that when two drivers simultaneously request an overlapping
    hold on the same parking bay, exactly one succeeds (HTTP 201) and one fails (HTTP 409).
    """
    payload = {
        "parking_space_id": test_space_id,
        "vehicle_id": str(uuid4()),
        "start_time": "2026-11-01T10:00:00+05:30",
        "end_time": "2026-11-01T12:00:00+05:30"
    }

    # Dispatch simultaneous hold requests
    responses = await asyncio.gather(
        app_client.post("/api/v1/bookings/hold", json=payload, headers={"Authorization": f"Bearer {test_driver_tokens[0]}", "Idempotency-Key": str(uuid4())}),
        app_client.post("/api/v1/bookings/hold", json=payload, headers={"Authorization": f"Bearer {test_driver_tokens[1]}", "Idempotency-Key": str(uuid4())}),
        return_exceptions=True
    )

    status_codes = [r.status_code for r in responses]
    assert 201 in status_codes, "At least one hold request must succeed"
    assert 409 in status_codes, "The competing hold request must be rejected with 409 Conflict"
    assert status_codes.count(201) == 1, "Exactly one reservation hold can be granted"
```

### 3.2 Ledger Balancing Invariant Test (`tests/financial/test_ledger_invariants.py`)
```python
import pytest
from asyncpg.exceptions import RaiseException

@pytest.mark.asyncio
async def test_ledger_rejects_unbalanced_journal(db_session):
    """
    TS-16: Verifies that the database trigger trg_verify_journal_balance
    rejects any attempt to post an unbalanced journal entry (Debits != Credits).
    """
    # Create draft journal entry
    journal_id = await db_session.fetchval(
        """
        INSERT INTO journal_entries (journal_number, transaction_reference, transaction_type, posting_status)
        VALUES ('TEST-JRN-UNBALANCED', 'REF-001', 'TEST', 'DRAFT')
        RETURNING id
        """
    )

    # Insert unbalanced lines (Debit 9180 paise, Credit 5000 paise)
    await db_session.execute(
        """
        INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise)
        VALUES 
            (:jid, 1, '1010', 'DEBIT', 9180),
            (:jid, 2, '2010', 'CREDIT', 5000)
        """,
        {"jid": journal_id}
    )

    # Attempt to post journal -> Must raise database trigger exception
    with pytest.raises(RaiseException) as excinfo:
        await db_session.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = :jid",
            {"jid": journal_id}
        )
    assert "does not balance" in str(excinfo.value)
```

---

## 4. Automated Test Execution Commands

```bash
# 1. Run all backend unit & domain tests
pytest tests/unit/ -v

# 2. Run transactional concurrency & GiST exclusion tests
pytest tests/concurrency/test_booking_exclusion.py -v --asyncio-mode=auto

# 3. Run double-entry ledger balance invariants test
pytest tests/financial/test_ledger_invariants.py -v

# 4. Run webhook signature & replay security tests
pytest tests/security/test_webhook_security.py -v

# 5. Run Flutter mobile widget & integration tests
flutter test test/widget/
flutter test integration_test/driver_booking_journey_test.dart
```
