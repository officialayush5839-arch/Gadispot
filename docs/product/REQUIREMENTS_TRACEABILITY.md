# Gadispot (formerly SmartPark Exchange) — Requirements Traceability Matrix (RTM)

> **Document Version:** 2.3.0  
> **Last Updated:** 2026-10-31  
> **Status:** Baselined Engineering Spec (V2.3 Harmonized)  
> **Audience:** QA Leads, Test Engineers, Software Developers, Technical Documentation  

---

## 1. Traceability Overview & Verification Methodology

Every functional and non-functional requirement defined in the Gadispot specification is mapped to its user persona, feature domain, release priority, architectural component, testable acceptance criteria, and explicit test scenario in [`docs/quality/TEST_STRATEGY.md`](../quality/TEST_STRATEGY.md).

### Verification Levels
- **UNIT:** Pytest / Flutter unit tests (isolated functions, state reducers, pricing math).
- **INT:** Service-level integration tests with local PostgreSQL and Redis test containers.
- **API:** OpenAPI schema contract and HTTP API integration tests (`pytest-httpx`, `TestClient`).
- **CONCURRENCY:** Multi-threaded / async race-condition tests (e.g., simultaneous booking holds).
- **SEC:** Security penetration tests (IDOR, token replay, signature forgery, rate-limiting stress).
- **E2E:** End-to-end integration workflows simulating driver, payment aggregator, and guard interactions.

---

## 2. Authentication & Account Management (AUTH)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **AUTH-001** | Phone Number Registration & OTP Request | Driver, Owner, Guard | **P0 (MVP)** | §14.1 | Given a valid 10-digit Indian mobile number (+91), when requested, an OTP verification process is triggered via Firebase Auth. Plaintext OTP is NEVER stored in SmartPark database. | `INT`, `API`, `SEC` | `TS-01` |
| **AUTH-002** | OTP Verification & Token Exchange | Driver, Owner, Guard | **P0 (MVP)** | §14.2 | Given a valid Firebase ID token submitted to `POST /api/v1/auth/session`, backend verifies signature against Google x509 certs, validates expiration, and returns internal SmartPark session JWT. | `UNIT`, `INT`, `SEC` | `TS-01` |
| **AUTH-003** | Auth Rate Limiting & Cooldown | All | **P0 (MVP)** | §14.3 | Max 3 OTP requests per phone number per 15 minutes; 60-second mandatory cooldown between consecutive requests. Violations return HTTP 429 Too Many Requests. | `INT`, `API`, `SEC` | `TS-03` |
| **AUTH-004** | Role Identification & Scoped Claims | All | **P0 (MVP)** | §14.4 | Scoped JWT contains user ID and active role (`driver`, `owner`, `guard`, `ops`). Accessing unauthorized role endpoints returns HTTP 403 Forbidden. | `UNIT`, `API`, `SEC` | `TS-11`, `TS-12` |
| **AUTH-005** | Seamless Role Switching | Driver, Owner | **P0 (MVP)** | §14.5 | A single verified phone number can toggle between Driver and Owner interfaces in the Flutter app without logging out, exchanging token claims via `POST /api/v1/auth/switch-role`. | `INT`, `API` | `Unit-Auth` |
| **AUTH-006** | Secure Session Logout & Revocation | All | **P0 (MVP)** | §14.6 | Upon logout, current refresh token is added to Redis revocation blocklist with remaining TTL; local secure storage is wiped on mobile device. | `INT`, `API`, `SEC` | `Sec-Token` |
| **AUTH-007** | Privileged Operations 2FA (TOTP) | Platform Ops | **P1** | §14.7 | Operations staff accessing sensitive audit or payout overrides must provide an RFC 6238 TOTP code verified via PyOTP. | `UNIT`, `INT`, `SEC` | `Sec-MFA` |

---

