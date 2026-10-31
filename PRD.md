# Master Product Requirements Document (PRD)
# SmartPark Exchange

> **Document Title:** SmartPark Exchange — Master Product Requirements Document  
> **Document Identifier:** PRD-SPX-2026-V2.2-REVIEW  
> **Target Market:** India (Urban Metros — Bengaluru Pilot)  
> **Target Platforms:** Mobile-Only (Android & iOS via single Flutter Codebase)  
> **Backend Architecture:** In-Process Modular Monolith (Python / FastAPI / PostgreSQL 16 / Redis 7.0+)  
> **Authoring Team:** Multidisciplinary Senior Product, Engineering & Security Architecture Group  
> **Status:** Architectural Design Review — Conditional Approval (Implementation Gates Outstanding)  

---

## 1. Document Control and Version History

### 1.1 Revision History

| Version | Release Date | Primary Authors / Roles | Summary of Major Changes | Approval Status |
|---|---|---|---|---|
| **v0.1.0** | 2026-10-15 | Principal PM, Lead Architect | Initial product framing, discovery, and high-level market problem definition. | Conceptual Draft |
| **v1.0.0** | 2026-10-31 | Multi-disciplinary Team | Comprehensive initial PRD across 45 sections. | Initial Draft (Found Defects) |
| **v2.0.0** | 2026-10-31 | Unified Senior Architecture Team | Comprehensive Technical Re-engineering: Unified data model, GiST locks, LPRP, double-entry ledger, QR separation. | Re-engineered Draft |
| **v2.1.0** | 2026-10-31 | Unified Senior Architecture Team | Targeted Architectural Corrections: Concurrency locks, multi-stage refund states, 128-bit CSPRNG entropy. | Review Draft |
| **v2.2.0** | 2026-10-31 | Unified Senior Architecture Team | **Comprehensive Precision Refinement & Final Audit Alignment:**<br>1. Universal checkout hold duration standardization (strictly 480 seconds / 8 minutes across all sections).<br>2. De-escalated 'instant refund' claims to 6-stage asynchronous refund lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`).<br>3. Durable database-level payment idempotency (`payment_webhook_events`) and transactional outbox.<br>4. Reconciled financial arithmetic (platform absorbs MDR; exact ₹15.87 net take-rate & ₹68.00 owner payable; 12 balanced journal templates).<br>5. Removed unbacked escrow claims; established MoR status and scheduled batch bank transfers during pilot.<br>6. Eradicated residual scalar vehicle compatibility SQL in §18.1.<br>7. Standardized search radius to 3 km default (5 km max configurable).<br>8. Two-tier hold expiration engine transaction semantics and locking.<br>9. GPRP 8-step atomic order of operations with 180s driver decision timeout.<br>10. Offline basement manual exception privacy controls (automated 7-day photo purge rule).<br>11. Formal entry/exit credential state machine with extension and overstay transitions.<br>12. Downgraded unverified legal, tax, and provider claims, removing 'zero web attack surface' and '₹0 CapEx'.<br>13. Complete 65-question decision register and enumerated 20 high-risk test scenarios. | **Conditional Approval (Sprint 0/1)** |

### 1.2 Formal Founder Decisions (V2.2 Baselines)

| Decision ID | Operational Domain | Founder Approved Value | Implementation Guidance |
|---|---|---|---|
| **Q1 / OQ-PAY-001** | Payment Provider Strategy | **Dual Application (Razorpay Primary, Cashfree Secondary)** | Maintain runtime-swappable `PaymentGatewayPort` abstraction. |
| **Q2 / OQ-OPS-004** | Alternative Space Failure | **100% Full Refund to Original Instrument** | Automatic fallback to `REFUND_PENDING` if GPRP alternative space cannot be secured or is declined. |
| **Q3 / OQ-TECH-010** | Offline Guard Admission | **Controlled Manual Exception Protocol** | Offline entry allowed with plate match against cached schedule, mandatory photo proof, and async sync. |
| **Q4 / OQ-BIZ-003** | Maximum Booking Duration | **Configurable by Property (Default 24 Hours)** | Space owners can set maximum continuous hours up to 24h. Multi-day leases deferred to Phase 2. |
| **Q5 / OQ-PAY-002** | MVP Marketplace Payouts | **Scheduled Batch Bank Transfers from Corporate Account** | Direct IMPS payouts under prior bank agreement and strict owner KYC (PAN + Penny Drop). |

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
| **Privacy & Data Protection Specialist** | Legal & DPDPA Compliance Counsel | 2026-10-31 | **CONDITIONAL (Subject to legal terms)** |
| **QA & Test Strategy Director** | QA Automation & Test Lead | 2026-10-31 | **APPROVED FOR SPRINT 0/1** |

---

## 2. Executive Summary

**SmartPark Exchange** is an authoritative, mobile-first two-sided parking marketplace engineered specifically for the hyper-dense urban mobility landscape in India. It unlocks underutilized, dormant private residential driveways, gated society visitor bays, commercial office basements, and authorized private parking lots, transforming them into a reliable network of pre-bookable, time-slotted parking inventory.

Unlike passive directories that display unverified locations or crowdsourced approximations, SmartPark operates as a **deterministic reservation exchange**. Every reservation is guaranteed by:
1. **Multi-Source Availability Intelligence (MSAI):** Synthesizing 7 operational signals to eliminate speculative inventory and double-bookings.
2. **PostgreSQL GiST Concurrency Locks:** Mathematical exclusion of overlapping time-window holds directly at the database engine level via `EXCLUDE USING gist`.
3. **Late Payment Resolution Protocol (LPRP):** Automated handling of payments arriving after 480-second hold expirations, ensuring zero double-bookings and a deterministic multi-stage refund protocol when slots are claimed by competing drivers.
4. **Authorization-Aware Inventory:** Strictly prohibiting property publication until legal right-of-use evidence (freehold title deeds, tenancy sublet clauses, or society NOCs) is validated.
5. **Hardware-Agnostic Gate Verification:** Secure, opaque, one-time access QR tokens scanned by existing on-premise security guards via a lightweight mobile app, minimizing gate infrastructure CapEx by utilizing existing guard smartphones.
6. **Controlled Offline Guard Fallback:** A realistic, audited manual fallback protocol for underground basements with zero cellular connectivity, governed by automated 7-day photo retention limits.
7. **True Double-Entry General Ledger:** An immutable, append-only financial accounting engine with standard Chart of Accounts, balanced debits and credits ($\sum \text{Debits} = \sum \text{Credits}$), and compliant weekly payout mechanisms.
6. **Controlled Offline Guard Fallback:** A realistic, audited manual fallback protocol for underground basements with zero cellular connectivity.
7. **True Double-Entry General Ledger:** An immutable, append-only financial accounting engine with standard Chart of Accounts, balanced debits and credits ($\sum \text{Debits} = \sum \text{Credits}$), and compliant weekly payout mechanisms.

### Core Platform Decision
SmartPark is strictly **MOBILE-ONLY**. In the MVP, all customer-facing, space-owner, and gate-guard interactions are delivered through a single cross-platform **Flutter mobile application** for **Android** and **iOS** featuring dynamic role-based shells. There is **no public consumer website**, **no desktop booking portal**, and **no public web admin dashboard**. Internal platform operations workflows are managed via restricted mobile views and secure backend scripts.

---

## 3. Product Vision

### 3.1 The Central Product Promise
> **"Find parking, reserve it, pay securely, access it reliably, and receive a clear resolution if something goes wrong."**

SmartPark rejects the practice of making unconditional commercial guarantees that cannot be operationally fulfilled. Instead, dependability is achieved through strict contract enforcement, pessimistic availability logic, and a structured recovery protocol.

### 3.2 Five Solved Marketplace Problems
1. **Discovery:** Precision PostGIS spatial search filtering available bays by physical vehicle dimensions within a 3km radius.
2. **Authorization:** Rigorous legal right-of-use vetting before a property can publish bookable inventory.
3. **Availability:** Mathematical concurrency exclusion eliminating double-bookings and phantom availability.
4. **Fulfillment:** Sub-second gate validation via single-use, non-guessable QR tokens scanned on guard smartphones.
5. **Recovery:** The Guaranteed Parking Recovery Protocol (GPRP), providing an atomic 8-step alternative space reallocation within a 500m search boundary, or a deterministic refund protocol if an alternative cannot be secured.

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

## 5. Target Users & Stakeholders

SmartPark serves four discrete operational user groups in the Indian urban ecosystem:
1. **Daily Urban Commuters (Drivers):** Office workers, shoppers, and event attendees seeking dependable short-term parking (30 minutes to 24 hours).
2. **Private Residential Owners (Hosts):** Homeowners with empty driveways or gated villa bays seeking passive income with zero security risk.
3. **Commercial Facility Managers:** Operators of commercial office basements, malls, and banquet halls monetizing off-peak excess bay capacity.
4. **On-Premise Security Guards & Attendants:** Gate personnel responsible for physical access control, visitor validation, and vehicle admitting.

---

## 6. User Personas

```
+--------------------------------------------------------------------------------------------------+
|                                  USER PERSONA MATRIX                                             |
+---------------------+-------------------------------+--------------------------------------------+
| Persona             | Profile & Demographics       | Primary Motivations & Core Pain Points    |
+---------------------+-------------------------------+--------------------------------------------+
| **Rohan (Driver)**  | • 31-year-old tech worker     | • Needs guaranteed parking near meetings.  |
| Daily Urban Commuter| • Drives mid-size SUV (Creta) | • Frustrated by 20-min parking hunts.      |
|                     | • High UPI usage (GPay/PhonePe)| • Wants transparent pricing & instant QR. |
+---------------------+-------------------------------+--------------------------------------------+
| **Mrs. Rao (Owner)**| • 58-year-old homeowner       | • Has 2 empty gated driveway slots daily.  |
| Residential Landlord| • Independent villa in Koram. | • Wants extra monthly passive income.      |
|                     | • Values safety & peace of mind| • Terrified of unauthorized trespassers.  |
+---------------------+-------------------------------+--------------------------------------------+
| **Vikram (Manager)**| • 42-year-old facility manager| • 35 commercial basement bays empty weekends|
| Commercial Operator | • Manages multi-tenant building| • Needs automated accounting & ledgering. |
|                     | • Tech-comfortable            | • Requires strict guard access controls.   |
+---------------------+-------------------------------+--------------------------------------------+
| **Bahadur (Guard)** | • 35-year-old security guard  | • Manages residential / commercial gate.   |
| Gate Attendant      | • Uses budget Android phone   | • Needs dead-simple, 1-tap QR scanning.    |
|                     | • Hindi/Kannada speaker       | • Cannot deal with complex UI or slow apps.|
+---------------------+-------------------------------+--------------------------------------------+
```

---

## 7. Goals and Non-Goals

### 7.1 Measurable Product Goals (MVP)
1. **Zero Double-Bookings:** 100% transactional exclusion of overlapping bookings on the same physical space via PostgreSQL exclusion constraints (`EXCLUDE USING gist`).
2. **Sub-300ms Search Latency:** Enable drivers to discover verified available spaces within a 5km radius in less than 300ms (P95).
3. **Under 3-Second Gate Clearance:** Security guards validate a booking QR code and open the gate in less than 3 seconds via native camera barcode scanning.
4. **98%+ Successful Arrival Rate:** Over 98% of confirmed reservations result in smooth, unobstructed physical parking sessions.
5. **100% Authoritative Payment Reconciliation:** Zero bookings confirmed without authoritative backend cryptographic verification of Razorpay webhook signatures or server-to-server polling proofs.
6. **Automated Recovery Triggering:** 100% of reported arrival failures initiate the Guaranteed Parking Recovery Protocol (GPRP) within 15 seconds.

### 7.2 Explicit Non-Goals (Strictly Excluded from MVP)
1. **No Public Web Portal:** No customer-facing desktop or web application. SmartPark is 100% mobile-native (Flutter).
2. **No Mandatory IoT Hardware or Boom Barriers:** No requirements for owners to install smart barrier gates, magnetic loop detectors, or ultrasonic bay sensors. Verification is hardware-agnostic via guards and mobile devices.
3. **No Automatic Number Plate Recognition (ANPR):** No deployment of computer vision or edge camera hardware for license plate recognition in MVP.
4. **No Proprietary Digital Wallet or Escrow Holding:** SmartPark will not issue stored-value balances or act as an unlicensed payment intermediary. All monetary flows utilize RBI-compliant licensed payment aggregators.
5. **No Speculative Dynamic Pricing Surges:** Rates are fixed explicitly by property owners (hourly base rates) with predictable rules. No black-box machine-learning pricing surges in the MVP.
6. **No Monthly Long-Term Lease Contracts:** Focus is exclusively on hourly, short-duration parking (1 to 24 hours). Monthly subscriptions and corporate fleet accounts are deferred to P2.

---

## 8. Product Scope & Functional Boundary

```
+---------------------------------------------------------------------------------------------------+
|                                  MVP FUNCTIONAL BOUNDARY                                          |
+------------------------------------+--------------------------------------------------------------+
| IN SCOPE (Mandatory P0 MVP)        | OUT OF SCOPE (Deferred to P1 / P2)                           |
+------------------------------------+--------------------------------------------------------------+
| • Single Flutter App (iOS/Android) | • Desktop customer booking web portal                        |
| • Firebase Phone Auth (SMS OTP)    | • ANPR edge camera gate hardware                             |
| • Vehicle Management (2W / 4W)     | • Automated boom barriers / IoT floor sensors                |
| • PostGIS Proximity Search (3km)   | • Dynamic surge pricing machine learning models              |
| • Interval-Aware Holds (5-min TTL) | • EV charging session electrical billing                     |
| • PostgreSQL GiST Concurrency Lock | • Monthly subscription passes / Corporate fleet billing      |
| • Razorpay UPI Intent & Dynamic QR | • Multi-city expansion outside Bengaluru pilot               |
| • Raw HMAC Webhook Verifier        | • Proprietary stored-value consumer wallet balances          |
| • Opaque Single-Use Access QR      | • Automated OCR parsing of property deeds                    |
| • Guard Mobile Camera Scanner      | • Multi-entry / multi-exit commuter passes                   |
| • Controlled Offline Gate Fallback |                                                              |
| • Basic GPRP 500m Proximity Search |                                                              |
| • Double-Entry Append-Only Ledger  |                                                              |
| • Weekly Payout Batch Transfers    |                                                              |
| • Property Authorization Audit     |                                                              |
| • FCM Transactional Push Alerts    |                                                              |
+------------------------------------+--------------------------------------------------------------+
```

---

## 9. Mobile-Only Product Strategy

### 9.1 Strategic Rationale
1. **Context of Use:** Drivers search and book parking from their smartphones while in transit. Guards operate physically at gates where desktop workstations are completely absent. Owners manage availability and review check-ins on mobile devices.
2. **Hardware Capabilities:** The core experience relies on hardware sensors: GPS/Geolocation for proximity search, high-resolution Camera for guard QR scanning, and native Push Notifications (FCM) for gate alerts.
3. **Single Cross-Platform Codebase:** Flutter provides 60fps native performance across Android and iOS while sharing 100% of the business logic, state management, and API client networking code.
4. **Targeted Mobile-First API Boundary:** Eliminating public browser booking portals removes browser-specific XSS and iframe clickjacking vulnerabilities, directing all traffic through authenticated, rate-limited mobile API gateways.

---

## 10. Role and Permission Model (RBAC)

SmartPark enforces strict Role-Based Access Control (RBAC) combined with Object-Level Authorization:

| Capability / API Operation | Driver | Space Owner | Security Guard | Platform Ops |
|---|---|---|---|---|
| Register / Authenticate via Phone OTP | ✅ | ✅ | ✅ | ✅ |
| Add / Manage Personal Vehicles | ✅ | ❌ | ❌ | ❌ |
| Search & Discover Parking Inventory | ✅ | ✅ | ❌ | ✅ |
| Create Booking Hold & Initiate Payment | ✅ | ❌ | ❌ | ❌ |
| View Issued Access QR Token | ✅ (Own) | ❌ | ❌ | ✅ (Audit) |
| Cancel Booking (Per Policy) | ✅ (Own) | ❌ | ❌ | ✅ (Override)|
| Register Property & Define Parking Bays | ❌ | ✅ | ❌ | ❌ |
| Upload Legal Authorization Documents | ❌ | ✅ | ❌ | ❌ |
| Set Availability Schedules & Hourly Pricing | ❌ | ✅ (Own) | ❌ | ❌ |
| Assign Security Guards to Property | ❌ | ✅ (Own) | ❌ | ❌ |
| View Property Revenue & Payout Ledger | ❌ | ✅ (Own) | ❌ | ✅ (All) |
| Scan & Authoritatively Validate Access QR | ❌ | ❌ | ✅ (Assigned) | ✅ |
| Record Physical Vehicle Entry & Exit | ❌ | ❌ | ✅ (Assigned) | ❌ |
| Report Space Blocked / Arrival Incident | ✅ (Own) | ✅ (Own) | ✅ (Assigned) | ✅ |
| Review & Approve Property Authorization Proof | ❌ | ❌ | ❌ | ✅ |
| Trigger Manual Emergency Refund | ❌ | ❌ | ❌ | ✅ |
| Suspend Malicious Listing or User Account | ❌ | ❌ | ❌ | ✅ |

---

## 11. User Journeys & End-to-End Workflows

All user flows adhere to the re-engineered architectural specifications documented in [`docs/product/USER_FLOWS.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/USER_FLOWS.md):
- **Journey 1: Driver Search-to-Completion:** Proximity search -> 5-min interval hold -> UPI checkout -> Late Payment Resolution Protocol -> Opaque Access QR -> Guard scan check-in -> Departure -> Rating.
- **Journey 2: Owner Onboarding:** Property registration -> Precise geo-pinning -> Tiered document proof upload -> Ops human audit -> Schedule/pricing activation.
- **Journey 3: Guard Verification:** Camera barcode scan -> Online DB validation -> Admit vehicle -> Controlled offline manual fallback in basements -> Exit logging.
- **Journey 4: Failure Recovery (GPRP):** Bay obstruction report -> 500m proximity search -> Alternative bay offer -> Driver acceptance / 100% automated refund fallback.

