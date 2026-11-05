# Gadispot Engineering Decision Log & Architectural Decision Records (ADR)

> **Document Version:** 1.0.0 (Phase 0 Engineering Baseline)  
> **Authoritative Specification:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
> **Format:** Michael Nygard Architectural Decision Record Template  
> **Audience:** Principal Architects, Engineering Leads, Core Developers, Auditors  
> **Status:** APPROVED & BASELINED (Phase 0)  
> **Last Updated:** 2026-11-05T11:20:00Z  

---

## 1. Master Architectural Decision Register

| ADR ID | Decision Title | Status | Date | Decision Category | Primary Invariant Enforced |
|---|---|:---:|---|---|---|
| **ADR-001** | PostgreSQL GiST Exclusion Constraints for Temporal Concurrency | **APPROVED** | 2026-10-31 | Storage & Concurrency | Zero double-bookings at storage engine level |
| **ADR-002** | In-Process Modular Monolith on Python FastAPI over Microservices | **APPROVED** | 2026-10-31 | Architecture & Framework | Sub-millisecond ACID transactions across domains |
| **ADR-003** | Cryptographic Separation of Payment QR and Parking Access QR | **APPROVED** | 2026-10-31 | Security & Access Control | Zero PII in access passes; replay immunity |
| **ADR-004** | Append-Only Double-Entry General Ledger with Zero Child Lock Protocol | **APPROVED** | 2026-10-31 | Finance & Accounting | $\sum \text{Debits} = \sum \text{Credits}$; deadlock freedom |
| **ADR-005** | Two-Phased Marketplace Payout Architecture (Direct Batch Fallback) | **APPROVED** | 2026-10-31 | Payments & Settlements | Automated payouts prior to ₹40L turnover limit |
| **ADR-006** | Firebase Phone Auth Client SDK with Authoritative Server JWT Minting | **APPROVED** | 2026-10-31 | Authentication & Identity | Zero plaintext OTP storage; server-verified claims |
| **ADR-007** | Single Cross-Platform Flutter Mobile Binary with Dynamic Role Navigation | **APPROVED** | 2026-10-31 | Mobile Application | Single codebase for Driver, Owner, Guard, Ops |
| **ADR-008** | Controlled Manual Fallback Protocol for Offline Guard Operations | **APPROVED** | 2026-10-31 | Gate Operations & Offline | Reliable basement gate admission with audit trails |
| **ADR-009** | Late Payment Resolution Protocol (LPRP) with Automated 6-Stage Refund | **APPROVED** | 2026-10-31 | Payments & Concurrency | Slot recovery or 100% automated customer refund |
| **ADR-010** | Pessimistic Safety in Multi-Source Availability Intelligence (MSAI) | **APPROVED** | 2026-10-31 | Inventory & Availability | Any conflict forces slot offline; zero false promises |
| **ADR-011** | Universal Payment Orchestration Platform (Hyperswitch) & Pluggable Gateways | **APPROVED** | 2026-11-05 | Payments & Integrations | Vendor independence; smart failover; zero-MDR UPI |
| **ADR-012** | Version-Controlled Alembic Migrations & Session-Scoped Test Infrastructure | **APPROVED** | 2026-11-05 | Database & Testing | Elimination of raw SQL test schemas and connection churn |
| **ADR-013** | DPDPA Data Minimization via Automated 7-Day S3 Gate Photo Purge | **APPROVED** | 2026-11-05 | Privacy & Compliance | Statutory data minimization under Digital Data Protection Act |

---

## 2. Established Founder Baselines (`FD-01` through `FD-05`)

These five architectural baseline decisions were formally established and approved by founder direction. They serve as immutable foundation rules for the Gadispot engineering architecture:

### `FD-01` (Payment Gateway Multi-Provider Architecture)
- **Question Ref:** `Q1` / `OQ-PAY-001`.
- **Founder Decision:** Adopt a Dual Application strategy: Razorpay as primary payment gateway, Cashfree as secondary standby gateway.
- **Architectural Implementation:** Isolated behind the `PaymentGatewayPort` interface. Domain checkout services interact exclusively with the port contract, allowing runtime gateway switching and automated failover without modifying business logic.