## 3. Driver Capabilities (DRV)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **DRV-001** | Profile & Vehicle Registration | Driver | **P0 (MVP)** | §10.1 | Driver can add multiple vehicles (Registration Number, Vehicle Type: 2W/4W Hatchback/Sedan/SUV). Registration numbers validated against Indian format (e.g., `KA-01-AB-1234`). | `UNIT`, `API` | `Unit-Veh` |
| **DRV-002** | Location-Based Parking Search | Driver | **P0 (MVP)** | §10.2 | Given GPS coordinates or destination search query + arrival time + duration, backend returns only verified, available, and vehicle-compatible parking spaces within radius. | `INT`, `API` | `Int-Search` |
| **DRV-003** | Interactive Map & List Synchronization | Driver | **P0 (MVP)** | §10.3 | Map renders pin markers with price-per-hour badges. Tapping a map pin highlights the corresponding card in the bottom list carousel. | `E2E (Flutter UI)` | `E2E-Map` |
| **DRV-004** | Space Details Page | Driver | **P0 (MVP)** | §10.4 | Displays verified photos, exact hourly rate, security features (CCTV, Covered, Gated), access restrictions, cancellation policy, and operating hours. | `API`, `E2E` | `API-Details` |
| **DRV-005** | Atomic Time-Window Hold Creation | Driver | **P0 (MVP)** | §10.5 | Initiating booking inserts row into `space_reservations` with status `ACTIVE_HOLD` and 480-second (8-minute) TTL. Enforced by PostgreSQL GiST exclusion constraint (`23P01` on conflict). | `CONCURRENCY`, `INT` | `TS-01`, `TS-02`, `TS-03` |
| **DRV-006** | Razorpay Checkout Launch | Driver | **P0 (MVP)** | §10.6 | Flutter app launches Razorpay SDK with backend-generated `order_id`, pre-filling driver phone and amount. No payment gateway secret exists in app. | `INT`, `E2E` | `E2E-Pay` |
| **DRV-007** | Authoritative Booking Confirmation | Driver | **P0 (MVP)** | §10.7 | Booking confirmation screen renders ONLY after backend confirms payment via webhook or polling verification. Never confirms on frontend callback alone. | `INT`, `API`, `E2E` | `TS-04`, `TS-05` |
| **DRV-008** | Dynamic Access QR Display | Driver | **P0 (MVP)** | §10.8 | Renders high-contrast QR code generated from backend cryptosecure opaque token (`spx_...`); displays active booking countdown timer and navigation link. | `UNIT`, `E2E` | `TS-08`, `TS-09` |
| **DRV-009** | Authoritative Policy Cancellation | Driver | **P0 (MVP)** | §10.9 | Driver cancels booking prior to arrival. Refund computed per authoritative cancellation policy (>2h: 100% parking fee; 30m–2h: 50% parking fee; <30m: 0% refund; convenience fee non-refundable; marked PROPOSED pending founder approval) and multi-stage refund queued. | `INT`, `API` | `TS-14` |
| **DRV-010** | Active Session Tracking & Countdown | Driver | **P0 (MVP)** | §10.10 | Once guard records entry, app displays live elapsed session time, scheduled exit time, and "Extend Parking" button. | `INT`, `API` | `E2E-Session` |
| **DRV-011** | Booking Extension Flow | Driver | **P0 (MVP)** | §10.11 | Extension request re-validates availability for extra duration; creates secondary payment order; upon payment, extends reservation end time atomically. | `CONCURRENCY`, `INT` | `TS-02`, `TS-19` |
| **DRV-012** | Booking History & Receipts | Driver | **P0 (MVP)** | §10.12 | Lists past, active, and cancelled bookings with itemized receipts showing base price, platform fee, GST, and payment method reference. | `API` | `API-Hist` |
| **DRV-013** | Rate & Review Completed Session | Driver | **P0 (MVP)** | §10.13 | Once session completes, driver can submit 1-5 star rating and structured tags (Clean, Easy Access, Courteous Guard, Safe). | `API` | `API-Review` |
| **DRV-014** | Arrival Issue Reporting (SOS) | Driver | **P0 (MVP)** | §10.14 | If driver encounters a locked gate or occupied slot, tapping "Report Arrival Issue" triggers GPRP incident protocol immediately. | `INT`, `API`, `E2E` | `TS-07`, `TS-13` |

---

