# Gadispot — Project-Wide Engineering, Product & Operational Rules

> **Document Identifier:** RULES-GSP-2026-V1.0-VERIFIED  
> **Document Title:** Project-Wide Engineering, Product, Security, Financial, Architectural, Testing, Documentation & AI Agent Rules  
> **Governing Baseline:** Master PRD V2.3.2-VERIFIED ([PRD.md](PRD.md)) & Product Goal Specification ([goal.md](goal.md))  
> **Target Pilot Geography:** Bengaluru Urban Metro, Karnataka, India (Koramangala, Indiranagar, HSR Layout — 200 Pilot Bays)  
> **Target Execution Platforms:** Mobile-Only (Single Cross-Platform Flutter Codebase for Android & iOS)  
> **Backend Architecture:** In-Process Modular Monolith (Python 3.11+ / FastAPI / PostgreSQL 16 + PostGIS / Redis 7.0+)  
> **Enforcement Level:** Mandatory & Non-Negotiable across all human engineers, architects, operations staff, and AI agents  
> **Status:** Authoritative Repository Governance Standard (Verified Implementation Freeze)  

---

## Section 1 — Document Identity and Governance

### 1.1 Purpose & Authority
This document, `rules.md`, is the authoritative, binding, project-wide specification of engineering, architectural, product, financial, security, testing, documentation, and automated agent operating rules for **Gadispot** (formerly SmartPark Exchange). All code written, commits submitted, architectural designs drafted, operational workflows implemented, and automated software agents executed in this repository MUST strictly comply with these rules.

### 1.2 Strict Source-of-Truth Priority Hierarchy
When resolving ambiguity, evaluating competing specifications, or implementing requirements, all engineers and automated agents MUST follow this strict 8-level precedence order:
1. **Explicitly Approved Founder Decisions:** The 5 foundational baselines formally approved by executive leadership (`FD-01` through `FD-05`), cataloged in [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md).
2. **Latest Authoritative Master PRD:** [PRD.md](PRD.md) (Version 2.3.2-VERIFIED), containing the 50 canonical sections, stable functional requirement IDs (`FR-AUTH-001` through `FR-GPRP-001`), and 15 business acceptance workflows.
3. **Current Decision Log and Founder Decision Checklist:** [docs/product/DECISION_LOG.md](docs/product/DECISION_LOG.md) (ADR-001 through ADR-010) and [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) (distinguishing approved baselines from proposed policies).
4. **Product Goals and Governance:** [goal.md](goal.md) (Version 1.0.2-VERIFIED) and core repository governance charters ([PROJECT.md](PROJECT.md), [README.md](README.md)).
5. **Approved Product and Technical Specifications:** Deep domain blueprints:
   - [docs/product/REQUIREMENTS_TRACEABILITY.md](docs/product/REQUIREMENTS_TRACEABILITY.md)
   - [docs/product/USER_FLOWS.md](docs/product/USER_FLOWS.md)
   - [docs/product/SCREEN_REQUIREMENTS.md](docs/product/SCREEN_REQUIREMENTS.md)
   - [docs/product/BUSINESS_ASSUMPTIONS.md](docs/product/BUSINESS_ASSUMPTIONS.md)
   - [docs/product/OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md)
   - [docs/product/SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md)
   - [docs/product/OPEN_SOURCE_INTEGRATIONS.md](docs/product/OPEN_SOURCE_INTEGRATIONS.md)
   - [docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md)
   - [docs/technical/API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md)
   - [docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)
   - [docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md)
   - [docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md)
   - [docs/technical/QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md)
   - [docs/quality/TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md)
6. **Existing Implementation & Verified Tests:** The running code, database schema migrations, and executable test suites in `tests/` (when establishing what has actually been implemented and empirically proven).
7. **Audit Findings & Risk Registers:** Empirical verification logs and risk catalogs: [docs/audits/V2_3_2_FINAL_AUDIT.md](docs/audits/V2_3_2_FINAL_AUDIT.md), [docs/audits/V2_3_1_RESIDUAL_RISK_REGISTER.md](docs/audits/V2_3_1_RESIDUAL_RISK_REGISTER.md), and [docs/audits/V2_3_1_BASELINE_INVENTORY.md](docs/audits/V2_3_1_BASELINE_INVENTORY.md).
8. **Historical Recommendations & Older Documents:** Historical changelogs and pre-V2.3 audits retained strictly for historical continuity ([docs/audits/V2_3_1_CHANGELOG.md](docs/audits/V2_3_1_CHANGELOG.md), [docs/audits/V2_3_1_FINAL_AUDIT.md](docs/audits/V2_3_1_FINAL_AUDIT.md), [docs/audits/PRD_V2_3_FINAL_AUDIT.md](docs/audits/PRD_V2_3_FINAL_AUDIT.md), [docs/audits/TECHNICAL_AUDIT.md](docs/audits/TECHNICAL_AUDIT.md)).

### 1.3 Rule of Interpretation & Discrepancy Handling
- **No Silent Reconciliation:** If two documentation sources conflict, engineers and AI agents MUST document the exact conflict and escalate it to leadership rather than silently choosing a preference.
- **No Promotion of Proposed Policies:** An item marked `PROPOSED (Pending Founder Approval)` MUST NEVER be treated as an approved policy or hardcoded without explicit parameterization.
- **No Conflation of Architecture with Implementation:** An architectural design or recommendation MUST NOT be treated as an existing implemented feature until verified by automated tests running against real infrastructure.

### 1.4 Enforceability & Amendment Policy
- Every rule in this document is enforceable. Compliance is validated through automated test suites (`pytest tests/ -v`), specification linting (`python scripts/validate_spec.py`), and code review.
- Amendments to `rules.md` require formal review and approval by the Lead Software Architect and the Product Manager, recorded with an explicit rationale and version bump.

---

## Section 2 — Non-Negotiable Product Principles

### 2.1 Commercial Product Grounding
- **Commercial Reality, Not Academic Prototype:** Gadispot is an authoritative commercial marketplace utility engineered for high-concurrency urban mobility in India. All technical designs, documentation, and code MUST reflect commercial reliability, statutory legal compliance, and customer unit economics. Framing the platform as an "academic research prototype", "toy demo", or "experimental concept" is strictly FORBIDDEN.
- **Target Launch Geography:** Initial commercial pilot is bounded strictly to the Bengaluru Urban Metro, Karnataka, India, focusing on Koramangala, Indiranagar, and HSR Layout across a capped baseline of 200 parking bays.
- **Currency & Monetary Granularity:** All platform transactions, tariffs, commissions, fines, and balances MUST be accounted for in Indian Rupees (INR / ₹) and stored in database schemas as integer paise (`BIGINT` paise, where ₹1.00 = 100 paise) to eliminate floating-point rounding errors.
- **Timezone Invariants:** All database timestamps MUST be stored in UTC using PostgreSQL `TIMESTAMPTZ`. All user-facing mobile interfaces, guard schedules, and notifications MUST display timestamps in Indian Standard Time (IST, UTC+05:30).

### 2.2 Core Product Tenets
1. **Pessimistic Availability Over Speculative Volume:** In urban parking, a false positive (dispatching a driver to an unavailable, occupied, or obstructed bay) permanently destroys trust. If any operational signal indicates uncertainty, conflict, or obstruction, the inventory MUST be suppressed from search.
2. **Deterministic Reservation Guarantee:** Every confirmed reservation is an authoritative contract backed by physical and mathematical exclusion at the database engine layer. Overbooking is categorically prohibited.
3. **Hardware-Agnostic Gate Verification:** Access control MUST operate reliably on existing security guard smartphones without requiring expensive, fragile on-premise hardware infrastructure such as ultrasonic sensors, magnetic loops, automated boom barriers, or ANPR cameras.
4. **Append-Only Financial Integrity:** Every monetary movement MUST balance to zero across an immutable double-entry ledger. No mutable balance columns, unverified "escrows", or untracked refunds are permitted.
5. **Non-Bailment Legal Posture:** Gadispot is an information exchange and marketplace facilitator operating under Section 79 of the Information Technology Act 2000. The platform does not assume custody, possession, control, or bailment of parked vehicles.

### 2.3 Canonical Vehicle Categories & Dimensional Compatibility Invariant
- **Canonical Categories:** Vehicle compatibility is defined across six canonical vehicle category enum values (`vehicle_category_enum` in [docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)): `TWO_WHEELER`, `HATCHBACK`, `SEDAN`, `SUV`, `EV_FOUR_WHEELER`, and `EV_TWO_WHEELER` (representing five physical form-factor classes plus EV-specific powertrain variants).
- **Multi-Dimensional Matching Invariant:** Parking space compatibility cannot be evaluated with scalar comparisons (`compatibility >= driver_vehicle`). Space matching MUST evaluate physical bay dimensions ($\text{length} \ge L$, $\text{width} \ge W$, $\text{height} \ge H$), permitted bay type, and active EV charger status (`fn_check_vehicle_bay_compatibility()` in [docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md)). An oversized vehicle MUST NEVER be routed to an undersized bay.

---

## Section 3 — AI Agent and Developer Operating Rules

### 3.1 Prohibited Agent Behaviors
- **No Invention or Hallucination:** Agents and developers MUST NOT invent unverified rules, metrics, imaginary APIs, fictitious founder signoffs, or synthetic test passes.
- **No Unapproved Policy Conversion:** Agents MUST NOT convert a `PROPOSED (Pending Founder Approval)` policy into an approved decision.
- **No Verification Theater:** Agents MUST NOT claim a test passes without executing the actual test runner. Substring checks on Markdown files MUST NOT be reported as "verified database integrity".
- **No Scope Creep:** Agents MUST NOT modify files outside their assigned task boundaries.
- **No Verbatim Wholesale Duplication:** Agents MUST NOT duplicate massive text blocks wholesale across repository files; synthesize concise, enforceable engineering rules instead.

