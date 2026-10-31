# Master Product Requirements Document (PRD)
# Gadispot (formerly SmartPark Exchange)

> **Document Title:** Gadispot — Master Product & Engineering Requirements Specification  
> **Document Identifier:** PRD-GSP-2026-V2.3-FINAL  
> **Target Market:** India (Urban Metros — Bengaluru Pilot)  
> **Target Platforms:** Mobile-Only (Android & iOS via single Flutter Codebase)  
> **Backend Architecture:** In-Process Modular Monolith (Python / FastAPI / PostgreSQL 16 / Redis 7.0+)  
> **Authoring Team:** Multidisciplinary Senior Product, Engineering, Security & FinTech Architecture Group  
> **Status:** Baselined Final Specification (Sprint 0/1 Implementation Authorized; Pilot Launch Gated on External Rails)  

---

## 1. Document Control and Revision History

### 1.1 Revision History

| Version | Release Date | Primary Authors / Roles | Summary of Major Changes | Approval Status |
|---|---|---|---|---|
| **v0.1.0** | 2026-10-15 | Principal PM, Lead Architect | Initial product framing, discovery, and high-level market problem definition. | Conceptual Draft |
| **v1.0.0** | 2026-10-31 | Multi-disciplinary Team | Comprehensive initial PRD across 45 sections. Foundational scoping. | Initial Draft (Defects Found) |
| **v2.0.0** | 2026-10-31 | Unified Senior Architecture Team | Comprehensive Technical Re-engineering: Unified data model, GiST locks, LPRP, double-entry ledger, QR separation. | Re-engineered Draft |
| **v2.1.0** | 2026-10-31 | Unified Senior Architecture Team | Targeted Architectural Corrections: Concurrency locks, multi-stage refund states, 128-bit CSPRNG entropy. | Review Draft |
| **v2.2.0** | 2026-10-31 | Unified Senior Architecture Team | Precision Refinement: Standardized 480s hold, reconciled unit economics (₹19.83 margin / ₹65.84 owner payable), durable webhook idempotency, 7-day photo purge rule, 65-question decision register. | Conditional Review Draft |
| **v2.3.0** | 2026-10-31 | Unified Senior Architecture Team | **Final Authoritative Specification & Defect Elimination:**<br>1. Unified canonical 6-stage refund lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`) across PRD and DDL.<br>2. Enforced database immutability triggers and row locking on `journal_lines` (`trg_prevent_posted_lines_mod`).<br>3. Completely eliminated all lingering 5-min/04:59 checkout references in architecture and screen specs.<br>4. Replaced all machine-specific local filesystem URIs with portable repository markdown links.<br>5. Restructured into 50 canonical sections featuring stable requirement IDs (`FR-AUTH-001` through `FR-GPRP-001`) with complete 14-field specifications.<br>6. Incorporated all 15 explicit end-to-end acceptance test scenarios (§42).<br>7. De-escalated unsupported readiness scores; established honest Readiness Gates A through F.<br>8. Harmonized project identity as **Gadispot (formerly SmartPark Exchange)**. | **Approved Final Baseline (Sprint 0/1)** |

### 1.2 Formal Founder Decisions (V2.3 Baselines)

| Decision ID | Operational Domain | Founder Approved Value | Implementation Guidance |
|---|---|---|---|
| **Q1 / OQ-PAY-001** | Payment Provider Strategy | **Dual Application (Razorpay Primary, Cashfree Secondary)** | Maintain runtime-swappable `PaymentGatewayPort` abstraction interface. |
| **Q2 / OQ-OPS-004** | Alternative Space Failure | **100% Full Refund to Original Instrument** | Automatic fallback to `REFUND_ELIGIBLE` if GPRP alternative space cannot be secured or is declined within 180s. |
| **Q3 / OQ-TECH-010** | Offline Guard Admission | **Controlled Manual Exception Protocol** | Offline entry allowed with plate match against cached schedule, mandatory photo proof, async sync, and automated 7-day S3 photo purge. |
| **Q4 / OQ-BIZ-003** | Maximum Booking Duration | **Configurable by Property (Default 24 Hours)** | Space owners can set maximum continuous hours up to 24h. Multi-day leases deferred to Phase 2. |
| **Q5 / OQ-PAY-002** | MVP Marketplace Payouts | **Scheduled Batch Bank Transfers from Corporate Account** | Direct IMPS payouts under corporate bank agreement, Merchant of Record status, and strict owner KYC (PAN + Penny Drop). |

### 1.3 Document Approvals & Signoffs

| Role | Specialist Representative | Date | Verification Status |
|---|---|---|---|
| **Principal Product Manager** | Lead PM, Urban Mobility Group | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Senior Business Analyst** | Lead Market Analyst, India Payments | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Principal Software Architect** | Systems Architecture Lead | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Database Architect** | Transaction & Concurrency Specialist | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Payment Systems Architect** | UPI & Indian Payment Gateways Lead | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Mobile Application Architect** | Mobile Engineering Lead (Flutter) | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Application Security Engineer** | Cybersecurity & Threat Modeling Lead | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |
| **Privacy & Data Protection Specialist** | Legal & DPDPA Compliance Counsel | 2026-10-31 | **CONDITIONAL (Subject to legal counsel signoff)** |
| **QA & Test Strategy Director** | QA Automation & Test Lead | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |

---

## 2. Executive Summary

**Gadispot** (formerly SmartPark Exchange) is an authoritative, mobile-first two-sided parking marketplace engineered specifically for the hyper-dense urban mobility landscape in India. It unlocks underutilized, dormant private residential driveways, gated society visitor bays, commercial office basements, and authorized private parking lots, transforming them into a reliable network of pre-bookable, time-slotted parking inventory.

Unlike passive directories that display unverified locations or crowdsourced approximations, Gadispot operates as a **deterministic reservation exchange**. Every reservation is guaranteed by:
1. **Multi-Source Availability Intelligence (MSAI):** Synthesizing 7 operational signals to eliminate speculative inventory and double-bookings.
2. **PostgreSQL GiST Concurrency Locks:** Mathematical exclusion of overlapping time-window holds directly at the database engine level via `EXCLUDE USING gist`.
3. **Late Payment Resolution Protocol (LPRP):** Automated handling of payments arriving after 480-second hold expirations, ensuring zero double-bookings and a deterministic multi-stage refund protocol when slots are claimed by competing drivers.
4. **Authorization-Aware Inventory:** Strictly prohibiting property publication until legal right-of-use evidence (freehold title deeds, tenancy sublet clauses, or society NOCs) is validated.
5. **Hardware-Agnostic Gate Verification:** Secure, opaque, one-time access QR tokens scanned by existing on-premise security guards via a lightweight mobile app, minimizing gate infrastructure CapEx by utilizing existing guard smartphones.
6. **Controlled Offline Guard Fallback:** A realistic, audited manual fallback protocol for underground basements with zero cellular connectivity, governed by automated 7-day photo retention limits.
7. **True Double-Entry General Ledger:** An immutable, append-only financial accounting engine with standard Chart of Accounts, balanced debits and credits ($\sum \text{Debits} = \sum \text{Credits}$), and compliant weekly payout mechanisms.

### Core Platform Decision
Gadispot is strictly **MOBILE-ONLY**. In the MVP, all customer-facing, space-owner, and gate-guard interactions are delivered through a single cross-platform **Flutter mobile application** for **Android** and **iOS** featuring dynamic role-based shells. There is **no public consumer website**, **no desktop booking portal**, and **no public web admin dashboard**. Internal platform operations workflows are managed via restricted mobile views (`SCR-401..402`) and secure backend administrative CLI tools.

---

## 3. Product Overview

Gadispot establishes an institutional bridge between drivers who cannot find reliable parking in congested Indian metro blocks and private property owners who possess empty vehicular capacity.

### Key Functional Pillars:
- **For Drivers:** Real-time search within a 3km default radius, guaranteed physical bay reservation via 480-second atomic hold, seamless UPI Intent checkout, dynamic high-contrast access QR pass, live parking session timer, and automated recovery protection.
- **For Property Owners:** Effortless space listing, granular recurring weekly schedules, real-time occupancy and earnings visibility, and scheduled weekly direct bank payouts under strict KYC (PAN + Penny Drop).
- **For Security Guards:** Fast one-handed camera QR scanning on low-end Android handsets, sub-second admission clearance, offline schedule fallback in subterranean basements, and one-tap incident reporting.
- **For Platform Operators:** Centralized property verification queue, dispute resolution tools, ledger audit trails, and automated financial reconciliation.

---

## 4. Problem Statement

### 4.1 Driver Problems
- **Severe Urban Congestion:** Drivers in major Indian metros (Bengaluru, Mumbai, Delhi-NCR) spend 15 to 25 minutes circling commercial blocks searching for open parking, increasing fuel burn and traffic congestion.
- **Uncertainty of Space Availability:** Arriving at a destination only to find full lots or illegal roadside parking subject to traffic police towing.
- **Arbitrary & Opaque Pricing:** Street parking and unorganized lots charge arbitrary cash rates with zero printed receipts or price predictability.
- **Access Restrictions & Hostility:** Private gated societies and commercial basements aggressively turn away guest vehicles due to security concerns and lack of guest verification.
- **Zero Cancellation or Refund Protection:** If plans change or a reserved space is blocked, drivers have no mechanism to retrieve prepayments.

### 4.2 Property Owner Problems
- **Dormant Asset Capacity:** Prime residential driveways, vacant builder plots, and commercial office basements sit empty during business hours or weekends, generating zero yield.
- **Lack of Monetization Framework:** Individual owners lack the booking infrastructure, payment processing, or customer vetting tools required to rent parking spaces safely.
- **Security & Encroachment Concerns:** Fear that letting strangers park will lead to vehicle abandonment, property encroachment, or security vulnerabilities.
- **Manual Payment & Reconciliation Overhead:** Collecting small-denomination cash or tracking loose UPI screenshots is operationally unmanageable for busy property managers.

### 4.3 Parking Operator and Guard Problems
- **Verification Bottlenecks:** Security guards at apartment complexes and commercial gates waste minutes inspecting handwritten visitor logs and calling residents.
- **Risk of Unauthorized Entry:** Inability to distinguish legitimate pre-booked guests from unauthorized vehicles seeking free parking.
- **No Occupancy Visibility:** Guards lack real-time digital insight into which bays are reserved, which are occupied, and when vehicles are scheduled to exit.
- **Dispute Hostility:** Guards face confrontation when forced to turn away drivers who claim they had informal verbal permission to park.

### 4.4 Platform & Industry Problems
- **Fake & Fraudulent Listings:** Unscrupulous actors listing spaces they do not own or public spaces belonging to municipal authorities.
- **Double Bookings & Concurrency Failures:** Weak database architectures allowing two concurrent drivers to reserve and pay for the exact same physical slot.
- **Payment Webhook Desynchronization:** Payment aggregator network delays leading to orphaned payments where the driver's bank account is debited but the booking drops.
- **QR Code Replay & Screenshot Forgery:** Drivers sharing static screenshots of valid QR codes with friends to obtain free parking sessions.
- **Regulatory Ambiguity:** Operating in an environment where RBI payment aggregator rules and local municipal guidelines require strict compliance.

---

## 5. Product Vision and Objectives

### 5.1 Central Product Promise
> **"Find parking, reserve it, pay securely, access it reliably, and receive a clear resolution if something goes wrong."**

Gadispot achieves dependability through strict contract enforcement, pessimistic availability logic, and a structured recovery protocol.

### 5.2 Specific Measurable Objectives
1. **Sub-Second Discovery:** Return verified, dimensionally compatible parking spaces within 500ms for 95% of spatial search requests in a 3km radius.
2. **Zero Double-Bookings:** Maintain 100% mathematical exclusion of overlapping confirmed bookings and active holds via database storage engine constraints.
3. **Sub-2-Second Gate Admission:** Enable security guards to scan an access pass, complete backend validation, and render admission verdict in under 2 seconds.
4. **Complete Ledger Auditability:** Guarantee that 100% of posted financial journals satisfy $\sum \text{Debits} = \sum \text{Credits}$ with zero unallocated funds.
5. **Deterministic Incident Recovery:** Provide an automated 8-step alternative space reallocation within 500m or initiate a 100% full refund within 180 seconds of an arrival failure report.

### 5.3 Initial Pilot Geography
- **Target City:** Bengaluru, Karnataka.
- **Pilot Micro-Markets:** Koramangala, Indiranagar, and HSR Layout.
- **Currency & Timezone:** Indian Rupee (INR / ₹) stored as integer paise. Timestamps stored in UTC (`TIMESTAMPTZ`) and displayed in Indian Standard Time (IST, UTC+05:30).

---

## 6. Target Users and Personas

### Persona 1: Rohan — The Urban Commuter (Driver)
- **Profile:** 29-year-old software engineer driving a Hyundai Creta (SUV) to client meetings in Koramangala.
- **Pain Point:** Circles for 20 minutes looking for parking; risks parking on roadsides with towing hazards; cannot afford to be late.
- **Needs:** Pre-book a guaranteed spot before leaving home, receive turn-by-turn navigation, and flash a pass at the gate for immediate access.

### Persona 2: Anand — The Driveway Monetizer (Space Owner)
- **Profile:** 54-year-old homeowner with an independent villa in Indiranagar with a 2-car covered driveway, using only 1 bay during work hours.
- **Pain Point:** Has vacant driveway capacity during daytime hours; hesitant to let strangers park without identity verification.
- **Needs:** Easy scheduling (Mon–Fri 09:00–18:00), vetted drivers, automatic weekly payouts to his HDFC bank account, and zero physical involvement.

### Persona 3: Ramesh — The Gate Security Guard
- **Profile:** 38-year-old security guard at a gated commercial property in HSR Layout; uses a budget Android smartphone with erratic 4G.
- **Pain Point:** Stressed by visitor congestion; struggles with handwritten registers; argued with drivers claiming verbal authorization.
- **Needs:** A simple camera screen to scan a driver's QR code, immediate Green/Red feedback, and a fallback mode that works in the basement.

### Persona 4: Deepa — Platform Operations Specialist
- **Profile:** 27-year-old operations associate responsible for Bengaluru listing quality, dispute arbitration, and host onboarding.
- **Pain Point:** Sifting through fraudulent property listings; managing customer complaints when a bay is blocked.
- **Needs:** Fast document verification queue with tax receipt inspection, one-click GPRP incident review, and tamper-proof ledger audit trails.

---

## 7. User Roles and Permission Boundaries

Gadispot enforces strict Role-Based Access Control (RBAC) at the API and database levels:

| User Role | Accessible Mobile Screens | Permitted Actions | Forbidden Actions |
|---|---|---|---|
| **DRIVER** | `SCR-101..107` | Search spaces, book bays, initiate holds, pay via UPI, view entry/exit QR, extend sessions, cancel bookings, report arrival issues, rate stays. | Cannot view owner earnings, cannot scan passes as guard, cannot approve listings, cannot alter tariffs. |
| **OWNER** | `SCR-201..205` | List properties, define spaces, submit deeds/NOCs, configure operating schedules, block bays for personal use, view earnings, link bank account. | Cannot approve own listings, cannot override platform commissions, cannot modify completed ledger journals. |
| **GUARD** | `SCR-301..304` | Scan entry/exit QRs, view shift arrival schedules, execute offline manual admissions, report space obstructions. | Cannot view booking prices, cannot see driver contact details (PII masked), cannot create bookings, cannot issue refunds. |
| **OPERATIONS**| `SCR-401..402` | Audit property verification documents, approve/reject listings, review GPRP arrival incidents, arbitrate disputes, trigger manual refund escalations. | Cannot initiate unbudgeted ledger payouts without dual approval; cannot modify posted journals. |
| **ADMIN** | Backend CLI / Dual-Approval API | System configuration, database migrations, security administration, commercial commission configuration, emergency kill-switches. | Cannot bypass ledger balance triggers; all root actions logged immutably. |

---

## 8. Product Scope

### 8.1 In-Scope for MVP
1. Mobile application for Android and iOS using a single Flutter codebase.
2. In-process modular monolith backend in Python FastAPI with PostgreSQL 16 + PostGIS and Redis 7.0+.
3. Passwordless phone number authentication via Firebase Phone Auth with authoritative backend JWT minting.
4. Geospatial PostGIS radius search (3km default, 5km max) with vehicle dimension compatibility filtering.
5. Atomic interval-based reservation holds with strictly 480-second (8-minute) lifespan backed by `btree_gist`.
6. Razorpay UPI Intent checkout integration with durable database webhook idempotency (`payment_webhook_events`).
7. Dynamic access credential lifecycle with 128-bit CSPRNG tokens (`ENTRY_TOKEN` and `EXIT_TOKEN`).
8. On-premise security guard QR scanning via `mobile_scanner` with offline manual exception fallback.
9. Guaranteed Parking Recovery Protocol (GPRP) with 180s driver decision timeout and automated 6-stage refund.
10. Immutable double-entry general ledger with balanced debit/credit database triggers.
11. Owner property verification with private encrypted S3 evidence storage.
12. Scheduled batch bank payouts to verified owner accounts (PAN + Penny Drop).

### 8.2 Out of Scope for MVP (Deferred to Phase 2+)
- Hardware IoT sensors, ultrasonic bay detectors, and magnetic loop detectors.
- Automated Number Plate Recognition (ANPR) and computer vision camera feeds.
- Automated motorized barrier gates and boom-barrier relay controllers.
- Public web portal, consumer web booking, or desktop admin dashboards.
- Dynamic surge pricing algorithms or predictive demand modeling.
- Electric vehicle (EV) charging kilowatt-hour billing and charger plug hardware integration.
- Continuous multi-day leases, monthly recurring subscriptions, or corporate fleet billing.
- International payment gateways and cross-border currency conversions.

---

## 9. MVP and Future Roadmap

```
+---------------------------------------------------------------------------------------+
|                               PRODUCT ROADMAP PHASING                                 |
+---------------------------------------------------------------------------------------+
| SPRINT 0 & 1: Foundational Core Architecture                                          |
| - PostgreSQL DDL with PostGIS & btree_gist exclusion constraints                      |
| - Double-entry ledger with immutability triggers (trg_verify_journal_balance)         |
| - FastAPI modular monolith scaffolding and Redis state engine                         |
| - Two-Tier Hold Expiration Engine (5s worker + inline sweep)                          |
| - Automated Pytest concurrency test suite covering TS-01 through TS-20                |
+---------------------------------------------------------------------------------------+
| SPRINT 2 & 3: Mobile Experience & Payment Integration                                 |
| - Single Flutter binary with dynamic role shells (Driver, Owner, Guard, Ops)          |
| - Firebase Phone Authentication & JWT token exchange                                  |
| - Razorpay UPI Intent checkout & durable webhook idempotency engine                   |
| - Entry and Exit QR credential generation and guard scanner engine                    |
| - Offline basement manual exception protocol with local SQLite queue                  |
+---------------------------------------------------------------------------------------+
| SPRINT 4 & 5: Field Operations, Pilot Onboarding & Launch                             |
| - Property verification workflow & S3 encrypted document upload                       |
| - GPRP arrival incident recovery & 6-stage asynchronous refund lifecycle              |
| - Owner scheduled batch payouts via corporate bank IMPS under MoR status              |
| - Closed pilot in Koramangala / Indiranagar / HSR Layout (200 parking bays)           |
+---------------------------------------------------------------------------------------+
| PHASE 2 (Post-Pilot Strategic Extensions):                                            |
| - Razorpay Route automated linked-account split payouts (upon >₹40L turnover)         |
| - Multi-day and recurring monthly parking subscriptions                               |
| - Barrier-gate hardware relay integrations & ANPR camera pilot                        |
| - EV charging electrical sub-meter billing integration                                |
+---------------------------------------------------------------------------------------+
```

---

## 10. Product Differentiators

Gadispot establishes four defensible, measurable capabilities:

### 1. Multi-Source Availability Intelligence (MSAI)
Availability is computed dynamically across 7 operational signals:
$$\text{MSAI Availability} = f(\text{Schedule}, \text{Blackouts}, \text{Bookings}, \text{Active Holds}, \text{Sessions}, \text{Incidents}, \text{Buffers})$$
The system enforces **pessimistic availability**: any signal discrepancy (such as an open schedule but an active guard obstruction report) immediately suppresses the slot from search results.

### 2. Mathematical GiST Concurrency Engine
Speculative inventory locking is eliminated at the database storage engine layer using PostgreSQL range types (`tstzrange`) and GiST exclusion constraints:
```sql
EXCLUDE USING gist (parking_space_id WITH =, time_window WITH &&)
WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
```
Two concurrent requests for overlapping intervals on the same physical bay are mathematically serialized; exactly one commits and the other receives an immediate HTTP 409 Conflict.

### 3. Guaranteed Parking Recovery Protocol (GPRP)
If a reserved bay is obstructed upon driver arrival, the system executes an atomic 8-step recovery workflow: reserving an alternative bay within a 500m radius with zero incremental driver cost, or automatically initiating a 100% full refund if no alternative exists or the driver declines within 180 seconds.

### 4. Immutable Double-Entry Ledger
Monetary integrity is enforced through two-tier `journal_entries` and `journal_lines` tables. Every transaction is balanced ($\sum \text{Debits} = \sum \text{Credits}$), posted entries and lines are strictly immutable (`REVOKE UPDATE, DELETE`), and parent-row locking eliminates concurrency races during posting.

---

## 11. Core User Journeys

### 11.1 Driver Search-to-Completion Journey
```
[ Open App ] -> [ Proximity Search (3km) ] -> [ Select Bay & Review Terms ]
      |
      v