## 4. Space Owner & Property Management (OWN)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **OWN-001** | Property Registration | Owner | **P0 (MVP)** | §11.1 | Owner creates property profile: Name, Address, Geolocation (Lat/Long), Property Type (Independent House, Gated Society, Commercial Lot). | `API`, `INT` | `API-Prop` |
| **OWN-002** | Parking Space Inventory Definition | Owner | **P0 (MVP)** | §11.2 | Owner adds specific parking bays: Bay Identifier, Vehicle Size Compatibility, Covered/Open, EV Charging Available (Yes/No). | `API`, `INT` | `API-Bays` |
| **OWN-003** | Authorization Evidence Submission | Owner | **P0 (MVP)** | §11.3 | Uploads required legal proof (Property Tax Receipt, Electricity Bill, Society NOC, or Lease Agreement). Files stored in private encrypted S3 bucket. | `INT`, `SEC` | `Sec-Upload` |
| **OWN-004** | Operating Hours & Schedule Setup | Owner | **P0 (MVP)** | §11.4 | Owner sets recurring weekly operating windows (e.g., Mon-Fri 09:00 - 18:00) and temporary blackout dates. Slots outside operating windows are never bookable. | `UNIT`, `INT`, `API` | `Int-Sched` |
| **OWN-005** | Pricing Configuration | Owner | **P0 (MVP)** | §11.5 | Configures base hourly rate per space (e.g., ₹40/hr for 4W, ₹20/hr for 2W) and minimum booking duration (30 minutes, marked PROPOSED pending founder approval). | `UNIT`, `API` | `Unit-Price` |
| **OWN-006** | Listing Verification Gatekeeper | Owner, System | **P0 (MVP)** | §11.6 | A space CANNOT transition to `PUBLISHED` or appear in search results until property authorization is marked `APPROVED` by Platform Operations. | `INT`, `API`, `SEC` | `TS-20` |
| **OWN-007** | Real-time Owner Dashboard | Owner | **P0 (MVP)** | §11.7 | Mobile dashboard displays: Active Parked Vehicles, Today's Upcoming Bookings, Gross Today's Earnings, and Space Occupancy Status. | `API`, `E2E` | `E2E-Dash` |
| **OWN-008** | Manual Space Blackout / Block | Owner | **P0 (MVP)** | §11.8 | Owner can manually block a space for personal use for specific future hours, provided no confirmed booking already exists for that window. | `CONCURRENCY`, `INT` | `TS-02` |
| **OWN-009** | Bank Account Linking (Penny-Drop) | Owner | **P0 (MVP)** | §11.9 | Owner inputs Account Number + IFSC. System validates account via Razorpay automated Penny-Drop verification prior to enabling payouts. | `INT`, `API`, `SEC` | `API-Bank` |
| **OWN-010** | Earnings & Payout History | Owner | **P0 (MVP)** | §11.10 | Itemized breakdown of gross bookings, platform fee deductions (15%), net payable, settlement status (Processing / Transferred), and UTR reference. | `INT`, `API` | `TS-15` |
| **OWN-011** | Guard Assignment to Property | Owner | **P0 (MVP)** | §11.11 | Owner enters security guard's verified mobile number to grant them scoped QR scanning rights for that specific property. | `API`, `INT` | `TS-11` |

---