### 3.2 Mandatory Agent Verification Workflow
Before declaring any task or implementation complete, developers and AI agents MUST:
1. Run `python scripts/validate_spec.py` and confirm 100% green execution with zero banned pattern violations and zero broken links.
2. Run `pytest tests/ -v` (or `python -m pytest tests/ -v`) and confirm 100% pass across all executable test cases.
3. Check `git status` to verify that no unauthorized files have been created or modified.
4. Provide an explicit Verification Record separating tested claims (with exact command outputs) from untested claims.

### 3.3 Anti-Slop Engineering Standards
- **Zero AI Visual Slop:** User interfaces MUST enforce clean, human craftsmanship: monochromatic neutral base palettes, hair-thin 1px borders, tight typography (`tracking-[-0.03em]`), and functional spacing (4px/8px grid). Banned: generic purple radial background glows, heavy frosted glass (`backdrop-blur`), oversized card border radii, and emoji icons in place of SVG/Lucide vectors.
- **Zero Code Slop:** Code MUST NOT contain placeholder comments (`# TODO: implement later`), silent exception swallowing (`except Exception: pass`), or fake mock responses in production code paths.
- **Explicit Rationale Requirement:** When establishing a constraint or rule, engineers MUST state the engineering or business rationale (the "Why") explaining what failure mode the rule prevents.

---

## Section 4 — Requirements and Change Management

### 4.1 Requirements Traceability Mandate
- Every functional requirement MUST carry a stable, unique identifier formatted as `FR-<DOMAIN>-<NUMBER>` (e.g., `FR-AUTH-001` through `FR-GPRP-001`), as cataloged in [PRD.md](PRD.md) §12.
- Every mobile screen MUST map to a canonical screen identifier (`SCR-001..004`, `SCR-101..108`, `SCR-201..205`, `SCR-301..304`, `SCR-401..402`), as specified in [docs/product/SCREEN_REQUIREMENTS.md](docs/product/SCREEN_REQUIREMENTS.md) and [docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) (incorporating GPRP reporting `SCR-107` and alternative space proposal card `SCR-108`).
- Every high-risk test scenario MUST trace back to a canonical scenario identifier (`TS-01` through `TS-20`), as detailed in [docs/quality/TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md).
- Any code or schema modification that alters a functional contract MUST update the traceability matrix in [docs/product/REQUIREMENTS_TRACEABILITY.md](docs/product/REQUIREMENTS_TRACEABILITY.md).

### 4.2 Evidentiary Classification of Information
All domain data, commercial numbers, and operational policies across the repository MUST be classified under one of four unambiguous categories per [docs/product/BUSINESS_ASSUMPTIONS.md](docs/product/BUSINESS_ASSUMPTIONS.md):
1. **`[VERIFIED FACT]`:** Statutory rates, legal opinions, and published vendor contracts (e.g., 18.0% GST on services per Notification 11/2017, Razorpay 2.0% + 18% GST MDR = 2.36%, Firebase 10k free tier).
2. **`[FOUNDER_APPROVED]`:** Explicitly approved executive baselines (`FD-01` through `FD-05` in [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)).
3. **`[PROPOSED (Pending Founder Approval)]`:** Working technical defaults awaiting executive signature (`POL-COM-01` 15% commission, `POL-DUR-01` 30m minimum, `POL-CAN-01` cancellation tiers, `POL-ARR-02` 30m grace, `POL-OST-01` 1.5× overstay penalty, `POL-SUB-01` ₹100 subsidy cap, `POL-POT-01` weekly Tuesday payout threshold ₹500).
4. **`[OPEN COMMERCIAL DECISION]`:** Contractual or vendor terms under active negotiation (`ASM-006` Route pricing, `OQ-xxx` items in [docs/product/OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md)).

---

## Section 5 — Architecture and Code Organization Rules

### 5.1 In-Process Modular Monolith Baseline
- **Monolith Over Microservices:** Gadispot is architected as an **In-Process Modular Monolith** built on **Python FastAPI** ([docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md), ADR-002). Premature decomposition into microservices is strictly FORBIDDEN for MVP.
- **Rationale:** Microservices introduce distributed transaction sagas, eventual consistency windows between booking and payment boundaries, network serialization latency, and complex deployment pipelines that are lethal to a high-concurrency booking exchange.
- **Domain Encapsulation:** The backend codebase is partitioned into distinct bounded domains:
  - `auth`: Identity, Firebase token exchange, and JWT minting.
  - `inventory`: Properties, parking bays, physical dimensions, and operating schedules.
  - `msai`: Multi-Source Availability Intelligence and spatial query filtering.
  - `booking`: 480-second holds, GiST exclusion constraints, and reservation lifecycle.
  - `access`: Dynamic 128-bit CSPRNG QR credentials, guard scanner validation, and offline exceptions.
  - `payment`: Razorpay / Cashfree orchestration, raw webhook HMAC verification, and LPRP.
  - `ledger`: Append-only double-entry general ledger, journal templates, and weekly batch payouts.
  - `gprp`: Guaranteed Parking Recovery Protocol and alternative bay rerouting.
  - `admin`: Document verification queue, property authorization, and manual escalation tools.
- **Inter-Domain Communication:** Domains MUST interact exclusively through strongly typed Python service interfaces within the same OS process. Cross-domain HTTP or RPC calls within the monolith are strictly prohibited.
- **Transactional Atomicity:** Multi-domain mutations (e.g., Hold Acquisition $\to$ Journal Entry Draft $\to$ Reservation State) MUST execute within a single PostgreSQL ACID transaction.

### 5.2 Decoupled Provider Adapter Pattern
- **Strict Vendor Isolation:** All external SaaS providers (Razorpay, Cashfree, Firebase, AWS S3, FCM) MUST sit behind abstract port interfaces (`PaymentGatewayPort`, `PayoutEnginePort`, `AuthVerifierPort`, `NotificationPort`) defined in `app/integrations/` ([docs/product/OPEN_SOURCE_INTEGRATIONS.md](docs/product/OPEN_SOURCE_INTEGRATIONS.md)).
- **Domain Decoupling:** Domain logic in `app/services/` MUST NEVER import third-party vendor SDKs directly. Swapping a gateway or authentication provider MUST require only implementing a new adapter class conforming to the port interface.

---

## Section 6 — Flutter and Mobile Application Rules

### 6.1 Mobile-Only Delivery Model
- **Single Binary, Multi-Role Shell:** The customer, property owner, security guard, and operations experiences MUST be delivered via a single cross-platform **Flutter mobile binary** deploying to Android (API 29+ / Android 10+) and iOS (iOS 15+) ([PRD.md](PRD.md) §7, ADR-007).
- **No Public Consumer Web App:** There is **no public consumer website**, **no desktop booking portal**, and **no public web admin dashboard** in the MVP scope ([PRD.md](PRD.md) §8.2). All user interactions occur on the mobile application or secure administrative CLI tools.
- **Dynamic Role Navigation:** The Flutter app MUST dynamically render role-specific shells based on verified JWT claims:
  - Auth & Onboarding Shell: `SCR-001..004`
  - Driver Shell: `SCR-101..108`
  - Space Owner Shell: `SCR-201..205`
  - Guard Scanner: `SCR-301..304`
  - Operations View: `SCR-401..402`
- **Instant Role Switching:** Multi-role users (e.g., Driver + Owner) MUST be able to toggle viewports in under 300ms without logging out or re-authenticating (`FR-AUTH-002`).

### 6.2 Mobile Engineering & Camera Scanner Lifecycle
- **State Management:** All business state in Flutter MUST be managed using the **BLoC (Business Logic Component)** or **Cubit** pattern. Direct UI state mutation across screens is forbidden.
- **Battery-Safe Camera Scanner (`mobile_scanner`):** In `SCR-301`, the camera scanning engine MUST automatically pause frame processing and release hardware resources whenever the screen loses focus, the app transitions to the background, or a modal sheet is rendered.
- **High-Contrast Guard UI:** Guard verification screens (`SCR-301..304`) MUST provide full-screen high-contrast visual feedback readable under harsh direct sunlight: **BOLD GREEN** for permitted entry and **BOLD RED** for rejection.
- **Zero Client-Side Secrets:** The compiled mobile binary MUST NOT contain payment gateway API secrets, Firebase service account keys, database connection strings, or administrative JWT signing keys.
- **Encrypted Local Storage (SQLCipher AES-256):** Guard offline admission queues and cached shift schedules MUST be stored in an encrypted SQLite database using **SQLCipher (AES-256)** ([docs/technical/QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md)). The encryption key MUST be derived from the guard's authenticated session JWT and NEVER written to disk. The offline queue MUST employ tamper-evident SHA-256 event chaining.
- **Defensive UI States:** Every mobile screen MUST explicitly handle 5 core UI states: **Loading**, **Populated**, **Empty**, **Error**, and **Offline/Degraded Network** ([docs/product/SCREEN_REQUIREMENTS.md](docs/product/SCREEN_REQUIREMENTS.md)).

---

## Section 7 — Backend and API Rules