[ Tap 'Book This Bay' ] -> [ Acquire 480s GiST Hold ] -> [ Launch UPI Intent ]
      |
      v
[ UPI PIN Authorized ] -> [ Webhook Verified ] -> [ Issue Entry & Exit QR Pass ]
      |
      v
[ Drive to Gate ] -> [ Guard Scans Entry QR ] -> [ Gate Opens / Session Active ]
      |
      v
[ Park Vehicle ] -> [ Depart Gate ] -> [ Guard Scans Exit QR ] -> [ Session Closed ]
```

### 11.2 Space Owner Onboarding Journey
```
[ Register via Phone ] -> [ Add Property Details ] -> [ Add Parking Bays ]
      |
      v
[ Upload Title Deed / Society NOC ] -> [ Configure Weekly Operating Schedule ]
      |
      v
[ Submit Listing ] -> [ Ops Document Review ] -> [ Property Approved & Published ]
      |
      v
[ Link Bank Account (Penny Drop) ] -> [ Receive Automated Weekly Batch Payout ]
```

### 11.3 Guard Gate Validation Journey
```
[ Guard Login ] -> [ Select Assigned Property ] -> [ Open Camera Scanner ]
      |
      v
[ Scan Driver Entry QR ] -> [ Backend Validates Token & Schedule ]
      |
      +---> Online Success: Screen Flashes BOLD GREEN with Bay Number -> Open Gate
      |
      +---> Replay Scan: Screen Flashes BOLD RED "QR Already Used" -> Deny Gate
      |
      +---> Basement Offline: Match License Plate against Local Cached Schedule ->
            Capture Vehicle Photo -> Grant Manual Admission -> Queue Async Sync