## 5. Guard & Access Management (GRD & ACC)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **GRD-001** | Guard Scoped Mobile Access | Guard | **P0 (MVP)** | §12.1 | Guard authenticates via phone OTP; app renders ONLY guard interface for assigned properties. Guard cannot access financial or owner payout data. | `API`, `SEC` | `TS-11` |
| **ACC-001** | Dynamic Access QR Token Issuance | System | **P0 (MVP)** | §21.1 | Upon booking confirmation, backend generates opaque, cryptosecure 128-bit random token stored in `access_credentials` table with reference to reservation ID. | `UNIT`, `INT`, `SEC` | `TS-08` |
| **ACC-002** | Guard QR Code Scanning | Guard | **P0 (MVP)** | §21.2 | Guard uses `mobile_scanner` view to scan driver QR. Guard app transmits scanned token + guard geolocation to `POST /api/v1/access/validate-scan`. | `INT`, `API` | `TS-08` |
| **ACC-003** | Comprehensive QR Scan Validation | System | **P0 (MVP)** | §21.3 | Backend validates: 1) Token exists, 2) Booking is CONFIRMED, 3) Token matches property, 4) Current time is within valid arrival window (Start - 15 min to End), 5) Token has not been consumed. | `UNIT`, `INT`, `API` | `TS-08`, `TS-10` |
| **ACC-004** | QR Replay Prevention (One-Time Burn) | System | **P0 (MVP)** | §21.4 | Upon successful entry scan, token status transitions to `CONSUMED`. Subsequent scans of same token or screenshot return HTTP 409 "QR Code Already Used". | `CONCURRENCY`, `SEC` | `TS-09` |
| **ACC-005** | Entry Recording & Session Initiation | Guard, System | **P0 (MVP)** | §22.1 | Valid entry scan updates booking to `ACTIVE_SESSION`, records exact `entry_timestamp`, guard ID, and sends push alert to driver and owner. | `INT`, `API` | `E2E-Entry` |
| **ACC-006** | Exit Recording & Session Completion | Guard, System | **P0 (MVP)** | §22.2 | Guard scans driver exit QR or taps "Confirm Exit" against active session. Backend records `exit_timestamp`, calculates total duration, and marks session `COMPLETED`. | `INT`, `API` | `TS-18` |
| **ACC-007** | Overstay Detection & Penalty Flagging | System | **P0 (MVP)** | §22.3 | If exit timestamp exceeds reserved departure by >15 minutes (grace period), backend calculates overstay penalty (1.5x hourly rate) and logs unbilled charge. | `UNIT`, `INT` | `TS-19` |
| **ACC-008** | Controlled Manual Guard Fallback | Guard | **P0 (MVP)** | §21.4 | In underground cellular dead zones, guard cross-checks physical vehicle plate against locally cached shift schedule, logs entry locally, and syncs upon reconnection. | `INT`, `E2E` | `TS-17` |
| **GRD-002** | Guard Arrival Incident Reporting | Guard | **P0 (MVP)** | §12.2 | If driver arrives but reserved slot is physically blocked, guard taps "Report Space Blocked" on scan result screen, automatically triggering GPRP. | `INT`, `API` | `TS-07` |
| **GRD-003** | Today's Expected Vehicle Schedule | Guard | **P0 (MVP)** | §12.3 | Guard can view chronological list of expected arrivals for current shift, displaying Vehicle Number, Slot Number, and Arrival Time. PII is strictly masked. | `API`, `SEC` | `API-Schedule` |

---

## 6. Multi-Source Availability Intelligence (AVAIL)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **AVAIL-001** | Multi-Source Signal Ingestion | System | **P0 (MVP)** | §18.1 | Ingests 7 signals: 1) Owner Operating Schedule, 2) Owner Blackout, 3) Confirmed Database Bookings, 4) Active Database Holds, 5) Active Sessions, 6) Guard Incidents, 7) Buffers. | `UNIT`, `INT` | `Int-MSAI` |
| **AVAIL-002** | Database GiST Exclusion Constraint | System | **P0 (MVP)** | §18.2 | `space_reservations` table enforces `EXCLUDE USING gist (parking_space_id WITH =, time_window WITH &&)` where status in `('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION')`. | `CONCURRENCY`, `INT` | `TS-01`, `TS-02` |
| **AVAIL-003** | 8 Canonical Availability States | System | **P0 (MVP)** | §18.3 | Explicit state evaluation: `AVAILABLE`, `TEMPORARILY_HELD`, `BOOKED`, `OCCUPIED`, `BLOCKED`, `UNVERIFIED`, `UNCERTAIN`, `UNAVAILABLE`. No ambiguous booleans. | `UNIT`, `API` | `Unit-States` |
| **AVAIL-004** | Signal Conflict Resolution (Pessimistic Safety) | System | **P0 (MVP)** | §18.4 | If owner schedule indicates AVAILABLE but guard reports space OCCUPIED or incident active, conflict resolution algorithm forces state to `UNCERTAIN` / `UNAVAILABLE`. Never optimistically sold. | `UNIT`, `INT` | `Int-Conflict` |
| **AVAIL-005** | Booking Buffer Enactment | System | **P0 (MVP)** | §18.5 | Configurable 15-minute buffer automatically inserted between consecutive bookings to absorb minor traffic delays and parking turnover. | `UNIT`, `INT` | `Unit-Buffer` |
| **AVAIL-006** | Stale Hold Lazy Cleanup | System | **P0 (MVP)** | §18.6 | Every hold creation query executes `UPDATE space_reservations SET status='EXPIRED_HOLD' WHERE hold_expires_at < NOW() AND status='ACTIVE_HOLD'`. | `INT`, `API` | `TS-04` |