### 7.1 Framework & Concurrency Conventions
- **FastAPI & Python 3.11+:** The backend MUST be implemented using FastAPI on Python 3.11+, taking full advantage of native async/await syntax and Pydantic v2 data validation.
- **Non-Blocking Event Loop:** All route handlers MUST be declared as `async def`. Synchronous, blocking SDK operations (e.g., Razorpay Python SDK calls which use synchronous `requests`) MUST be offloaded to a thread pool using `asyncio.get_event_loop().run_in_executor()` to prevent stalling the main event loop.
- **Read-Replica Query Routing:** Spatial discovery queries (`POST /api/v1/spaces/search`) are read-heavy PostGIS operations and MUST be routed to PostgreSQL read replicas, preserving the primary database writer exclusively for ACID transaction holds, state transitions, and ledger entries ([docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) §4).

### 7.2 API Contract & Error Standards
- **Authoritative Base URL:** All API communication MUST route through the canonical versioned base URL: `https://api.gadispot.in/api/v1` ([docs/technical/API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md)).
- **RFC 7807 Problem Details:** All API error responses MUST return HTTP status codes $\ge 400$ with an RFC 7807 compliant JSON payload (`application/problem+json`) containing:
  - `type`: URI identifying the error problem type.
  - `title`: Short, human-readable summary.
  - `status`: HTTP status code integer.
  - `detail`: Specific explanation of the failure.
  - `instance`: URI path of the endpoint that generated the error.
  - `code`: Domain-specific machine-readable error token (e.g., `SLOT_INTERVAL_CONFLICT`, `HOLD_EXPIRED`, `IMMUTABLE_LEDGER_VIOLATION`).
  - `timestamp`: ISO-8601 UTC timestamp of error generation.
- **Mandatory Idempotency Headers:** All mutating POST requests that initiate financial holds or order creations (`/api/v1/bookings/hold`, `/api/v1/payments/orders`) MUST require an `Idempotency-Key` HTTP header (UUIDv4). Duplicate requests within a 24-hour window MUST return the identical cached response without re-executing business mutations.
- **Strict Role-Based Access Control (RBAC):** API endpoints MUST enforce role checks via dependency injection (`@require_roles(UserRole.DRIVER)`).
- **IDOR Elimination:** Endpoints MUST NEVER accept user identity as a path parameter. Identity MUST be extracted directly from verified JWT claims (`current_user.id = token.sub`), and database queries MUST bind `WHERE driver_id = :current_user_id`.

### 7.3 API Rate Limiting & Defense-in-Depth Standards
To protect platform availability and prevent speculative inventory hoarding:
- **Spatial Discovery Flood Protection:** Search endpoints are rate-limited via CloudFront / AWS WAF at **100 requests per minute per IP**.
- **Checkout Hold Anti-Hoarding Limits:** `/api/v1/bookings/hold` is throttled at **10 requests per minute per IP** at WAF, with an application-layer limit of **maximum 5 hold attempts per 30 minutes per driver account** and **maximum 2 concurrent active holds**.
- **Authentication OTP Throttling:** Phone OTP generation is capped at **maximum 3 attempts per 15 minutes per phone number** with a mandatory **60-second cooldown** between attempts.

---

## Section 8 — Database and Data Integrity Rules

### 8.1 Database Engine & Extensions
- **PostgreSQL 16 Baseline:** The authoritative database engine is **PostgreSQL 16**.
- **Mandatory Extensions:** The database MUST have the following extensions enabled:
  - `btree_gist`: Required to support equality comparison (`=`) on UUID and scalar columns alongside temporal range operators within GiST indices.
  - `uuid-ossp` or `pgcrypto`: Required for UUID generation (`gen_random_uuid()`).
  - `postgis`: Required for high-performance geospatial spherical distance queries on spatial coordinates (`GEOGRAPHY(Point, 4326)`).

### 8.2 GiST Temporal Exclusion Constraint
- **Storage-Engine Concurrency Authority:** Elimination of double-bookings is enforced strictly at the database storage engine level using PostgreSQL range types (`tstzrange`) and an exclusion constraint:
  ```sql
  CONSTRAINT prevent_overlapping_active_reservations
  EXCLUDE USING gist (
      parking_space_id WITH =,
      time_window WITH &&
  ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'));
  ```
- **Rationale:** Application-level distributed locks (e.g., Redis mutexes) fail during network partitions, Redis restarts, or process crashes, leading to split-brain double bookings. GiST exclusion constraints guarantee mathematical atomicity within the database ACID engine.
- **Interval Boundary Semantics:** All booking windows MUST be represented as half-open intervals: $[t_{\text{start}}, t_{\text{end}})$. Under PostgreSQL range math, adjacent intervals (e.g., `[10:00, 11:00)` and `[11:00, 12:00)`) do NOT overlap (`&&` evaluates to `FALSE`), allowing back-to-back bookings on the same physical bay without lock contention.
- **Canonical Reservation Status Lifecycle:** Space reservations track state via `reservation_status_enum` ([docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)):
  - *Active Statuses (Subject to GiST Exclusion):* `ACTIVE_HOLD`, `CONFIRMED`, `ACTIVE_SESSION`, `MAINTENANCE_BLOCK`, `OWNER_BLACKOUT`.
  - *Terminal/Inactive Statuses (Excluded from GiST Index):* `EXPIRED_HOLD`, `COMPLETED`, `CANCELLED_BY_DRIVER`, `CANCELLED_BY_OWNER`, `NO_SHOW`, `ARRIVAL_FAILED`, `REPLACED`, `RELEASED_UNFULFILLABLE`.
  - *Schema Harmonization Note:* In production Alembic migrations, `reservation_status_enum` MUST explicitly include operational blocking states (`MAINTENANCE_BLOCK`, `OWNER_BLACKOUT`) alongside reservation states to ensure full type compatibility with the partial exclusion index filter. In test fixtures (`tests/conftest.py`), historical aliases `RELEASED_EXPIRED` (for `EXPIRED_HOLD`) and `CANCELLED_BY_HOST` (for `CANCELLED_BY_OWNER`) are permitted only for test suite compatibility.
- **Database Schema Migration Invariant:** All schema changes MUST be executed via forward-only **Alembic migrations**. Down-revisions (`alembic downgrade`) are strictly forbidden in production. Destructive schema alterations (dropping columns or tables) require a multi-release deprecation cycle.

---

## Section 9 — Booking, Availability and Concurrency Rules

### 9.1 Universal 480-Second (8-Minute) Hold Standard
- **The 480-Second Standard:** The temporary checkout hold lifespan is **strictly 480 seconds (8 minutes)** from creation ([PRD.md](PRD.md) §19, [DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)).
- **Absolute Ban on Obsolete Values:** Hardcoding or referencing obsolete hold intervals (such as five minutes or shorter legacy durations) is strictly PROHIBITED across all backend workers, frontend countdown timers, payment gateways, and documentation.
- **Two-Tier Hold Expiration Engine:**
  - **Tier 1 (Scheduled Background Sweeper):** A Celery / ARQ worker runs every 5 seconds, executing an atomic batch query with non-blocking concurrency:
    ```sql
    UPDATE space_reservations 
    SET status = 'EXPIRED_HOLD', updated_at = NOW() 
    WHERE id IN (
        SELECT id FROM space_reservations 
        WHERE status = 'ACTIVE_HOLD' AND hold_expires_at <= NOW() 
        FOR UPDATE SKIP LOCKED 
        LIMIT 100
    );
    ```
  - **Tier 2 (Opportunistic Inline Sweep):** During search or hold creation for a specific bay, any expired hold on that bay is swept inline within the active database transaction, releasing inventory without waiting for the background worker.
- **Minimum Booking Duration (`POL-DUR-01`):** The minimum continuous booking duration is **30 minutes** (`[PROPOSED (Pending Founder Approval)]`, [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)), accommodating short errands while minimizing slot fragmentation. Booking duration validation MUST be parameterized via application configuration rather than hardcoded.
- **Maximum Booking Duration (`FD-04`):** Continuous reservations are capped at a maximum of **24 hours** by property default (`properties.max_booking_hours`, `FD-04`). Continuous multi-day and monthly recurring leases are deferred to Phase 2.
- **Driver Arrival Grace Window (`POL-ARR-02`):** Drivers are granted an arrival grace window of **exactly 30 minutes** past the scheduled reservation start time (`[PROPOSED (Pending Founder Approval)]`). If the driver has not checked in within 30 minutes, the booking transitions to `NO_SHOW` and access passes are revoked.

### 9.2 Late Payment Resolution Protocol (LPRP)
- When a payment gateway delivers a `payment.captured` webhook for a hold that has transitioned to `EXPIRED_HOLD` ([docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md), ADR-009):
  1. The backend MUST attempt to atomically transition the reservation from `EXPIRED_HOLD` to `CONFIRMED`.
  2. If the slot has been booked by a competing driver in the interim, PostgreSQL throws an `ExclusionViolation` (`23P01`).
  3. The backend MUST catch the exclusion violation, transition the reservation to `RELEASED_UNFULFILLABLE`, and automatically initiate a 100% full refund through the canonical 6-stage refund lifecycle with reason `HOLD_EXPIRED_SLOT_UNAVAILABLE`.
  4. The competing driver's confirmed booking MUST remain completely untouched. Under no circumstance may the system create a double-booking or displace a legitimate confirmed driver.
- **Driver Hold Limit:** A driver account is restricted to a maximum of **2 simultaneous active holds** to prevent speculative inventory hoarding and denial-of-service attacks.

---

## Section 10 — Payment, Refund, Ledger and Payout Rules

### 10.1 Webhook Ingestion & Durable Idempotency
- **Never Trust Client Callbacks:** A booking MUST NEVER be confirmed based on a Flutter client callback or checkout sheet dismissal. Confirmation strictly requires authoritative server-to-server webhook ingestion or authenticated server-to-gateway polling.
- **Raw HMAC-SHA256 Signature Validation:** Webhook endpoints MUST retrieve raw body bytes (`request.body()`) before JSON parsing and verify signatures using `hmac.compare_digest()` to eliminate timing attacks. Invalid signatures MUST return HTTP 400 Bad Request immediately.
- **Durable Database Deduplication:** Webhook deduplication MUST be enforced via a unique database constraint on `(gateway_name, gateway_event_id)` in `payment_webhook_events`. Redis is an optional speed cache, never the sole deduplication authority.