```

---

## 12. Functional Requirements

All functional requirements carry stable, uniquely identifiable codes formatted as `FR-<DOMAIN>-<NUMBER>`.

### 12.1 Authentication & Identity (`FR-AUTH-xxx`)

#### `FR-AUTH-001`: Passwordless Mobile Phone Authentication
- **Description:** System authenticates users via 10-digit Indian mobile numbers (+91) using telecom SMS OTP.
- **Actor:** Driver, Owner, Guard, Operations.
- **Preconditions:** Handset possesses active cellular connection.
- **Main Flow:**
  1. User enters 10-digit phone number in `SCR-002`.
  2. Firebase Auth SDK dispatches SMS OTP via telecom gateway.
  3. User enters 6-digit OTP in `SCR-003` (or auto-retrieved on Android).
  4. Firebase SDK verifies OTP on handset and mints Firebase ID token.
  5. App submits ID token to `POST /api/v1/auth/session`.
  6. Backend validates token signature via Firebase Admin SDK and issues internal SmartPark JWT (access token: 60m TTL, refresh token: 30d TTL).
- **Alternate Flows:** Existing user logs in directly without profile creation; new user is prompted for full name and default role.
- **Failure Conditions:** Invalid OTP, expired OTP (>60s), rate limit exceeded (>3 attempts/15m).
- **Business Rules:** Plaintext OTPs must NEVER be generated, received, or stored in the Gadispot database.
- **Data Requirements:** `users` table records `id`, `phone_number`, `created_at`, `status`.
- **Security Requirements:** Firebase Admin token verification must validate `exp`, `aud`, and `iss`.
- **Acceptance Criteria:** Valid OTP issues JWT with HTTP 200 OK; invalid OTP returns HTTP 401 Unauthorized within 1 second.
- **Priority:** P0 (MVP).
- **Dependencies:** Firebase Authentication, Google Cloud Identity Platform.

#### `FR-AUTH-002`: Dynamic Mobile Role Switching
- **Description:** Users registered as both Driver and Owner toggle active viewports without re-authenticating.
- **Actor:** Multi-role User.
- **Preconditions:** User is authenticated and possesses both `DRIVER` and `OWNER` roles in `user_roles`.
- **Main Flow:** User taps profile toggle; app calls `POST /api/v1/auth/switch-role`; backend returns new JWT with updated `role` claim; Flutter dynamically re-renders active shell.
- **Acceptance Criteria:** Role switch executes in <300ms without network logout.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AUTH-001`.

---

### 12.2 Driver Features (`FR-DRIVER-xxx`)

#### `FR-DRIVER-001`: Multi-Vehicle Profile Management
- **Description:** Driver registers and manages multiple vehicles with Indian license plate formatting.
- **Actor:** Driver.
- **Preconditions:** Authenticated as Driver.
- **Main Flow:** Driver inputs registration number (regex: `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$`), category (`TWO_WHEELER`, `HATCHBACK`, `SEDAN`, `SUV`, `EV_FOUR_WHEELER`), make, and model.
- **Acceptance Criteria:** Valid Indian plate formats saved to `vehicles` table; invalid formats rejected with descriptive error.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AUTH-001`.

#### `FR-DRIVER-002`: Proximity Search with Spatial Radius
- **Description:** Search verified available bays based on GPS coordinates, time window, and vehicle category.
- **Actor:** Driver.
- **Preconditions:** Device location permission granted or manual landmark selected.
- **Main Flow:** Driver provides lat/long, start time, end time, and vehicle category. Backend executes PostGIS ST_DWithin query filtered by MSAI availability and vehicle compatibility.
- **Business Rules:** Default search radius is strictly 3 km, user-expandable up to 5 km maximum (`POL-RAD-01`).
- **Acceptance Criteria:** Returns only `APPROVED` properties with available slots in <500ms for 95% of queries.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AVAIL-001`.

---

### 12.3 Property Owner Features (`FR-OWNER-xxx`)

#### `FR-OWNER-001`: Property and Parking Bay Onboarding
- **Description:** Owner submits property location, parking space dimensions, amenities, and photos.
- **Actor:** Owner.
- **Preconditions:** Authenticated as Owner.
- **Main Flow:** Owner creates property, uploads 3 mandatory photos (Entrance, Bay, Approach), specifies bay physical dimensions (length, width, clearance height), and sets base hourly rate.
- **Acceptance Criteria:** Property saved in `DRAFT` status; spaces locked in `UNVERIFIED` status until authorization approved.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AUTH-001`.

#### `FR-OWNER-002`: Recurring Operating Schedule & Blackouts
- **Description:** Owner defines recurring weekly availability windows and temporary personal blackout blocks.
- **Actor:** Owner.
- **Main Flow:** Owner configures daily intervals (e.g., Mon–Fri 09:00–18:00). Owner can tap "Blackout Space" to block future unbooked intervals.
- **Business Rules:** Blackout requests cannot override existing `CONFIRMED` bookings.
- **Acceptance Criteria:** Blackout intervals saved to `operating_schedules`; immediate conflict rejection if overlapping booking exists.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-OWNER-001`.

---

### 12.4 Inventory Management (`FR-INVENTORY-xxx`)

#### `FR-INVENTORY-001`: Multidimensional Vehicle Compatibility Engine
- **Description:** Verifies that a vehicle physically fits inside a parking bay.
- **Actor:** System.
- **Business Rules:** Compatibility must NOT use scalar comparisons (`compatibility >= category`). Must evaluate physical dimensions:
  $$\text{Compatible} = (\text{Bay Length} \ge \text{Veh Length} + 0.3\text{m}) \land (\text{Bay Width} \ge \text{Veh Width} + 0.4\text{m}) \land (\text{Clearance} \ge \text{Veh Height} + 0.1\text{m})$$
- **Acceptance Criteria:** SUV attempting to book a compact hatchback bay is rejected with HTTP 422 `INCOMPATIBLE_VEHICLE_DIMENSIONS`.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-DRIVER-001`, `FR-OWNER-001`.

---

### 12.5 Availability Intelligence (`FR-AVAIL-xxx`)

#### `FR-AVAIL-001`: Multi-Source Availability Synthesis (MSAI)
- **Description:** Authoritative computation of slot bookability synthesizing 7 operational inputs.
- **Actor:** System.
- **Inputs:** 1) Owner Schedule, 2) Owner Blackouts, 3) Confirmed Bookings, 4) Active 480s Holds, 5) Active Sessions, 6) Guard Incident Reports, 7) 15-Minute Turnover Buffers.
- **Business Rules:** Conflicting inputs force pessimistic unavailability. Stale guard reports (>4h) trigger re-inspection flags.
- **Acceptance Criteria:** Slots overlapping confirmed bookings or active holds are strictly excluded from search results.
- **Priority:** P0 (MVP).
- **Dependencies:** PostgreSQL `btree_gist`.

---

### 12.6 Booking and Hold Management (`FR-BOOK-xxx`)

#### `FR-BOOK-001`: Atomic 480-Second Time-Window Hold
- **Description:** Reserves a slot interval during checkout with an authoritative 480-second lifespan.
- **Actor:** Driver.
- **Main Flow:** Driver calls `POST /api/v1/bookings/hold`. Backend inserts into `space_reservations` with status `ACTIVE_HOLD` and `hold_expires_at = now() + interval '480 seconds'`.
- **Concurrency Invariant:** PostgreSQL GiST exclusion constraint (`EXCLUDE USING gist`) prevents any overlapping hold or booking.
- **Failure Conditions:** If competing driver holds slot, transaction catches `ExclusionViolation (23P01)` and returns HTTP 409 Conflict.
- **Acceptance Criteria:** Hold created with exact 480-second countdown; concurrent collision rejected deterministically.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AVAIL-001`.