---

## 7. Payments, Ledgers & Payouts (PAY, LEDG, POUT)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **PAY-001** | Server-Side Order Generation | Driver, System | **P0 (MVP)** | §20.1 | Backend creates payment order via Razorpay API (`POST /v1/orders`) with exact amount in paise, currency `INR`, and linked `reservation_id` in order notes. | `INT`, `API` | `Int-Order` |
| **PAY-002** | Authoritative Webhook Verification | System | **P0 (MVP)** | §20.2 | `POST /api/v1/webhooks/razorpay` verifies HMAC-SHA256 signature using raw request body. Rejects invalid signatures with HTTP 400. Never processes unverified events. | `UNIT`, `INT`, `SEC` | `TS-05` |
| **PAY-003** | Webhook Idempotency & Replay Shield | System | **P0 (MVP)** | §20 | Webhook event recorded in PostgreSQL `payment_webhook_events` table with unique constraint on `(gateway_name, gateway_event_id)`; Redis accelerates in-flight checking. Duplicate deliveries return HTTP 200 without duplicate database mutations. | `CONCURRENCY`, `INT` | `TS-05` |
| **PAY-004** | Fallback Status Verification Polling | System | **P0 (MVP)** | §20 | If webhook is delayed (>60 sec post-checkout), mobile app triggers `GET /api/v1/payments/verify-status/{order_id}`, prompting backend to query Razorpay REST API directly. | `INT`, `API` | `Int-Poll` |
| **PAY-005** | Late Payment Resolution Protocol (LPRP) | System | **P0 (MVP)** | §20 | If payment arrives after hold expired and slot was claimed by another driver, system marks `RELEASED_UNFULFILLABLE` and automatically dispatches 100% full refund via 6-stage lifecycle. | `INT`, `API`, `CONCURRENCY` | `TS-04` |
| **LEDG-001** | Double-Entry Immutable Ledger | System | **P0 (MVP)** | §22 | Every financial mutation creates balanced debit and credit entries in append-only `journal_entries` and `journal_lines` tables ($\sum \text{Debits} = \sum \text{Credits}$). Updates and deletes are database-revoked. | `UNIT`, `INT` | `TS-16` |
| **LEDG-002** | Automated Revenue & Commission Split | System | **P0 (MVP)** | §22 | Upon confirmation, ledger records: Debit Gateway Transit (₹91.80), Credit Owner Payable (₹65.84), Credit Commission (₹12.00), Credit Convenience (₹10.00), Credit GST (₹3.96). | `UNIT`, `INT` | `TS-16` |
| **REF-001** | Automated Policy-Authorized Refund | System | **P0 (MVP)** | §21 | When cancellation or GPRP failure qualifies for refund, system triggers 6-stage asynchronous refund lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`), creates reversal ledger entries, and updates booking. | `INT`, `API` | `TS-14` |
| **POUT-001** | Weekly Owner Settlement Calculation | System | **P0 (MVP)** | §23 | Weekly payout engine aggregates completed sessions for eligible owners; checks minimum ₹500 balance threshold; prepares transfer batch. | `INT`, `API` | `TS-15` |
| **POUT-002** | Two-Phased Marketplace Payouts | System | **P0 (MVP)** | §23 | Phase 1 executes automated direct batch bank transfers via corporate account IMPS under MoR status; Phase 2 executes Razorpay Route linked account transfers upon turnover qualification. | `INT`, `API` | `TS-15` |

---

## 8. Guaranteed Parking Recovery Protocol (REC)

| Req ID | Feature Domain | User Role | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **REC-001** | Arrival Incident Trigger | Guard, Driver | **P0 (MVP)** | §26 | Incident triggered when space is occupied, blocked, or gate inaccessible. Space is immediately marked `BLOCKED` in MSAI to prevent future bookings. | `INT`, `API` | `TS-07` |
| **REC-002** | Dynamic Alternative Search Algorithm | System | **P0 (MVP)** | §26 | System queries active inventory within 500m walking radius with compatible vehicle size and matching time window. Excludes unverified or conflicted spaces. | `UNIT`, `INT` | `TS-07` |
| **REC-003** | Alternative Offer Presentation | Driver | **P0 (MVP)** | §26 | App presents alternative space card with photo, exact walking distance, and clear "Accept Reassignment" / "Decline & Get Full Refund" options with 180s countdown timer. | `E2E (Flutter UI)` | `TS-07` |
| **REC-004** | Alternative Acceptance & QR Re-issue | Driver, System | **P0 (MVP)** | §26 | Upon acceptance, system invalidates original QR token, creates booking re-allocation record, generates new QR token for alternative property, and notifies new guard. | `INT`, `API`, `E2E` | `TS-13` |
| **REC-005** | No Alternative / Decline Fallback | Driver, System | **P0 (MVP)** | §26 | If no alternative is found within 500m OR driver taps "Decline", system immediately triggers 100% full refund (`REFUND_ELIGIBLE`); marks incident `UNRESOLVED_REFUNDED`. | `INT`, `API` | `TS-07` |

---

## 9. Security, Privacy & Non-Functional Requirements (SEC, NFR)

| Req ID | Feature Domain | Scope | Priority | PRD Section | Acceptance Criteria | Automated Test Coverage | Test Scenario Ref |
|---|---|---|---|---|---|---|---|
| **SEC-001** | Object-Level Authorization & IDOR Shield | All APIs | **P0 (MVP)** | §30.1 | Users cannot access or mutate bookings, vehicles, or properties owned by another user ID. `user_id` extracted strictly from validated session claims, never query parameters. | `SEC`, `API` | `TS-11`, `TS-12` |
| **SEC-002** | Secret Management & Zero App Secrets | Mobile & CI/CD | **P0 (MVP)** | §30.2 | Zero payment API secrets, Firebase service account keys, or database credentials bundled in Flutter binary. Static code analysis (`trufflehog`) passes clean in CI. | `SEC (Static Scan)` | `Sec-Secrets` |
| **SEC-003** | Data Encryption at Rest & In Transit | Backend / DB | **P0 (MVP)** | §30.3 | All traffic forced over TLS 1.3. Database storage volumes encrypted via AWS KMS (AES-256). Sensitive PII (vehicle numbers, phone numbers) encrypted in database. | `SEC`, `INT` | `Sec-Crypto` |
| **SEC-004** | Immutable Comprehensive Audit Trail | All Mutating APIs | **P0 (MVP)** | §30.4 | Every state change on bookings, authorization reviews, payouts, and access scans generates an immutable record in `audit_events` with actor ID, IP, and before/after JSON delta. | `INT`, `API` | `TS-16` |
| **NFR-001** | Search API Response Latency | System Performance | **P0 (MVP)** | §31.1 | Spatial search query for available parking spaces within 5km radius responds in <300ms at 95th percentile (P95) under 100 concurrent requests. | `STRESS (Locust)` | `Perf-Search` |
| **NFR-002** | Atomic Booking Hold Latency | System Performance | **P0 (MVP)** | §31.2 | Temporary hold acquisition and GiST lock insertion executes in <50ms P99 in PostgreSQL. | `STRESS (Locust)` | `TS-01` |
| **NFR-003** | QR Code Validation Scan Latency | System Performance | **P0 (MVP)** | §31.3 | Guard scan validation endpoint `POST /api/v1/access/validate-scan` responds in <250ms P95 over 4G cellular connections. | `STRESS`, `API` | `Perf-Scan` |
| **NFR-004** | High Availability Uptime Target | Infrastructure | **P0 (MVP)** | §31.4 | Target 99.9% uptime for core booking and access verification APIs during operating hours (06:00 - 23:00 IST). | `INFRA MONITORING` | `Infra-SLA` |
| **NFR-005** | Offline Network Resilience (Guard App) | Mobile App | **P0 (MVP)** | §31.5 | Guard app handles network dropouts gracefully; allows controlled manual verification against locally cached shift schedule and syncs upon reconnection. | `E2E`, `UNIT` | `TS-17` |