### 10.2 True Double-Entry General Ledger
- **Append-Only Immutability:** Financial accounting MUST use a true double-entry ledger with `journal_entries` headers and `journal_lines` ([docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md), ADR-004). Posted entries and lines are strictly immutable (`REVOKE UPDATE, DELETE`).
- **Standard Chart of Accounts:** All monetary lines MUST map to established account codes:
  - `1010`: Gateway Transit Account (Asset, Debit normal balance)
  - `1020`: Operating Current Bank Account (Asset, Debit normal balance)
  - `2010`: Owner Payable Liability (Liability, Credit normal balance)
  - `2020`: Customer Refund Payable (Liability, Credit normal balance)
  - `2030`: GST Output Tax Payable (Liability, Credit normal balance)
  - `3010`: Platform Commission Revenue (Revenue, Credit normal balance)
  - `3020`: Driver Convenience Fee Revenue (Revenue, Credit normal balance)
  - `4010`: Payment Gateway MDR Expense (Expense, Debit normal balance)
  - `4020`: GPRP Customer Recovery Subsidy Expense (Expense, Debit normal balance)
- **Zero Child Lock Protocol (Deadlock-Free Posting):**
  - In `fn_verify_journal_balance()`, the posting trigger verifies balance ($\sum \text{Debits} = \sum \text{Credits}$ and $\text{line\_count} \ge 2$) using the exclusive parent row lock acquired by `UPDATE journal_entries SET posting_status = 'POSTED'`.
  - The posting trigger MUST NOT acquire child row locks (`FOR UPDATE` on `journal_lines` is strictly forbidden).
  - Child line mutations (`INSERT`, `UPDATE`, `DELETE`) fire `fn_prevent_posted_lines_modification()`, which acquires a `FOR SHARE` lock on the parent journal row.
  - This guarantees a strictly acyclic wait-for graph ($T_{\text{mutation}} \to T_{\text{posting}}$ with zero edges $T_{\text{posting}} \to T_{\text{mutation}}$), provably eliminating lock-order inversion deadlocks under concurrent execution.
  - **Deterministic Cross-Journal Locking Order:** In `fn_prevent_posted_lines_modification()`, any mutation that reassigns a line between different journals (`OLD.journal_id != NEW.journal_id`) MUST acquire parent row locks in deterministic ascending order (`IF OLD.journal_id < NEW.journal_id THEN ... ELSE ... END IF`), structurally preventing deadlocks between concurrent bidirectional line transfers.

### 10.3 Standard Financial Calculation Sequence & Unit Economics
All transactions MUST compute and record exact integer paise values without rounding distortion ([docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) §3). Worked baseline for a 2-hour stay at ₹40/hr:
1. **Driver Inflow:**
   - Gross Parking Base ($P_{\text{base}}$): $2 \times ₹40.00 = ₹80.00$ (8,000 paise).
   - Driver Convenience Fee ($F_{\text{conv}}$): ₹10.00 (1,000 paise).
   - GST on Convenience Fee ($T_{\text{conv}}$ @ 18%): ₹1.80 (180 paise).
   - **Total Driver Paid via UPI:** **₹91.80 (9,180 paise)**.
2. **Platform Commission Invoice to Host (`POL-COM-01`):**
   - Platform Commission ($P_{\text{comm}}$ @ 15% on ₹80.00): ₹12.00 (1,200 paise) (`[PROPOSED (Pending Founder Approval)]`, parameterized via application configuration).
   - GST on Commission ($T_{\text{comm}}$ @ 18% on ₹12.00): ₹2.16 (216 paise).
   - Total Platform Facilitation Charge to Host: ₹14.16 (1,416 paise).
3. **Net Property Owner Entitlement (Credit Account 2010):**
   - Gross Parking Base (₹80.00) - Total Commission & Tax (₹14.16) = **₹65.84 (6,584 paise)**.
4. **Payment Gateway Processing (Debit Account 4010):**
   - Gateway MDR ($G_{\text{mdr}}$ @ 2.0% + 18% GST on MDR = 2.36% on ₹91.80): ₹2.17 (217 paise), absorbed by platform as an operating expense.
5. **GST Output Tax Liability (Credit Account 2030):**
   - GST on Convenience Fee (₹1.80) + GST on Commission (₹2.16) = **₹3.96 (396 paise)**.
6. **Platform Net Operating Margin (P&L):**
   - Gross Platform Revenues (Commission ₹12.00 + Convenience Fee ₹10.00): ₹22.00.
   - Less Gateway MDR (-₹2.17): **₹19.83 (1,983 paise)** (21.6% Net Take-Rate).
7. **Mathematical Cash Flow Reconciliation:**
   $$\text{Total Inflow (₹91.80)} = \text{Owner (₹65.84)} + \text{Platform Margin (₹19.83)} + \text{GST (₹3.96)} + \text{MDR (₹2.17)} = ₹91.80 \quad \text{[EXACT]}$$

### 10.4 Canonical Balanced Journal Entry Templates
Every financial event MUST be posted via a balanced journal entry where $\sum \text{Debits} = \sum \text{Credits}$ across at least 2 lines ([docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) §4). Core event templates:
- **Template 1: Driver Payment Captured (`JRN-BK`):**
  - Line 1: `1010` Gateway Transit Account (Asset) | DEBIT 9,180 paise (₹91.80)
  - Line 2: `2010` Owner Payable Liability | CREDIT 6,584 paise (₹65.84)
  - Line 3: `3010` Platform Commission Revenue | CREDIT 1,200 paise (₹12.00)
  - Line 4: `3020` Driver Convenience Fee Revenue | CREDIT 1,000 paise (₹10.00)
  - Line 5: `2030` GST Output Tax Payable | CREDIT 396 paise (₹3.96)
  - *Balance:* 9,180 Debits = 9,180 Credits [BALANCED]
- **Template 2: Gateway Settlement & MDR Deduction (`JRN-MDR`):**
  - Line 1: `1020` Operating Current Bank Account | DEBIT 8,963 paise (₹89.63)
  - Line 2: `4010` Payment Gateway MDR Expense | DEBIT 217 paise (₹2.17)
  - Line 3: `1010` Gateway Transit Account (Asset) | CREDIT 9,180 paise (₹91.80)
  - *Balance:* 9,180 Debits = 9,180 Credits [BALANCED]
- **Template 3: Weekly Owner Batch Payout Disbursement (`JRN-PO`):**
  - Line 1: `2010` Owner Payable Liability | DEBIT 6,584 paise (₹65.84)
  - Line 2: `1020` Operating Current Bank Account | CREDIT 6,584 paise (₹65.84)
  - *Balance:* 6,584 Debits = 6,584 Credits [BALANCED]
- **Template 4: GPRP Alternative Space Platform Subsidy (`JRN-SUB`):**
  - Line 1: `4020` GPRP Customer Recovery Expense | DEBIT 3,000 paise (₹30.00)
  - Line 2: `2010` Owner Payable (Alternative Host) | CREDIT 3,000 paise (₹30.00)
  - *Balance:* 3,000 Debits = 3,000 Credits [BALANCED]
- **Template 5: Overstay Penalty Billing Settlement (`JRN-OST`, `POL-OST-01`):**
  - Line 1: `1010` Gateway Transit Account (Asset) | DEBIT 6,000 paise (₹60.00)
  - Line 2: `2010` Owner Payable (50% Compensation) | CREDIT 3,000 paise (₹30.00)
  - Line 3: `3010` Platform Commission Revenue | CREDIT 2,085 paise (₹20.85)
  - Line 4: `2030` GST Output Tax Payable | CREDIT 915 paise (₹9.15)
  - *Balance:* 6,000 Debits = 6,000 Credits [BALANCED]
- **Template 6: 100% Driver Cancellation / LPRP Auto-Refund Reversal (`JRN-CAN100` / `JRN-LPRP`):**
  - Line 1: `2010` Owner Payable Liability (Rev) | DEBIT 6,584 paise (₹65.84)
  - Line 2: `3010` Platform Commission Revenue (Rev) | DEBIT 1,200 paise (₹12.00)
  - Line 3: `3020` Driver Convenience Fee Revenue (Rev) | DEBIT 1,000 paise (₹10.00)
  - Line 4: `2030` GST Output Tax Payable (Rev) | DEBIT 396 paise (₹3.96)
  - Line 5: `1010` Gateway Transit Account (Asset) | CREDIT 9,180 paise (₹91.80)
  - *Balance:* 9,180 Debits = 9,180 Credits [BALANCED]
- **Template 7: Failed Gateway Refund Escrow Earmarking (`JRN-FLR`):**
  - Line 1: `1010` Gateway Transit Account (Asset) | DEBIT 9,180 paise (₹91.80)
  - Line 2: `2020` Customer Refund Payable | CREDIT 9,180 paise (₹91.80)
  - *Balance:* 9,180 Debits = 9,180 Credits [BALANCED]