---

## 12. Screen Inventory & UX Specifications

The Flutter application implements 20 core mobile screens documented in [`docs/product/SCREEN_REQUIREMENTS.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/SCREEN_REQUIREMENTS.md):
- **Driver Views:** `SCR-101` Explore Map, `SCR-102` Space Details, `SCR-103` Booking Review, `SCR-104` Access Pass, `SCR-105` Active Session, `SCR-106` Session Rating.
- **Owner Views:** `SCR-201` Operations Dashboard, `SCR-202` Property Setup & Bay Scaffolding, `SCR-203` Operating Hours & Pricing, `SCR-204` Earnings & Payouts.
- **Guard Views:** `SCR-301` Camera Viewfinder, `SCR-302` Admit/Deny Result Modal, `SCR-303` Shift Schedule (Offline Cache), `SCR-304` Incident Form.
- **Operations Views:** `SCR-401` Property Legal Review Queue, `SCR-402` Incident Triage & Dispute Override.

---

## 13. Authoritative Operational Policy Table

To eliminate cross-document contradictions, this table serves as the **sole authoritative reference** for operational rules across SmartPark Exchange.

| Policy Code | Operational Domain | Rule Definition | Default Baseline Value | Configurability | Enforcement Mechanism |
|---|---|---|---|---|---|
| **POL-DUR-01** | Booking Duration | Minimum continuous reservation duration | **30 Minutes** | Global Config | API Validation on `/bookings/hold` |
| **POL-DUR-02** | Booking Duration | Maximum continuous reservation duration | **24 Hours (Configurable by property)** | Property Config | API Validation on `/bookings/hold` |
| **POL-DUR-03** | Advance Window | Maximum future advance booking window | **7 Days** | Global Config | API Validation on search & hold |
| **POL-BUF-01** | Turnover Buffer | Mandatory buffer between consecutive bookings | **15 Minutes** | Property Config | MSAI Engine query filter |
| **POL-HLD-01** | Checkout Hold | Temporary reservation lifespan during checkout | **480 Seconds (8 Minutes)** | Global Config | PostgreSQL Two-Tier Expiration + Redis UI Timer |
| **POL-ARR-01** | Early Arrival | Permitted early arrival window before start time | **15 Minutes Prior** | Global Config | Guard Scan API validation |
| **POL-ARR-02** | Late Arrival | Grace period before booking transitions to NO-SHOW | **30 Minutes Past Start** | Global Config | Automated Background Worker |
| **POL-DEP-01** | Departure Grace | Grace period to exit after scheduled end time | **15 Minutes Past End** | Global Config | Guard Exit Scan API validation |
| **POL-OST-01** | Overstay Billing | Penalty rate applied when exceeding departure grace | **1.5x Base Hourly Rate** | Global Config | Computed in 30-min incremental blocks |
| **POL-CAN-01** | Free Cancellation| Full refund window (net of gateway fee) | **> 2 Hours Before Start** | Global Config | Automated Cancellation Evaluator |
| **POL-CAN-02** | Partial Refund | 50% refund window | **30 Minutes to 2 Hours Before Start** | Global Config | Automated Cancellation Evaluator |
| **POL-CAN-03** | Non-Refundable | Zero refund window (Host retains full earnings) | **< 30 Minutes Before Start** | Global Config | Automated Cancellation Evaluator |
| **POL-RAD-01** | Search Radius | Default geographic discovery radius | **3 Kilometers (Expandable to 5 km)** | User Config | PostGIS `ST_DWithin` spatial filter |
| **POL-GPR-01** | Recovery Radius | Maximum search distance for GPRP alternative bay | **500 Meters Walking** | Global Config | GPRP PostGIS spatial query |
| **POL-GPR-02** | Price Subsidy | Maximum platform-subsidized price difference | **Up to ₹100.00 Total** | Business Config | GPRP Transfer Accounting Engine |
| **POL-POT-01** | Owner Settlement| Minimum accumulated balance required for payout | **₹500.00 Net Payable** | Global Config | Weekly Payout Batch Engine |
| **POL-POT-02** | Settlement Day | Day of week when batch disbursements execute | **Tuesdays 02:00 IST** | Global Config | Scheduled Cron Worker |


---

## 14. Authentication and OTP

### 14.1 AUTH-001: Mobile Phone Authentication Lifecycle
SmartPark implements passwordless mobile phone authentication as the primary identity mechanism.
- **Phone Number Format:** E.164 standard format with `+91` prefix for India (e.g., `+919876543210`).
- **Client OTP Verification:** Handled natively on the Flutter handset using **Firebase Phone Authentication** SDK. Firebase leverages native Android Play Integrity APIs and iOS APNs remote notifications to perform automated SMS retrieval and bot detection.
- **Authoritative Backend Token Verification:**
  1. The Flutter mobile app NEVER sends an OTP to the backend. The app verifies the OTP directly with Firebase and obtains an ephemeral Firebase ID Token (JWT).
  2. The mobile app submits the ID token to the FastAPI backend via `POST /api/v1/auth/session`.
  3. The backend executes `firebase_admin.auth.verify_id_token(id_token)`:
     - Validates cryptographic signature against Google's public x509 certificates.
     - Confirms token expiration (`exp > now()`).
     - Validates project audience (`aud == FIREBASE_PROJECT_ID`).
     - Extracts verified phone number string.
  4. The backend queries `users` table:
     - If phone exists, retrieves profile and active roles.
     - If phone is new, inserts new `User` record with default role `DRIVER`.
  5. Backend mints an internal SmartPark Bearer Access Token (JWT, 60-minute TTL) and Refresh Token (UUIDv4, 30-day TTL stored in secure Redis cache).
  6. The client stores the internal tokens in `flutter_secure_storage` (Android KeyStore / iOS Keychain).

### 14.2 AUTH-002: Abuse Prevention and Rate Limiting
- **Phone Rate Limiting:** Maximum 3 OTP requests per phone number within any 15-minute sliding window. Exceeding triggers HTTP 429 Too Many Requests.
- **Resend Cooldown:** Mandatory 60-second cooldown timer enforced on both client UI and backend between consecutive OTP dispatches.
- **Plaintext OTP Prohibition:** Under zero circumstances does the SmartPark database or API generate, transmit, or store plaintext SMS OTP codes.

### 14.3 AUTH-003: Staff Operations Two-Factor Authentication (TOTP)
- Privileged operations and administrative personnel accessing legal document audits, dispute overrides, or payout releases must provide an RFC 6238 Time-Based One-Time Password (TOTP) verified via **PyOTP**.
- PyOTP is utilized exclusively for internal 2FA authenticator apps (Google Authenticator / Authy), **NOT** for customer SMS delivery.

---

## 15. Property Onboarding

### 15.1 PROP-001: Property Profile & Geo-Location Anchoring
- **Feature ID:** `PROP-001`
- **Objective:** Enable property owners and managers to register real estate assets with geographic coordinates.
- **Data Attributes Required:** Property Name, Address, City, Pincode, Property Type (`RESIDENTIAL_DRIVEWAY`, `APARTMENT_SOCIETY`, `COMMERCIAL_BUILDING`, `OPEN_PLOT`).
- **Precision Geocoding:** Owner drops a pin on the interactive Google Map widget to capture high-precision latitude and longitude, stored as PostGIS `GEOGRAPHY(Point, 4326)` in PostgreSQL.
- **Gate Access Instructions:** Free-text operational notes for drivers (e.g., "Enter via Gate 2; inform security you are parking in Visitor Bay 3").

---

## 16. Authorization Verification

### 16.1 AUTHZ-001: Tiered Legal Evidence Framework
Physical access to a parking bay does not establish the legal right to monetize it. To shield drivers, property owners, and the platform from civil disputes and trespassing claims, SmartPark enforces tiered evidence audits:

| Ownership Category | Legal Basis | Mandatory Document Evidence Required |
|---|---|---|
| **Individual Private Owner** | Freehold Title | 1. Property Tax Assessment Receipt (Current Fiscal Year) OR Registered Sale Deed, AND<br>2. Electricity/Water Bill matching owner legal name. |
| **Residential Tenant** | Leasehold Tenancy | 1. Registered Tenancy Agreement showing allocated parking clause, AND<br>2. Written Landlord Subletting No-Objection Certificate (NOC). |
| **Apartment Society Member** | Housing Society Allotment | 1. Share Certificate / Allotment Letter specifying bay number, AND<br>2. Society Management Committee No-Objection Certificate (NOC). |
| **Commercial Facility Manager** | Building Operations | 1. Business Registration (GSTIN / Certificate of Incorporation), AND<br>2. Property Management Agreement / Power of Attorney authorizing monetization. |
| **Authorized Parking Operator** | Concession Contract | 1. Municipal Concession Agreement or Commercial Lease, AND<br>2. Trade License & Commercial GST Registration. |

### 16.2 AUTHZ-002: Verification Gatekeeper
- Uploaded legal documents are stored in an encrypted private S3 bucket, accessible only via temporary 15-minute presigned URLs generated for authorized operations reviewers.
- **Non-Negotiable Rule:** A parking space CANNOT transition to `PUBLISHED` or appear in search results while property authorization status is `DRAFT`, `PENDING_REVIEW`, `REJECTED`, or `SUSPENDED`.

---

## 17. Parking Space Management

### 17.1 SPC-001: Discrete Bay Hierarchy & Dimension Constraints
Each physical parking space is modeled as a distinct entity linked to its parent property:
- **Bay Identifier:** Human-readable label (e.g., "Slot 1", "Bay B-4").
- **Space Type:** `COVERED`, `OPEN`, `BASEMENT`.
- **Vehicle Compatibility Enum:**
  * `TWO_WHEELER`: Motorcycles, scooters, mopeds.
  * `FOUR_WHEELER_COMPACT`: Hatchbacks and compact cars (length < 4.0m, e.g., Swift, i10).
  * `FOUR_WHEELER_SEDAN`: Standard sedans and compact SUVs (length < 4.6m, e.g., City, Creta).
  * `FOUR_WHEELER_LARGE`: Full-size SUVs, minivans, pickup trucks (e.g., Innova, Fortuner).
- **Physical Clearance Attributes:** Maximum height clearance in meters (mandatory for basement spaces).
- **EV Amenities:** Boolean flag indicating dedicated Level 2 AC charger availability.

---

## 18. Search and Discovery

### 18.1 DISC-001: Spatial PostGIS Proximity Matching
- **Spatial Query:** Discovery search executes PostGIS spatial indexing (`ST_DWithin`) against the property `location` column over a default 3,000-meter radius (user-expandable up to 5,000 meters per `POL-RAD-01`):
  ```sql
  SELECT p.*, ps.*, pr.hourly_rate_paise
  FROM properties p
  JOIN parking_spaces ps ON p.id = ps.property_id
  JOIN pricing_rules pr ON ps.id = pr.parking_space_id
  WHERE ST_DWithin(p.location, ST_MakePoint(:search_lon, :search_lat)::geography, :radius_meters)
    AND p.authorization_status = 'APPROVED'
    AND ps.is_active = TRUE
    AND fn_check_vehicle_bay_compatibility(
        :driver_vehicle_category,
        ps.space_type::text,
        ps.length_meters,
        ps.width_meters,
        ps.height_clearance_meters,
        ps.has_ev_charging,
        :driver_requires_ev
    );
  ```
- **Performance Target:** Sub-300ms response time at P95 across 500 active bays (proposed engineering SLO).

---

## 19. Availability Intelligence (MSAI)

### 19.1 AVAIL-001: Multi-Signal Synthesis & Pessimistic Safety
The Multi-Source Availability Intelligence engine evaluates 7 operational signals:
1. Owner weekly recurring operating schedule.
2. Owner manual blackout windows.
3. Confirmed database reservations in `space_reservations`.
4. Active 300-second temporary holds enforced by PostgreSQL GiST constraints.
5. Active guard-verified check-in sessions.
6. Guard obstruction reports submitted within the last 4 hours.
7. Mandatory 15-minute turnover buffers between consecutive bookings.

**Pessimistic Safety Invariant:** When evidence conflicts (e.g., calendar shows available, but guard reported an obstruction), the engine forces an `UNCERTAIN` or `BLOCKED` state. Inventory is never optimistically sold.

---

## 20. Booking and Hold Management

### 20.1 BOOK-001: Unified Reservation Data Model
SmartPark records all temporary holds, confirmed bookings, and active sessions in a single authoritative PostgreSQL table: `space_reservations`.

```sql
CONSTRAINT prevent_overlapping_active_reservations
EXCLUDE USING gist (
    parking_space_id WITH =,
    time_window WITH &&
) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'));
```

### 20.2 BOOK-002: Two-Tier Deterministic Expiration Engine
Because PostgreSQL partial exclusion constraints maintain index locks as long as a row has `status = 'ACTIVE_HOLD'`, expired holds do not leave the exclusion constraint automatically upon timestamp passage. To resolve this deterministically:
1. **Tier 1 (Active Scheduled Worker):** A background worker runs every 5 seconds, identifies holds where `hold_expires_at <= CLOCK_TIMESTAMP()`, and atomically transitions them to `EXPIRED_HOLD` in batches (`FOR UPDATE SKIP LOCKED`).
2. **Tier 2 (Inline Opportunistic Sweep):** Every `POST /bookings/hold` transaction executes an inline opportunistic update clearing stale holds on the target space immediately before attempting insert.
Competing reservations are permitted only after this transition commits. Redis TTL is strictly a client countdown aid and has zero authority over inventory locks.

### 20.3 BOOK-003: Late Payment Resolution Protocol (LPRP) & Multi-Stage Refund
If a driver's 8-minute hold expires while they are authorizing payment in their UPI app, and a competing driver claims the slot:
1. When Razorpay's `payment.captured` webhook arrives, the backend attempts to atomically transition the reservation from `EXPIRED_HOLD` to `CONFIRMED`.
2. If another driver secured the interval, PostgreSQL raises `ExclusionViolation` (`23P01`).
3. The system catches the error, transitions status to `RELEASED_UNFULFILLABLE`, and enters the **multi-stage refund lifecycle**:
   `REFUND_PENDING` -> `REFUND_PROCESSING` -> `REFUNDED` (or `REFUND_FAILED`).
4. SmartPark calls the gateway refund API, records gateway refund reference / ARN / UTR, and dispatches a transparent push notification to the driver.

### 20.4 BOOK-004: Explicit Vehicle Compatibility Matrix
Compatibility is evaluated via an explicit multidimensional matrix rather than a scalar comparison. Bay length, width, and height clearance are checked against the driver's vehicle category (`TWO_WHEELER`, `HATCHBACK`, `SEDAN`, `SUV`, `EV_FOUR_WHEELER`, `EV_TWO_WHEELER`). EV charging requirements are strictly matched against `has_ev_charging = TRUE`.

---

## 21. Payment Lifecycle

### 21.1 PAY-001: End-to-End Financial Orchestration
1. **Hold Acquisition:** Driver initiates hold; backend inserts row into `space_reservations` with status `ACTIVE_HOLD` and `hold_expires_at = now() + 480s` (strictly 8 minutes).
2. **Order Creation:** Backend generates Razorpay Order via `POST /v1/orders` specifying amount in paise and linking `reservation_id` in notes.
3. **Client Checkout:** Flutter launches Razorpay Checkout SDK via UPI Intent with parameter `close_by` set to 480 seconds.
4. **Server Webhook Verification:** Gateway dispatches `payment.captured`. Backend verifies raw HMAC-SHA256 signature, records and deduplicates event in PostgreSQL `payment_webhook_events` table (enforcing durable database idempotency), and atomically confirms the booking.
5. **No Frontend Trust:** Flutter client callbacks are treated as untrusted hints. State transitions execute exclusively upon server-side webhook verification.

---

## 22. UPI Integration

### 22.1 UPI-001: Native UPI Intent & Dynamic QR Flows
- **UPI Intent (Primary Mobile Flow):** Razorpay Flutter SDK queries device package managers for installed UPI apps (`net.one97.paytm`, `com.google.android.apps.nbu.paisa.user`, `com.phonepe.app`) and triggers native app-switching.
- **Provider-Generated Dynamic UPI QR:** Generated via server-side payment gateway QR APIs with explicit 480-second TTL to match the booking hold window. (Dynamic UPI QR operates via standard UPI intent rails and is distinct from legacy multi-bank BharatQR).
- **Static Merchant QR Ban:** SmartPark strictly prohibits static unlinked merchant QR codes.

---

## 23. Payment QR

### 23.1 PQR-001: Lifecycle of the Financial Payment QR
- **Issuer:** Payment Gateway API (Razorpay / Cashfree).
- **Consumer:** Driver UPI mobile application.
- **Payload:** NPCI UPI standard URI (`upi://pay?pa=...&am=...&tr=...`).
- **Lifespan:** Exactly 480 seconds (8 minutes, synchronized with booking hold).
- **Purpose:** Monetary settlement and fund transfer from driver bank account to aggregator transit balance.

---

## 24. Parking Access QR & Credential Lifecycle

### 24.1 AQR-001: Complete Access Credential Lifecycle (Entry & Exit)
SmartPark establishes that a consumed entry credential cannot be reused for exit:
1. **Phased Credential States:** Credentials follow a strict 5-state lifecycle: `ISSUED` $\to$ `ACTIVE` $\to$ `CONSUMED` $\to$ `REVOKED` $\to$ `EXPIRED`.
2. **ENTRY_TOKEN:** Server-minted upon booking confirmation using CSPRNG 128-bit random entropy (`spx_ent_` + `secrets.token_hex(16)`). Valid from $t_{\text{start}} - 15\text{m}$ to $t_{\text{start}} + 30\text{m}$ (arrival grace). Transitioned atomically to `CONSUMED` upon verified entry scan. Transitions to `EXPIRED` if no scan occurs by $t_{\text{start}} + 30\text{m}$ (`NO_SHOW`).
3. **ACTIVE_SESSION:** Live parking session activated in the driver mobile app with live timer and bay navigation.
4. **EXIT_TOKEN:** Minted and pre-cached securely in driver local storage upon check-in, enabling display even if cellular connectivity is lost in basement parking. Valid until $t_{\text{end}} + 15\text{m}$ (departure grace). Session extensions (`EXT-001`) dynamically update `valid_until` in the database and client cache. Scanned by guard upon departure to close the session (`COMPLETED`) and compute overstay billing if applicable.
5. **Zero PII & Replay Shield:** Credentials encode zero PII. Rescanning a consumed token triggers HTTP 409 Conflict and flashes **BOLD RED** on the guard scanner.

---

## 25. Guard Workflow & Controlled Manual Fallback

### 25.1 GRD-001: High-Speed Gate Validation
- Security guards authenticate via phone OTP and access a single-purpose camera viewfinder (`SCR-301`).
- Scanning driver QR decodes token and executes `POST /api/v1/access/validate-scan`.
- Backend verifies: 1) Token exists, 2) Reservation is `CONFIRMED`, 3) Property matches, 4) Current time is within arrival window, 5) Token is not `CONSUMED`.
- Screen flashes **BOLD GREEN** with vehicle plate and bay identifier. (Sub-1.5s is an engineering Service Level Objective).