### `FD-02` (GPRP Alternative Space Rejection / Failure Refund)
- **Question Ref:** `Q2` / `OQ-OPS-004`.
- **Founder Decision:** Provide a **100% Full Refund to the Original Payment Instrument** if an alternative parking space cannot be located within 500 meters or if the driver declines the offered alternative space within the 180-second decision window.
- **Architectural Implementation:** State machine transitions to `ARRIVAL_FAILED` $\to$ `RELEASED_UNFULFILLABLE` $\to$ `REFUND_ELIGIBLE`. The automated 6-stage refund pipeline dispatches the refund request to the gateway transit account without charging cancellation or platform fees.

### `FD-03` (Basement Offline Access Fallback)
- **Question Ref:** `Q3` / `OQ-TECH-010`.
- **Founder Decision:** Implement a Controlled Manual Exception Protocol for subterranean parking garages experiencing cellular outages.
- **Architectural Implementation:** The guard mobile application uses an encrypted local SQLite database (SQLCipher AES-256) caching the active shift's arrival schedule. In offline mode, the guard cross-checks license plates, captures gate photo proof, and records offline admissions. Reconnection flushes the synchronization queue, and photos are purged after 7 days per DPDPA rules.

### `FD-04` (Configurable Maximum Booking Duration)
- **Question Ref:** `Q4` / `OQ-BIZ-003`.
- **Founder Decision:** Maximum booking duration is configurable per property, defaulting to **24 hours** for standard residential and commercial properties.
- **Architectural Implementation:** Configured via `properties.max_booking_duration_hours`. Enforced by database check constraint `chk_positive_time_window` and application validation during hold creation.

### `FD-05` (Marketplace Host Payout Settlement Mechanism)
- **Question Ref:** `Q5` / `OQ-PAY-002`.
- **Founder Decision:** MVP marketplace host payouts executed via scheduled batch bank transfers (IMPS/NEFT) from the platform's corporate bank account under Merchant of Record (MoR) status.
- **Architectural Implementation:** Automated weekly batch worker (Tuesdays) aggregates eligible balances ($\ge ₹500$) and dispatches IMPS transfers via RazorpayX or Cashfree Payouts API, posting balancing ledger journals (`JRN-PO`).

---

## 3. Commercial Policies Parameterized as Proposed (`POL-COM-01` .. `POL-SUB-01`)

The following seven commercial policies are marked `PROPOSED (Pending Founder Approval)`. Per engineering governance rules, they are **never hardcoded in source code** and are instead parameterized via database configuration tables (`system_configurations`) with safe runtime defaults:

1. **`POL-COM-01` (Platform Commission Rate):** Flat 15.0% of gross parking tariff.
   - *Default Setting:* `0.1500` stored in `system_configurations.platform_commission_rate`.
   - *Ledger Impact:* Credited to Account 3010 (Platform Commission Revenue).
2. **`POL-DUR-01` (Minimum Booking Duration):** Exactly 30 Minutes.
   - *Default Setting:* `30` stored in `system_configurations.min_booking_duration_minutes`.
   - *Validation Impact:* Booking requests shorter than 30 minutes rejected with HTTP 422.
3. **`POL-CAN-01` (Tiered Cancellation Refunds):**
   - $>2$ hours before arrival: 100% of parking tariff refunded.
   - 30 minutes to 2 hours before arrival: 50% of parking tariff refunded.
   - $<30$ minutes before arrival: 0% refund (100% forfeited to host).
   - Platform convenience fee is non-refundable across all tiers.
   - *Default Setting:* Stored as JSON policy matrix in `system_configurations.cancellation_tiers`.
4. **`POL-ARR-02` (Driver No-Show Grace Period):** Exactly 30 Minutes past scheduled arrival time.
   - *Default Setting:* `30` stored in `system_configurations.no_show_grace_minutes`.
   - *Lifecycle Impact:* Booking transitions to `NO_SHOW` and space released if guard check-in has not occurred after 30 minutes.
5. **`POL-OST-01` (Overstay Penalty Tariff):** 1.5× Base Hourly Rate in 30-minute increments.
   - *Default Setting:* `1.50` stored in `system_configurations.overstay_multiplier`.
   - *Billing Impact:* Overstay assessed on guard exit scan if departure exceeds 15-minute grace period.
6. **`POL-POT-01` (Host Payout Schedule & Minimum Balance Threshold):** Weekly batch payouts on Tuesdays for accumulated host balances $\ge ₹500$.
   - *Default Setting:* `50000` (in paise) stored in `system_configurations.min_payout_threshold_paise`.
   - *Settlement Impact:* Balances under ₹500 roll over to the subsequent payout cycle.