### 10.5 Canonical 6-Stage Refund Lifecycle
- **Baseline Database State:** For any unrefunded reservation, the database column `space_reservations.refund_status` is initialized to `'NONE'` ([docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)).
- **Deterministic 6-Stage Lifecycle:** When a refund is initiated (via policy cancellation, LPRP late capture race loss, or GPRP arrival failure), the refund state machine MUST transition deterministically through the canonical 6-stage lifecycle ([PRD.md](PRD.md) §21, [docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md)):
$$\text{REFUND\_ELIGIBLE} \longrightarrow \text{REFUND\_REQUESTED} \longrightarrow \text{GATEWAY\_ACCEPTED} \longrightarrow \text{REFUND\_PROCESSING} \longrightarrow \text{REFUND\_SETTLED}$$
$$\text{with terminal failure state: } \text{REFUND\_FAILED}$$
- **Prohibited Enums:** Obsolete non-canonical refund enum states (such as legacy pending or unqualified completion tokens) are strictly BANNED.
- **No False Real-Time Settlement Promises:** Documentation and customer interfaces MUST NOT promise immediate settlement for customer paybacks. Indian banking switches require 5 to 7 business days for UPI/card credit settlement once the gateway accepts the request.
- **Independent State Modeling:** Reservation state (`CONFIRMED`, `ACTIVE_SESSION`), payment state (`CAPTURED`), and refund state MUST be modeled as orthogonal, independent state machines.

### 10.6 Marketplace Payout Governance
- **Merchant of Record (MoR):** Gadispot acts as the Merchant of Record for driver collections and bears legal liability for chargebacks, refunds, and disputes.
- **Phase 1 Pilot Strategy (`FD-05`):** Payouts are executed via scheduled batch bank transfers (IMPS) from the corporate current account under strict owner KYC (PAN verification + Penny Drop bank validation confirming account holder name matches).
- **Phase 2 Migration:** Migration to Razorpay Route linked-account splits will occur upon meeting statutory turnover thresholds (>₹40 Lakhs turnover) without schema alteration.
- **Payout Threshold:** Weekly batch payouts execute on Tuesdays for accumulated host balances $\ge ₹500$ (`POL-POT-01`).

### 10.7 Cancellation Policies & Penalties (`POL-CAN-01`)
- **Driver Cancellation Tiers:**
  - $>2$ Hours before start: 100% parking fee refunded; owner payable ₹0.00; platform absorbs gateway MDR.
  - 30m – 2 Hours before start: 50% parking fee refunded; owner receives 50% entitlement; platform retains commission on non-refunded base.
  - $<30$m before start / Post-start: 0% refund (100% forfeited); owner receives 100% entitlement; platform retains full commission.
  - *Platform convenience fee is non-refundable across all driver cancellation tiers.*
- **Host Cancellation Penalty:**
  - If a property owner cancels a confirmed reservation at any time prior to driver arrival, the driver immediately receives an automated 100% full refund (base fee + convenience fee, platform absorbing MDR).
  - The host receives ₹0.00 entitlement and is assessed a **₹100 platform cancellation penalty** debited against future earnings; repeated host cancellations trigger automated listing suspension.

---

## Section 11 — Authentication, Authorization and Account Security

### 11.1 Identity & Session Architecture
- **Passwordless Mobile Login:** Authentication uses 10-digit Indian mobile numbers (+91) via Firebase Phone Authentication on Flutter (`FR-AUTH-001`, ADR-006).
- **Authoritative Backend Token Exchange:** The client-side Firebase token is strictly untrusted for business domain operations. The Flutter client submits the Firebase ID token to `POST /api/v1/auth/session`. The FastAPI backend verifies the cryptographic signature via the Firebase Admin SDK and mints internal scoped SmartPark JWTs (Access Token: 60-minute TTL, Refresh Token: 30-day TTL).
- **Prohibition of Plaintext OTPs:** Plaintext OTPs MUST NEVER be generated, handled, transmitted, or stored in the Gadispot backend database. Telecom SMS routing is delegated entirely to Firebase.
- **Staff 2FA:** Privileged Operations and Admin accounts MUST enforce time-based one-time password (TOTP) two-factor authentication via `pyotp` (RFC 6238).
- **Backend Secrets Injection & Network Isolation:** Application secrets (database passwords, payment gateway secrets, JWT private keys) MUST NEVER be committed to Git or stored in plaintext configuration files. All secrets MUST be injected at container boot from **AWS Secrets Manager** or **GCP Secret Manager** into environment variables. Production PostgreSQL RDS and ElastiCache Redis instances MUST reside strictly within isolated VPC private subnets with zero public IP addresses ([docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) §3).

### 11.2 STRIDE Threat Model Mitigations
The system enforces defensive mitigations against all six STRIDE threat categories ([docs/product/SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md)):
- **Spoofing Defense:** Webhooks verify raw HMAC-SHA256 signatures; driver and guard authentication enforces Play Integrity and Firebase Admin SDK token signature checks; QR passes use 128-bit unguessable tokens.
- **Tampering Defense:** Pricing, durations, and taxes are computed authoritatively on the backend; booking overlap tampering is prevented by PostgreSQL GiST exclusion constraints; property title uploads are validated via S3 MIME and virus scans.
- **Repudiation Defense:** Every gate admission creates an immutable audit record in `access_scan_logs`; all financial transfers post to the immutable double-entry ledger.
- **Information Disclosure Defense:** Zero PII is embedded in QR pass payloads; API endpoints extract user identity strictly from JWT claims (`token.sub`); property deeds and KYC documents are restricted to private S3 buckets accessed only via time-bounded presigned URLs.
- **Denial of Service Defense:** Speculative inventory lockup is prevented by universal 480-second hold TTLs and a cap of 2 concurrent active holds per driver; APIs enforce AWS WAF rate limits.
- **Elevation of Privilege Defense:** Scoped RBAC middleware enforces role boundaries; guards and space owners cannot access administrative or cross-tenant endpoints.

---

## Section 12 — QR Code and Parking Access Rules

### 12.1 Cryptographic Separation of the Two QR Subsystems
A catastrophic defect is conflating payment confirmation tokens with gate access passes. Gadispot enforces complete cryptographic and architectural separation ([docs/technical/QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md), ADR-003):
1. **Payment Dynamic QR:** Generated by Razorpay, encodes NPCI UPI transaction string, 480-second TTL, scanned by driver UPI apps (PhonePe, GPay, Paytm) to transfer funds.
2. **Parking Access QR:** Generated by the Gadispot server, encodes an unguessable 128-bit CSPRNG opaque token (`spx_ent_...` / `spx_ext_...`), scanned by guard smartphones via `mobile_scanner`, atomically burned upon entry.

### 12.2 Credential Lifecycle & Single-Use Replay Protection
- **Token Format:** `spx_ent_` (or `spx_ext_`) followed by 32 hexadecimal characters (`secrets.token_hex(16)` = 128 bits of cryptographic entropy).
- **Zero PII Payload:** The QR payload MUST contain only the opaque token string. License plates, customer names, phone numbers, and payment IDs MUST NOT be embedded in the QR payload.
- **Atomic Replay Burn:** When a guard scans an entry pass, the backend MUST atomically validate the temporal window and update `access_credentials.status = 'CONSUMED'` within the same transaction that initializes `space_reservations.status = 'ACTIVE_SESSION'`. Subsequent presentations of the same QR MUST immediately flash **BOLD RED**: "ACCESS REJECTED: QR code already consumed".
- **Validity Windows:**
  - `ENTRY_TOKEN`: Valid $[t_{\text{start}} - 15\text{m}, t_{\text{start}} + 30\text{m})$ (incorporating the 30-minute driver arrival grace window per `POL-ARR-02`). If unscanned after 30 minutes past scheduled start, booking transitions to `NO_SHOW`.
  - `EXIT_TOKEN`: Pre-cached on driver handset upon check-in; valid $[t_{\text{checkin}}, t_{\text{end}} + 15\text{m})$. Overstay exit calculations execute dynamically if scanned after grace period.

### 12.3 Controlled Manual Exception Protocol in Deep Basements (`FD-03`)
In subterranean parking garages (B1/B2/B3) where cellular connectivity is absent, guards MUST NOT treat offline admission as an authoritative QR scan ([docs/technical/QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md), ADR-008). Instead:
1. When scanner network timeout exceeds 3 seconds, guard app enters **Controlled Manual Exception Mode**.
2. Guard manually inputs vehicle registration plate and matches against locally cached 8-hour shift schedule.
3. Guard takes mandatory gate photo proof of vehicle plate and captures driver phone number last 4 digits.
4. Guard taps "ADMIT ON CONDITIONAL MANUAL EXCEPTION". Mobile screen flashes **AMBER WARNING**: "CONDITIONAL ADMISSION - PENDING RECONCILIATION".
5. Admission is signed with tamper-evident SHA-256 event chaining and queued in encrypted SQLCipher SQLite storage. Guard handsets MUST re-authenticate online every 12 hours.
6. Upon surface network reconnection, queued records flush to `POST /api/v1/access/reconcile-offline-admissions`:
   - *Clean Reconciliation:* Booking was valid; reservation session recorded.
   - *Conflict Detected:* Booking was cancelled, refunded under LPRP, or plate duplicated; system logs a Security Incident, alerts property manager, and bills the driver account with an outstanding penalty balance.

---

## Section 13 — Privacy, Security and Legal Readiness

