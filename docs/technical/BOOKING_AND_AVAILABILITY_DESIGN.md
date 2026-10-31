# Gadispot (formerly SmartPark Exchange) — Booking & Availability Engine Technical Specification (V2.3)

> **Document Version:** 2.3.0  
> **Date:** October 31, 2026  
> **Authors:** Principal Software Architect, Database Architect, Senior Backend Engineer  
> **Status:** Authoritative Engineering Design (Targeted Revision V2.3)  

---

## 1. System Overview & Core Engineering Principles

The SmartPark Booking & Availability Engine is responsible for authoritative parking inventory allocation, temporal concurrency control, multi-signal occupancy synthesis, and payment-reconciliation race handling.

### Non-Negotiable Engineering Principles
1. **PostgreSQL as Sole Concurrency Authority:** Double-bookings are physically prevented by PostgreSQL GiST exclusion constraints on `tstzrange` intervals at the storage engine level. Redis is strictly limited to ephemeral read-caching, UI rate-limiting, and client countdown timers. It is never the authoritative concurrency gate.
2. **Interval-Based Concurrency:** A hold or booking reserves a discrete time range $[t_{\text{start}}, t_{\text{end}})$, not an entire physical space. Non-overlapping requests for the same physical bay proceed in parallel without contention.
3. **Deterministic Expiration via Database Transactions:** A temporary hold row remains an active constraint in PostgreSQL until its status is explicitly transitioned. Expired holds are transitioned to `EXPIRED_HOLD` via an explicit, two-tier expiration mechanism (active background worker + opportunistic inline transition). Competing reservations are allowed only after this transition commits.
4. **Authoritative Hold Lifespan:** The checkout hold duration is strictly **480 seconds (8 minutes)** across all application components, API endpoints, payment credentials, and database records.
5. **Pessimistic Availability Synthesis (MSAI):** Conflicting operational signals (e.g., owner schedule open, but guard reports physical bay blocked) force an `UNCERTAIN` or `UNAVAILABLE` state. Inventory is never optimistically sold.
6. **Asynchronous Multi-Stage Refund Protocol:** Late payment reconciliation separates gateway refund initiation from bank settlement confirmation, tracking multi-stage refund states with durable database idempotency.

---

## 2. Unified Reservation-Occupancy Data Model

To eliminate split-brain states between temporary holds, active checkouts, confirmed bookings, and physical parking sessions, SmartPark implements a unified table: `space_reservations`.