### 25.2 GRD-002: Deep Basement Outage: Controlled Manual Exception
In underground basements with zero cellular reception, a local schedule cannot authoritatively prove current booking validity (as the booking may have been cancelled, refunded, or already admitted). SmartPark treats offline admission as an **Audited Controlled Manual Exception** (`MANUAL_OVERRIDE_PENDING_RECONCILIATION`), not a verified QR scan:
1. Guard app switches to Manual Exception Mode.
2. Guard enters physical vehicle plate and cross-checks against locally encrypted shift schedule (stored via SQLCipher AES-256).
3. Guard captures mandatory photo proof of the vehicle at the gate and enters driver phone last 4 digits.
4. Guard taps "Admit on Conditional Exception", logging a cryptographically signed audit event with SHA-256 hash chaining.
5. Upon regaining 4G/Wi-Fi connection at the surface, the app flushes pending admissions via `POST /access/reconcile-offline-admissions`. If a conflict is detected (e.g. cancelled/refunded booking), an urgent security incident is flagged to property management.
6. **Privacy Retention Limit:** An automated S3 lifecycle policy **permanently deletes vehicle gate photos within 7 days of successful backend reconciliation**, retaining only the cryptographic event hash for permanent audit.

---

## 26. Parking Session Lifecycle

### 26.1 SESS-001: Active Session Tracking & State Changes
- **Check-In Event:** Guard entry scan transitions reservation from `CONFIRMED` to `ACTIVE_SESSION`. Driver app initiates live elapsed timer.
- **Check-Out Event:** Guard exit scan verifies departure time. If within scheduled end + 15-minute grace period, session transitions to `COMPLETED`. Bay enters 15-minute turnover buffer.
- **Overstay Billing:** If departure exceeds the 15-minute grace period, overstay penalty (1.5x hourly rate) is billed in 30-minute blocks.