### 13.1 DPDP Act 2023 Statutory Compliance Matrix
Gadispot complies with all core statutory obligations under the Digital Personal Data Protection Act (DPDPA) 2023 ([docs/product/SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md)):
1. **Notice & Consent (Sections 5 & 6):** Explicit, affirmative consent recorded with timestamp, IP, and policy version upon mobile registration.
2. **Purpose Limitation (Section 7):** PII collected strictly for parking reservation, gate access, and tax invoicing; never shared or sold to advertising brokers.
3. **Data Minimization (Section 8):** Zero collection of Aadhaar, driving license numbers, or bank login credentials. Only mobile number, name, and vehicle plate are retained.
4. **Storage Limitation (Section 8):** Spatial search GPS queries purged after 180 days via automated background task; offline gate photos purged after 7 days.
5. **Data Security (Section 8):** Customer data encrypted at rest using AWS KMS AES-256; TLS 1.3 enforced for all network transit.
6. **Right to Erasure (Section 12):** Account deletion soft-deletes profile with a 30-day purge cycle. *Statutory Exemption:* Double-entry financial journal records and tax invoices are retained for 8 years to comply with statutory audit mandates under the Indian Companies Act 2013 and Section 44AB of the Income Tax Act.
7. **Grievance Redressal (Section 13):** Resident Grievance Officer details published in mobile settings with a strict **48-hour acknowledgment SLA** and **30-day resolution SLA**.

### 13.2 Data Localization & Guard Minimization
- **Data Localization:** All production databases, Redis instances, S3 document storage buckets, and application containers MUST reside strictly within Indian data centers (AWS Mumbai `ap-south-1` / GCP Mumbai). Exporting customer PII outside India is strictly prohibited.
- **Data Minimization on Guard Viewports:** Guard mobile screens MUST display masked PII only (e.g., driver name "Rohan S.", phone masked as `+91 98*** **345`). Guards MUST NOT have access to driver payment receipts or home addresses.

### 13.3 Automated 7-Day S3 Photo Purge Lifecycle
- Photos captured by guards during subterranean offline check-in exceptions (`FD-03`) MUST be uploaded to private, server-side encrypted S3 buckets (`kms:aws:s3`).
- S3 bucket lifecycle configurations MUST enforce an automated, non-bypassable deletion rule purging all offline exception photos exactly **7 days after upload** (`Expiration Days: 7`).

---

## Section 14 — MSAI and Availability Evidence Rules

### 14.1 7-Signal Availability Synthesis
Multi-Source Availability Intelligence (MSAI) computes bay availability across 7 operational field inputs ([PRD.md](PRD.md) §15, [docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md)):
$$\text{MSAI Availability} = f(\text{Schedule}, \text{Blackouts}, \text{Bookings}, \text{Active Holds}, \text{Sessions}, \text{Incidents}, \text{Buffers})$$
1. **`operating_schedules`:** Host-defined recurring weekly windows. Outside operating hours, bay is `CLOSED`.
2. **`OWNER_BLACKOUT`:** Temporary owner reservations for personal family use. Overrides open schedule (`BLOCKED`).
3. **`space_reservations`:** Active interval holds (`TEMPORARILY_HELD`) and confirmed bookings (`BOOKED`).
4. **`ACTIVE_SESSION`:** Real-world vehicles currently occupying the bay (`OCCUPIED`).
5. **`MAINTENANCE_BLOCK`:** Administrative or physical repair closures (`MAINTENANCE`).
6. **`space_incidents`:** Active guard obstruction or encroachment reports (`UNCERTAIN`).
7. **`Turnaround Buffers`:** 15-minute buffers before and after bookings.
- **Property Authorization Prerequisite:** A parking space is bookable only if its parent property has `property_authorizations.status = 'APPROVED'`. Unapproved properties are marked `UNVERIFIED` and suppressed unconditionally from search results.

### 14.2 Strict Pessimistic Safety Algorithm
- If any operational signal indicates conflict, obstruction, or uncertainty, the slot MUST be marked `UNAVAILABLE` or `UNCERTAIN` and suppressed from search results (ADR-010).
- Missing or stale evidence MUST NEVER be interpreted as positive availability.

### 14.3 Multi-Dimensional Vehicle Compatibility Evaluation
Parking space compatibility cannot be evaluated with scalar comparisons (`compatibility >= driver_vehicle`). Space matching MUST be evaluated via the multi-dimensional function `fn_check_vehicle_bay_compatibility()` ([docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) §5.2):
- **`TWO_WHEELER` / `EV_TWO_WHEELER`:** Bay type in (`TWO_WHEELER`, `BIKE_BAY`), length $\ge 2.0\text{m}$, width $\ge 0.8\text{m}$.
- **`HATCHBACK`:** Bay type in (`COMPACT_CAR`, `STANDARD_CAR`, `LARGE_CAR`, `SUV_BAY`), length $\ge 3.8\text{m}$, width $\ge 1.7\text{m}$.
- **`SEDAN`:** Bay type in (`STANDARD_CAR`, `LARGE_CAR`, `SUV_BAY`), length $\ge 4.5\text{m}$, width $\ge 1.8\text{m}$.
- **`SUV` / `EV_FOUR_WHEELER`:** Bay type in (`LARGE_CAR`, `SUV_BAY`), length $\ge 4.8\text{m}$, width $\ge 1.9\text{m}$, height $\ge 2.0\text{m}$.
- **EV Charging:** If driver requests EV charging, `has_ev_charger = TRUE` is mandatory; otherwise the bay is incompatible.

---

## Section 15 — GPRP and Parking Recovery Rules

### 15.1 The 8-Step Guaranteed Parking Recovery Protocol
If a driver arrives and finds their reserved bay physically obstructed (e.g., unauthorized vehicle parked), the system executes an automated recovery workflow (`FR-GPRP-001`, [PRD.md](PRD.md) §26, ADR-009):
1. **Driver Reports Obstruction:** Driver taps "Report Bay Blocked" in `SCR-107` (accessed via pass `SCR-104` or session `SCR-105`), or the security guard triggers an obstruction report in `SCR-304`.
2. **Proximity Geofence Verification:** Backend verifies driver handset is within 100 meters of the property.
3. **Spatial Alternative Search:** Backend searches for an available, compatible bay within a 500-meter radius.
4. **Platform Tariff Subsidy:** If the alternative bay has a higher tariff, the platform absorbs the price difference up to ₹100 (`POL-SUB-01`, Ledger Account 4020). The driver pays zero incremental fee.
5. **Driver Option Window:** The alternative bay is held atomically for **180 seconds** while presented to the driver via in-app proposal card `SCR-108` ([docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) §7, [docs/product/USER_FLOWS.md](docs/product/USER_FLOWS.md)).
6. **Option A (Driver Accepts):** System issues a new `ENTRY_TOKEN`, updates navigation, transitions the original reservation to `REPLACED` ([docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md)), and logs an incident of type `BAY_OBSTRUCTED` in `space_incidents`.
7. **Option B (Alternative Unavailable or Declined):** If no alternative exists within 500m or the driver declines/times out, the system automatically marks the reservation `ARRIVAL_FAILED`.
8. **Automated 100% Full Refund (`FD-02`):** System immediately transitions the booking to `REFUND_ELIGIBLE` and initiates an automated full refund of 100% of the parking base fee and convenience fee back to the driver's original payment instrument.

### 15.2 Host Accountability and Platform Subsidy Accounting
- **Host Incident Penalty:** When an arrival failure is confirmed due to host negligence or unannounced driveway blocking, the host receives ₹0.00 entitlement, is assessed a **₹100 platform incident penalty**, and their space is suspended until re-verified (`FR-ADMIN-001`).
- **Accounting for Alternative Reroutes (`JRN-SUB`):** When the driver accepts a higher-tariff alternative bay, the platform debits Account 4020 (GPRP Customer Recovery Subsidy Expense) and credits Account 2010 (Alternative Owner Payable Liability) for the difference up to ₹100 ([docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md)).

---

## Section 16 — Testing and Quality Assurance Rules

### 16.1 Automated Testing Pyramid & Targets
The Gadispot test harness adheres to a strict test distribution ([docs/quality/TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md)):
- **40% Unit & Domain Logic Tests:** Pure functions, pricing algorithms, tax invariants, DPDPA data masking.
- **25% API Contract & Integration Tests:** FastAPI endpoints, OpenAPI validation, authentication scopes.
- **25% Concurrency & Chaos Tests:** Multi-connection Pytest suites, concurrent booking races, webhook arrival order permutations.
- **10% End-to-End Mobile User Journeys:** Flutter integration tests across complete driver, owner, and guard workflows.

### 16.2 Test Scenario Harmonization Standard
- **The 20 High-Risk Technical Scenarios:** [docs/quality/TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md) defines **exactly 20 high-risk technical test scenarios (`TS-01` through `TS-20`)**, which represent the definitive test specification.
- **The 15 PRD Acceptance Flows:** [PRD.md](PRD.md) §42 defines **15 core end-to-end user acceptance workflows**.
- **Governance Alignment:** Documentation and audit reports MUST maintain this explicit distinction: 15 PRD §42 business acceptance flows mapped directly to the 20 technical scenarios in `TEST_STRATEGY.md`.

### 16.3 Executable Test Invariants
- All database tests MUST run against real PostgreSQL 16 instances with `btree_gist` enabled. Testing against SQLite or in-memory mocks for concurrency features is strictly FORBIDDEN.
- Native asyncpg queries MUST use positional parameters (`$1, $2`), never named SQLAlchemy placeholders (`:jid`).
- Exception handling in asyncpg tests MUST catch `asyncpg.exceptions.RaiseError` (the real asyncpg exception for PostgreSQL `RAISE EXCEPTION`), not non-existent classes.
- Tests MUST NEVER be weakened, deleted, or mocked out to make CI pass.

---

## Section 17 — Error Handling, Logging and Observability

### 17.1 Structured JSON Logging
- All backend logs MUST be emitted in structured JSON format to `stdout`.
- Every log entry MUST include:
  - `timestamp`: ISO-8601 UTC timestamp.
  - `level`: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
  - `service`: `gadispot-backend`.
  - `trace_id` / `request_id`: Correlation UUID propagated from client headers.
  - `domain`: Bounded context (`booking`, `payment`, `access`, etc.).
  - `message`: Human-readable summary.