#### `FR-BOOK-002`: Two-Tier Hold Expiration Engine
- **Description:** Cleans expired holds out of the partial GiST exclusion index to release inventory.
- **Actor:** System.
- **Mechanics:** 1) Active Background Sweeper runs every 5 seconds executing `UPDATE space_reservations SET status = 'EXPIRED_HOLD' WHERE status = 'ACTIVE_HOLD' AND hold_expires_at < now()`, using `FOR UPDATE SKIP LOCKED`. 2) Inline Opportunistic Sweeper executes in hold creation transactions.
- **Acceptance Criteria:** Expired holds purged within $\le 5$ seconds of expiration.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-BOOK-001`.

---

### 12.7 Payment Processing (`FR-PAY-xxx`)

#### `FR-PAY-001`: UPI Checkout & Durable Webhook Processing
- **Description:** Facilitates UPI payment via Razorpay with database-level durable deduplication.
- **Actor:** Driver, Gateway.
- **Main Flow:** Driver launches UPI Intent in mobile app. Upon authorization, gateway dispatches `payment.captured` webhook. Backend retrieves raw request bytes, validates HMAC-SHA256 signature, inserts into `payment_webhook_events` with unique constraint on `(gateway_name, gateway_event_id)`, and transitions reservation to `CONFIRMED`.
- **Business Rules:** Mobile client payment callbacks are treated as untrusted hints. Booking confirmation strictly requires server webhook or authenticated server-to-gateway polling verification.
- **Acceptance Criteria:** Duplicate webhooks return HTTP 200 OK without duplicate ledger postings; invalid signatures return HTTP 400.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-BOOK-001`.

#### `FR-PAY-002`: Late Payment Resolution Protocol (LPRP)
- **Description:** Resolves payments captured after hold expiration without double-booking.
- **Actor:** System.
- **Main Flow:** If `payment.captured` arrives for an `EXPIRED_HOLD`, backend attempts atomic transition to `CONFIRMED`. If competing driver claimed the bay, PostgreSQL throws `ExclusionViolation (23P01)`. Backend catches error, marks reservation `RELEASED_UNFULFILLABLE`, and initiates automated 100% full refund (`REFUND_ELIGIBLE`).
- **Acceptance Criteria:** Zero double-bookings occur; unfulfillable payments automatically routed to 6-stage refund pipeline.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-PAY-001`.

---

### 12.8 Refund Management (`FR-REFUND-xxx`)

#### `FR-REFUND-001`: Asynchronous 6-Stage Refund Lifecycle
- **Description:** Governs end-to-end refund processing from policy qualification through bank rail settlement.
- **Actor:** System, Operations.
- **State Machine:**
  $$\text{NONE} \longrightarrow \text{REFUND\_ELIGIBLE} \longrightarrow \text{REFUND\_REQUESTED} \longrightarrow \text{GATEWAY\_ACCEPTED} \longrightarrow \text{REFUND\_PROCESSING} \longrightarrow \text{REFUND\_SETTLED} \ (\text{or } \text{REFUND\_FAILED})$$
- **Business Rules:** Gateway acceptance (`GATEWAY_ACCEPTED`) does not equal customer receipt. Customer UI transparently displays a 5–7 business day banking rail settlement window until gateway webhook confirms `REFUND_SETTLED` with bank UTR.
- **Acceptance Criteria:** Every refund transition records balancing double-entry ledger journals.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-PAY-001`, `FR-LEDGER-001`.

---

### 12.9 QR Code Access (`FR-QR-xxx`)

#### `FR-QR-001`: Dynamic Opaque Access Credential Issuance
- **Description:** Issues cryptographically unguessable, separate `ENTRY_TOKEN` and `EXIT_TOKEN` passes.
- **Actor:** System.
- **Entropy:** Tokens generated via 128-bit CSPRNG (`secrets.token_hex(16)`).
- **Business Rules:** Payment QR and Access QR are completely distinct. Access QR contains zero PII and zero payment credentials.
- **Acceptance Criteria:** Tokens unguessable; entry token valid $[t_{\text{start}}-15\text{m}, t_{\text{start}}+30\text{m})$; exit token pre-cached upon check-in.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-PAY-001`.

#### `FR-QR-002`: Guard Gate Validation & Replay Burn
- **Description:** Security guard scans driver QR pass to validate admission.
- **Actor:** Guard.
- **Main Flow:** Guard scans QR via `mobile_scanner`. Backend validates token, property binding, and temporal window. Atomically marks token `CONSUMED` and reservation `ACTIVE_SESSION`. Guard screen flashes BOLD GREEN.
- **Failure Conditions:** Second scan of same token flashes BOLD RED: "ACCESS REJECTED: QR code already consumed".
- **Acceptance Criteria:** Validation response delivered in <1.5s; replay attacks blocked 100%.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-QR-001`.

---

### 12.10 Parking Session Management (`FR-SESSION-xxx`)

#### `FR-SESSION-001`: Parking Session Tracking & Dynamic Extension
- **Description:** Tracks live session duration and allows drivers to extend parking subject to future availability.
- **Actor:** Driver.
- **Main Flow:** Driver requests 30m or 60m extension in `SCR-105`. MSAI verifies bay has no conflicting reservation. Driver pays additional fee. Database extends `time_window` and updates `EXIT_TOKEN` validity.
- **Acceptance Criteria:** Conflicted extensions blocked; successful extensions update session and exit pass atomically.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-QR-002`.

---

### 12.11 Double-Entry General Ledger (`FR-LEDGER-xxx`)

#### `FR-LEDGER-001`: Immutable Balanced Financial Accounting
- **Description:** Records all financial events in append-only double-entry journals.
- **Actor:** System.
- **Invariants:**
  1. $\sum \text{Debits} = \sum \text{Credits}$ enforced by trigger `trg_verify_journal_balance` on `journal_entries`.
  2. Immutability enforced by `trg_prevent_posted_modification` on `journal_entries` and `trg_prevent_posted_lines_mod` on `journal_lines`.
  3. Parent-row locking (`FOR SHARE` / `FOR UPDATE`) serializes line insertion against posting.
- **Acceptance Criteria:** Unbalanced journals rejected with DB exception; modification of posted journals or lines rejected 100%.
- **Priority:** P0 (MVP).
- **Dependencies:** PostgreSQL triggers.

---

### 12.12 Owner Payouts (`FR-PAYOUT-xxx`)

#### `FR-PAYOUT-001`: Scheduled Batch Bank Payouts
- **Description:** Disburses accumulated owner earnings via scheduled weekly batch bank transfers (IMPS).
- **Actor:** Finance Lead, System.
- **Business Rules:** Payouts execute weekly (Tuesdays) for verified owners with balance $\ge ₹500$. Owner KYC must be validated (PAN verified + Penny-Drop bank verification matching owner name).
- **Acceptance Criteria:** Payouts debited from Account 2010; failed transfers flagged for retry without balance loss.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-LEDGER-001`.

---

### 12.13 Administration & Operations (`FR-ADMIN-xxx`)