---

## 27. Cancellation and Refund

### 27.1 CANC-001: Authoritative Policy Tiers
All cancellation refund calculations follow the authoritative business policy table:
- **More than 2 hours before start:** 100% refund of base parking fee (net of gateway fee per policy).
- **30 minutes to 2 hours before start:** 50% refund of base parking fee.
- **Less than 30 minutes before start:** 0% refund (host retains full earnings).
- **Arrival failure / Host cancellation / LPRP:** 100% full refund including all fees and taxes.

### 27.2 CANC-002: Multi-Stage Refund Execution
Refunds operate through a multi-stage lifecycle (`REFUND_PENDING` -> `REFUND_PROCESSING` -> `REFUNDED` / `REFUND_FAILED`). The backend dispatches the refund request via the gateway API (`POST /v1/payments/{payment_id}/refund`), records the gateway refund ID and ARN/UTR, and polls or receives webhooks until final bank rail confirmation.

---

## 28. Overstay and Extensions

### 28.1 EXT-001: Dynamic Session Extensions
- Drivers may request extensions (30 min or 60 min) from the active session view (`SCR-105`).
- The backend evaluates availability for the consecutive extension interval.
- If unbooked, a secondary payment order is generated. Upon payment, the reservation `time_window` is extended atomically.
- **Inflexible Rule:** If another driver holds or booked the subsequent interval, the extension is strictly rejected: "Extension unavailable: Space booked by next driver."