### 17.2 Sanitization & Privacy Shield
- Application logs MUST NEVER contain:
  - Plaintext authentication tokens, passwords, or Firebase ID tokens.
  - Plaintext SMS OTP values.
  - Full credit card numbers, CVVs, or UPI PINs.
  - Unmasked customer phone numbers, driver license numbers, or national identity IDs (PAN).
- Any accidental logging of sensitive PII is classified as a P0 security incident.

---

## Section 18 — External Integrations and Dependency Rules

### 18.1 Mandatory Status Tagging
Every external dependency and third-party integration across the platform MUST be classified under one of six explicit integration statuses:
1. **Mock:** Local in-memory test double used exclusively within isolated unit tests.
2. **Stub:** Fixed HTTP response server used in local development environments.
3. **Sandbox:** Vendor-provided test environment using simulated test credentials (e.g., Razorpay Test Mode).
4. **Simulated:** Chaos-testing harness injecting synthetic network latency, dropped packets, or malformed payloads.
5. **Partially Integrated:** Adapter interface implemented and functional in staging, awaiting production merchant underwriting or regulatory paperwork.
6. **Production-Integrated:** Fully underwritten, credentialed, and live in production with real banking and telecom rails.

### 18.2 Resilient Circuit Breakers & Timeouts
- All outbound HTTP requests to external SaaS providers MUST enforce strict connection timeouts (3 seconds) and read timeouts (5 seconds).
- Retries on external APIs MUST be restricted to idempotent endpoints and MUST employ exponential backoff with randomized jitter.

### 18.3 External Regulatory & Statutory Dependencies
Commercial pilot launch (Gate 5) is gated on five mandatory external statutory and partner approvals ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)):
1. **`DEP-PAY-01` (Payment Aggregator Merchant Underwriting):** Formal production merchant underwriting approval from Razorpay / Cashfree under RBI Payment Aggregator guidelines (DPSS.CO.PD.No.1810/02.14.008/2019-20).
2. **`DEP-TEL-01` (TRAI DLT Transactional SMS Templates):** Principal entity and transactional SMS header/template registration with Indian telecom operators via DLT portal.
3. **`DEP-LEG-01` (GST Legal Memorandum):** Formal tax opinion from chartered accountants certifying the 18% GST treatment on platform commissions and convenience fees.
4. **`DEP-LEG-02` (Municipal Pilot Clearance):** Operational advisory clearance from BBMP / DULT for shared private parking in Koramangala, Indiranagar, and HSR Layout.
5. **`DEP-LEG-03` (IT Act Section 79 Non-Bailment Terms of Service):** Legal review and signoff on customer and host terms establishing marketplace intermediary status and non-bailment of parked vehicles.

### 18.4 Dual Payment Gateway Strategy & Runtime Failover (`FD-01`)
- **Dual Gateway Architecture:** To eliminate single-point-of-failure risks on payment processing and mitigate merchant underwriting delays, Gadispot implements dual payment gateway integration with Razorpay as primary and Cashfree as secondary (`FD-01` / `OQ-PAY-001`, [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)). Both gateways are underwritten simultaneously.
- **Port Interface Abstraction:** Both gateways MUST implement the `PaymentGatewayPort` abstract interface in `app/integrations/payment/` ([docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) §2). Domain booking services MUST NEVER import gateway-specific SDKs.
- **Automated Circuit Breaker & Failover:** If the primary gateway experiences network partitions, circuit breaker tripping, or elevated error rates (>5% over 60 seconds), checkout traffic MUST dynamically fail over to the secondary gateway without codebase redeployment.

---

## Section 19 — Performance, Reliability and Scalability

### 19.1 Operational SLA Metrics
- **Spatial Discovery Latency:** Sub-second discovery: $\le 300\text{ms}$ (P95) for spatial radius searches (3km default, 5km max) across 10,000 active bay geometries via PostGIS index.
- **Hold Acquisition Latency:** $\le 200\text{ms}$ (P95) for atomic GiST reservation hold acquisition.
- **Gate Clearance Verdict:** $\le 2.0\text{s}$ (P95) from camera QR scan to green/red verdict display on guard handset under normal 4G connectivity.
- **Ledger Invariant Headroom:** 100% mathematical zero-sum balance ($\sum \text{Debits} = \sum \text{Credits}$) across all posted transactions. Target failure rate: 0.00%.

### 19.2 Real-World Operational Resilience
1. **Subterranean Basement Cellular Dropouts (`FD-03`):**
   - When a guard handset experiences a network timeout (>3s) in underground parking basements (B1/B2/B3), the app transitions to **Controlled Manual Fallback Mode**.
   - The guard verifies the physical vehicle plate against a locally cached 8-hour shift schedule and captures driver phone number last 4 digits.
   - Guard captures a timestamped vehicle plate photo proof, issues manual admission, and queues an encrypted record in local SQLCipher AES-256 SQLite storage. Screen flashes **AMBER WARNING** ("CONDITIONAL ADMISSION - PENDING RECONCILIATION").
   - Queued records employ tamper-evident SHA-256 event chaining. Handset re-authenticates every 12 hours.
   - When the handset reconnects to cellular/Wi-Fi, queued admissions synchronize asynchronously via `POST /api/v1/access/reconcile-offline-admissions`. Clean admissions record sessions; conflicts trigger Security Incidents. Uploaded gate photos are permanently purged from S3 after 7 days.
2. **Delayed Payment Webhooks:** Handled deterministically via the Late Payment Resolution Protocol (LPRP) without creating double-bookings or displacing confirmed drivers.
3. **Duplicate QR Presentation:** Handled via atomic single-use state burn on `access_credentials.status = 'CONSUMED'`; duplicate scans flash **BOLD RED** instantly.
4. **Guard Mistake & Encroachment Handling:** If a guard admits an incorrect vehicle or an unauthorized driver occupies a bay, the driver or guard triggers GPRP incident workflows (`FR-GPRP-001`, `SCR-304`), dispatching alternative rerouting within 500m or an automated 100% full refund within 180 seconds.

---

## Section 20 — UI/UX and Product Quality Standards

### 20.1 Design Craftsmanship & Anti-Slop Principles
- **Monochromatic Base Structures:** Interfaces MUST use deep neutral foundations (slate, zinc, warm paper) with hair-thin 1px borders (`border-neutral-200 dark:border-neutral-800`).
- **Functional Typography:** Clean sans-serif typefaces with tight letter-spacing (`tracking-[-0.03em]`) and high legibility.
- **No Decorative Emojis:** System icons MUST use production vector icons (Lucide, Material Icons), never decorative emojis.
- **Touch Target Ergonomics:** All interactive buttons, inputs, and list items on mobile shells MUST satisfy a minimum touch target size of $48 \times 48\text{dp}$.

### 20.2 Indian Localization Invariants
- Vehicle registration plates MUST strictly match standard Indian RTO notation validated against regex `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$` (e.g., `KA-01-AB-1234`, `DL-01-A-1234`) per `FR-DRIVER-001`.
- All currency values MUST display the Rupee symbol (₹) and use Indian number grouping where applicable.
- Phone numbers MUST be formatted with the Indian country code (`+91 98765 43210`).

---

## Section 21 — Git, Version Control and Release Rules

### 21.1 Branching and Commit Standards
- **Trunk-Based Delivery:** All development branches MUST be short-lived feature branches merged into `main` via pull requests. Direct commits to `main` without review are prohibited.
- **Conventional Commits:** All commit messages MUST follow the Conventional Commits specification:
  - `feat(booking): implement two-tier hold expiration engine`
  - `fix(ledger): eliminate lock-order inversion in journal posting trigger`
  - `test(concurrency): add multi-worker GiST exclusion collision test`
  - `docs(rules): baseline project-wide engineering and product rules`

### 21.2 Pipeline Verification Mandate
- Every commit pushed to remote repositories MUST pass automated GitHub Actions CI pipelines (`validate_spec.py` and `pytest tests/ -v`).
- Developers and agents MUST NEVER declare work complete with a failing or broken CI pipeline.

---

## Section 22 — Documentation Rules

### 22.1 Link Integrity & Structure
- Every relative Markdown link across all documentation files MUST resolve to an existing, valid file in the repository. Broken links cause immediate CI failure.
- In-document anchor links MUST accurately correspond to existing section headings.

### 22.2 Banned Text Patterns and Anti-Patterns
To prevent regressions to obsolete, ungrounded, or legally hazardous specifications, `scripts/validate_spec.py` enforces a complete ban on obsolete patterns across all `.md` files (excluding historical audit files in `docs/audits/`):
- Legacy 5-minute / 300-second hold phrases: Obsolete hold TTL tokens (the universal standard is 480 seconds / 8 minutes).
- Guard screen references MUST be written as `SCR-301..304` or `SCR-301 to SCR-304` to avoid word-boundary token collisions.
- Obsolete legacy duration phrases: Banned five-minute checkout duration expressions.
- Compatibility scalar comparisons: Parking space compatibility cannot be evaluated with scalar comparisons (`compatibility >= driver_vehicle`).
- Regulatory escrow claims: Inaccurate claims alleging proprietary escrow compliance are banned (Gadispot operates under Merchant of Record batch payouts, not an RBI escrow license).
- Immediate customer payback claims: Promising real-time banking credit is prohibited (banking settlement requires 5–7 business days).
- Non-canonical refund enums: Legacy non-standard refund statuses are banned (the canonical lifecycle is strictly REFUND_ELIGIBLE through REFUND_SETTLED).

---

## Section 23 — Prohibited Engineering Practices