7. **`POL-SUB-01` (GPRP Customer Recovery Subsidy Cap):** Up to ₹100 absorbed by platform.
   - *Default Setting:* `10000` (in paise) stored in `system_configurations.max_gprp_subsidy_paise`.
   - *Ledger Impact:* Rate differential charged to Account 4020 (GPRP Customer Recovery Subsidy Expense).

---

## 4. Architectural Decision Records (ADRs)

### ADR-001: PostgreSQL GiST Exclusion Constraints for Authoritative Concurrency
- **Status:** APPROVED
- **Context:** In a time-slotted parking marketplace, double-bookings occur when two concurrent checkout requests attempt to reserve the same physical bay for overlapping time intervals. Using application-level locks or Redis keys introduces split-brain risks during network partitions or process crashes.
- **Decision:** Enforce temporal non-overlapping exclusion directly in the PostgreSQL storage engine using `btree_gist`, range types (`tstzrange`), and an exclusion constraint:
  ```sql
  CONSTRAINT prevent_overlapping_active_reservations
  EXCLUDE USING gist (
      parking_space_id WITH =,
      time_window WITH &&
  ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'));
  ```
  PostgreSQL is the single authoritative source of truth. Redis is used solely for non-authoritative caching and countdown presentation.
- **Consequences:** Eliminates race conditions and double-bookings with database ACID transaction guarantees. GiST write overhead is negligible for parking reservation frequencies.

### ADR-002: In-Process Modular Monolith on Python FastAPI over Microservices
- **Status:** APPROVED
- **Context:** Microservice architectures introduce network serialization overhead, eventual consistency latencies, distributed transaction complexities, and heavy DevOps overhead. For an early-stage marketplace, booking confirmation and ledger entries must commit atomically.
- **Decision:** Build Gadispot as an in-process **Modular Monolith** using **Python FastAPI**. Domains (Auth, Inventory, Booking, Payments, Ledger, Access) are encapsulated in distinct packages communicating via typed in-memory interfaces.
- **Consequences:** Sub-millisecond ACID transactions across domain boundaries; simplified local development and testing; single Docker container deployment on AWS ECS Fargate.

### ADR-003: Architectural Separation of Payment QR and Parking Access QR Subsystems
- **Status:** APPROVED
- **Context:** Conflating payment QR codes with physical gate passes introduces critical vulnerabilities: drivers could reuse payment receipts as access passes, or security guards could view sensitive financial transaction IDs.
- **Decision:** Absolute architectural and cryptographic separation:
  1. **Payment QR:** Generated by payment gateway, encodes NPCI UPI transaction string (`upi://pay`), 480-second TTL, scanned by driver UPI app to transfer funds.
  2. **Parking Access QR:** Minted by Gadispot backend using 128-bit CSPRNG entropy (`spx_ent_...` / `spx_ext_...`), scanned by guard app via `mobile_scanner`, atomically burned upon entry.
- **Consequences:** Zero financial or personal PII exposed to gate guards; single-use replay protection; independent failure domains.

### ADR-004: Append-Only Double-Entry General Ledger with Zero Child Lock Protocol
- **Status:** APPROVED
- **Context:** Loose "amount paid" fields fail financial audits, prevent automated reconciliation, and violate statutory accounting rules. Furthermore, locking child ledger lines during parent journal posting introduces lock-order inversion deadlocks under high concurrent write loads.
- **Decision:** Implement a true **Double-Entry General Ledger** adhering to a 9-account Chart of Accounts. Every transaction satisfies $\sum \text{Debits} = \sum \text{Credits}$. Posted rows are immutable. To prevent deadlocks, the posting trigger validates child line balance via an MVCC snapshot without acquiring row locks on `journal_lines`, while child mutations acquire `FOR SHARE` locks on parent entries. The directed wait-for graph is a strict DAG.
- **Consequences:** Mathematical auditability; complete tax reconciliation; deadlocks are mathematically impossible.