```sql
-- Enable necessary PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Enumeration of Canonical Reservation Types
CREATE TYPE reservation_type_enum AS ENUM (
    'TEMPORARY_HOLD',
    'CONFIRMED_BOOKING',
    'ACTIVE_SESSION',
    'MAINTENANCE_BLOCK',
    'OWNER_BLACKOUT'
);

-- Enumeration of Lifecycle Statuses
CREATE TYPE reservation_status_enum AS ENUM (
    'ACTIVE_HOLD',              -- Temporary hold during checkout (strictly 480s / 8 min)
    'EXPIRED_HOLD',             -- Hold TTL elapsed without payment capture; slot released
    'CONFIRMED',                -- Payment captured and verified; awaiting driver arrival
    'ACTIVE_SESSION',           -- Driver checked in by guard; physically occupying bay
    'COMPLETED',                -- Driver checked out; session cleanly closed
    'CANCELLED_BY_DRIVER',      -- Driver cancelled per policy
    'CANCELLED_BY_OWNER',       -- Host emergency cancellation
    'NO_SHOW',                  -- Driver failed to check in within 30-min grace period
    'ARRIVAL_FAILED',           -- Bay obstructed; GPRP alternative/refund workflow triggered
    'REPLACED',                 -- Driver accepted alternative space under GPRP
    'RELEASED_UNFULFILLABLE'    -- Late payment arrived after hold expired & slot claimed by another
);

-- Enumeration of Multi-Stage Refund Lifecycle (Canonical 6-Stage Lifecycle)
CREATE TYPE refund_status_enum AS ENUM (
    'NONE',
    'REFUND_ELIGIBLE',          -- Qualification verified against cancellation or recovery policy
    'REFUND_REQUESTED',         -- Queued for gateway API execution in outbox
    'GATEWAY_ACCEPTED',         -- Gateway acknowledged refund request with refund_id
    'REFUND_PROCESSING',        -- Gateway processing on banking rails
    'REFUND_SETTLED',           -- Settlement confirmed via gateway webhook with bank UTR
    'REFUND_FAILED'             -- Gateway or bank rail rejected refund; requires manual ops review
);

-- Enumeration of Vehicle Categories
CREATE TYPE vehicle_category_enum AS ENUM (
    'TWO_WHEELER',
    'HATCHBACK',
    'SEDAN',
    'SUV',
    'EV_FOUR_WHEELER',
    'EV_TWO_WHEELER'
);

-- Unified Space Reservations Table
CREATE TABLE space_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parking_space_id UUID NOT NULL REFERENCES parking_spaces(id) ON DELETE RESTRICT,
    driver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    
    -- Temporal Range: [start_time, end_time) with timezone
    time_window TSTZRANGE NOT NULL,
    
    reservation_type reservation_type_enum NOT NULL,
    status reservation_status_enum NOT NULL,
    
    -- Hold Lifespan Management (strictly 480 seconds from creation)
    hold_expires_at TIMESTAMPTZ,
    
    -- Payment & Gateway Correlation
    payment_order_id VARCHAR(64),
    payment_transaction_id VARCHAR(64),
    booking_reference VARCHAR(32) NOT NULL UNIQUE,
    idempotency_key VARCHAR(64) UNIQUE,
    
    -- Multi-Stage Refund Tracking
    refund_status refund_status_enum NOT NULL DEFAULT 'NONE',
    refund_gateway_id VARCHAR(64),
    refund_arn_utr VARCHAR(64),
    refund_initiated_at TIMESTAMPTZ,
    refund_completed_at TIMESTAMPTZ,
    refund_failure_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CHECK CONSTRAINT: Holds must have an expiration timestamp
    CONSTRAINT chk_hold_expiration CHECK (
        (status != 'ACTIVE_HOLD') OR (hold_expires_at IS NOT NULL)
    ),
    
    -- CHECK CONSTRAINT: Time range must be strictly positive (start < end)
    CONSTRAINT chk_positive_time_window CHECK (
        lower(time_window) < upper(time_window)
    ),

    -- AUTHORITATIVE EXCLUSION CONSTRAINT:
    -- Prevents overlapping active reservations for the same physical bay
    CONSTRAINT prevent_overlapping_active_reservations
    EXCLUDE USING gist (
        parking_space_id WITH =,
        time_window WITH &&
    ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
);

-- Performance Indexes
CREATE INDEX idx_reservations_space_time ON space_reservations USING gist (parking_space_id, time_window);
CREATE INDEX idx_reservations_status ON space_reservations(status);
CREATE INDEX idx_reservations_driver ON space_reservations(driver_id);
CREATE INDEX idx_reservations_hold_expiry ON space_reservations(hold_expires_at) WHERE status = 'ACTIVE_HOLD';
CREATE INDEX idx_reservations_refund_status ON space_reservations(refund_status) WHERE refund_status IN ('REFUND_PENDING', 'REFUND_PROCESSING');
```

---

## 3. Explicit Hold Expiration Engine: Transaction Semantics & Concurrency

### 3.1 The Exclusion Constraint Expiration Dilemma
Because PostgreSQL partial exclusion constraints filter rows based on static column values (e.g., `WHERE status IN ('ACTIVE_HOLD', ...)`), **a row does not automatically leave the exclusion constraint when its timestamp passes in wall-clock time**. 