The following technical shortcuts, premature optimizations, and architectural anti-patterns are strictly FORBIDDEN in the Gadispot repository:
1. **NO Premature Microservices:** Do not decompose the backend into separate microservice repositories or separate HTTP services. Maintain the modular monolith.
2. **NO Premature IoT Hardware:** Do not integrate or depend on hardware ultrasonic parking sensors, geomagnetic sensors, or automated boom barrier relays for MVP.
3. **NO Premature ANPR / Computer Vision:** Do not build automated camera plate recognition pipelines for MVP. Utilize the guard mobile camera scanner.
4. **NO In-App Wallet or Stored Value:** Do not implement a proprietary closed-loop wallet or customer cash balance (which requires an RBI Prepaid Payment Instrument license). All funds must flow directly through payment gateways.
5. **NO Dynamic Surge Pricing Algorithms:** Do not implement machine-learning dynamic surge pricing algorithms for MVP. Maintain transparent, predictable hourly tariffs.
6. **NO Multi-Day Continuous Leases:** Do not implement multi-day or monthly recurring leases in MVP. Maximum continuous booking duration is capped at 24 hours (`FD-04`).
7. **NO Optimistic Availability Locking:** Do not rely on application-layer optimistic locking or Redis-only mutexes for availability. Rely exclusively on PostgreSQL GiST exclusion constraints.
8. **NO Client-Side Payment Confirmation:** Do not confirm bookings based on Flutter client presentation callbacks. Rely exclusively on verified server webhooks.
9. **NO Mutable Financial Records:** Do not update or delete posted journal rows. Post balancing compensating entries instead.
10. **NO Scalar Vehicle Compatibility Comparisons:** Parking space compatibility cannot be evaluated with scalar comparisons (`compatibility >= driver_vehicle`). Use multi-dimensional category matching.

---

## Section 24 — Definition of Done

A task, feature, or pull request is strictly defined as **DONE** if and only if all eight criteria are satisfied:
1. **Specification Alignment:** Feature maps directly to a stable requirement ID (`FR-xxx`) and satisfies all acceptance criteria in [PRD.md](PRD.md).
2. **Clean Domain Implementation:** Code adheres to the modular monolith domain structure, decoupled adapter interfaces, and typed contracts.
3. **Database Integrity:** Database migrations execute forward cleanly; GiST exclusion constraints and foreign keys are verified.
4. **Financial Balance:** Any ledger-impacting code uses balanced two-tier journal templates ($\sum \text{Debits} = \sum \text{Credits}$) and passes Zero Child Lock deadlock tests.
5. **Security & Privacy:** Scoped RBAC enforced, PII masked, zero hardcoded secrets, and DPDPA data localization respected.
6. **Automated Test Coverage:** Unit, integration, and concurrency tests written and passing in `tests/`.
7. **CI & Harmonization Verification:** `python scripts/validate_spec.py` passes 100% green with zero violations; `pytest tests/ -v` passes 100% green (15/15 tests passing).
8. **Documentation Synchronization:** Associated schemas in [docs/technical/API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md) or architecture docs updated if contracts were modified.

---

## Section 25 — Product Readiness Gates

The commercial deployment of Gadispot is governed by **five progressive readiness gates** ([goal.md](goal.md) §17, [PRD.md](PRD.md) §47):
- **Gate 1: Specification Harmonization & Empirical Database Proof (STATUS: ACHIEVED)**  
  Empirically proven Zero Child Lock ledger trigger, 15 passing automated tests on PostgreSQL 16, zero banned patterns in `scripts/validate_spec.py`, and harmonized commercial policies.
- **Gate 2: Core Engineering Implementation (STATUS: IN PROGRESS)**  
  Completion of FastAPI modular monolith services, single Flutter binary with dynamic role shells, and Alembic database migrations.
- **Gate 3: Integration & Chaos Testing (STATUS: PLANNED)**  
  Verification against Razorpay / Cashfree Sandbox, Firebase Phone Auth, and simulated basement offline network dropouts.
- **Gate 4: Regulatory, Legal & Security Clearance (STATUS: PLANNED)**  
  Finalization of GST tax memorandum (`DEP-LEG-01`), TRAI DLT transactional SMS templates (`DEP-TEL-01`), and IT Act Section 79 non-bailment Terms of Service (`DEP-LEG-03`).
- **Gate 5: Commercial Pilot Launch (STATUS: GATED ON EXTERNAL RAILS)**  
  Formal Payment Aggregator merchant underwriting approval (`DEP-PAY-01`), municipal pilot clearance (`DEP-LEG-02`), and onboarding of 200 parking bays in Koramangala, Indiranagar, and HSR Layout.

---

## Section 26 — Conflict Resolution and Rule Exceptions

### 26.1 Conflict Resolution Protocol
1. **Apply Priority Hierarchy:** Check Section 1.2. The higher-priority document supersedes lower-priority documents.
2. **Document the Ambiguity:** If the contradiction represents an unrecorded business decision, draft an issue detailing the competing arguments.
3. **Formal Escalation:** Escalate to the Lead Architect and Product Manager for written resolution. Record the decision in [docs/product/DECISION_LOG.md](docs/product/DECISION_LOG.md).

### 26.2 Rule Exception Workflow
- Exceptions to these rules are granted only under extreme operational necessity and MUST be approved in writing by both the Chief Technology Officer and the Principal Product Manager.
- Any granted exception MUST be documented in `docs/product/DECISION_LOG.md` as a time-bounded Architecture Decision Record (ADR) specifying the expiration date and remediation plan.

---

## Section 27 — Quick Reference Checklist

| Operational Domain | Non-Negotiable Standard | Canonical Reference |
|---|---|---|
| **Concurrency Authority** | PostgreSQL `btree_gist` exclusion constraint (`tstzrange` `&&`). Redis is read-only cache. | ADR-001 / [DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) |
| **Checkout Hold TTL** | **Strictly 480 seconds (8 minutes)**. Shorter legacy hold intervals prohibited. | [PRD.md](PRD.md) §19 / [DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) |
| **Driver Active Holds** | Maximum 2 simultaneous active holds per driver account. | [PRD.md](PRD.md) §19 / [SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md) |
| **Minimum Duration** | **30 minutes** (`POL-DUR-01`, `[PROPOSED]`), parameterized in software configuration. | `POL-DUR-01` / [FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) §3 |
| **Backend Architecture** | In-Process Modular Monolith on Python FastAPI. No microservices. | ADR-002 / [ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) |
| **Mobile Application** | Single Flutter binary for Android & iOS with dynamic role shells. Mobile-only. | ADR-007 / [PRD.md](PRD.md) §7 |
| **Gateway Strategy** | Dual integration (Razorpay primary, Cashfree secondary) behind `PaymentGatewayPort` with automated failover. | `FD-01` / [FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) §2 |
| **Guard Screens** | Refer to guard screens as `SCR-301..304` (avoiding word boundary regex collisions). | [SCREEN_REQUIREMENTS.md](docs/product/SCREEN_REQUIREMENTS.md) |
| **General Ledger** | Append-only double-entry. $\sum \text{Debits} = \sum \text{Credits}$. Min 2 lines. Zero Child Lock. | ADR-004 / [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) |
| **Posting Concurrency** | Parent exclusive row lock only; child `FOR UPDATE` strictly forbidden. | [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) §2.2 |
| **Refund Lifecycle** | Canonical 6-stage lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`). 5-7 day banking credit. | [PRD.md](PRD.md) §21 / [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) |
| **Payment Confirmation** | Server-to-server webhook with raw HMAC-SHA256 signature check. Never trust client. | [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) §1 |
| **QR Credential Separation**| Dynamic Razorpay UPI QR (Payment) vs 128-bit CSPRNG server token (Access). | ADR-003 / [QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md) |
| **Gate Token Replay** | Single-use atomic burn (`CONSUMED`). Flash green on success, red on replay. | [QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md) §3 |
| **Basement Offline Mode** | Plate match against cached schedule, photo proof, sync on reconnect, 7-day S3 purge. | `FD-03` / ADR-008 / [QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md) |
| **GPRP Incident SLA** | Reroute within 500m (up to ₹100 platform subsidy) or 100% full refund in 180s. | `FD-02` / ADR-009 / [PRD.md](PRD.md) §26 |
| **Vehicle Compatibility** | Multi-dimensional (`fn_check_vehicle_bay_compatibility`). Length, width, height, EV. No scalar comparisons. | [BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) §5 |
| **Unit Economics** | ₹19.83 platform net margin (21.6%), ₹65.84 host payable, ₹2.17 MDR, ₹3.96 GST on ₹91.80 gross. | [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) §3 |
| **Cancellation Policy** | >2h: 100%, 30m-2h: 50%, <30m: 0%. Host cancel: 100% full refund + ₹100 host penalty. | `POL-CAN-01` / [PRD.md](PRD.md) §27 |
| **Data Privacy** | DPDPA 2023 compliance. Data localization in India (`ap-south-1`). Zero client secrets. | [SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md) |
| **Commercial Policies** | Commission (15%), Minimum (30m), Cancel Tiers, Overstay (1.5×) are `PROPOSED`. | [FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) §3 |
| **External Launch Gates** | PA Underwriting (DEP-PAY-01), DLT SMS (DEP-TEL-01), GST Memo (DEP-LEG-01), BBMP (DEP-LEG-02), Non-Bailment (DEP-LEG-03). | [FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) §4 |
| **Test Verification** | Run `python scripts/validate_spec.py` and `pytest tests/ -v` (15/15 tests passing). | [TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md) / [V2_3_2_FINAL_AUDIT.md](docs/audits/V2_3_2_FINAL_AUDIT.md) |