### ADR-005: Two-Phased Marketplace Payout Strategy (Direct Bank Payout Fallback)
- **Status:** APPROVED
- **Context:** Automated marketplace split products (such as Razorpay Route) require merchants to have an annual domestic turnover exceeding ₹40 Lakhs per RBI guidelines, which a Day 1 startup cannot satisfy.
- **Decision:** Adopt a two-phased settlement model:
  - **Phase 1 (MVP Pilot):** Merchant of Record batch payouts via RazorpayX or Cashfree Payouts API (IMPS/NEFT) executing weekly batch disbursements from the corporate bank account.
  - **Phase 2 (Scale):** Transition to Razorpay Route linked account transfers upon meeting the ₹40L turnover threshold without any database schema changes.
- **Consequences:** Enables Day 1 commercial operations while retaining automated, auditable bank disbursements.

### ADR-006: Firebase Phone Auth Client SDK with Authoritative Server JWT Minting
- **Status:** APPROVED
- **Context:** Indian urban drivers demand passwordless mobile login. Managing private SMS gateways and telecom DLT registration in-house introduces high operational burden.
- **Decision:** Use Firebase Phone Authentication on the Flutter client for carrier OTP delivery and handset auto-retrieval. The Flutter client submits the Firebase ID token to FastAPI, which cryptographically verifies the token using the `firebase-admin` Python SDK and mints an internal scoped SmartPark JWT (60m access, 30d refresh).
- **Consequences:** Free tier covers 10,000 monthly active users; high delivery rates across Indian carriers; client Firebase tokens are never trusted for business authorization.

### ADR-007: Single Cross-Platform Flutter Mobile Binary with Dynamic Role Navigation
- **Status:** APPROVED
- **Context:** Maintaining four separate mobile apps for Drivers, Owners, Guards, and Operations would quadruple maintenance overhead, code duplication, and app store review cycles.
- **Decision:** Build a single cross-platform Flutter application. The application dynamically renders role-specific viewport shells (`DriverTabs`, `OwnerTabs`, `GuardTabs`, `OpsView`) based on verified JWT role claims. Multi-role users switch viewports seamlessly via a profile toggle without re-authenticating.
- **Consequences:** 100% shared networking, caching, and state management code; single binary to publish on Google Play Store and Apple App Store.

### ADR-008: Controlled Manual Fallback Protocol for Offline Guard Operations
- **Status:** APPROVED
- **Context:** Subterranean parking garages frequently experience cellular dead zones. Claiming cryptographic offline one-time token burning without inter-device synchronization is mathematically impossible and vulnerable to replay attacks.
- **Decision:** In offline basement environments, the guard app switches to **Controlled Manual Fallback Mode**: the guard cross-checks physical license plates against a locally cached 8-hour shift schedule, captures gate photo proof, records the entry locally in encrypted SQLite (SQLCipher), and flushes the queue upon reconnection.
- **Consequences:** Honest, operationally realistic, and resilient to cellular outages without unprovable cryptographic claims.