If a hold has `hold_expires_at = 10:08:00` and the current time is `10:08:01`, any competing `INSERT` statement for an overlapping window will still fail with `ExclusionViolation (23P01)` until the expired row is explicitly updated to a status outside the exclusion predicate (such as `EXPIRED_HOLD`).

### 3.2 Two-Tier Deterministic Expiration Architecture

SmartPark implements a two-tier database expiration mechanism to guarantee that expired holds are released reliably without relying on Redis TTL:

```
+---------------------------------------------------------------------------------------+
|                       TWO-TIER HOLD EXPIRATION ENGINE                                 |
+---------------------------------------------------+-----------------------------------+
| Tier 1: Active Periodic Background Worker         | Tier 2: Inline Opportunistic Sweep|
| (Scheduled ARQ / Celery Task every 5 seconds)     | (Executed within hold transaction)|
+---------------------------------------------------+-----------------------------------+
| Runs globally across all spaces.                  | Runs on the specific space being  |
| Identifies holds where hold_expires_at <= NOW().  | requested right before INSERT.    |
| Atomically updates status to 'EXPIRED_HOLD'.      | Clears stale holds in same atomic |
| Broadcasts WebSocket cancellation to client.     | transaction if worker is delayed. |
+---------------------------------------------------+-----------------------------------+
```

#### Tier 1: Active Background Expiration Worker (Runs every 5 seconds)
```sql
-- Executed by background worker in an explicit transaction
WITH expired_candidates AS (
    SELECT id, parking_space_id, payment_order_id, driver_id
    FROM space_reservations
    WHERE status = 'ACTIVE_HOLD'
      AND hold_expires_at <= CLOCK_TIMESTAMP()
    FOR UPDATE SKIP LOCKED
    LIMIT 100
)
UPDATE space_reservations r
SET status = 'EXPIRED_HOLD',
    updated_at = CLOCK_TIMESTAMP()
FROM expired_candidates c
WHERE r.id = c.id
RETURNING r.id, r.parking_space_id, r.payment_order_id, r.driver_id;
```
*Concurrency Semantics:*
- Uses `FOR UPDATE SKIP LOCKED` to prevent deadlocks with concurrent transactions (e.g. late webhook processing or user checkout actions).
- Commits immediately. The GiST partial index automatically excludes the row, releasing the interval for competing drivers.

#### Tier 2: Inline Opportunistic Expiration (Within Hold Creation Transaction)
To guard against worker stoppage or network jitter, every `POST /bookings/hold` transaction executes an inline sweep on the target space:

```python
async def create_booking_hold(space_id: UUID, window: TimeRange, driver_id: UUID, vehicle_id: UUID) -> SpaceReservation:
    """
    Executes atomic hold creation within a single READ COMMITTED transaction.
    Duration is strictly 480 seconds (8 minutes).
    """
    async with db.transaction(isolation_level="READ_COMMITTED") as tx:
        # Step 1: Inline opportunistic sweep for target space
        await tx.execute(
            """
            UPDATE space_reservations
            SET status = 'EXPIRED_HOLD', updated_at = CLOCK_TIMESTAMP()
            WHERE parking_space_id = :space_id
              AND status = 'ACTIVE_HOLD'
              AND hold_expires_at <= CLOCK_TIMESTAMP()
            """,
            {"space_id": space_id}
        )
        
        # Step 2: Attempt hold insertion with strict 480-second TTL
        try:
            reservation = await tx.fetch_one(
                """
                INSERT INTO space_reservations (
                    parking_space_id, driver_id, vehicle_id, time_window,
                    reservation_type, status, hold_expires_at, booking_reference
                ) VALUES (
                    :space_id, :driver_id, :vehicle_id, :time_window,
                    'TEMPORARY_HOLD', 'ACTIVE_HOLD', CLOCK_TIMESTAMP() + INTERVAL '480 seconds',
                    generate_booking_reference()
                ) RETURNING *
                """,
                {
                    "space_id": space_id,
                    "driver_id": driver_id,
                    "vehicle_id": vehicle_id,
                    "time_window": window
                }
            )
            return reservation
        except ExclusionViolation:
            raise SpaceUnavailableException("Selected time slot is currently locked by another driver or confirmed.")
```