### 28.2 OST-001: Overstay Penalty Enforcement
Drivers exceeding the 15-minute departure grace period without an approved extension are billed an overstay penalty of **1.5x the standard hourly rate** in 30-minute incremental blocks. 50% of the penalty is credited to the space owner as compensation for delay.

---

## 29. Guaranteed Parking Recovery Protocol (GPRP)

### 29.1 REC-001: Atomic 8-Step Operational Recovery Workflow
When a driver arrives and finds the reserved bay obstructed or unavailable:
1. **Original Reservation Kept Intact:** Original reservation is flagged `ARRIVAL_FAILED` but remains legally tied to the driver while alternatives are evaluated.
2. **Search Boundary Evaluation:** GPRP engine queries active, verified inventory within a **500m walking radius** (defined as a strict search boundary, not an unconditional supply promise).
3. **Atomic Alternative Reservation:** The alternative space is reserved via an atomic transaction with a temporary hold (`FOR UPDATE SKIP LOCKED`).
4. **Alternative Offer Creation:** The alternative bay details, photos, and walking route are presented in the app (`SCR-108`). Driver has 180 seconds to accept or decline.
5. **Driver Explicit Acceptance:** Driver confirms acceptance within the 180-second window.
6. **Booking Confirmation & Original Release:** System atomically confirms the alternative reservation and releases the original reservation (`status = 'REPLACED'`).
7. **Financial Adjustment:** Platform absorbs any price difference up to ₹100 via Goodwill Subsidy Account `4020`.
8. **Credential Revocation & Re-issuance:** Original QR credential is transitioned to `REVOKED`; a new `ENTRY_TOKEN` is minted for the alternative bay.
*Fallback Rule (Founder Decision Q2):* If an alternative cannot be secured atomically within 500m, or if the driver declines the proposal, the system automatically transitions the reservation to `REFUND_PENDING` and dispatches a deterministic full refund of all charges and fees.

---

## 30. Owner Financial Model & Unit Economics

### 30.1 FIN-001: Transparent Commission & Fee Split
Every parking fee is broken down into discrete components with unambiguous tax attribution:
- **Base Parking Fee:** Set by space owner (e.g., ₹40.00/hr $\times$ 2 hrs = ₹80.00 base).
- **Driver Convenience Fee:** Flat ₹10.00 billed to the customer to cover SMS and verification infrastructure.
- **GST on Convenience Fee:** 18.0% GST on convenience fee = ₹1.80.
- **Total Paid by Driver via UPI:** **₹91.80 (9,180 paise)**.
- **Platform Commission:** Flat 15.0% commission on base parking = ₹12.00 (1,200 paise).
- **GST on Platform Commission:** 18.0% GST on commission = ₹2.16 (216 paise).
- **Total Platform Facilitation Deduction from Host:** ₹12.00 + ₹2.16 = ₹14.16.
- **Net Property Owner Entitlement (Credit Account 2010):** Gross (₹80.00) - Facilitation (₹14.16) = **₹65.84 (6,584 paise)**.
- **Payment Gateway MDR Expense:** 2.36% (2.0% + 18% GST) on ₹91.80 = ₹2.17 (217 paise). Absorbed by platform as an operating expense (Account `4010`).
- **GST Output Tax Liability (Account 2030):** ₹1.80 + ₹2.16 = **₹3.96 (396 paise)** remitted to the government.
- **Net Platform Operating Margin (P&L):** Commission (₹12.00) + Convenience Fee (₹10.00) - Gateway MDR (₹2.17) = **₹19.83 (1,983 paise)** (21.6% Net Take-Rate).
- **Cash Flow Reconciliation Invariant:**
  $$\text{Inflow (₹91.80)} = \text{Owner (₹65.84)} + \text{Platform Net (₹19.83)} + \text{GST (₹3.96)} + \text{MDR (₹2.17)} = ₹91.80 \quad \text{[EXACT]}$$

---

## 31. Ledger and Payouts

### 31.1 LEDG-001: True Double-Entry General Ledger
All monetary movements generate balancing journal entries across `journal_entries` and `journal_lines` satisfying:
$$\sum_{\text{lines}} \text{Debits} = \sum_{\text{lines}} \text{Credits} \quad \text{and line count} \ge 2$$
The database enforces this invariant via trigger `trg_verify_journal_balance` before any journal can transition to `POSTED`. Posted journals are permanently immutable; corrections are executed exclusively via reversing journals.
The standard Chart of Accounts segregates:
- `1010` Gateway Transit Account (Asset)
- `1020` Operating Bank Account (Asset)
- `2010` Owner Payable Liability (Liability)
- `2020` Customer Refund Payable (Liability)
- `2030` GST Output Tax Payable (Liability)
- `3010` Platform Commission Revenue (Revenue)
- `3020` Driver Convenience Fee Revenue (Revenue)
- `4010` Payment Gateway MDR Expense (Expense)
- `4020` GPRP Customer Recovery Subsidy Expense (Expense)

### 31.2 LEDG-002: Regulatory Payout Architecture (MoR & Pilot Approach)
- SmartPark acts as the Merchant of Record (MoR) for driver payments and bears full refund and chargeback liability.
- Dual application is maintained for both Razorpay Route and Cashfree Marketplace.
- If automated marketplace nodal routing is not approved by Day 1 due to turnover thresholds, owner settlements will operate via **scheduled batch bank transfers** from the platform corporate current account under strict internal KYC (PAN verification + Penny Drop bank validation) and prior bank/legal agreement (Founder Decision Q5). Direct bank transfers are not described as "escrow" accounts.