### ADR-009: Late Payment Resolution Protocol (LPRP) with Automated 6-Stage Refund
- **Status:** APPROVED
- **Context:** A driver's 480-second checkout hold may expire right as they authenticate their UPI PIN. Another driver might immediately reserve the bay, followed seconds later by the arrival of the first driver's captured payment webhook.
- **Decision:** When a late `payment.captured` webhook arrives for an `EXPIRED_HOLD`:
  1. Backend attempts an atomic transition to `CONFIRMED`.
  2. If the slot was re-booked, PostgreSQL throws an `ExclusionViolation (23P01)`.
  3. The system catches the error, marks the booking `RELEASED_UNFULFILLABLE`, and automatically dispatches an asynchronous 100% full refund via the 6-stage lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`).
  4. The competing driver's booking remains completely undisturbed.
- **Consequences:** Absolute protection against double-booking; transparent, automated customer refund workflow without customer support intervention.

### ADR-010: Pessimistic Conflict Resolution in Multi-Source Availability Intelligence (MSAI)
- **Status:** APPROVED
- **Context:** Operational signals frequently conflict: an owner's schedule might show a bay available, but a security guard may have reported an obstruction 10 minutes prior.
- **Decision:** MSAI enforces **Strict Pessimistic Safety**: when any reliable evidence source indicates obstruction, maintenance, or conflict, the bay's state is forced to `UNCERTAIN` or `BLOCKED`. A bay is presented as `AVAILABLE` if and only if **all** validation checks pass cleanly.
- **Consequences:** Protects the brand promise; prevents drivers from arriving at obstructed spaces.

### ADR-011: Universal Payment Orchestration Platform (Hyperswitch) & Pluggable Gateways
- **Status:** APPROVED
- **Date:** 2026-11-05
- **Context:** Hardcoding a single proprietary gateway (such as Razorpay) creates single-point-of-failure risks and vendor lock-in. Open-source universal payment orchestration platforms provide smart routing and failover across multiple Indian acquirers.
- **Decision:** Implement a pluggable `PaymentGatewayPort` architecture supporting:
  1. `RazorpayAdapter` (P0 Primary Gateway).
  2. `CashfreeAdapter` (P0 Secondary Standby Gateway with promotional 0% fee up to ₹20L GMV).
  3. `HyperswitchAdapter` (Open-Source Universal Payment Orchestration Platform by Juspay, Apache-2.0, Rust) for dynamic routing and automated failover.
  4. `UpiDirectAdapter` (Open-source dynamic UPI QR generation via Python `qrcode[pil]`).
- **Consequences:** Eliminates single-vendor lock-in; ensures 99.9% payment checkout uptime; provides zero-MDR dynamic UPI capabilities.

### ADR-012: Version-Controlled Alembic Migrations & Session-Scoped Test Infrastructure
- **Status:** APPROVED
- **Date:** 2026-11-05
- **Context:** The Phase 0 audit revealed that `tests/conftest.py` executes an inline raw SQL string that omits 9 production tables and PostGIS, while function-scoped connection pool fixtures cause socket exhaustion on Windows.
- **Decision:** Retire raw SQL test schemas immediately. All database schemas must derive strictly from version-controlled Alembic migrations (`backend/alembic/`). The test harness in `conftest.py` must use a `session`-scoped asyncpg connection pool that applies Alembic migrations once and uses per-test database transaction rollbacks for complete test isolation.
- **Consequences:** 100% schema fidelity between testing and production; test suite execution time drops from >70s to <15s; socket exhaustion on Windows is completely eliminated.

### ADR-013: DPDPA Data Minimization via Automated 7-Day S3 Gate Photo Purge
- **Status:** APPROVED
- **Date:** 2026-11-05
- **Context:** Under India's Digital Personal Data Protection Act (DPDPA 2023), platforms must practice strict data minimization. Retaining vehicle gate photos indefinitely creates privacy liabilities.
- **Decision:** Configure an automated AWS S3 Lifecycle expiration rule that permanently purges offline gate admission photos within **7 days** of successful reconciliation. The database retains only the immutable SHA-256 audit hash and admission timestamp in `offline_manual_admissions`.
- **Consequences:** Statutory compliance with Indian privacy laws; reduced long-term S3 storage expenses; cryptographic auditability preserved via SHA-256 hashes.

---

## 5. External Regulatory & Legal Dependency Register

| Dependency ID | Domain | Requirement Description | Risk / Impact | Mitigation Strategy |
|---|---|---|---|---|
| **DEP-PAY-01** | Payment Processing | Payment Aggregator Merchant Underwriting & KYC approval for parking category. | Live checkout blocked without active PA credentials. | Use mock/sandbox adapters during Sprint 1–4; initiate underwriting concurrently. |
| **DEP-TEL-01** | Telecom & SMS | TRAI DLT Principal Entity Registration, Header `GDSPOT`, and OTP template approval. | Direct SMS delivery blocked across Indian telecom operators. | Use Firebase Phone Auth for MVP pilot, which handles telecom routing internally. |
| **DEP-LEG-01** | Indirect Taxation | Written tax legal memorandum on GST Section 9(1) (facilitation) vs 9(5) (e-commerce operator). | Misclassification of GST collection and liability reporting. | Ledger isolates gross parking tariff, platform fee, and GST liability in distinct accounts. |
| **DEP-LEG-02** | Municipal Law | Written legal clarity on private residential driveway monetization under BBMP jurisdiction. | Potential municipal notices for unauthorized commercial lot usage. | Restrict pilot to private driveways; require property tax receipts and society NOCs. |
| **DEP-LEG-03** | Platform Safe Harbor | Terms of Service explicitly disclaiming vehicle custody, fire, and theft under IT Act Section 79. | Potential bailment liability claims for damaged or stolen vehicles. | Prominent non-bailment disclaimer presented during driver booking checkout. |