---

## 4. Late Payment Resolution Protocol (LPRP) & Multi-Stage Refund

### 4.1 Race Handling: Webhook vs Expiration
1. Driver pays via UPI at $t = 478\text{s}$.
2. Hold expires at $t = 480\text{s}$; background worker sets status to `EXPIRED_HOLD`.
3. Driver 2 secures hold on the same space at $t = 485\text{s}$.
4. Payment gateway webhook `payment.captured` arrives for Driver 1 at $t = 505\text{s}$.

### 4.2 Webhook Handling Algorithm (Durable & Idempotent)

```python
async def handle_payment_captured_webhook(order_id: str, payment_id: str, amount_in_paise: int, event_id: str):
    """
    Authoritative payment webhook processor.
    Uses PostgreSQL unique constraints on payment_webhook_events for durable deduplication.
    """
    async with db.transaction(isolation_level="READ_COMMITTED") as tx:
        # 1. Deduplicate webhook at the database level
        event_inserted = await tx.execute(
            """
            INSERT INTO payment_webhook_events (gateway_name, gateway_event_id, event_type, payload, status)
            VALUES ('RAZORPAY', :event_id, 'payment.captured', :payload, 'PROCESSING')
            ON CONFLICT (gateway_name, gateway_event_id) DO NOTHING
            RETURNING id
            """,
            {"event_id": event_id, "payload": json.dumps({"order_id": order_id, "payment_id": payment_id})}
        )
        if not event_inserted:
            # Already processed or currently processing; idempotent exit
            return

        # 2. Acquire row-level lock on reservation
        res = await tx.fetch_one(
            "SELECT * FROM space_reservations WHERE payment_order_id = :order_id FOR UPDATE",
            {"order_id": order_id}
        )
        if not res:
            await record_orphan_payment(payment_id, order_id, amount_in_paise, tx)
            return

        # 3. Case A: Hold is still active
        if res.status == "ACTIVE_HOLD":
            await tx.execute(
                """
                UPDATE space_reservations 
                SET status = 'CONFIRMED', payment_transaction_id = :pid, updated_at = CLOCK_TIMESTAMP() 
                WHERE id = :id
                """,
                {"id": res.id, "pid": payment_id}
            )
            await issue_access_credentials(res.id, tx)
            await post_ledger_booking_confirmation(res, amount_in_paise, tx)
            await enqueue_outbox_event("BOOKING_CONFIRMED", {"reservation_id": str(res.id)}, tx)
            return

        # 4. Case B: Hold EXPIRED, but slot might still be vacant
        if res.status == "EXPIRED_HOLD":
            try:
                # Attempt to reclaim slot atomically
                await tx.execute(
                    """
                    UPDATE space_reservations 
                    SET status = 'CONFIRMED', payment_transaction_id = :pid, updated_at = CLOCK_TIMESTAMP() 
                    WHERE id = :id
                    """,
                    {"id": res.id, "pid": payment_id}
                )
                # Reclaim succeeded!
                await issue_access_credentials(res.id, tx)
                await post_ledger_booking_confirmation(res, amount_in_paise, tx)
                await enqueue_outbox_event("BOOKING_CONFIRMED", {"reservation_id": str(res.id)}, tx)
                return

            except ExclusionViolation:
                # 5. Case C: Race lost! Competing driver claimed the slot.
                # Mark UNFULFILLABLE and enter multi-stage refund workflow.
                await tx.execute(
                    """
                    UPDATE space_reservations 
                    SET status = 'RELEASED_UNFULFILLABLE',
                        payment_transaction_id = :pid,
                        refund_status = 'REFUND_PENDING',
                        refund_initiated_at = CLOCK_TIMESTAMP(),
                        updated_at = CLOCK_TIMESTAMP()
                    WHERE id = :id
                    """,
                    {"id": res.id, "pid": payment_id}
                )
                await post_ledger_unfulfillable_refund_pending(res, amount_in_paise, tx)
                await enqueue_outbox_event("REFUND_DISPATCH_REQUIRED", {"reservation_id": str(res.id), "payment_id": payment_id}, tx)

    # Outside atomic DB transaction: Asynchronous gateway refund dispatcher
    await dispatch_gateway_refund(res.id, payment_id, amount_in_paise)
```