### 31.3 LEDG-003: Balanced Journal Templates for Core Financial Events
1. **Driver Payment Captured (`JRN-BK`):** Debit `1010` (₹91.80), Credit `2010` (₹65.84), Credit `3010` (₹12.00), Credit `3020` (₹10.00), Credit `2030` (₹3.96).
2. **Gateway Settlement & MDR Deduction (`JRN-MDR`):** Debit `1020` (₹89.63), Debit `4010` (₹2.17), Credit `1010` (₹91.80).
3. **Weekly Owner Batch Payout (`JRN-PO`):** Debit `2010` (₹65.84), Credit `1020` (₹65.84).
4. **GST Tax Remittance (`JRN-TAX`):** Debit `2030` (₹3.96), Credit `1020` (₹3.96).
5. **Full Cancellation Refund >2h (`JRN-CAN-100`):** Debit `2010` (₹65.84), Debit `3010` (₹12.00), Debit `3020` (₹10.00), Debit `2030` (₹3.96), Credit `1010` (₹91.80).
6. **Partial Cancellation Refund 30m-2h (`JRN-CAN-50`):** Debit `2010` (₹32.92), Debit `3010` (₹6.00), Debit `3020` (₹5.00), Debit `2030` (₹1.98), Credit `1010` (₹45.90).
7. **LPRP Unfulfillable Refund (`JRN-LPRP`):** Debit `2010` (₹65.84), Debit `3010` (₹12.00), Debit `3020` (₹10.00), Debit `2030` (₹3.96), Credit `1010` (₹91.80).
8. **Failed Refund Earmarking (`JRN-FLR`):** Debit `1010` (₹91.80), Credit `2020` (₹91.80).
9. **Chargeback Dispute Reversal (`JRN-CHG`):** Debit `2010` (₹65.84), Debit `3010` (₹12.00), Debit `3020` (₹10.00), Debit `2030` (₹3.96), Credit `1020` (₹91.80).
10. **GPRP Price Subsidy (`JRN-SUB`):** Debit `4020` (₹30.00), Credit `2010` (₹30.00).
11. **Overstay Penalty Billing (`JRN-OST`):** Debit `1010` (₹60.00), Credit `2010` (₹30.00), Credit `3010` (₹20.85), Credit `2030` (₹9.15).
12. **Stale Hold Expiration (`JRN-EXP`):** Zero financial journal entry required; database inventory lock released.

### 31.4 POUT-001: Progressive Marketplace Payout Transition
- **Phase 1 (Pilot Launch):** Scheduled batch bank transfers via **RazorpayX / Cashfree Payouts API** (IMPS/NEFT) executing weekly batch settlements against penny-drop verified bank accounts for balances $\ge ₹500$ under corporate current account agreement.
- **Phase 2 (Scale):** Programmatic marketplace splitting via **Razorpay Route** or **Cashfree Marketplace** linked accounts upon provider underwriting approval.
- **Unified Schema:** Both phases use the identical double-entry ledger accounts (`2010 Owner Payable`), requiring zero database migration when upgrading to automated Route settlement.

---

## 32. Notifications

### 32.1 NOTIF-001: Real-Time Event Dispatch
Powered by **Firebase Cloud Messaging (FCM)** across Android and iOS:
- `HOLD_EXPIRING_SOON`: Push alert at 60 seconds remaining on hold.
- `BOOKING_CONFIRMED`: Access pass issued alert with bay identifier.
- `SESSION_CHECKIN_SUCCESS`: Active session confirmation.
- `SESSION_ENDING_REMINDER`: 15-minute departure countdown alert.
- `GPRP_ALTERNATIVE_OFFERED`: Recovery alternative proposed alert.
- `WEEKLY_PAYOUT_INITIATED`: Bank transfer UTR notification to host.

---

## 33. Platform Operations (Admin/Ops)

### 33.1 OPS-001: Restricted Operations Role
Internal operations workflows are executed via a restricted mobile view (`SCR-401` / `SCR-402`) and secure backend CLI scripts:
- **Property Legal Audit Queue:** Review uploaded tax receipts and society NOCs; approve or reject with structured reason codes.
- **Incident Investigation:** Audit full timeline (Hold -> Webhook -> Scan -> Photo -> GPRP).
- **Emergency Refund Override:** Authorized staff can trigger 100% manual refund overrides requiring TOTP 2FA.
- **Zero Web Admin Portal:** No public or web-hosted admin dashboard exists in MVP.

---

## 34. Database Overview