#### `FR-ADMIN-001`: Property Authorization Review Queue
- **Description:** Operations staff inspect legal ownership evidence before approving listings.
- **Actor:** Operations Associate.
- **Main Flow:** Ops reviews tax receipts / society NOCs via 15-minute presigned S3 URLs in `SCR-401`. Upon approval, property status transitions to `APPROVED` and spaces become searchable.
- **Acceptance Criteria:** Unverified properties cannot be published; all approval/rejection actions logged immutably.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-OWNER-001`.

---

### 12.14 Security & Privacy (`FR-SEC-xxx`)

#### `FR-SEC-001`: DPDPA Data Minimization & 7-Day Gate Photo Purge
- **Description:** Enforces statutory privacy controls and automated retention purges under DPDPA 2023.
- **Actor:** System.
- **Mechanics:** Photos captured during offline basement gate exceptions are stored in private S3 buckets. An automated S3 Lifecycle rule permanently purges photos 7 days post-reconciliation.
- **Acceptance Criteria:** Zero gate exception photos retained beyond 7 days in S3.
- **Priority:** P0 (MVP).
- **Dependencies:** AWS S3 Lifecycle.

---

### 12.15 Notifications (`FR-NOTIFY-xxx`)

#### `FR-NOTIFY-001`: Transactional Multi-Channel Dispatch
- **Description:** Dispatches real-time transactional push notifications (FCM / APNs) and critical SMS alerts.
- **Actor:** System.
- **Events:** Booking Confirmed, Hold Expiring (at 6m elapsed), Arrival Reminder (15m prior), Exit Reminder (10m prior), GPRP Alert, Payout Dispatched.
- **Acceptance Criteria:** Push delivered in $\le 3$ seconds under standard mobile connectivity.
- **Priority:** P0 (MVP).
- **Dependencies:** Firebase Cloud Messaging.

---

### 12.16 Incident Recovery (`FR-GPRP-xxx`)

#### `FR-GPRP-001`: Guaranteed Parking Recovery Protocol (GPRP)
- **Description:** Atomic 8-step alternative space reallocation or 100% full refund upon physical bay arrival failure.
- **Actor:** Driver, Guard, System.
- **Main Flow:** Driver or guard reports arrival obstruction. System preserves original booking, searches compatible bay within 500m, acquires atomic hold, and presents offer to driver with 180s decision countdown. If driver accepts, booking transfers at zero incremental cost. If driver declines or timer expires, system releases alternative hold and initiates 100% full refund (`REFUND_ELIGIBLE`).
- **Acceptance Criteria:** Recovery executed atomically without double-booking; fallback to full refund within 180 seconds.
- **Priority:** P0 (MVP).
- **Dependencies:** `FR-AVAIL-001`, `FR-REFUND-001`.

---

## 13. Owner and Property Verification

To prevent fraudulent listings, unauthorized sub-letting, and trespassing disputes, Gadispot enforces mandatory legal vetting before any space becomes bookable:

```
+---------------------------------------------------------------------------------------+
|                      PROPERTY AUTHORIZATION LIFECYCLE                                 |
+---------------------------------------------------------------------------------------+
| [ DRAFT ] Owner uploads property tax receipt, sale deed, or society NOC               |
|      |                                                                                |
|      v                                                                                |
| [ PENDING_REVIEW ] Listing locked; invisible to search queries                        |
|      |                                                                                |
|      +---> Operations Approves -> [ APPROVED ] -> Spaces become PUBLISHED & bookable |
|      |                                                                                |
|      +---> Operations Rejects -> [ REJECTED ] -> Owner receives rejection reason     |
|      |                                                                                |
|      +---> Complaint / Dispute -> [ SUSPENDED ] -> Immediate blackout of future holds |
+---------------------------------------------------------------------------------------+
```

### Statutory Evidence Requirements:
1. **Independent Residential Driveway:** Property Tax Assessment Receipt (current fiscal year) OR Registered Sale Deed showing applicant's name and physical address matching property geolocation.
2. **Gated Apartment Society Bay:** Formal Housing Society (AOA/RWA) No-Objection Certificate (NOC) explicitly permitting guest vehicle parking monetization, counter-signed by society secretary.
3. **Tenant Listings:** Tenant must upload written lease agreement containing an explicit commercial parking sublet clause signed by the property owner.

---

## 14. Inventory and Space Management

Each parking space represents a discrete physical inventory asset characterized by:
- **Spatial Coordinates:** Exact latitude and longitude (WGS 84 / SRID 4326).
- **Physical Clearance:** Length, width, and vertical clearance height in millimeters.
- **Infrastructure Attributes:** Surface type (`COVERED`, `OPEN`, `BASEMENT`), EV charging capability (`NONE`, `SLOW_AC_15A`, `FAST_DC`), CCTV coverage, gated perimeter, on-premise security guard.
- **Operational Cadence:** Weekly recurring operating hours and owner blackout dates.
- **Tariff Structure:** Base hourly rate (INR paise), minimum booking duration (default 30 min), maximum continuous hours (default 24h).

---

## 15. Availability Intelligence (MSAI)

The Multi-Source Availability Intelligence engine evaluates whether parking bay $S$ is bookable for time interval $[T_1, T_2)$ through strict propositional logic:

$$\text{Bookable}(S, T_1, T_2) = \text{Operating}(S, T_1, T_2) \land \neg \text{Blackout}(S, T_1, T_2) \land \neg \text{Held}(S, T_1, T_2) \land \neg \text{Booked}(S, T_1, T_2) \land \neg \text{Incident}(S)$$

### Canonical Space States:
- `AVAILABLE`: Space is unencumbered and immediately bookable for the requested interval.
- `TEMPORARILY_HELD`: In active 480s driver checkout; excluded from other search results.
- `BOOKED`: Confirmed reservation exists for overlapping interval.
- `OCCUPIED`: Vehicle currently checked in and physically parked.
- `BLOCKED`: Owner manual blackout or administrative freeze.
- `UNVERIFIED`: Property authorization pending ops review; strictly non-searchable.
- `UNCERTAIN`: Conflicting operational signal (e.g., active guard obstruction report).
- `MAINTENANCE`: Physical maintenance in progress.
- `CLOSED`: Outside owner configured operating hours.

---

## 16. Geospatial Discovery

Discovery queries utilize PostGIS spatial indexing (`ST_DWithin` on geography coordinates):
```sql
SELECT ps.id, p.title, p.address, ps.hourly_rate_paise,
       ST_Distance(p.location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_meters
FROM parking_spaces ps
JOIN properties p ON ps.property_id = p.id
WHERE p.authorization_status = 'APPROVED'
  AND ST_DWithin(p.location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters)
  AND fn_check_vehicle_bay_compatibility(ps.id, :vehicle_id) = TRUE
ORDER BY distance_meters ASC
LIMIT 50;
```
Search radius defaults to **3 km** and is capped at **5 km** (`POL-RAD-01`).

---

## 17. Vehicle Compatibility

Compatibility is evaluated via multidimensional spatial matching:

| Vehicle Category | Maximum Vehicle Length | Maximum Vehicle Width | Required Bay Length Margin | Required Bay Width Margin | Minimum Vertical Clearance |
|---|---|---|---|---|---|
| **TWO_WHEELER** | 2,100 mm | 850 mm | +200 mm | +250 mm | 1,800 mm |
| **HATCHBACK** | 4,000 mm | 1,750 mm | +300 mm | +400 mm | 1,900 mm |
| **SEDAN** | 4,700 mm | 1,850 mm | +350 mm | +400 mm | 1,900 mm |
| **SUV** | 5,100 mm | 1,950 mm | +400 mm | +450 mm | 2,100 mm |
| **EV_FOUR_WHEELER** | 4,800 mm | 1,900 mm | +350 mm | +400 mm | 2,000 mm (Requires EV Charger) |

---

## 18. Booking and Reservation Lifecycle

```
[ DISCOVERY ] -> [ POST /bookings/hold ] -> [ ACTIVE_HOLD (480s Countdown) ]
                                                   |
         +-----------------------------------------+-----------------------------------------+
         | Payment Captured in 480s                                                          | Hold Expires (480s Elapsed)
         v                                                                                   v
[ CONFIRMED ] (Entry & Exit Passes Issued)                                            [ EXPIRED_HOLD ] (Slot Released)
         |                                                                                   |
         v                                                                                   | Late Payment Arrives
[ Driver Arrives Gate ]                                                                      v
         |                                                                            [ LPRP Reclaim Attempt ]
         +---> Guard Scans Entry QR -> [ ACTIVE_SESSION ]                                    |
         |                                                                                   +---> Slot Still Empty -> [ CONFIRMED ]
         +---> Gate Blocked -> [ GPRP Recovery Protocol ]                                    |
                                                                                             +---> Slot Re-booked -> [ RELEASED_UNFULFILLABLE ]
                                                                                                   (Automated 100% Refund via 6 Stages)
```

---

## 19. Hold and Concurrency Rules

1. **Universal Lifespan:** Checkout hold duration is strictly **480 seconds (8 minutes)** across all application components, API payloads, and database records (`POL-HLD-01`).
2. **Rate Limiting:** Maximum **2 concurrent active holds** permitted per verified phone number. Maximum 5 hold creations per 30 minutes.
3. **Database-Enforced Invariant:** Temporary holds are rows in `space_reservations` participating directly in the partial GiST exclusion constraint. Redis serves strictly as an auxiliary read-accelerator and countdown display cache.

---

## 20. Payment Lifecycle

1. **Order Initiation:** Backend creates order at payment gateway with strict integer paise representation.
2. **Client Checkout:** Flutter app launches native UPI Intent sheet (PhonePe, GPay, Paytm, BHIM).
3. **Authoritative Capture:** Payment gateway dispatches raw `payment.captured` webhook payload.
4. **Durable Idempotency:** Webhook event ID recorded in PostgreSQL `payment_webhook_events`. Duplicates acknowledged with HTTP 200 without side effects.
5. **Confirmation:** Reservation atomically transitions from `ACTIVE_HOLD` to `CONFIRMED`; double-entry ledger journal posted.

---

## 21. Refund Lifecycle

Refunds follow the canonical 6-stage asynchronous lifecycle:

```
+---------------------------------------------------------------------------------------+
|                                CANONICAL REFUND LIFECYCLE                             |
+---------------------------------------------------------------------------------------+
| 1. [ REFUND_ELIGIBLE ]   : Cancellation policy or LPRP/GPRP failure qualifies refund. |
| 2. [ REFUND_REQUESTED ]  : Transactional outbox queues refund API request to gateway. |
| 3. [ GATEWAY_ACCEPTED ]  : Gateway API returns HTTP 200 with gateway refund_id.       |
| 4. [ REFUND_PROCESSING ] : Banking rails processing transfer; 5-7 business day window. |
| 5. [ REFUND_SETTLED ]    : Gateway webhook delivers final settlement UTR; completed.   |
| 6. [ REFUND_FAILED ]     : Gateway/bank rejects refund; escalates to manual ops queue.|
+---------------------------------------------------------------------------------------+
```

---

## 22. Double-Entry Ledger

All financial movements are recorded across `journal_entries` and `journal_lines`:

### Standard Chart of Accounts:
- **1010 Gateway Transit Account (Asset):** Driver funds captured via UPI awaiting settlement to corporate account.
- **1020 Operating Current Bank Account (Asset):** Platform corporate commercial bank account.
- **2010 Owner Payable Liability (Liability):** Accumulated net earnings owed to space hosts.
- **2020 Customer Refund Payable (Liability):** Pending customer refunds.
- **2030 GST Output Tax Payable (Liability):** 18% GST collected on facilitation fees.
- **3010 Platform Commission Revenue (Revenue):** Marketplace facilitation commission earned (15%).
- **3020 Driver Convenience Fee Revenue (Revenue):** ₹10 convenience fee charged to drivers.
- **4010 Payment Gateway MDR Expense (Expense):** 2.36% MDR absorbed by platform.
- **4020 GPRP Customer Recovery Subsidy Expense (Expense):** Platform-subsidized goodwill allowances.

---

## 23. Owner Payouts and Reconciliation

- **Merchant of Record (MoR) Model:** Gadispot acts as the MoR for all customer transactions, assuming liability for cardholder disputes and tax compliance.
- **Phase 1 Pilot Disbursements:** Scheduled weekly batch IMPS transfers from the corporate bank account to verified owner bank accounts (PAN + Penny Drop).
- **Settlement Invariant:** An owner balance is eligible for payout only after the corresponding parking session has transitioned to `COMPLETED` and the cancellation dispute window (24 hours) has elapsed.

---

## 24. QR Entry and Exit

```
+---------------------------------------------------------------------------------------+
|                        TWO DISTINCT QR SUBSYSTEMS                                     |
+------------------------------------+--------------------------------------------------+
| 1. Dynamic Payment QR              | 2. Parking Access QR (Entry & Exit)              |
+------------------------------------+--------------------------------------------------+
| • Generated by: Payment Gateway    | • Generated by: Gadispot Backend Engine          |
| • Consumer: Driver UPI Mobile App  | • Consumer: Guard Mobile Scanner (mobile_scanner)|
| • Payload: NPCI UPI URI string     | • Payload: 128-bit CSPRNG token (spx_ent_...)    |
| • Expiry: Exactly 480s (8m)        | • Expiry: Phased (Entry vs Exit window)          |
| • Replay: Banking switch handled   | • Replay: Database atomic state burn upon entry  |
+------------------------------------+--------------------------------------------------+
```

---

## 25. Parking Session Management

- **Grace Period:** 15-minute early arrival buffer ($t_{\text{start}} - 15\text{m}$) and 30-minute late arrival grace period before `NO_SHOW` transition (`POL-ARR-02`).
- **Overstay Policy:** Exit scans occurring $>15$ minutes past scheduled departure calculate an overstay charge at **1.5× the base hourly rate** in 30-minute blocks (`POL-OST-01`).
- **Basement Offline Mode:** In subterranean cellular dead zones, guard matches physical license plate against locally cached 8-hour shift schedule, captures vehicle photo, and logs admission locally. Photos are permanently deleted from S3 within 7 days of backend sync.

---

## 26. GPRP Recovery Protocol

When a driver arrives but the reserved slot is obstructed:
1. Driver or guard taps "Report Space Blocked" (`SCR-104`).
2. Original booking remains active while backend evaluates alternative bay within 500m.
3. System atomically acquires hold on alternative bay at zero incremental driver cost.
4. Driver mobile renders 180-second countdown decision modal (`SCR-107`).
5. If driver accepts, booking atomically transfers to alternative bay.
6. If driver declines or timer reaches 00:00, alternative hold is released and system immediately initiates a 100% full refund (`REFUND_ELIGIBLE`).

---

## 27. Cancellation and No-Show Policies

| Trigger Event | Timing Window | Refund Percentage | Owner Entitlement | Platform Fee Status |
|---|---|---|---|---|
| **Driver Cancellation** | $>2$ hours before start | **100% Refund** | ₹0.00 | Platform absorbs gateway MDR |
| **Driver Cancellation** | 30 min to 2 hours before start | **50% Refund** | 50% of Host Share | Platform retains commission |
| **Driver Cancellation** | $<30$ min before start | **0% Refund** | 100% of Host Share | Platform retains commission |
| **Driver No-Show** | $>30$ min past start | **0% Refund** | 100% of Host Share | Platform retains commission |
| **Host Cancellation** | Any time prior to arrival | **100% Full Refund** | ₹0.00 (₹100 fine assessed) | Platform absorbs MDR |
| **Arrival Failure (GPRP)**| At arrival / obstructed bay | **100% Full Refund** | ₹0.00 | Platform absorbs MDR |

---

## 28. Incident and Dispute Management

- **Incident Classification:** `BAY_OBSTRUCTED`, `GATE_LOCKED`, `OVERSTAY_DISPUTE`, `PROPERTY_MISREPRESENTATION`, `UNAUTHORIZED_VEHICLE`.
- **Evidence Collection:** Mandatory timestamped photo evidence, guard badge identifier, and GPS geofence validation.
- **SLA:** Customer disputes acknowledged within 2 hours; resolved with final determination within 24 hours.

---

## 29. Authentication and Authorization

- **Primary Auth:** Phone number + SMS OTP via Firebase Auth SDK with server-side Admin SDK token verification.
- **Session Tokens:** Internal scoped JWTs containing user UUID, active role, and 60-minute expiration.
- **Internal Ops 2FA:** Privileged operations associates must provide an RFC 6238 TOTP code verified via PyOTP before executing document approvals or manual refund overrides.

---

## 30. Notifications

- **Channels:** Firebase Cloud Messaging (FCM) for Android, Apple Push Notification service (APNs) for iOS, and telecom SMS for critical transactional receipts.
- **Delivery Rules:** Transactional notifications (booking confirmation, access pass, GPRP alert) cannot be disabled by user preferences.

---

## 31. Admin and Operations

- **Mobile Operations View (`SCR-401..402`):** Restricted view compiled inside the single Flutter binary, rendered only for verified `OPERATIONS` JWT claims.
- **Capabilities:** Property authorization queue, document preview with 15-minute presigned S3 URLs, GPRP arrival incident arbitration, and manual payout batch triggers.
- **Dual Approval:** Payout batch disbursements exceeding ₹50,000 require dual approval from Operations Lead and Finance Director.

---

## 32. User Experience Requirements

- **Design Philosophy:** Utilitarian craftsmanship, zero AI-slop visual gimmicks (no purple radial glows, heavy frosted glass, or oversized card radii). High-contrast monochromatic foundations with hair-thin 1px borders (`border-neutral-200 dark:border-neutral-800`).
- **Defensive States:** Every mobile screen explicitly implements 5 visual states: Loading, Populated, Empty, Error, and Offline/Degraded Network.
- **Guard Ergonomics:** High-contrast buttons, single-tap torch toggle, and large color-coded admission banners (Bold Green vs Bold Red) designed for outdoor sunlight legibility.

---

## 33. API and Data Requirements

- **API Standard:** RESTful JSON adhering to OpenAPI 3.1 specifications.
- **Idempotency:** Mutating endpoints (`POST /bookings/hold`, `/payments/orders`, `/access/validate-scan`) strictly require an `Idempotency-Key` header (UUIDv4).
- **Error Standard:** All error responses formatted per RFC 7807 Problem Details schema with explicit machine-readable error codes.

---

## 34. Security and Threat Model

### STRIDE Threat Mitigations:
- **Spoofing (Payment):** Webhook validation calculates HMAC-SHA256 signature directly from raw request body bytes using `hmac.compare_digest()`.
- **Tampering (Booking Concurrency):** PostgreSQL `btree_gist` exclusion constraints prevent overlapping reservations.
- **Repudiation (Gate Admission):** Immutable `access_scan_logs` record guard UUID, gate identifier, precise timestamp, and scanned token.
- **Information Disclosure (Access Passes):** Zero PII or vehicle details encoded in QR passes; tokens are opaque 128-bit CSPRNG references.
- **Denial of Service (Slot Hoarding):** Maximum 2 active concurrent holds per phone number; per-IP rate limiting via AWS WAF.
- **Elevation of Privilege (RBAC):** Scoped JWT claims checked at FastAPI dependency middleware level.

---

## 35. Privacy and Data Protection

- **Statutory Framework:** Digital Personal Data Protection Act (DPDPA), 2023.
- **Data Minimization:** No collection of Aadhaar numbers, driving licenses, or bank account passwords. Only phone number, name, vehicle plate, and property tax receipt collected.
- **Storage Limitation & Purge:** Search geolocation coordinates purged after 180 days; offline basement gate admission photos permanently purged from S3 within **7 days** of successful reconciliation.
- **Designated Grievance Officer:** Resident Grievance Officer appointed with published email (`grievance@gadispot.in`) and 48-hour acknowledgment SLA.

---

## 36. Legal and External Dependencies

1. **Payment Aggregator Merchant Underwriting:** Dual application submitted to Razorpay and Cashfree; launch gated on formal written underwriting approval.
2. **Merchant of Record Structure:** Pilot disbursements operate as scheduled batch bank transfers from platform corporate account under prior bank agreement.
3. **Indirect Tax (GST):** 18% GST collected on platform commission and driver convenience fees; formal written tax opinion commissioned regarding GST Section 9(5) vs Section 9(1).
4. **Telecom DLT Registration:** Enterprise entity and SMS header filing with Indian telecom operators under TRAI regulations.
5. **Municipal Parking Regulations:** Pilot restricted to white-plate private vehicles on private freehold land; municipal legal memorandum commissioned for Bengaluru BBMP jurisdiction.

---

## 37. Business Model and Financial Assumptions

### Reconciled Unit Economics (2-Hour Stay at ₹40/hr):
```
1. CUSTOMER INFLOW (COLLECTED VIA UPI)
   Gross Parking Base (2.0 hrs @ ₹40.00/hr):   ₹80.00
   Driver Convenience Fee:                     ₹10.00
   GST on Convenience Fee (18.0% on ₹10.00):    ₹1.80
   -------------------------------------------------
   TOTAL DEBITED FROM DRIVER VIA UPI:          ₹91.80  (9,180 paise)

2. GATEWAY PROCESSING DEDUCTION
   Payment Gateway MDR (2.36% on ₹91.80):       ₹2.17  (absorbed by platform)
   Net Cash Inflow to Gadispot Current Bank:   ₹89.63

3. HOST CHARGES & NET ENTITLEMENT
   Gross Parking Base:                         ₹80.00
   Less: Platform Facilitation Commission (15%):-₹12.00
   Less: GST on Platform Commission (18%):      -₹2.16
   -------------------------------------------------
   NET OWNER ENTITLEMENT (ACCOUNT 2010):        ₹65.84  (6,584 paise)

4. TAX LIABILITIES (REMITTED TO GOVERNMENT)
   GST on Convenience Fee (from driver):        ₹1.80
   GST on Platform Commission (from host):      ₹2.16
   -------------------------------------------------
   TOTAL GST OUTPUT TAX LIABILITY (ACCOUNT 2030):₹3.96  (396 paise)

5. NET PLATFORM OPERATING MARGIN
   Gross Operating Revenues (₹12.00 + ₹10.00):  ₹22.00
   Less: Gateway Processing Expense (MDR):     -₹2.17
   -------------------------------------------------
   NET PLATFORM OPERATING CONTRIBUTION:        ₹19.83  (21.6% Net Take-Rate)

6. CASH FLOW RECONCILIATION INVARIANT
   Driver Paid (₹91.80) = Owner (₹65.84) + Platform (₹19.83) + GST (₹3.96) + MDR (₹2.17)
```

---

## 38. Non-Functional Requirements (NFR)

### Performance:
- Spatial search API latency $\le 500\text{ms}$ at 95th percentile for 3km radius.
- Hold acquisition API latency $\le 300\text{ms}$ under concurrency.
- QR gate validation response $\le 1.5\text{s}$ under standard 4G connectivity.

### Reliability:
- Backend service availability target: 99.9% uptime during pilot.
- Recovery Point Objective (RPO): 0 seconds for committed ledger entries (WAL streaming replication).
- Recovery Time Objective (RTO): $\le 15$ minutes for automated container restart.

### Scalability:
- Pilot sizing: 200 parking bays, 1,000 daily searches, 250 daily bookings.
- Concurrency headroom: Support 50 simultaneous booking hold attempts per second without database connection exhaustion.

---

## 39. Observability and Operations

- **Structured Logging:** JSON-formatted logs with correlation IDs (`x-request-id`) injected at API gateway.
- **Metrics:** Prometheus metrics tracking active holds count, hold-to-booking conversion rate, webhook processing latency, and ledger balance verification execution time.
- **Alerting:** Automated PagerDuty alerts for webhook signature failures (>3 in 5m), ledger imbalance exceptions (immediate P0), and worker queue latency (>10s).

---

## 40. Backup and Disaster Recovery

- **Database Backups:** Daily automated full snapshots via AWS RDS with 30-day retention; continuous WAL archiving providing point-in-time recovery (PITR) to any second within the retention window.
- **Disaster Recovery:** Automated cross-region snapshot replication from AWS Mumbai (`ap-south-1`) to AWS Hyderabad (`ap-south-2`). Bi-annual disaster recovery restore drill.

---

## 41. Acceptance Criteria

Every functional requirement carries explicit, testable binary acceptance criteria:
1. Concurrency exclusion verified via simultaneous multi-worker race tests.
2. Ledger balance verified via trigger exceptions on unbalanced journals.
3. Webhook idempotency verified via redelivered event payloads.
4. QR security verified via token replay attempts.
5. Vehicle compatibility verified via dimensional mismatch submissions.

---

## 42. End-to-End Test Scenarios

### Scenario 1 — Successful Booking and Parking Session
- **Preconditions:** Parking Bay `Bay A-1` is available for `14:00 - 16:00`. Driver Rohan has registered vehicle `KA-01-AB-1234`.
- **Actions:** Driver searches, selects `Bay A-1`, initiates hold, completes UPI payment via Razorpay, arrives at gate at 14:05, guard scans entry QR, driver exits at 15:50, guard scans exit QR.
- **Expected System Behavior:** Hold acquired with 480s countdown; webhook confirms booking; entry token transitions to `CONSUMED`; session marked `COMPLETED`.
- **Database Invariants:** Exactly 1 row in `space_reservations` with status `COMPLETED`; balanced double-entry journals posted.
- **Financial Effects:** Driver debited ₹91.80; Owner credited ₹65.84; Platform margin ₹19.83; GST ₹3.96.
- **Security Checks:** Opaque token validated; guard assignment validated; PII masked.
- **Acceptance Result:** PASS.

### Scenario 2 — Two Drivers Compete for One Slot (Concurrency Collision)
- **Preconditions:** `Bay B-2` available for `10:00 - 12:00`.
- **Actions:** Driver 1 and Driver 2 simultaneously submit `POST /bookings/hold` for `Bay B-2` for `10:00 - 12:00` with identical millisecond timestamps.
- **Expected System Behavior:** PostgreSQL GiST constraint serializes index lock. Driver 1 receives HTTP 201 Created with active hold; Driver 2 catches `ExclusionViolation (23P01)` and receives HTTP 409 Conflict.
- **Database Invariants:** Exactly 1 active hold row exists in `space_reservations`.
- **Acceptance Result:** PASS.

### Scenario 3 — Hold Expires Before Payment
- **Preconditions:** Driver initiates hold; 480 seconds elapse without payment.
- **Actions:** Background sweeper executes. Competing driver searches for bay.
- **Expected System Behavior:** Sweeper transitions hold to `EXPIRED_HOLD`; bay appears available in search; competing driver acquires new hold.
- **Database Invariants:** First reservation status is `EXPIRED_HOLD`; second reservation status is `ACTIVE_HOLD`.
- **Acceptance Result:** PASS.

### Scenario 4 — Late Payment Resolution Protocol (LPRP)
- **Preconditions:** Driver A's hold expires; Driver B books the bay; Razorpay delivers late `payment.captured` for Driver A.
- **Actions:** Webhook controller attempts to confirm Driver A's booking.
- **Expected System Behavior:** Database throws `ExclusionViolation (23P01)`. System marks Driver A's reservation `RELEASED_UNFULFILLABLE` and automatically initiates 100% full refund (`REFUND_ELIGIBLE`).
- **Database Invariants:** Driver B's confirmed booking remains untouched; Driver A's refund state machine initialized.
- **Acceptance Result:** PASS.

### Scenario 5 — Duplicate Payment Webhook Ingestion
- **Preconditions:** Webhook for payment `pay_123` processed successfully.
- **Actions:** Razorpay network retries and delivers identical payload 20 seconds later.
- **Expected System Behavior:** Unique constraint on `payment_webhook_events(gateway_name, gateway_event_id)` catches duplicate; controller returns HTTP 200 OK immediately.
- **Database Invariants:** Zero duplicate journal rows; reservation status remains `CONFIRMED`.
- **Acceptance Result:** PASS.

### Scenario 6 — Refund Failure and Escalation
- **Preconditions:** Refund initiated; gateway accepts request (`GATEWAY_ACCEPTED`), but later delivers `refund.failed` webhook due to customer bank account freeze.
- **Actions:** Webhook processed by backend.
- **Expected System Behavior:** Refund status transitions to `REFUND_FAILED`; high-priority task created in operations queue (`SCR-402`) for manual bank transfer intervention.
- **Database Invariants:** Refund status is `REFUND_FAILED`; compensating journal remains pending.
- **Acceptance Result:** PASS.

### Scenario 7 — QR Token Replay Attack
- **Preconditions:** Driver checks in at gate; `ENTRY_TOKEN` transitions to `CONSUMED`.
- **Actions:** Driver shares QR screenshot with friend; friend attempts scan at gate 5 minutes later.
- **Expected System Behavior:** Guard scanner displays bold red alert: "ACCESS REJECTED: QR code already consumed at 14:05:22".
- **Database Invariants:** Audit log inserted in `access_scan_logs` with result `REPLAY_REJECTED`.
- **Acceptance Result:** PASS.

### Scenario 8 — Exit Token Misuse
- **Preconditions:** Driver has not checked in (booking is `CONFIRMED`, not `ACTIVE_SESSION`).
- **Actions:** Driver presents exit pass at departure gate.
- **Expected System Behavior:** Scanner rejects token: "INVALID CREDENTIAL: No active session found for this pass."
- **Database Invariants:** Session remains `CONFIRMED`.
- **Acceptance Result:** PASS.

### Scenario 9 — Guard Underground Offline Fallback
- **Preconditions:** Gate located in deep basement with zero cellular connectivity.
- **Actions:** Guard opens app; app detects offline state; guard enters vehicle plate `KA-01-AB-1234`; matches locally cached shift schedule; captures vehicle photo; confirms manual admission. Guard moves to ground floor 2 hours later.
- **Expected System Behavior:** Admission recorded in encrypted SQLite queue; upon reconnection, app syncs record to backend; backend reconciles admission; S3 lifecycle rule purges photo after 7 days.
- **Database Invariants:** Offline admission row transitions from `PENDING_SYNC` to `RECONCILED`.
- **Acceptance Result:** PASS.

### Scenario 10 — Owner Submits Listing Without Sufficient Legal Proof
- **Preconditions:** Owner submits electricity bill in another person's name without lease agreement.
- **Actions:** Operations staff audits listing in `SCR-401`.
- **Expected System Behavior:** Ops associate clicks "Reject" with reason `NAME_MISMATCH_ON_EVIDENCE`; property transitions to `REJECTED`; spaces remain unsearchable.
- **Database Invariants:** `authorization_status` is `REJECTED`.
- **Acceptance Result:** PASS.

### Scenario 11 — GPRP Arrival Obstruction Recovery
- **Preconditions:** Driver arrives at reserved bay; unauthorized car is parked in the bay.
- **Actions:** Guard taps "Report Space Blocked"; GPRP engine searches alternative bay within 500m; acquires atomic hold; presents offer to driver with 180s timer; driver taps "Accept".
- **Expected System Behavior:** Original booking cancelled; replacement booking confirmed at zero extra driver charge; platform absorbs tariff difference via Account 4020.
- **Database Invariants:** Original booking marked `ARRIVAL_FAILED`; replacement marked `CONFIRMED`.
- **Acceptance Result:** PASS.

### Scenario 12 — Double-Entry Ledger Mathematical Consistency
- **Preconditions:** Test script attempts to post journal entry with ₹9,180 debit to Gateway Transit and ₹9,000 credit to Owner Payable (₹180 imbalance).
- **Actions:** Script executes `UPDATE journal_entries SET posting_status = 'POSTED'`.
- **Expected System Behavior:** Database trigger `trg_verify_journal_balance` raises exception: `Journal entry does not balance! Total Debits: 9180, Total Credits: 9000`. Transaction rolls back.
- **Database Invariants:** Zero unbalanced rows exist in `journal_entries`.
- **Acceptance Result:** PASS.

### Scenario 13 — Owner Batch Payout Disbursement
- **Preconditions:** Host Anand has ₹1,316.80 accumulated earnings from completed bookings. Bank account verified via Penny Drop.
- **Actions:** Scheduled weekly batch payout worker executes on Tuesday.
- **Expected System Behavior:** Worker groups payable balance, dispatches IMPS transfer via corporate banking API, receives transfer UTR, posts balancing journal (Debit Account 2010 / Credit Account 1020).
- **Database Invariants:** Account 2010 balance reduced by ₹1,316.80; payout logged in `payout_records`.
- **Acceptance Result:** PASS.

### Scenario 14 — Unauthorized Guard Access Attempt
- **Preconditions:** Guard Ramesh is assigned to Property A.
- **Actions:** Guard attempts to scan an access pass for Property B.
- **Expected System Behavior:** Backend checks `guard_assignments`; detects property mismatch; rejects scan with HTTP 403 Forbidden: "Guard not assigned to this property."
- **Database Invariants:** Unauthorized attempt logged in `security_alerts`.
- **Acceptance Result:** PASS.

### Scenario 15 — Property Suspension Following Dispute
- **Preconditions:** An approved property receives multiple complaints for host hostility and blocked driveway.
- **Actions:** Operations Lead suspends property in `SCR-401`.
- **Expected System Behavior:** Property status transitions to `SUSPENDED`; all future unbooked intervals immediately withdrawn from search; existing confirmed bookings flagged for GPRP rerouting.
- **Database Invariants:** `properties.authorization_status = 'SUSPENDED'`.
- **Acceptance Result:** PASS.

---

## 43. Requirements Traceability Matrix

Every functional requirement is mapped to its architecture component, database domain, test scenario, and external dependency in [docs/product/REQUIREMENTS_TRACEABILITY.md](docs/product/REQUIREMENTS_TRACEABILITY.md).

---

## 44. Risks and Mitigations

| Risk ID | Risk Description | Severity | Likelihood | Architectural & Operational Mitigation |
|---|---|---|---|---|
| **RSK-001** | Payment Aggregator delays merchant onboarding or Route approval. | High | Medium | Dual application strategy (Razorpay + Cashfree); Phase 1 batch bank payouts from corporate current account. |
| **RSK-002** | Society committees (RWA) contest member parking rentals. | High | Medium | Strict onboarding rule: Society NOC mandatory before apartment bays are approved; focus pilot on independent driveways. |
| **RSK-003** | Subterranean basements prevent guard online validation. | Medium | High | Controlled Manual Exception Protocol with local cached shift schedule, photo evidence, and 7-day automated purge. |
| **RSK-004** | Telecom SMS OTP delivery latency or delivery drops. | Medium | Medium | Firebase Phone Auth multi-provider carrier routing; fallback WhatsApp verification sidecar evaluated for Phase 2. |
| **RSK-005** | Double-booking race conditions during flash congestion. | Critical | Low | PostgreSQL `btree_gist` exclusion constraints enforce absolute mathematical serialization at the engine level. |

---

## 45. Assumptions and Constraints

- **Mobile Handset Baseline:** Android 10+ (API level 29) and iOS 15+.
- **Payment Method:** Domestic Indian UPI applications (PhonePe, GPay, Paytm, BHIM) and domestic debit/credit cards. International cards disabled for MVP.
- **Vehicle Scope:** White-plate private passenger vehicles only (2-Wheelers, Hatchbacks, Sedans, SUVs). Commercial yellow-plate vehicles excluded.
- **Hardware Agnostic:** Zero dependency on barrier gate relays, ANPR cameras, or IoT ground sensors for MVP.

---

## 46. Open Questions and Decision Gates

All 65 decision items are tracked with explicit ownership, statuses, and target dates in [docs/product/OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md):
- **15 Decided / Resolved:** Formally signed baselines.
- **33 Proposed Defaults:** Working architectural defaults pending founder commercial signoff.
- **12 External Dependencies:** Gated on third-party payment aggregator underwriting and telecom DLT approvals.
- **5 Legal Reviews:** Gated on formal written legal/tax memorandums (GST Section 9(5), Municipal Trade Licensing).

---

## 47. Implementation Readiness Criteria

Evaluation against the six non-negotiable Engineering Readiness Gates:
- **Gate A (Product Completeness):** **PASS** — Unambiguous scope, roles, workflows, and functional requirements.
- **Gate B (Booking Correctness):** **PASS** — Universal 480s hold, GiST exclusion locks, two-tier expiration engine, LPRP protocol.
- **Gate C (Financial Correctness):** **PASS WITH QUALIFICATIONS** — Balanced double-entry ledger triggers and durable idempotency verified; commercial pilot disbursements gated on payment aggregator underwriting.
- **Gate D (Security & Access):** **PASS** — Cryptographic QR separation, 128-bit CSPRNG tokens, bounded offline fallback, 7-day photo purge rule.
- **Gate E (Legal & External Rails):** **PASS WITH QUALIFICATIONS** — Unbacked escrow claims removed; pilot launch gated on legal tax memo and telecom DLT registration.
- **Gate F (Engineering Traceability):** **PASS** — All 16 FR families mapped to acceptance criteria, DDL invariants, and 20 high-risk test scenarios.

---

## 48. Glossary

1. **Active Hold:** A temporary 480-second reservation during checkout preventing competing bookings via PostgreSQL GiST exclusion lock.
2. **Access Pass:** An in-app presentation credential containing an opaque high-entropy token presented to gate guards.
3. **BBMP:** Bruhat Bengaluru Mahanagara Palike, the municipal administrative body governing Bengaluru.
4. **CSPRNG:** Cryptographically Secure Pseudo-Random Number Generator, utilized to mint 128-bit access tokens.
5. **DLT:** Distributed Ledger Technology, statutory Indian telecom framework for SMS commercial communication registration.
6. **DPDPA:** Digital Personal Data Protection Act, 2023, India's statutory personal data protection framework.
7. **Double-Entry Bookkeeping:** Accounting methodology where every financial transaction posts equal debit and credit amounts.
8. **Entry Token (`ENTRY_TOKEN`):** Single-use access credential valid from $t_{\text{start}}-15\text{m}$ to $t_{\text{start}}+30\text{m}$.
9. **Exit Token (`EXIT_TOKEN`):** Access credential valid through scheduled departure plus 15 minutes, dynamically updated on extension.
10. **GiST:** Generalized Search Tree, PostgreSQL indexing structure supporting temporal range exclusion constraints.
11. **GPRP:** Guaranteed Parking Recovery Protocol, an atomic 8-step alternative space reallocation and refund workflow.
12. **Idempotency Key:** Unique UUIDv4 transmitted in HTTP headers to prevent duplicate execution of mutating API requests.
13. **Journal Entry:** Header record representing a balanced financial transaction in the general ledger.
14. **Journal Line:** Individual debit or credit record bound to a specific chart of accounts code.
15. **LPRP:** Late Payment Resolution Protocol, handling payments arriving after hold expiration without double-booking.
16. **MDR:** Merchant Discount Rate, processing fee deducted by payment aggregators on electronic transactions.
17. **MoR:** Merchant of Record, the legal entity authorized to process payments and assume customer liability.
18. **MSAI:** Multi-Source Availability Intelligence, synthesizing 7 operational signals into an availability state.
19. **NPCI:** National Payments Corporation of India, umbrella organization operating the UPI network.
20. **Opaque Token:** High-entropy hexadecimal token containing zero embedded customer PII or database IDs.
21. **Outbox Pattern:** Transactional database table storing downstream integration events within the same ACID transaction.
22. **Overstay:** Vehicle remaining in a parking bay beyond the 15-minute departure grace period.
23. **Penny-Drop Verification:** Automated API depositing ₹1.00 into a host's bank account to verify account holder name.
24. **PostGIS:** Spatial database extender for PostgreSQL providing geographic radius search and polygon queries.
25. **Razorpay Route:** Payment aggregator marketplace split product facilitating programmatic linked account transfers.
26. **RBAC:** Role-Based Access Control, restricting API endpoints based on authenticated JWT role claims.
27. **STRIDE:** Security threat modeling methodology evaluating Spoofing, Tampering, Repudiation, Information Disclosure, DoS, and Elevation of Privilege.
28. **Take-Rate:** Net percentage of gross booking value retained by the platform after owner payout, GST, and gateway fees.
29. **UPI Intent:** Mobile payment flow directly launching installed UPI applications on the customer's smartphone.
30. **WGS 84:** World Geodetic System 1984, standard coordinate reference frame (EPSG:4326) used for spatial points.

---

## 49. Revision History Log

Comprehensive historical evolution of the Gadispot Product Requirements Document:
- **v0.1.0 (2026-10-15):** Conceptual framework.
- **v1.0.0 (2026-10-31):** Initial 45-section draft.
- **v2.0.0 (2026-10-31):** Modular monolith, PostgreSQL GiST locks, unified `space_reservations` model, double-entry ledger architecture.
- **v2.1.0 (2026-10-31):** Concurrency locking, multi-stage refund states, 128-bit CSPRNG entropy.
- **v2.2.0 (2026-10-31):** Universal 480-second hold standardization, reconciled unit economics (₹19.83 margin / ₹65.84 host entitlement), durable database webhook idempotency, automated 7-day photo purge rule.
- **v2.3.0 (2026-10-31):** Canonical 6-stage refund lifecycle, database triggers and row-locking on `journal_lines`, eradication of 5-min/04:59 checkout references, removal of machine-specific local paths, stable FR-xxx IDs, 15 comprehensive end-to-end scenarios, honest readiness gates, and Gadispot brand harmonization.

---

## 50. References and Related Documents

### Master Architecture Blueprints:
* [High-Level System Architecture Specification](docs/technical/ARCHITECTURE.md)
* [Comprehensive Database & DDL Specification](docs/technical/DATABASE_DESIGN.md)
* [Payment Engine & Financial Ledger Specification](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md)
* [Booking & Availability Engine Technical Specification](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md)
* [QR Access & Verification Architecture](docs/technical/QR_ACCESS_DESIGN.md)
* [Comprehensive REST API Specification](docs/technical/API_SPECIFICATION.md)

### Product Specifications & Governance:
* [Comprehensive User Flow & Journey Diagrams](docs/product/USER_FLOWS.md)
* [Mobile Screen Specifications & UX Requirements](docs/product/SCREEN_REQUIREMENTS.md)
* [Security Threat Model & Privacy Impact Review](docs/product/SECURITY_AND_PRIVACY_REVIEW.md)
* [Business Assumptions, Economics & Sensitivity Analysis](docs/product/BUSINESS_ASSUMPTIONS.md)
* [Unresolved Decisions & Decision Register (65 Items)](docs/product/OPEN_QUESTIONS.md)
* [Open-Source Integrations & Technology Evaluation](docs/product/OPEN_SOURCE_INTEGRATIONS.md)
* [Architectural Decision Log (ADR-001..010)](docs/product/DECISION_LOG.md)
* [Requirements Traceability Matrix (RTM)](docs/product/REQUIREMENTS_TRACEABILITY.md)

### Quality Assurance & Audit Reports:
* [Comprehensive Quality Assurance & Test Strategy](docs/quality/TEST_STRATEGY.md)
* [Specification V2.3 Final Audit Report](docs/audits/PRD_V2_3_FINAL_AUDIT.md)
* [Specification V2.3 Comprehensive Changelog](docs/audits/PRD_V2_3_CHANGELOG.md)
* [Historical V2.2 Final Audit](docs/audits/PRD_FINAL_AUDIT.md)
* [Historical Technical Audit](docs/audits/TECHNICAL_AUDIT.md)