### 4.3 Multi-Stage Refund States & Customer Settlement Window
A refund is **never described to the customer as instant**. The lifecycle spans:
1. `REFUND_PENDING`: Refund record created in database; queued in outbox.
2. `REFUND_PROCESSING`: Payment gateway accepted the refund request; ARN/UTR issued.
   - *Customer-Facing Status:* *"Refund initiated. Bank settlement typically completes in 5–7 business days per banking switch standards."*
3. `REFUNDED`: Bank confirmation webhook received; settlement confirmed.
4. `REFUND_FAILED`: Bank rail rejected refund (e.g. closed account); routed to ops finance queue for manual resolution.

---

## 5. Explicit Vehicle Compatibility Matrix

Parking bay compatibility cannot be evaluated with scalar comparisons (`ps.compatibility >= driver_vehicle`). A compact car bay cannot fit an SUV, and a standard car bay is an inefficient misuse of space for a two-wheeler unless specifically designated.

### 5.1 Compatibility Matrix Table

| Vehicle Category | Permitted Bay Types | Min Length (m) | Min Width (m) | Min Clearance (m) | EV Charger Matching |
|---|---|---|---|---|---|
| `TWO_WHEELER` | `TWO_WHEELER`, `BIKE_BAY` | 2.0 | 0.8 | 1.8 | Optional |
| `HATCHBACK` | `COMPACT_CAR`, `STANDARD_CAR`, `LARGE_CAR` | 3.8 | 1.7 | 1.9 | Optional |
| `SEDAN` | `STANDARD_CAR`, `LARGE_CAR` | 4.5 | 1.8 | 1.9 | Optional |
| `SUV` | `LARGE_CAR`, `SUV_BAY` | 4.8 | 1.9 | 2.1 | Optional |
| `EV_FOUR_WHEELER` | `STANDARD_CAR`, `LARGE_CAR` (must have `has_ev_charger = TRUE` if requested) | 4.5 | 1.8 | 1.9 | **Mandatory** if driver toggles "EV Required" |
| `EV_TWO_WHEELER` | `TWO_WHEELER` (must have `has_ev_charger = TRUE` if requested) | 2.0 | 0.8 | 1.8 | **Mandatory** if driver toggles "EV Required" |