### 34.1 DB-001: Relational Schema & Concurrency Locks
- **Engine:** PostgreSQL 15+ with PostGIS and `btree_gist`.
- **Core Entities:** `users`, `user_roles`, `vehicles`, `properties`, `property_authorizations`, `parking_spaces`, `pricing_rules`, `operating_schedules`, `guard_assignments`, `space_reservations`, `access_credentials`, `access_scans`, `ledger_entries`, `owner_payouts`, `incidents`, `alternative_offers`.
- **Immutability:** Application database role has `INSERT` and `SELECT` grants only on `ledger_entries`. `UPDATE` and `DELETE` grants are explicitly revoked.
- Reference: Detailed DDL and ER diagrams in [`docs/technical/DATABASE_DESIGN.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/technical/DATABASE_DESIGN.md).

---

## 35. API Overview

### 35.1 API-001: RESTful JSON Contracts
- **Framework:** Python FastAPI with OpenAPI 3.1 specifications.
- **Base URL:** `https://api.smartpark.in/api/v1`
- **Security:** Bearer JWT auth, IDOR protection, RFC 7807 error responses.
- **Idempotency:** Mutating endpoints strictly require `Idempotency-Key` headers (UUIDv4) cached in Redis for 24 hours.
- Reference: Exhaustive endpoint documentation in [`docs/technical/API_SPECIFICATION.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/technical/API_SPECIFICATION.md).

---

## 36. Security and Privacy

### 36.1 SEC-001: STRIDE Threat Remediation & DPDPA Posture
- **Zero Secrets in Mobile App:** Flutter client binary contains zero payment secrets, webhook secrets, or service account credentials.
- **Raw Body Webhook Verification:** Verifies HMAC-SHA256 signatures directly against raw request body bytes before JSON deserialization.
- **Phased Access Credentials:** Separate `ENTRY_TOKEN` and `EXIT_TOKEN` with true 128-bit CSPRNG entropy (`secrets.token_hex(16)`), burned atomically upon scan to eliminate QR screenshot sharing.
- **Privacy & DPDPA Compliance:** Bilingual consent notices (English & Kannada), data minimization (no Aadhaar/DL storage; masked phone numbers in transit), and published Resident Grievance Officer details (`grievance@smartpark.in`). Retention policies (e.g. 180-day GPS purge vs statutory tax retention) and full DPDPA compliance are subject to qualified legal counsel audit.
- **Intermediary Status:** SmartPark asserts intermediary status under Section 79 of the IT Act 2000 subject to strict compliance with the Intermediary Guidelines Rules 2021; bailment is explicitly disclaimed in user terms.
- Reference: Comprehensive threat model in [`docs/product/SECURITY_AND_PRIVACY_REVIEW.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/SECURITY_AND_PRIVACY_REVIEW.md).

---

## 37. Non-Functional Requirements (NFR)

### 37.1 Proposed Engineering Service Level Objectives (SLOs)
*Note: The performance metrics below represent engineering design targets (SLOs) for system sizing and load testing, not verified production benchmark results.*

| NFR Metric | Engineering Design Target (SLO) | Measurement Methodology | Target SLA |
|---|---|---|---|
| **Discovery Search Latency** | P95 latency across 500 active bays in 3–5km radius | Locust load testing (100 concurrent requests) | **< 300 ms** (Target) |
| **Booking Hold Acquisition** | Database GiST exclusion insert latency | P99 latency under 200 concurrent threads | **< 50 ms** (Target) |
| **Guard QR Scan Validation** | Camera decode to green/red admission modal | P95 latency over 4G mobile cellular | **< 1.5 seconds** (Target) |
| **API Availability Uptime** | Booking, search, and access validation APIs | Synthetic monitoring via CloudWatch/Datadog | **99.9% Uptime** (06:00 - 23:00 IST) |
| **Mobile Battery Consumption**| Continuous camera viewfinder in Guard App | Battery drain per hour of continuous shift | **< 12% battery/hour** |

---

## 38. Error Handling and Edge Cases

### 38.1 Comprehensive 30-Scenario Edge Case Matrix
The platform defines explicit recovery logic across all 30 failure scenarios:

| Category | ID | Failure Scenario | Architectural Recovery Logic |
|---|---|---|---|
| **Concurrency & Inventory** | SCN-01 | Simultaneous hold requests for overlapping time | PostgreSQL GiST exclusion constraint serializes transaction; 2nd request encounters `23P01` and returns HTTP 409 Conflict. |
| | SCN-02 | Stale hold passes 480s expiration during checkout | Two-tier expiration engine cleans row; competing booking permitted; if original pays late, LPRP triggers auto-refund. |
| | SCN-03 | Host blocks property while active hold exists | Blackout check evaluates future bookings; active holds are protected or converted to GPRP failover. |
| | SCN-04 | Driver requests duration < 30 minutes | API validation layer rejects request with RFC 7807 problem details (`DURATION_TOO_SHORT`). |
| | SCN-05 | Driver requests booking > 24 hours | API validates property maximum allowed booking hours; rejects with `MAX_DURATION_EXCEEDED`. |
| | SCN-06 | Multi-space bay iteration encounters locked row | MSAI uses `SELECT ... FOR UPDATE SKIP LOCKED` to seamlessly evaluate next compatible space without thread blocking. |
| **Payment & Gateways** | SCN-07 | UPI payment captured after 480s hold expired (LPRP) | Database throws `23P01` on confirm; reservation marked `RELEASED_UNFULFILLABLE`; multi-stage refund initiated. |
| | SCN-08 | Webhook delivered with invalid HMAC signature | Server rejects with HTTP 400 Bad Request; booking remains unconfirmed; security alert logged. |
| | SCN-09 | Duplicate webhook delivered for captured payment | Database unique constraint on `payment_webhook_events(gateway_name, gateway_event_id)` catches duplicate; returns HTTP 200 OK without re-processing. |
| | SCN-10 | Payment gateway webhook network timeout / drop | Driver client polls `GET /payments/verify-status/{order_id}`; backend queries gateway API and confirms booking. |
| | SCN-11 | Driver payment succeeds but gateway refund times out | Outbox worker retries gateway refund API using idempotent refund reference; prevents duplicate refunds. |
| | SCN-12 | Card chargeback / dispute initiated by driver | System posts balancing reversal journal `JRN-CHG`; deducts owner payable deficit from future payouts. |
| **Gate Access & Security** | SCN-13 | Guard attempts scan in underground basement cellular blackout | Scanner switches to Controlled Manual Exception; verifies vehicle plate against local SQLCipher cache; logs signed entry event. |
| | SCN-14 | Offline manual entry reconciled against cancelled booking | System flags `RECONCILIATION_CONFLICT` incident; alerts property supervisor; assesses penalty charge. |
| | SCN-15 | Driver presents screenshot of already used QR code | Database checks `access_credentials.status = 'CONSUMED'`; throws HTTP 409 Conflict; flashes BOLD RED alert. |
| | SCN-16 | Driver arrives earlier than 15-minute grace window | Guard scanner validates server timestamp < `valid_from`; displays "EARLY ARRIVAL: Gate opens at [Time]". |
| | SCN-17 | Driver arrives after 30-minute late arrival grace | System marked reservation `NO_SHOW`; guard scanner flags conditional admission requiring space re-validation. |
| | SCN-18 | Driver phone battery dies at exit gate | Guard executes manual exit override in app (`SCR-304`); inputs vehicle plate; verifies session closure. |
| **Operations & GPRP** | SCN-19 | Reserved space physically blocked upon driver arrival | Guard/driver reports `ARRIVAL_FAILED`; bay marked `BLOCKED` in MSAI; launches atomic 8-step GPRP recovery. |
| | SCN-20 | GPRP alternative space more expensive than original | Platform absorbs tariff difference up to ₹100 via Goodwill Subsidy Account `4020`. |
| | SCN-21 | No alternative space available within 500m boundary | GPRP transitions reservation to `REFUND_PENDING`; dispatches 100% full refund of all charges and fees. |
| | SCN-22 | Driver declines proposed GPRP alternative within 180s | System releases alternative hold; automatically transitions reservation to `REFUND_PENDING`. |
| | SCN-23 | Driver overstays scheduled end + 15m departure grace | Overstay billed at 1.5× hourly rate in 30-minute blocks; automated post-session invoice generated. |
| | SCN-24 | Driver purchases session extension during active parking | Extension interval evaluated against future bookings; confirmed atomically; `EXIT_TOKEN` validity extended. |
| **Financial Ledger** | SCN-25 | Journal entry lines do not balance (Debits != Credits) | PostgreSQL trigger `trg_verify_journal_balance` raises exception; blocks transaction commit. |
| | SCN-26 | User attempts to update or delete a posted journal | Immutability trigger `trg_prevent_posted_modification` aborts query; enforces append-only accounting. |
| | SCN-27 | Owner weekly payout transfer fails at bank rail | Status marked `PAYOUT_FAILED`; funds retained in Account `2010` (Owner Payable) for next batch retry. |
| | SCN-28 | Driver cancels reservation > 2 hours before start | System posts `JRN-CAN-100` reversing journal; dispatches 100% refund via gateway API. |
| | SCN-29 | Driver cancels reservation 30m–2h before start | System posts `JRN-CAN-50` partial journal; refunds 50%; credits 50% retained earnings. |
| | SCN-30 | Property owner bank account verification (penny drop) fails | System suspends payout disbursement; flags owner KYC profile for banking details correction. |

---

## 39. Integrations

### 39.1 Third-Party Integration Inventory
SmartPark integrates strictly with vetted, enterprise-grade cloud providers:
1. **Firebase Authentication (Google Cloud):** Native handset SMS OTP delivery, Play Integrity verification, and iOS APNs integration.
2. **Firebase Cloud Messaging (FCM):** Transactional push notification dispatch for booking confirmations, hold expiries, and gate check-ins.
3. **Razorpay / Cashfree Payments:** Payment order generation, UPI Intent app-switching, dynamic UPI QR rendering, raw HMAC webhook callbacks, and automated refund APIs.
4. **RazorpayX / Cashfree Payouts API:** Penny-drop bank account validation and automated batch IMPS payouts for property owner disbursements.
5. **Amazon Web Services (AWS ap-south-1 Mumbai):** ECS Fargate container compute, RDS PostgreSQL Multi-AZ with PostGIS, ElastiCache Redis, S3 encrypted object storage, and CloudFront CDN.

---

## 40. Open-Source Dependency Strategy

### 40.1 Pragmatic Reuse & Decoupled Adapters
SmartPark leverages active, battle-tested open-source libraries under permissive licenses (`MIT`, `Apache-2.0`, `BSD-3-Clause`):
- **Mobile Client:** `flutterfire` (auth & messaging), `razorpay_flutter` (UPI checkout), `qr_flutter` (pass rendering), `mobile_scanner` (camera scanning), `flutter_secure_storage` (keychain storage).
- **Backend Core:** `fastapi` (REST framework), `sqlalchemy 2.0` + `asyncpg` (database ORM & async binary driver), `redis-py` (caching & locks), `pydantic v2` (schema validation), `pyotp` (internal staff 2FA).
- Reference: Full repository license audit and adapter interfaces in [`docs/product/OPEN_SOURCE_INTEGRATIONS.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/OPEN_SOURCE_INTEGRATIONS.md).

---

## 41. MVP Definition

### 41.1 Mandatory P0 Capabilities
The Minimum Viable Product constitutes the complete, reliable, end-to-end exchange loop:
1. Driver registers via phone OTP and registers personal vehicle.
2. Driver discovers verified parking bays via PostGIS spatial search (3km default, 5km max).
3. Driver secures an 8-minute (480-second) atomic interval hold enforced by PostgreSQL GiST exclusion locks.
4. Driver completes UPI payment via Razorpay / Cashfree Intent.
5. Backend verifies raw HMAC webhook, persists event in `payment_webhook_events`, and issues an opaque, one-time Access QR pass.
6. Guard scans QR at property gate, validates online, and admits vehicle.
7. Controlled manual fallback allows entry even in dead-zone underground basements with 7-day photo retention limits.
8. Departure exit scan completes session and logs total duration.
9. Double-entry ledger records balanced financial journal entries.
10. Weekly batch payout transfers net earnings to the space owner's verified bank account.

---

## 42. Development Phases

### 42.1 Phased Execution Timeline
- **Sprint 1–2 (Core Scaffolding & Identity):** FastAPI modular monolith setup, PostgreSQL PostGIS schema, Redis cluster, Firebase Phone Auth, and Flutter role navigation shell.
- **Sprint 3–4 (Inventory & Availability Engine):** Property and bay CRUD, legal document uploader, MSAI synthesis engine, and PostgreSQL GiST exclusion locks.
- **Sprint 5–6 (Booking & Payment Loop):** 480-second atomic hold orchestrator, UPI Intent integration, raw HMAC webhook processor, and double-entry ledger.
- **Sprint 7–8 (Guard Access & GPRP Recovery):** Phased access credentials (`ENTRY_TOKEN` & `EXIT_TOKEN`), Flutter camera viewfinder (`mobile_scanner`), check-in/out APIs, and GPRP 8-step recovery engine.
- **Sprint 9–10 (Payouts, Testing & Field Pilot):** Weekly IMPS payout batch worker, end-to-end concurrency chaos testing, security penetration audit, and Bengaluru field pilot launch.

---

## 43. Acceptance Criteria

### 43.1 Testable Scenario Signoffs
Detailed Given/When/Then scenarios are baselined across core domains:
- **AC-01 (Concurrency Collision):** Two simultaneous requests for the exact same bay and interval result in exactly 1 commit and 1 PostgreSQL `ExclusionViolation` (`23P01`), returning HTTP 409 Conflict.
- **AC-02 (Webhook Tampering):** Webhooks with altered payloads or invalid HMAC signatures are rejected with HTTP 400 Bad Request; booking remains unconfirmed.
- **AC-03 (QR Replay Shield):** Presenting a previously scanned QR code or screenshot returns HTTP 409 Conflict and flashes BOLD RED on the guard app.
- **AC-04 (Unverified Listing Gatekeeper):** A property in `PENDING_REVIEW` cannot publish spaces; bays are excluded from search results.
- **AC-05 (Late Payment Asynchronous Refund):** A payment webhook arriving after 480s hold expiration where the bay was claimed by another driver triggers a deterministic multi-stage refund protocol (`REFUND_PENDING` $\to$ `REFUND_PROCESSING`), notifying driver of a 5–7 business day banking rail settlement window.

---

## 44. Testing Strategy

### 44.1 Automated Test Execution Suite (20 Mandatory High-Risk Scenarios)
Quality assurance is enforced across all 20 mandatory high-risk test scenarios documented in [`docs/quality/TEST_STRATEGY.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/quality/TEST_STRATEGY.md):
- `TS-01`: Concurrent Booking Race for Same Physical Space.
- `TS-02`: Late Payment Webhook Arrival After Hold Expiry (LPRP).
- `TS-03`: Webhook Replay Attack & Duplicate Delivery Idempotency.
- `TS-04`: Payment Webhook Signature Tampering (Invalid HMAC).
- `TS-05`: Offline Guard Gate Admission in Underground Cellular Dead Zone.
- `TS-06`: Offline Reconciliation Conflict Detection (Entry on Cancelled Booking).
- `TS-07`: QR Access Replay Attack (Screenshot Reuse).
- `TS-08`: Double-Entry General Ledger Balance Trigger Invariant Enforcement.
- `TS-09`: Immutable Ledger Post-Modification Rejection.
- `TS-10`: Guaranteed Parking Recovery Protocol (GPRP) 8-Step Reallocation.
- `TS-11`: GPRP Alternative Space Exhaustion Auto-Refund Fallback.
- `TS-12`: Overstay Detection & Penalty Billing Calculation.
- `TS-13`: Active Session Extension Collision with Next Consecutive Booking.
- `TS-14`: Multi-Space Bay Iteration Allocation under High Load.
- `TS-15`: Driver Cancellation Refund Tier Calculation (>2h, 30m-2h, <30m).
- `TS-16`: Stale Hold Background Worker Cleanup Concurrency with Inline Sweep.
- `TS-17`: IDOR Security Attack on Driver Access Token Endpoint.
- `TS-18`: Bank Payout Batch Processing & Failure Handling.
- `TS-19`: Multidimensional Vehicle Compatibility Bay Filtering.
- `TS-20`: PostgreSQL Multi-AZ Database Failover Recovery.

---

## 45. Product Metrics and KPIs

### 45.1 North Star Metric
> **Total Monthly Successfully Completed Parking Sessions (MSCS):**  
> *The aggregate count of unique driver reservations that complete physical check-in and checkout without an unresolved arrival failure or refund dispute.*

### 45.2 Core Operational Benchmarks
- **Search-to-Booking Conversion:** $\ge 12.0\%$
- **Successful Arrival Rate:** $\ge 98.0\%$
- **False-Available Error Rate:** $< 1.0\%$
- **GPRP Resolution Rate:** $\ge 75.0\%$ resolved via alternative space.
- **Ledger Discrepancy Rate:** $0.00\%$ (Zero mathematical tolerance).
- **Average Gate Clearance Time:** $< 3.0$ seconds.

---

## 46. Business Assumptions & Reconciled Unit Economics

### 46.1 Financial & Operational Baseline
All commercial calculations adhere to [`docs/product/BUSINESS_ASSUMPTIONS.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/BUSINESS_ASSUMPTIONS.md):
- **Base Platform Commission:** 15.0% on gross parking fee (₹12.00 on a standard 2-hour ₹80.00 booking).
- **Driver Convenience Fee:** Flat ₹10.00 + 18% GST (₹1.80) = ₹11.80 billed to the customer.
- **Payment Gateway MDR Expense:** 2.36% (2.0% + 18% GST) on ₹91.80 = ₹2.17 (absorbed by platform).
- **Net Property Owner Entitlement:** ₹80.00 - ₹14.16 commission & GST = **₹65.84**.
- **Net GST Output Tax Payable to Govt:** ₹1.80 + ₹2.16 = **₹3.96**.
- **Net Platform Operating Contribution:** Commission (₹12.00) + Convenience Fee (₹10.00) - Gateway MDR (₹2.17) = **₹19.83** (21.6% Net Take-Rate).
- **Cash Flow Reconciliation Invariant:** $\text{Inflow (₹91.80)} = \text{Owner (₹65.84)} + \text{Platform Net (₹19.83)} + \text{GST (₹3.96)} + \text{MDR (₹2.17)} = ₹91.80$ [EXACT].

---

## 47. Risks and Mitigations

| Risk Code | Risk Description | Severity | Likelihood | Architectural & Operational Mitigation |
|---|---|---|---|---|
| **RSK-001** | Unauthorized vehicle parks in reserved bay before driver arrives. | HIGH | HIGH | **MSAI & GPRP Failover:** Guard reports obstruction; space marked `BLOCKED`; driver rerouted to alternative within 500m or entered into deterministic multi-stage refund workflow. |
| **RSK-002** | Razorpay Route marketplace payout approval delayed by >₹40L turnover rule. | HIGH | MEDIUM | **Automated Direct Bank Payout Fallback:** Weekly automated IMPS batch disbursements via RazorpayX / Cashfree Payouts on identical ledger schema. |
| **RSK-003** | Drivers overstay their booked slot, blocking the next reserved vehicle. | MEDIUM | HIGH | **1.5x Overstay Penalty & 15m Buffers:** Overstaying vehicles charged 1.5x hourly rate; 15-minute buffers absorb minor traffic delays. |
| **RSK-004** | Cellular dead zone in underground basements prevents guard scan. | HIGH | HIGH | **Controlled Manual Fallback Protocol:** Guard verifies physical license plate against locally cached shift schedule and syncs upon reconnection. |
| **RSK-005** | Legal disputes with Apartment Associations (AOAs) regarding guest parking. | HIGH | MEDIUM | **Strict Authorization Proofs:** Mandatory submission of Society Management Committee NOC before apartment listings can be activated. |
| **RSK-006** | Driver vehicle damaged or vandalized while parked on private property. | HIGH | LOW | **Strict Intermediary Terms of Service:** Disclaim platform and owner bailment liability under Section 79 IT Act; parking is at vehicle owner's sole risk. |

---

## 48. Open Questions Registry Reference

All 65 open business, legal, payment provider, technical, and operational decisions are formally cataloged, tracked, and assigned in:
👉 [`docs/product/OPEN_QUESTIONS.md`](file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/docs/product/OPEN_QUESTIONS.md)

---

## 49. Future Strategic Roadmap (P1 / P2)

### Phase 2: Operational Scale & Multi-City Expansion (Months 4 - 6)
- Expansion from Bengaluru pilot to Mumbai (BKC/Andheri) and Delhi-NCR (Cyber City Gurgaon).
- Automated CKYC verification for space owners via third-party identity APIs (Signzy / IDfy).
- Dynamic pricing surge engine based on localized neighborhood events and rain/monsoon indicators.
- Automated WhatsApp notifications via official Meta Cloud API.

### Phase 3: Hardware & Smart Infrastructure (Months 7 - 12)
- Edge ANPR camera integration for automated boom barrier clearance without human security guards.
- Solar-powered ultrasonic bay occupancy sensors for automated real-time space status updates.
- EV Charging Network integration (OCPP 1.6/2.0 protocol) allowing combined parking + charging billing.
- Corporate employee parking management portal for enterprise office campuses.

---

## 50. Final Readiness Assessment & Implementation Authorization

### 50.1 Mandatory Architectural Invariants
1. **The Backend is the Single Source of Truth:** The Flutter mobile application is strictly a presentation and input capture layer. No booking confirmation, payment success state, or authorization approval may be decided client-side.
2. **Cryptographic Proofs for All State Mutations:** Webhooks require raw HMAC-SHA256 signature verification; access passes require server-minted opaque tokens; auth sessions require Firebase Admin ID token verification.
3. **Database-Level Double-Booking Prevention:** Concurrency is guaranteed by PostgreSQL GiST exclusion constraints (`EXCLUDE USING gist`), never by optimistic application-layer checks alone.
4. **Separate QR Systems:** The Razorpay Payment Dynamic QR and the SmartPark Parking Access QR must never be combined, share schemas, or reuse endpoints.
5. **No Speculative Selling:** If an operational signal reports a bay blocked or unverified, the space must be withheld from search.

### 50.2 Implementation Authorization & External Dependencies
This Master Product Requirements Document (`PRD.md`), along with its supporting engineering specifications (`USER_FLOWS.md`, `OPEN_QUESTIONS.md`, `OPEN_SOURCE_INTEGRATIONS.md`, `REQUIREMENTS_TRACEABILITY.md`, `DATABASE_DESIGN.md`, `API_SPECIFICATION.md`, `ARCHITECTURE.md`, `BOOKING_AND_AVAILABILITY_DESIGN.md`, `PAYMENT_AND_LEDGER_DESIGN.md`, `QR_ACCESS_DESIGN.md`, `SCREEN_REQUIREMENTS.md`, `BUSINESS_ASSUMPTIONS.md`, `SECURITY_AND_PRIVACY_REVIEW.md`, `TEST_STRATEGY.md`, and `DECISION_LOG.md`), constitutes the complete, approved product and technical specification for **SmartPark Exchange**.

Engineering teams are authorized to begin implementation of **Phase 1 (Foundational Infrastructure & Core Booking Engine)**, subject to the formal acknowledgment of external dependencies (payment aggregator merchant approvals, DLT registration, and corporate legal counsel sign-off on terms of service and tax classifications).