### 5.2 Compatibility Evaluation Function
```sql
CREATE OR REPLACE FUNCTION fn_check_vehicle_bay_compatibility(
    p_vehicle_category vehicle_category_enum,
    p_bay_type VARCHAR(32),
    p_bay_length_m NUMERIC,
    p_bay_width_m NUMERIC,
    p_bay_height_m NUMERIC,
    p_bay_has_ev BOOLEAN,
    p_driver_req_ev BOOLEAN
) RETURNS BOOLEAN AS $$
BEGIN
    -- Check EV charger requirement
    IF p_driver_req_ev AND NOT p_bay_has_ev THEN
        RETURN FALSE;
    END IF;

    -- Evaluate physical dimensions based on vehicle category
    CASE p_vehicle_category
        WHEN 'TWO_WHEELER', 'EV_TWO_WHEELER' THEN
            RETURN p_bay_type IN ('TWO_WHEELER', 'BIKE_BAY') 
               AND p_bay_length_m >= 2.0 AND p_bay_width_m >= 0.8;
               
        WHEN 'HATCHBACK' THEN
            RETURN p_bay_type IN ('COMPACT_CAR', 'STANDARD_CAR', 'LARGE_CAR', 'SUV_BAY')
               AND p_bay_length_m >= 3.8 AND p_bay_width_m >= 1.7;
               
        WHEN 'SEDAN' THEN
            RETURN p_bay_type IN ('STANDARD_CAR', 'LARGE_CAR', 'SUV_BAY')
               AND p_bay_length_m >= 4.5 AND p_bay_width_m >= 1.8;
               
        WHEN 'SUV', 'EV_FOUR_WHEELER' THEN
            RETURN p_bay_type IN ('LARGE_CAR', 'SUV_BAY')
               AND p_bay_length_m >= 4.8 AND p_bay_width_m >= 1.9 AND p_bay_height_m >= 2.0;
               
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

---

## 6. Multi-Source Availability Intelligence (MSAI)

The MSAI engine synthesizes 7 discrete operational signals using a strict precedence hierarchy:

| Signal Priority | Signal Name | Authority Level | Freshness Threshold | Precedence Rule | Conflict Resolution |
|---|---|---|---|---|---|
| **Level 1 (Highest)** | Active GiST Reservations | Absolute | Real-time DB | Concurrency Lock | Overlapping windows throw `23P01`; slot marked `BOOKED`. |
| **Level 2** | Active 480s Holds | Absolute | 480 Seconds | Concurrency Lock | If active and unexpired, slot marked `HELD`. |
| **Level 3** | Guard Obstruction Reports | High (Negative) | 4 Hours | Negative Override | If guard reports bay blocked, bay marked `BLOCKED` immediately. |
| **Level 4** | Owner Manual Blackouts | High (Negative) | Defined Window | Negative Override | If owner blocks window, bay marked `UNAVAILABLE`. |
| **Level 5** | Operating Hours Schedule | Baseline | Weekly Rule | Operating Gate | If query falls outside open hours, bay marked `CLOSED`. |
| **Level 6** | Property Authorization Status| Baseline | Administrative | Eligibility Gate | If property is not `APPROVED`, entire property hidden from search. |
| **Level 7** | 15-Min Turnover Buffer | Policy | Continuous | Spacing Gate | 15-minute buffers appended before and after reservations to prevent clashes. |

*Pessimistic Invariant:* If any negative signal conflicts with an open calendar, the negative signal wins unconditionally.

---

## 7. Guaranteed Parking Recovery Protocol (GPRP): 8-Step Atomic Workflow

When an arriving driver finds their reserved bay obstructed (`ARRIVAL_FAILED`):
1. **Original Reservation Intact:** Original reservation is flagged `ARRIVAL_FAILED` but remains legally linked to the driver while alternatives are evaluated.
2. **Search Boundary Query:** GPRP engine queries active inventory within a **500m walking radius** (defined as a strict search boundary, not a guaranteed supply promise).
3. **Atomic Alternative Hold:** If an alternative bay is found, it is atomically reserved via a temporary hold (`FOR UPDATE SKIP LOCKED`) with an explicit 180-second driver decision timer.
4. **Driver Proposal:** In-app card (`SCR-108`) displays walking route, bay label, and photo.
5. **Driver Acceptance:** Driver taps "Accept Alternative" within 180 seconds.
6. **Booking Confirmation & Original Release:** System atomically confirms the alternative reservation and releases the original reservation (`status = 'REPLACED'`).
7. **Financial Adjustment:** If the alternative space has a higher tariff, platform absorbs the difference up to ₹100 via Account `4020` (Goodwill Subsidy Expense).
8. **Credential Swap:** A new `ENTRY_TOKEN` is minted for the alternative bay; the original QR is revoked.

*Fallback Rule:* If no alternative exists within 500m, or if the driver declines the alternative, the system immediately transitions to `REFUND_PENDING` and dispatches a 100% full refund of all charges and fees.
