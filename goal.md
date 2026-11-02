# Gadispot — Product Vision, Strategic Objectives & Implementation Goal Specification

> **Document Identifier:** GOAL-GSP-2026-V1.0.2-VERIFIED  
> **Document Title:** Gadispot Product Vision, Strategic Objectives & Implementation Goal Document  
> **Governing Baseline:** Master PRD V2.3.2-VERIFIED (`PRD-GSP-2026-V2.3.2-VERIFIED`)  
> **Target Pilot Geography:** Bengaluru Urban Metro, Karnataka, India (Koramangala, Indiranagar, HSR Layout)  
> **Target Execution Platforms:** Mobile-Only (Single Cross-Platform Flutter Codebase for Android & iOS)  
> **Backend Architecture:** In-Process Modular Monolith (Python / FastAPI / PostgreSQL 16 + PostGIS / Redis 7.0+)  
> **Status:** Baselined Final Goal Specification (Sprint 0/1 Implementation Authorized; Pilot Launch Gated on External Rails)  
> **Classification:** Authoritative Strategic & Engineering Direction Document  

---

## 1. Document Identity and Control

### 1.1 Document Identification & Metadata

This document, `goal.md`, serves as the authoritative strategic and implementation charter for **Gadispot** (formerly SmartPark Exchange). It translates the master technical and engineering requirements defined in `PRD.md` (V2.3.2) into an aligned product strategy, articulating the core vision, real-world operational problems, target customer economics, non-negotiable architectural philosophies, and verifiable launch criteria across the product lifecycle.

```
Document Identification Matrix
--------------------------------------------------------------------------------------------------------
Document Identifier       : GOAL-GSP-2026-V1.0.2-VERIFIED
Document Type             : Product Vision, Strategic Objectives & Implementation Goal Specification
Repository Path           : goal.md
Authoritative Spec Source : PRD.md (Version 2.3.2 Harmonized)
Target Launch Geography   : Bengaluru Urban Metro, Karnataka, India
Target Micro-Markets      : Koramangala, Indiranagar, HSR Layout (200 Pilot Bays)
Target Platforms          : Mobile-Only (Android & iOS via single Flutter binary)
Backend Engine            : Python FastAPI Modular Monolith + PostgreSQL 16 (PostGIS) + Redis 7.0+
Test Verification Status  : 15/15 Executable PostgreSQL 16 Tests Passing (100% Green in tests/database/)
Engineering Status        : Status B — Conditional Specification Freeze (Sprint 0/1 Authorized)
Commercial Status         : Pilot Launch Gated on External Rails (PA Underwriting & DLT Registration)
--------------------------------------------------------------------------------------------------------
```

### 1.2 Strict Source-of-Truth Hierarchy

To eliminate ambiguity and prevent specification drift, all technical implementations, governance audits, and strategic decisions in the Gadispot repository strictly adhere to the following governance priority hierarchy:

1. **Explicitly Approved Founder Decisions:** The 5 foundational baselines formally approved by executive leadership (`FD-01` through `FD-05`), cataloged in `docs/product/FOUNDER_DECISION_CHECKLIST.md`.
2. **Latest Authoritative Master PRD:** `PRD.md` (Version 2.3.2-VERIFIED), containing the authoritative 50 canonical sections, stable functional requirement IDs (`FR-AUTH-001` to `FR-GPRP-001`), and 15 business acceptance scenarios.
3. **Current Decision Log and Founder Decision Checklist:** `docs/product/DECISION_LOG.md` (ADR-001 through ADR-010) and `docs/product/FOUNDER_DECISION_CHECKLIST.md` (distinguishing approved baselines from proposed policies).
4. **Product Requirements and User Flows:** `docs/product/REQUIREMENTS_TRACEABILITY.md`, `docs/product/USER_FLOWS.md`, and `docs/product/SCREEN_REQUIREMENTS.md`.
5. **Technical Specifications:** Deep architectural blueprints: `docs/technical/ARCHITECTURE.md`, `docs/technical/DATABASE_DESIGN.md`, `docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md`, `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`, `docs/technical/QR_ACCESS_DESIGN.md`, and `docs/technical/API_SPECIFICATION.md`.
6. **Audit Findings and Risk Registers:** Empirical verification logs and risk catalogs: `docs/audits/V2_3_2_FINAL_AUDIT.md` and `docs/audits/V2_3_1_RESIDUAL_RISK_REGISTER.md`.
7. **Older Project Documentation:** Historical changelogs and pre-V2.3 audits retained strictly for audit continuity (`docs/audits/V2_3_1_FINAL_AUDIT.md`, `docs/audits/PRD_V2_3_FINAL_AUDIT.md`, `docs/audits/TECHNICAL_AUDIT.md`).

*Rule of Interpretation:* Discrepancies are never silently resolved. No proposed policy (`PROPOSED (Pending Founder Approval)`), unvalidated assumption, or architectural recommendation shall be treated as an approved decision or implemented feature without written founder signoff.

### 1.3 Document Revision History

| Version | Release Date | Primary Contributors | Core Changes & Governance Milestones | Approval Status |
|---|---|---|---|---|
| **v1.0.0** | 2026-11-02 | Senior Product & Engineering Architecture Group | Comprehensive creation of `goal.md` across 20 canonical sections synthesizing product vision, 22 capabilities, 13 principles, 12-step jury flow, 11 pilot areas, and 5-stage readiness gates. | **Baselined Final Implementation Goal** |
| **v1.0.1** | 2026-11-02 | Adversarial Reviewer 2 Group | Adversarial hardening: Harmonized Table 7.2 assumption IDs with canonical `docs/product/BUSINESS_ASSUMPTIONS.md`, mapped Risk Register to canonical RR- IDs, synchronized Stage 8 and Gate 5 with all 5 external launch gates (including DEP-LEG-02), and integrated all 4 marketplace roles into the jury demonstration journey. | **Verified Final Implementation Goal (Sprint 0/1 Authorized)** |
| **v1.0.2** | 2026-11-02 | Adversarial Reviewer 3 Group | Adversarial verification & hardening: Synchronized document identifier to V1.0.2; repaired all 13 non-canonical file paths to valid relative repository paths; incorporated complete statutory tax & cost invariants (ASM-003..ASM-009) in Section 7.3; integrated PRD §38 RPO, RTO, and concurrency headroom metrics in Section 12.1; expanded jury failure scenarios with Owner listing rejection and Guard subterranean offline admission; and harmonized Section 15.3 with ASM-002. | **Verified Final Implementation Goal (Sprint 0/1 Authorized)** |

---

## 2. Product Identity

### 2.1 One-Sentence Identity
**Gadispot is a mobile-first, two-sided parking reservation exchange that unlocks private residential driveways, gated society visitor bays, and commercial basements across congested Indian metros through mathematical concurrency locking, hardware-agnostic guard verification, and immutable double-entry financial accountability.**

### 2.2 One-Paragraph Identity
Gadispot (formerly SmartPark Exchange) bridges the critical divide between urban motorists circling congested city blocks and property owners possessing dormant vehicular capacity. Unlike passive directories displaying speculative pins or unverified municipal spots, Gadispot operates as an authoritative reservation clearinghouse: every booked time slot is physically and mathematically guaranteed via database-level PostgreSQL GiST exclusion locks (`btree_gist`), verified at the gate through high-entropy 128-bit CSPRNG QR credentials scanned on existing security guard smartphones, settled through an append-only double-entry general ledger, and protected by an automated Guaranteed Parking Recovery Protocol (GPRP) that ensures drivers never face stranded arrival without immediate alternative allocation or an automated 100% refund.

### 2.3 Detailed Strategic Description
Gadispot addresses the hyper-dense, chaotic mobility landscape of major Indian urban centers, starting with Bengaluru. The platform transforms underutilized private physical real estate into institutional-grade, liquid parking assets without requiring expensive, failure-prone IoT infrastructure like ground sensors, ultrasonic detectors, or automated boom gates. Instead, it leverages software precision, standard consumer UPI payment rails, and existing human guard personnel equipped with budget Android handsets.

The platform is built as a strict **Mobile-Only Single Binary** deploying to Android and iOS via Flutter. It houses dynamic, role-specific operational shells that adapt instantaneously to verified user JWT claims:

```
+----------------------------------------------------------------------------------------------------+
|                                    GADISPOT SINGLE MOBILE BINARY                                   |
|                                        (Flutter Android & iOS)                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ DRIVER SHELL ]          [ OWNER SHELL ]            [ GUARD SCANNER ]          [ OPS VIEW ]      |
|  SCR-101..107              SCR-201..205               SCR-301..304               SCR-401..402      |
|  - 3km Proximity Search    - Listing Onboarding       - 1-Handed QR Scanner      - Property Audit  |
|  - 480s GiST Hold          - Weekly Schedules         - Sub-2s Clearance         - KYC Penny Drop  |
|  - Seamless UPI Intent     - Real-Time Occupancy      - Offline Shift Cache      - GPRP Disputes   |
|  - Dynamic Entry/Exit QR   - KYC & Weekly Payouts     - 7-Day Photo Purge S3     - Ledger Journal  |
|  - Turn-by-Turn Arrival    - Personal Blackouts       - Incident Trigger SOS     - Policy Admin    |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 2.4 User Role Alignment Across the Marketplace
Gadispot harmonizes four distinct operational actors into a unified cyber-physical ecosystem:
1. **The Driver (Rohan):** Urban commuter seeking guaranteed, turn-by-turn navigation to a verified parking bay with upfront transparent pricing, sub-second search, UPI checkout, and absolute assurance against gate refusal.
2. **The Space Owner / Property Manager (Anand):** Residential villa owner, housing society (RWA/AOA), or commercial operator monetizing idle vehicular bays during business or off-peak hours with automated scheduling, verified driver screening, and hands-off weekly bank payouts.
3. **The Security Guard / Gate Attendant (Ramesh):** Low-bandwidth gatekeeper operating a low-cost Android handset who validates arrivals and departures within 2 seconds using a high-contrast camera scanner, backed by a deterministic offline fallback mode in subterranean basements.
4. **Platform Operations (Deepa):** Centralized operational oversight team responsible for auditing property title deeds/NOCs, reviewing automated GPRP arrival incidents, arbitrating host-driver disputes, and maintaining immutable financial integrity across the general ledger.

---

## 3. The Real-World Problem

### 3.1 Driver Problems (Urban Commuters)
* **Severe Urban Congestion & Circling Burn:** Motorists in major Indian commercial and IT corridors (e.g., Koramangala, Indiranagar, HSR Layout) spend 15 to 25 minutes circling blocks searching for open parking, burning fuel, escalating stress, and exacerbating metro gridlock.
* **Uncertainty of Space Availability:** Arriving at a destination only to find commercial lots saturated, private gates locked, or open plots claimed by informal parking cartels.
* **Arbitrary & Opaque Pricing:** Street parking and unorganized lot attendants charge arbitrary cash rates (₹50 to ₹150) without printed receipts, digital tracking, or predictable hourly schedules.
* **Hostility & Access Barriers at Gated Societies:** Independent security guards aggressively turn away non-resident guest vehicles due to safety protocols and the absence of digital guest pre-authorization.
* **Zero Recourse on Blocked Bays:** If a driver arrives and finds an unorganized lot blocked, or if plans change, prepayments are entirely lost with zero refund mechanism.

### 3.2 Property Owner Problems (Dormant Capacity Holders)
* **Dormant Real Estate Asset Yield:** Prime residential driveways, vacant builder plots, and commercial office basements sit empty 8 to 12 hours every day, generating zero economic return for owners.
* **Lack of Safe Monetization Tools:** Individual homeowners and housing societies lack booking platforms, digital payment gateways, customer identity vetting, and scheduling controls required to safely rent spaces.
* **Security, Trespassing & Encroachment Fears:** Property owners legitimately fear that opening driveways to strangers could lead to permanent vehicle abandonment, illegal trespassing, or security compromises.
* **Manual Collection & Accounting Overhead:** Collecting petty cash or verifying unlinked UPI transfer screenshots is socially awkward and operationally unmanageable for busy professionals and society committees.

### 3.3 Security Guard & Parking Operator Problems (Gatekeepers)
* **Gate Verification Bottlenecks:** Security guards at apartment complexes and commercial basements waste minutes interrogating drivers, making phone calls to residents, and filling out illegible physical paper visitor logs.
* **Inability to Identify Legitimate Bookings:** Guards have no digital tool to distinguish legitimate pre-authorized drivers from unauthorized vehicles attempting unauthorized entry.
* **Zero Occupancy Insight:** Guards lack visibility into how many vehicles are expected, which specific bays are reserved, and when parked vehicles are scheduled to vacate.
* **Confrontation & Conflict Exposure:** Guards are left to arbitrate angry disputes when drivers arrive claiming verbal permission to park in already occupied bays.
* **Subterranean Connectivity Blindspots:** Basement parking garages often have zero cellular connectivity, disabling standard cloud-connected verification apps.

### 3.4 Platform Operations & Industry Problems (Marketplace Friction)
* **Fake & Fraudulent Inventory:** Malicious actors listing municipal street parking, public roads, or property they do not own, leading to legal disputes and customer extortion.
* **Concurrency Failures & Double-Bookings:** Naive database designs allowing two concurrent drivers to check out and pay for the exact same physical slot at the same time.
* **Payment Webhook Desynchronization:** Payment aggregator network delays leading to orphaned payments where a driver's bank account is debited but the booking is dropped.
* **Access Pass Replay & Fraud:** Drivers capturing static screenshots of valid QR codes and circulating them among peers for illicit entry.
* **Regulatory & Tax Ambiguity:** Navigating RBI payment aggregator guidelines, GST Section 9(1) vs 9(5) marketplace liability, and municipal trade licensing without legal exposure.

---

## 4. Product Vision

### 4.1 Vision Statement
**To establish the definitive cyber-physical parking infrastructure for urban India by transforming millions of fragmented, dormant private parking spaces into a liquid, dependable, and pre-bookable mobility utility.**

### 4.2 Commercially Grounded Reality
Gadispot rejects fantasy startup metrics, unverified market size claims, and premature technology buzzwords. The vision is grounded strictly in operational unit economics, statutory compliance, and software engineering rigor:
* **No Speculative Hardware Deployment:** We do not rely on expensive IoT ultrasonic sensors or computer vision cameras that break down in dusty Indian street environments.
* **Pessimistic Availability as Brand Defense:** We recognize that in parking, a false positive (sending a driver to an unavailable bay) destroys trust permanently. Gadispot’s vision is built on strict pessimistic inventory allocation: if any operational signal is uncertain, the space is suppressed.
* **Institutional Capital and Real Estate Efficiency:** By unlocking existing residential and commercial capacity, Gadispot increases citywide parking density without requiring municipal governments to pour thousands of tons of concrete for multi-level car parks.

---

## 5. Product Mission

### 5.1 Operational Mission Breakdown
Gadispot executes its strategic purpose through an unbroken, eight-stage operational mission:

```
[ 1. Verified Inventory ] ──> [ 2. Sub-Second Discovery ] ──> [ 3. Deterministic Availability ] ──> [ 4. Concurrency Hold ]
          │                                                                                                    │
          ▼                                                                                                    ▼
[ 8. Financial Payouts ]  <── [ 7. Incident Recovery ]   <── [ 6. Sub-2s Gate Clearance ]     <── [ 5. Frictionless UPI ]
```

1. **Verified Inventory:** Strictly prohibiting property publication until legal right-of-use evidence (freehold title deeds, tenancy sublet clauses, or society NOCs) is validated by operations.
2. **Sub-Second Discovery:** Enabling drivers to discover dimensionally compatible parking bays within a 3km radius in under 300ms (P95) via PostGIS spatial queries.
3. **Deterministic Availability:** Synthesizing 7 operational inputs through Multi-Source Availability Intelligence (MSAI) to guarantee that only 100% accessible bays are displayed.
4. **Concurrency Hold:** Enforcing universal 480-second (8-minute) atomic reservation holds directly at the database engine level via PostgreSQL GiST exclusion locks.
5. **Frictionless Payment:** Providing seamless UPI Intent checkout via Razorpay with raw HMAC webhook verification, durable idempotency, and the Late Payment Resolution Protocol (LPRP).
6. **Sub-2-Second Gate Clearance:** Arming security guards with a lightweight camera scanner that validates dynamic 128-bit CSPRNG QR passes in under 2 seconds, with a secure offline fallback mode for basements.
7. **Incident Recovery & Customer Support:** Automatically resolving physical obstructions within 180 seconds via the Guaranteed Parking Recovery Protocol (GPRP), providing alternative bays within 500m or initiating an automated 100% full refund, backed by dedicated customer support adhering to a 24-hour dispute resolution SLA (`OQ-BIZ-009`).
8. **Financial Payouts & Auditability:** Recording every rupee through an append-only double-entry general ledger and disbursing weekly batch bank transfers to KYC-verified host accounts (PAN + Penny Drop).

---

## 6. Target Users and Customer Value

### 6.1 Comprehensive Persona & Value Matrix

| Persona | Identity Profile | Real-World Problem | Desired Target Outcome | Core Delivered Value | Mobile Interaction Surfaces | Trust Factors | Primary Churn Risks & Mitigation |
|---|---|---|---|---|---|---|---|
| **Driver** | **Rohan (29)**<br>IT Commuter, SUV Owner (Hyundai Creta), Bengaluru | Circles 20 mins; risks towing; faces arbitrary cash rates; rejected at private gates. | Guaranteed bay waiting at destination; sub-2s gate entry; turn-by-turn navigation. | Predictable arrival time; 100% money-back guarantee; zero street negotiation. | `SCR-101..107`<br>(Explore Map, Bay Details, Checkout, QR Pass, Active Timer) | Transparent hourly rate; atomic reservation hold; GPRP fallback protection. | **Risk:** Arriving to blocked bay.<br>**Mitigation:** 8-step GPRP reroute within 500m or 100% refund in 180s. |
| **Space Owner** | **Anand (54)**<br>Villa Owner, 2-car covered driveway in Indiranagar | Vacant driveway capacity during work hours; fears vandalism and unauthorized squatting. | Monetize idle bay; zero physical involvement; verified guest vehicles; timely bank payouts. | Passive income (₹3,000–₹6,000/mo); complete schedule control; vetted drivers. | `SCR-201..205`<br>(Listing Onboard, Schedule Setup, Earnings Dash, Bank Link) | Automated bank payouts; driver vehicle plate verification; personal blackout blocks. | **Risk:** Overstaying guest blocking host car.<br>**Mitigation:** 1.5× overstay penalty tariff; ops towing escalation. |
| **Security Guard** | **Ramesh (38)**<br>Gate Guard, Commercial Complex, HSR Layout | Stressed by gate queues; illegible registers; arguments with unauthorized visitors. | Fast 1-tap vehicle clearance; clear Green/Red admission; zero physical logbooks. | Sub-2-second validation; zero confrontation; works in offline basement garages. | `SCR-301..304`<br>(Camera Scanner, Scan Result, Shift Arrival List, Incident SOS) | High-contrast visual feedback; offline plate matching; non-confrontational authority. | **Risk:** Camera lag or dead battery on budget handset.<br>**Mitigation:** Battery-safe scanner lifecycle; 6-char fallback code. |
| **Platform Operations** | **Deepa (27)**<br>Operations Associate, Bengaluru Hub | Fraudulent property uploads; manual dispute arbitration; reconciling mismatched bank accounts. | Instant document audit queue; automated GPRP dispute logging; tamper-proof ledger. | Operational efficiency; zero reconciliation leaks; clear fraud prevention tools. | `SCR-401..402`<br>& Administrative CLI Tools (Verification Queue, Ledger Audit) | Cryptographic audit logs; balanced double-entry ledger; S3 encrypted document store. | **Risk:** Fraudulent hosts gaming payouts.<br>**Mitigation:** Mandatory PAN + Penny Drop verification prior to payout release. |

---

## 7. Core Product Value Proposition

### 7.1 Features vs Benefits vs Competitive Moats

```
+-------------------------------------------------------------------------------------------------------------+
|                                  GADISPOT VALUE PROPOSITION DECOMPOSITION                                   |
+------------------------------------+-----------------------------------+------------------------------------+
| TECHNICAL FEATURES                 | TANGIBLE USER BENEFITS            | DEFENSIBLE COMPETITIVE MOATS       |
+------------------------------------+-----------------------------------+------------------------------------+
| 1. PostgreSQL GiST Range Locks     | Zero double-bookings; booking is  | Mathematical storage-engine        |
|    (tstzrange exclusion constraint)| 100% guaranteed once confirmed.   | concurrency serialization.         |
|                                    |                                   |                                    |
| 2. Multi-Source Availability (MSAI)| Never sent to an occupied, closed,| Strict pessimistic safety algorithm|
|    synthesizing 7 field signals.   | or obstructed parking bay.        | suppressing uncertain inventory.   |
|                                    |                                   |                                    |
| 3. Dynamic 128-bit CSPRNG QR passes| Immediate sub-2s gate clearance;  | Separated access & payment tokens; |
|    with mobile_scanner integration.| screenshots cannot be forged.     | single-use atomic replay burning.  |
|                                    |                                   |                                    |
| 4. Guaranteed Recovery Protocol    | Instant peace of mind; alternative| Automated 8-step recovery workflow |
|    (GPRP) with 180s decision SLA.  | space within 500m or full refund. | with ₹100 platform fee subsidy cap.|
|                                    |                                   |                                    |
| 5. Double-Entry General Ledger with| Transparent host accounting;      | True append-only balanced ledger;  |
|    Penny-Drop bank verification.   | reliable weekly direct transfers. | zero-child-lock deadlock freedom.  |
+------------------------------------+-----------------------------------+------------------------------------+
```

### 7.2 Business Assumptions Requiring Pilot Validation

To maintain rigorous governance, all business policies and unit economics are categorized based on their evidentiary status:

| Canonical Policy / Assumption ID | Repository Source Reference | Policy / Parameter Description | Current Baseline Specification | Evidentiary Status | Validation Methodology During Pilot |
|---|---|---|---|---|---|
| **POL-COM-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/BUSINESS_ASSUMPTIONS.md` (`ASM-001`) | Platform Facilitation Take-Rate | **Flat 15.0%** of gross parking base fee | `PROPOSED (Pending Founder Approval)` | Measure host onboarding friction and platform operating contribution across 200 pilot spaces. |
| **ASM-002** | `docs/product/BUSINESS_ASSUMPTIONS.md` (`ASM-002`) / `PRD.md` §37 | Driver Platform Convenience Fee | **Flat ₹10.00** per completed reservation | `PROPOSED (Pending Founder Approval)` | A/B test driver checkout completion rates with and without convenience fee. |
| **POL-CAN-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §27 | Cancellation Refund Tiers | >2h: 100%, 30m–2h: 50%, <30m: 0% (Convenience fee non-refundable) | `PROPOSED (Pending Founder Approval)` | Track cancellation frequency, driver chargebacks, and host schedule disruption rates. |
| **POL-DUR-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §18 | Global Minimum Booking Duration | **30 Minutes** | `PROPOSED (Pending Founder Approval)` | Analyze booking duration distribution (30m vs 60m drop-offs) in commercial hubs. |
| **POL-ARR-02** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §27 | Driver No-Show Grace Period | **Exactly 30 Minutes** past scheduled start time | `PROPOSED (Pending Founder Approval)` | Measure arrival delay distribution in Bengaluru peak traffic hours. |
| **POL-OST-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §25 | Overstay Penalty Tariff | **1.5× Base Hourly Rate** in 30-min increments | `PROPOSED (Pending Founder Approval)` | Evaluate overstay deterrence effectiveness vs customer support dispute escalations. |
| **POL-SUB-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/BUSINESS_ASSUMPTIONS.md` (`ASM-010`) | GPRP Price Subsidy Cap | Platform absorbs tariff difference **up to ₹100** | `PROPOSED (Pending Founder Approval)` | Audit platform financial exposure per GPRP reallocation in Account 4020. |
| **POL-POT-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §23 | Host Payout Minimum Threshold | **Weekly (Tuesdays)** for balances **$\ge ₹500$** | `PROPOSED (Pending Founder Approval)` | Optimize bank API IMPS transaction costs (₹2–₹4/transfer) against host satisfaction. |
| **FD-01** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/DECISION_LOG.md` (ADR-001) / `PRD.md` §1.2 | Dual Payment Gateway Underwriting | Dual application (Razorpay primary, Cashfree secondary)| `FOUNDER_APPROVED` | Track gateway merchant onboarding approval and Route split qualification. |
| **FD-02** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/DECISION_LOG.md` (ADR-009) / `PRD.md` §1.2 | GPRP Failover 100% Full Refund | **100% Full Refund to Original Instrument** if bay unfulfillable | `FOUNDER_APPROVED` | Verify automatic transition to `REFUND_ELIGIBLE` and 6-stage settlement in pilot. |
| **FD-03** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/DECISION_LOG.md` (ADR-008) / `PRD.md` §1.2 | Offline Guard Photo Retention Rule | Automated **7-day S3 purge** lifecycle | `FOUNDER_APPROVED` | Verify AWS S3 lifecycle rule execution and DPDPA compliance audit logs. |
| **FD-04** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `PRD.md` §1.2 | Maximum Booking Duration | **Configurable by Property (Default 24 Hours)** | `FOUNDER_APPROVED` | Analyze driver multi-hour utilization patterns and host schedule turnover. |
| **FD-05** | `docs/product/FOUNDER_DECISION_CHECKLIST.md` / `docs/product/DECISION_LOG.md` (ADR-005) / `PRD.md` §1.2 | Marketplace Host Payout Mechanism | **Scheduled Batch Bank Transfers from Corporate Account** (IMPS) | `FOUNDER_APPROVED` | Reconcile bank API IMPS payouts against Ledger Account 2010 balances. |

### 7.3 Verified Statutory Tax & Operational Cost Invariants (Supporting Unit Economics)

In accordance with Section 1.2 source-of-truth governance, the financial modeling and general ledger accounting formulas in Section 12.1 and Section 20.4 incorporate the complete set of verified statutory tax rates and vendor cost invariants cataloged in `docs/product/BUSINESS_ASSUMPTIONS.md`:

| Assumption ID | Repository Source Reference | Parameter Description | Canonical Baseline Value | Evidentiary Classification | Statutory / Contractual Foundation |
|---|---|---|---|---|---|
| **ASM-003** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / Notification 11/2017 | GST on Marketplace Facilitation Services | **18.0% Goods & Services Tax** | `VERIFIED FACT` | Notification No. 11/2017-Central Tax (Rate); SAC 9985 (Support Services); remitted via Ledger Account 2030. |
| **ASM-004** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / Legal Tax Opinion | GST on Residential Driveway Rentals | **0.0% (Exempt for unregistered individuals)** | `VERIFIED FACT` | Rental of residential property for parking by unregistered individuals is not subject to forward-charge GST. |
| **ASM-005** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / `PRD.md` §37 | Payment Gateway MDR Rate (Razorpay) | **2.0% + 18% GST (Net: 2.36%)** | `VERIFIED FACT` | Published standard Razorpay India merchant rate for UPI, cards, and netbanking; absorbed in Account 4010. |
| **ASM-006** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / `docs/product/OPEN_QUESTIONS.md` (`OQ-PAY-002`) | Razorpay Route Marketplace Fee | **~0.25% + 18% GST per transfer** | `OPEN COMMERCIAL DECISION` | Published indicative Route fee for automated linked-account transfers; deferred to Phase 2 (>₹40L turnover). |
| **ASM-007** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / `FD-05` | Automated Batch Bank IMPS Transfer Fee | **₹2.00 to ₹4.00 per IMPS transfer** | `VERIFIED FACT` | Published corporate banking API rates (RazorpayX / Cashfree Payouts) for weekly direct host disbursements. |
| **ASM-008** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / Google Cloud Billing | Firebase Phone Auth SMS Free Tier | **10,000 verifications/month free** | `VERIFIED FACT` | Official Google Firebase Identity Platform pricing sheet; covers initial pilot user authentication volume. |
| **ASM-009** | `docs/product/BUSINESS_ASSUMPTIONS.md` §2 / `docs/product/OPEN_QUESTIONS.md` (`OQ-TECH-001`) | Firebase SMS Overage Cost in India | **~$0.015 per verification (~₹1.25/SMS)** | `VERIFIED FACT` | Published Firebase Identity Platform telecom routing rates for India (+91); budgeted for scale beyond 10k MAU. |

---

## 8. Core Product Capabilities

Gadispot provides exactly **22 core product capabilities** mapped directly from the functional requirements of `PRD.md` (§12). These capabilities represent the complete functional surface of the MVP without inventing ungrounded features:

```
+----------------------------------------------------------------------------------------------------+
|                                 THE 22 CORE PRODUCT CAPABILITIES                                   |
+----------------------------------------------------------------------------------------------------+
| [01] FR-AUTH-001 : Passwordless Mobile Phone Authentication via Firebase & Authoritative JWT       |
| [02] FR-AUTH-002 : Dynamic Mobile Role Switching (Driver <-> Owner <-> Guard <-> Ops)              |
| [03] FR-DRIVER-001: Multi-Vehicle Profile Management with Indian Plate Validation                  |
| [04] FR-DRIVER-002: Proximity Search with Spatial Radius (PostGIS 3km default, 5km max)           |
| [05] FR-OWNER-001 : Property and Parking Bay Onboarding with Geo-Coordinates & Photos              |
| [06] FR-OWNER-002 : Recurring Operating Schedule & Manual Blackout Management                     |
| [07] FR-INVENTORY-001: Multidimensional Vehicle Compatibility Engine (2W, Hatch, Sedan, SUV)       |
| [08] FR-AVAIL-001 : Multi-Source Availability Synthesis (MSAI 7-Signal Algorithm)                 |
| [09] FR-BOOK-001  : Atomic 480-Second Time-Window Hold via PostgreSQL GiST Exclusion Locks         |
| [10] FR-BOOK-002  : Two-Tier Hold Expiration Engine (5s Celery Worker + Opportunistic Inline Sweep)|
| [11] FR-PAY-001   : Razorpay UPI Intent Checkout & Durable Webhook Processing                      |
| [12] FR-PAY-002   : Late Payment Resolution Protocol (LPRP Concurrency Recovery)                   |
| [13] FR-REFUND-001: Asynchronous 6-Stage Refund Lifecycle (REFUND_ELIGIBLE -> SETTLED)             |
| [14] FR-QR-001    : Dynamic Opaque Access Credential Issuance (128-bit CSPRNG Tokens)              |
| [15] FR-QR-002    : Guard Gate Validation & Single-Use Atomic Replay Burn                          |
| [16] FR-SESSION-001: Physical Parking Session Tracking & Dynamic Extension Engine                  |
| [17] FR-LEDGER-001: Immutable Balanced Double-Entry General Ledger (Debit = Credit Triggers)       |
| [18] FR-PAYOUT-001: Scheduled Batch Bank Transfers (Penny-Drop Verified IMPS under MoR)           |
| [19] FR-ADMIN-001 : Property Authorization Review Queue & Title Verification Engine                |
| [20] FR-SEC-001   : DPDPA Data Minimization & Automated 7-Day S3 Gate Photo Purge                 |
| [21] FR-NOTIFY-001: Transactional Multi-Channel Dispatch Engine (FCM / APNs Push Alerts)          |
| [22] FR-GPRP-001  : Guaranteed Parking Recovery Protocol (8-Step 500m Reroute / 100% Refund)       |
+----------------------------------------------------------------------------------------------------+
```

### Detailed Capability Mapping to User Outcomes

1. **`FR-AUTH-001` (Passwordless Phone Authentication):** Drivers, hosts, and guards register in seconds using 10-digit Indian mobile numbers via native Firebase OTP verification, exchanged authoritatively for an internal scoped JWT session.
2. **`FR-AUTH-002` (Dynamic Role Switching):** Users possessing dual identities (e.g., driver commuting by day, driveway host on weekends) toggle operational views in a single tap without re-authenticating.
3. **`FR-DRIVER-001` (Multi-Vehicle Profile Management):** Drivers register multiple personal vehicles with standard Indian license plates (e.g., `KA-01-AB-1234`) and dimensional categories (2W, Hatchback, Sedan, SUV).
4. **`FR-DRIVER-002` (Proximity Search with Spatial Radius):** High-speed geospatial discovery returns dimensionally compatible, available parking bays within 3km in <300ms P95 via PostGIS bounding queries.
5. **`FR-OWNER-001` (Property & Bay Onboarding):** Hosts define parking properties, specify exact bay dimensions, upload mandatory access approach photos, and submit legal authorization evidence.
6. **`FR-OWNER-002` (Recurring Schedule & Blackouts):** Hosts configure granular operating hours (e.g., Mon–Fri 09:00–18:00) and block bays for personal family use with automatic conflict checks.
7. **`FR-INVENTORY-001` (Vehicle Compatibility Engine):** Eliminates physical mismatch (e.g., parking an SUV in a compact hatchback bay) through deterministic clearance rules.
8. **`FR-AVAIL-001` (Multi-Source Availability Synthesis):** Synthesizes 7 operational inputs to compute pessimistic availability, suppressing slots upon any conflict.
9. **`FR-BOOK-001` (Atomic 480-Second Time-Window Hold):** Reserves a discrete interval $[t_{\text{start}}, t_{\text{end}})$ via PostgreSQL `EXCLUDE USING gist`, guaranteeing mathematical exclusion during checkout.
10. **`FR-BOOK-002` (Two-Tier Hold Expiration Engine):** Sweeps abandoned holds every 5 seconds via background tasks and opportunistically cleans stale holds inline, releasing inventory immediately.
11. **`FR-PAY-001` (UPI Checkout & Webhook Processing):** Launches native UPI Intent flows (PhonePe, GPay, Paytm) with raw HMAC-SHA256 webhook validation and durable idempotency tables.
12. **`FR-PAY-002` (Late Payment Resolution Protocol):** Resolves edge cases where payments arrive after hold expiration by checking availability and automatically initiating a 100% full refund if the bay was claimed.
13. **`FR-REFUND-001` (Asynchronous 6-Stage Refund Lifecycle):** Tracks refunds deterministically through 6 canonical states (`REFUND_ELIGIBLE` $\to$ `REFUND_REQUESTED` $\to$ `GATEWAY_ACCEPTED` $\to$ `REFUND_PROCESSING` $\to$ `REFUND_SETTLED` / `REFUND_FAILED`).
14. **`FR-QR-001` (Dynamic Opaque Credential Issuance):** Mints unguessable 128-bit CSPRNG access tokens (`spx_entry_...` and `spx_exit_...`) completely isolated from payment tokens.
15. **`FR-QR-002` (Guard Gate Validation & Replay Burn):** Validates credentials in <2s via `mobile_scanner`, atomically transitioning tokens to `CONSUMED` to prevent screenshot reuse.
16. **`FR-SESSION-001` (Session Tracking & Dynamic Extension):** Tracks physical elapsed parking time, alerts drivers 15 minutes before expiration, and enables in-app session extensions if future intervals are unbooked.
17. **`FR-LEDGER-001` (Double-Entry General Ledger):** Enforces zero-sum mathematical balancing ($\sum \text{Debits} = \sum \text{Credits}$) with database triggers preventing line modifications on posted journals.
18. **`FR-PAYOUT-001` (Scheduled Batch Bank Payouts):** Aggregates weekly host earnings ($\ge ₹500$), validates bank accounts via Penny Drop, and disburses IMPS batch transfers under MoR status.
19. **`FR-ADMIN-001` (Property Authorization Review Queue):** Operations dashboard inspecting property deeds, tax receipts, and Society NOCs prior to publishing inventory.
20. **`FR-SEC-001` (DPDPA Data Minimization & Photo Purge):** Enforces statutory privacy controls, encrypts PII at rest via KMS AES-256, and executes automated 7-day S3 photo purge lifecycles.
21. **`FR-NOTIFY-001` (Transactional Multi-Channel Dispatch):** Dispatches asynchronous push alerts (FCM/APNs) for booking confirmations, arrival reminders, gate scans, and refund updates.
22. **`FR-GPRP-001` (Guaranteed Parking Recovery Protocol):** Automates an 8-step recovery workflow when a bay is obstructed upon arrival, securing an alternative within 500m or issuing an automated 100% refund.

---

## 9. Product Differentiation

Gadispot’s competitive defensibility rests on five structural, technical, and operational pillars:

```
+----------------------------------------------------------------------------------------------------+
|                                 THE 5 PILLARS OF DIFFERENTIATION                                   |
+----------------------------------------------------------------------------------------------------+
|  1. AUTHORIZATION-AWARE INVENTORY                                                                  |
|     Mandatory proof of legal right-of-use (Sale Deed / Tax Receipt / Society NOC) verified by Ops |
|     prior to search publication. Zero unverified municipal or common-area street parking.        |
+----------------------------------------------------------------------------------------------------+
|  2. MULTI-SOURCE AVAILABILITY INTELLIGENCE (MSAI)                                                  |
|     7-signal synthesis under strict pessimistic safety: open schedule + active guard obstruction   |
|     immediately suppresses slot. Mathematical elimination of speculative inventory.                |
+----------------------------------------------------------------------------------------------------+
|  3. GUARANTEED PARKING RECOVERY PROTOCOL (GPRP)                                                    |
|     Atomic 8-step alternative space reallocation within 500m in <= 180s with up to ₹100 platform   |
|     subsidy, or automatic fallback to 100% full refund. Drivers are never left stranded.           |
+----------------------------------------------------------------------------------------------------+
|  4. HARDWARE-AGNOSTIC GATE VERIFICATION                                                            |
|     Dynamic 128-bit CSPRNG QR passes scanned via existing guard smartphones with sub-2s latency.   |
|     Zero CapEx on barrier gates, loop detectors, or ANPR; bounded offline basement fallback mode. |
+----------------------------------------------------------------------------------------------------+
|  5. FINANCIAL ACCOUNTABILITY & TRUE DOUBLE-ENTRY LEDGER                                            |
|     Append-only general ledger with balanced debit/credit triggers (Sum Debits = Sum Credits) and  |
|     Zero Child Lock deadlock freedom. Automated Penny-Drop verified weekly host bank payouts.     |
+----------------------------------------------------------------------------------------------------+
```

---

## 10. Product Development Philosophy

The development of Gadispot is governed by **13 non-negotiable engineering and product principles**:

1. **PostgreSQL as Sole Concurrency Authority:** Double-bookings are physically prevented by PostgreSQL GiST exclusion constraints on `tstzrange` intervals at the database storage engine layer. Redis is strictly limited to ephemeral read-caching, rate-limiting, and UI timers; it is never the authoritative concurrency gate.
2. **Interval-Based Concurrency:** A hold or booking reserves a discrete time window $[t_{\text{start}}, t_{\text{end}})$, not an entire physical space. Non-overlapping requests for the same physical bay execute in parallel without lock contention.
3. **Universal 480-Second (8-Minute) Hold Standard:** The checkout hold duration is strictly 480 seconds across mobile clients, payment orders, background sweepers, and database records. No 5-minute or 10-minute inconsistencies are tolerated.
4. **Pessimistic Availability Synthesis (MSAI):** Conflicting operational signals force an `UNCERTAIN` or `UNAVAILABLE` state. Inventory is never optimistically sold to maximize short-term GMV.
5. **Strict Mobile-Only Architecture:** In the MVP, all customer, host, and guard interactions are delivered through a single cross-platform Flutter binary deploying to Android and iOS. There is no public consumer website, desktop booking portal, or public web dashboard.
6. **Architectural Separation of Payment and Access Subsystems:** An absolute architectural boundary exists between Razorpay UPI payment QR tokens (which collect funds) and Gadispot access pass QR tokens (which open gates).
7. **Dynamic Single-Use Cryptographic Gate Passes:** Gate passes contain high-entropy, opaque 128-bit CSPRNG tokens that are atomically burned upon scan. Static screenshot replays are mathematically prevented.
8. **Pragmatic Offline Fallback with Bounded Privacy:** In subterranean cellular dead zones, guards operate under a controlled manual exception workflow with encrypted local caching and an automated 7-day AWS S3 photo purge lifecycle.
9. **In-Process Modular Monolith Over Premature Microservices:** All backend services (Auth, Inventory, Booking, Payment, Ledger, Access) run within a single containerized FastAPI monolith, eliminating distributed transaction sagas and network serialization lag.
10. **Append-Only Financial Immutability with Zero-Child-Lock Deadlock Freedom:** General ledger entries are immutable (`REVOKE UPDATE, DELETE`). Journal balance triggers execute without redundant child line locks, completely eliminating lock-order inversion deadlocks.
11. **Two-Phased Marketplace Settlement Strategy:** Phase 1 operates via scheduled batch IMPS bank transfers from the corporate account under Merchant of Record status; Phase 2 migrates to Razorpay Route linked-account splits upon meeting turnover thresholds (>₹40L).
12. **Pragmatic Reuse of Battle-Tested Open-Source & SaaS:** Commodity functions (Firebase Phone Auth, Razorpay SDK, `mobile_scanner`) utilize trusted libraries, reserving custom engineering for core differentiators.
13. **Statutory Data Minimization & Zero Client-Side Secrets:** Strict compliance with India’s DPDPA 2023. Zero payment gateway secrets, Firebase keys, or database credentials exist in the client binary.

---

## 11. Product Scope and Boundaries

### 11.1 MVP Must-Haves (In-Scope)
* Cross-platform Flutter mobile binary for Android 10+ and iOS 15+.
* FastAPI modular monolith with PostgreSQL 16 + PostGIS and Redis 7.0+.
* Passwordless Firebase Phone Authentication with server-side JWT minting.
* PostGIS spatial search (3km default, 5km max) with vehicle dimension compatibility.
* Universal 480-second reservation hold backed by `btree_gist` exclusion constraints.
* Razorpay UPI Intent checkout with raw HMAC webhook verification and durable idempotency.
* Dynamic 128-bit CSPRNG entry/exit access credentials with camera QR scanning.
* Controlled manual offline exception protocol for underground basement garages.
* Guaranteed Parking Recovery Protocol (GPRP) with 180s driver decision window.
* Canonical 6-stage asynchronous refund lifecycle (`REFUND_ELIGIBLE` to `REFUND_SETTLED`).
* Immutable double-entry general ledger with zero-child-lock balanced posting triggers.
* Property authorization document upload (encrypted S3) and operations audit queue.
* Weekly scheduled batch bank payouts via corporate account IMPS under MoR status.

### 11.2 Conditional Dependencies (External Launch Blockers)
* **DEP-PAY-01 (Payment Underwriting):** Formal merchant onboarding approval for parking marketplace category and dual gateway application (Razorpay + Cashfree).
* **DEP-TEL-01 (TRAI DLT Registration):** Telecom DLT registration for entity, header/sender ID, and transactional SMS templates.
* **DEP-LEG-01 (GST Tax Memorandum):** Written legal/tax counsel memorandum confirming GST Section 9(1) marketplace facilitation classification vs Section 9(5) ECO.
* **DEP-LEG-02 (Municipal Parking Legality):** Legal review on private residential driveway monetization under Bengaluru BBMP municipal regulations.
* **DEP-LEG-03 (Terms of Service & Non-Bailment):** Clickwrap Terms of Service disclaiming platform bailment liability under IT Act Section 79.

### 11.3 Post-MVP Features (Deferred to Phase 2+)
* Razorpay Route automated linked-account split payouts (upon meeting >₹40 Lakh turnover).
* Continuous multi-day parking leases and recurring monthly subscriptions.
* Physical barrier-gate relay hardware integrations and automated ANPR camera pilots.
* Electric vehicle (EV) charging kilowatt-hour sub-metering and billing.
* WhatsApp Business API notification sidecar.
* Cross-border international credit card payment processing.

### 11.4 Explicitly Excluded Features (Strictly Forbidden for MVP)
* **Mandatory IoT Ground Sensors:** No ultrasonic bay detectors or magnetic loop sensors.
* **Automated Number Plate Recognition (ANPR):** No computer vision camera streams.
* **Boom-Barrier Automation:** No hardware relay wiring or barrier gate motors.
* **In-App Stored Wallet:** No proprietary digital wallet or prepaid stored value balance (avoids RBI PPI licensing).
* **Dynamic Surge Pricing:** No algorithmic price gouging or predictive surge multipliers.
* **Premature Microservices:** No distributed microservice decomposition or multi-repository setups.
* **Public Consumer Web Portal:** No desktop booking website or public consumer web app.

---

## 12. Product Success Objectives

### 12.1 Strategic Performance & Success Metrics

| Domain | Metric Name | Mathematical Calculation & Definition | Target / Benchmark | Measurement Source / PRD Reference |
|---|---|---|---|---|
| **User Experience** | Spatial Search Latency | $t_{\text{response}} - t_{\text{request}}$ for `GET /api/v1/spaces/search` PostGIS queries at 95th percentile under 100 concurrent requests | **< 300ms (P95)** | PRD §38 / RTM NFR-001 |
| **User Experience** | End-to-End Discovery Latency | Total client-perceived round-trip for spatial search over standard 4G mobile network | **≤ 500ms (P95)** | PRD §5.2 / §38 |
| **User Experience** | Hold Acquisition Latency | PostgreSQL execution duration for `INSERT INTO space_reservations (..., status='ACTIVE_HOLD')` with GiST exclusion lock | **< 50ms (P99)** | PRD §38 / RTM NFR-002 |
| **User Experience** | Gate Scan Validation Latency | Elapsed time from guard scan payload receipt at `POST /api/v1/access/validate-scan` to validation response transmission | **< 250ms (P95)** | PRD §38 / RTM NFR-003 |
| **User Experience** | Booking Checkout Completion Time | Total wall-clock elapsed time from hold creation timestamp (`SCR-103`) to confirmed payment webhook arrival (`SCR-104`) | **< 60 Seconds** | PRD §18 / User Flows §1 |
| **User Experience** | Mobile App Crash-Free Rate | `(1 - (Fatal Crash Sessions / Total Active User Sessions)) * 100%` across Android and iOS production builds | **> 99.5%** | Mobile Architecture Spec / Crashlytics |
| **Marketplace** | Search-to-Hold Conversion Rate | `(Total Unique Active Holds Created / Total Unique Spatial Search Queries) * 100%` | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [01] |
| **Marketplace** | Hold-to-Booking Conversion Rate | `(Total Confirmed Bookings / Total Active Holds Acquired) * 100%` | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [01] |
| **Marketplace** | Bay Utilization (Peak Hours) | `(Total Reserved Bay-Hours / Total Available Scheduled Bay-Hours during 09:00–18:00 IST) * 100%` | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [01] / [03] |
| **Marketplace** | Driver 30-Day Repeat Rate | `(Unique Drivers with >= 2 Completed Bookings within 30 Days / Total Unique Drivers with >= 1 Completed Booking) * 100%` | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [01] |
| **Reliability** | Double-Booking Rate | `(Overlapping Active Holds or Bookings for Same Bay & Interval / Total Bookings) * 100%` | **EXACTLY 0.0%** | PRD §5.2 / §10.2 / §19 (`btree_gist`) |
| **Reliability** | Core API Uptime | `((Total Operating Minutes - Unplanned Downtime Minutes) / Total Operating Minutes [06:00–23:00 IST]) * 100%` | **> 99.9%** | PRD §38 / RTM NFR-004 |
| **Reliability** | General Ledger Imbalance | $\sum |\text{Total Debits} - \text{Total Credits}|$ across all posted journal entries in paise | **EXACTLY 0.00 (0 paise)** | PRD §22 / `trg_verify_journal_balance` |
| **Reliability** | Webhook Processing Loss | `(Unprocessed or Dropped Webhooks / Total Valid Gateway Webhook Dispatches) * 100%` | **EXACTLY 0.0%** | PRD §20 (Durable `payment_webhook_events`) |
| **Reliability** | Recovery Point Objective (RPO) | Data loss tolerance for committed ledger transactions under database failover (WAL streaming replication) | **EXACTLY 0 Seconds** | PRD §38 / NFR Reliability |
| **Reliability** | Recovery Time Objective (RTO) | Time to restore full container services after unexpected host instance termination | **≤ 15 Minutes** | PRD §38 / NFR Reliability |
| **Reliability** | Peak Concurrency Headroom | Simultaneous booking hold attempts per second supported without database connection exhaustion | **≥ 50 Holds/Sec** | PRD §38 / NFR Scalability |
| **Commercial** | Platform Net Margin (2h Stay) | $\text{Gross Commission (₹12.00)} + \text{Convenience Fee (₹10.00)} - \text{Gateway MDR (₹2.17)} = ₹19.83$ ($₹19.83 / ₹91.80 = 21.6\%$) | **₹19.83 (21.6% Net Take-Rate)** | PRD §37 / Business Assumptions §3.1 |
| **Commercial** | Net Host Entitlement (2h Stay)| $\text{Gross Base (₹80.00)} - \text{Commission (₹12.00)} - \text{GST on Commission (₹2.16)} = ₹65.84$ ($₹65.84 / ₹80.00 = 82.3\%$) | **₹65.84 (82.3% of Base)** | PRD §37 / Business Assumptions §3.1 |
| **Commercial** | Customer Acquisition Cost (CAC)| $\text{Total Driver Acquisition & Marketing Spend} / \text{Total New Verified First-Time Bookers}$ | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [07] |
| **Commercial** | Host Lifetime Value (LTV) | $\text{Average Monthly Net Commission per Host Bay} \times \text{Average Host Retention Lifespan (Months)}$ | `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` | Pilot Validation Domain [07] |
| **Operations** | Property Review Turnaround Time| Wall-clock elapsed time from host submission (`DRAFT`/`PENDING_REVIEW`) to operations determination (`APPROVED`/`REJECTED`) | **< 24 Hours** | PRD §11.6 / §13 / §31 / `FR-ADMIN-001` |
| **Operations** | GPRP Incident Recovery Time | Wall-clock elapsed time from arrival obstruction report to replacement bay confirmed or refund initiated | **< 180 Seconds** | PRD §5.2 / §26 / `FR-GPRP-001` |
| **Operations** | Dispute Resolution SLA | Wall-clock elapsed time from customer support incident creation to final administrative resolution | **< 24 Hours** | PRD §28 / Open Questions `OQ-BIZ-009` |
| **Operations** | Offline Sync Reconciliation Rate| `(Successfully Reconciled Offline Gate Admissions / Total Offline Exception Admissions) * 100%` | **> 99.99%** | `docs/technical/QR_ACCESS_DESIGN.md` §4 / RTM NFR-005 |

*Note: Numerical marketplace targets not established in the PRD are explicitly marked `TARGET TO BE ESTABLISHED THROUGH PILOT VALIDATION` per Section 1.2 source-of-truth governance.*

---

## 13. Development Milestones

The product engineering lifecycle is structured into **8 sequential implementation stages**:

```
[ Stage 1: Data Architecture & Concurrency ] ──> [ Stage 2: Modular Monolith Scaffolding ]
                     │                                                   │
                     ▼                                                   ▼
[ Stage 4: Payments & Refund Machine ]       <── [ Stage 3: Flutter Mobile Binary ]
                     │
                     ▼
[ Stage 5: Access Credentials & Guard App ]  ──> [ Stage 6: GPRP Recovery & Ops Queue ]
                                                                         │
                                                                         ▼
[ Stage 8: Pilot Staging & Field Launch ]    <── [ Stage 7: E2E Automation & Sandbox ]
```

### Stage 1: Core Data Architecture, Concurrency Locks & Ledger Engine
* **Purpose:** Establish the foundational PostgreSQL 16 schema, PostGIS extensions, temporal exclusion constraints, and double-entry ledger triggers.
* **Measurable Outcome:** Verified DDL schema capable of enforcing interval-based holds and append-only ledger balancing.
* **Upstream Dependencies:** None.
* **Completion Evidence:** 15 passing automated tests in `tests/database/` (`tests/database/test_booking_exclusion.py`, `tests/database/test_concurrent_posting.py`, `tests/database/test_ledger_immutability.py`) executed against live PostgreSQL 16.

### Stage 2: Backend Domain Scaffolding, MSAI & Modular Monolith Services
* **Purpose:** Build the containerized FastAPI modular monolith structure, service layers, and Multi-Source Availability Intelligence engine.
* **Measurable Outcome:** RESTful APIs for Auth, Inventory, MSAI Search, and Bookings operating within a single process.
* **Upstream Dependencies:** Stage 1 completion.
* **Completion Evidence:** OpenAPI contract schemas passing validation; PostGIS spatial search resolving in <300ms.

### Stage 3: Cross-Platform Flutter Mobile Binary & Dynamic Role Shells
* **Purpose:** Implement the single Flutter mobile codebase deploying to Android and iOS with role-based navigation shells (`SCR-101..107`, `SCR-201..205`, `SCR-301..304`, `SCR-401..402`).
* **Measurable Outcome:** Seamless mobile UX supporting driver search, host onboarding, guard scanning, and role switching.
* **Upstream Dependencies:** Stage 2 API contracts.
* **Completion Evidence:** Flutter widget and integration test suite passing clean; APK/IPA builds successful.

### Stage 4: Payment Orchestration, Webhooks & 6-Stage Refund State Machine
* **Purpose:** Integrate Razorpay UPI Intent checkout, durable database webhook idempotency, and the canonical 6-stage refund engine.
* **Measurable Outcome:** Robust payment processing supporting Late Payment Resolution Protocol (LPRP) without double-bookings.
* **Upstream Dependencies:** Stage 1 ledger triggers and Stage 2 booking services.
* **Completion Evidence:** Webhook idempotency test (`TS-05`) and LPRP late payment test (`TS-04`) passing.

### Stage 5: Dynamic Access Credentials, Guard Scanner & Offline Fallback
* **Purpose:** Implement the separated 128-bit CSPRNG access QR token generator, camera QR scanner, and offline basement manual exception protocol.
* **Measurable Outcome:** Sub-2-second gate check-in and checkout validation on mobile devices.
* **Upstream Dependencies:** Stage 3 mobile shell and Stage 4 booking confirmation.
* **Completion Evidence:** Token replay test (`TS-09`) passing; offline SQLite sync verified (`TS-17`).

### Stage 6: GPRP Incident Recovery & Operations Queue Workflows
* **Purpose:** Build the Guaranteed Parking Recovery Protocol (GPRP) 8-step alternative allocation engine and ops property review queue.
* **Measurable Outcome:** Automated arrival obstruction resolution within 180 seconds.
* **Upstream Dependencies:** Stage 2 MSAI and Stage 5 access control.
* **Completion Evidence:** GPRP arrival failure test (`TS-07`) and replacement booking flow (`TS-13`) passing.

### Stage 7: End-to-End Test Automation, CI/CD Hardening & Sandbox Verification
* **Purpose:** Harden the complete test pyramid, integrate CI/CD GitHub Actions pipelines, and verify all 15 business acceptance scenarios.
* **Measurable Outcome:** 100% green CI pipeline; zero obsolete enum references; fully verified sandbox demonstration.
* **Upstream Dependencies:** Stages 1 through 6.
* **Completion Evidence:** `python scripts/validate_spec.py` passes; full Pytest suite passes; GitHub Actions run green.

### Stage 8: Pilot Staging, Field Deployment & Controlled Micro-Market Launch
* **Purpose:** Execute field onboarding of 200 parking bays in Koramangala, Indiranagar, and HSR Layout; conduct guard training; launch closed pilot.
* **Measurable Outcome:** Real drivers successfully parking in verified private driveways with weekly host payouts.
* **Upstream Dependencies:** Stage 7 completion; all 5 external launch gate approvals (`DEP-PAY-01`, `DEP-TEL-01`, `DEP-LEG-01`, `DEP-LEG-02`, `DEP-LEG-03`).
* **Completion Evidence:** 200 verified properties active; first scheduled weekly batch bank payout executed via corporate account IMPS.

---

## 14. Jury Demonstration Objective

### 14.1 Purpose and Sandbox Framework
The jury demonstration provides an incontrovertible, live end-to-end proof of Gadispot’s cyber-physical capabilities. The demonstration runs in an **explicitly labeled sandbox environment** utilizing Razorpay test mode API keys, mock UPI handles, and simulated GPS coordinates centered on Bengaluru’s Koramangala commercial hub. The demonstration comprehensively exercises all four marketplace user roles (Driver Rohan, Space Owner Anand, Security Guard Ramesh, and Platform Operations Deepa), proving dynamic role transitions and end-to-end operational integrity.

### 14.2 The 12-Step Demonstration Journey (The Golden Path)

**Pre-Journey Verification Setup (Space Owner Anand & Operations Deepa):**  
Prior to driver discovery, Space Owner Anand onboards Bay A-1 via the Host Shell (`SCR-201..202`), configuring weekly operating hours (09:00–18:00) and uploading property title deed documentation. Platform Operations Associate Deepa audits the listing in the Operations Verification Queue (`SCR-401`), validates right-of-use evidence, and marks the property `APPROVED`, publishing Bay A-1 to spatial search. Host Anand connects his bank account with Penny-Drop verification (`SCR-205`).

```
[ 1. Phone Login ] ──> [ 2. Vehicle Setup ] ──> [ 3. Proximity Search ] ──> [ 4. Select Bay ]
         │                                                                             │
         ▼                                                                             ▼
[ 8. Dynamic QR ]  <── [ 7. Journal Post ]   <── [ 6. UPI Payment ]     <── [ 5. 480s Hold ]
         │
         ▼
[ 9. Guard Scan ]  ──> [ 10. Active Timer ]  ──> [ 11. Exit Scan ]       ──> [ 12. Payout & Ops ]
```

1. **Step 1 — Passwordless Authentication:** Driver launches Flutter app, enters Indian phone number (`+91 98765 43210`), receives simulated Firebase OTP, and backend mints scoped JWT session.
2. **Step 2 — Vehicle Profile Configuration:** Driver selects vehicle profile: Hyundai Creta (SUV), License Plate `KA-01-AB-1234`.
3. **Step 3 — Proximity Search & Discovery:** Driver searches for parking in Koramangala 4th Block; app executes PostGIS query returning 3 verified bays within 1.2km in <250ms.
4. **Step 4 — Space Details & Fare Inspection:** Driver inspects Bay A-1 (villa driveway), reviews verified photos, CCTV amenity, operating schedule, and transparent fare breakdown (₹80 parking + ₹10 convenience + ₹1.80 GST = ₹91.80).
5. **Step 5 — Atomic 480-Second Hold Acquisition:** Driver taps "Book This Bay"; backend acquires PostgreSQL GiST exclusion lock; screen renders active 480s countdown timer (`SCR-103`).
6. **Step 6 — Razorpay UPI Intent Payment:** App launches simulated Razorpay checkout; driver approves payment via mock UPI PIN; bank debits ₹91.80.
7. **Step 7 — Webhook Processing & Ledger Posting:** Webhook arrives at backend; raw HMAC signature is validated; reservation updates to `CONFIRMED`; double-entry journal posts balanced debits and credits ($\sum = ₹91.80$).
8. **Step 8 — Dynamic Entry QR Pass Generation:** Flutter app navigates to `SCR-104`, displaying dynamic, high-contrast access pass encoding 128-bit CSPRNG token (`spx_entry_...`).
9. **Step 9 — Guard Scanner Gate Clearance:** Guard launches Guard Scanner (`SCR-301`) on Android device, scans driver QR code; backend validates token in <250ms; screen renders bold Green Clearance ("ACCESS GRANTED: KA-01-AB-1234"); token is burned.
10. **Step 10 — Live Active Parking Session Tracking:** Driver app transitions to `SCR-105`, displaying live elapsed session countdown, property navigation, and dynamic extension option.
11. **Step 11 — Departure Gate Exit Scan:** At departure, guard scans exit QR pass; backend verifies session duration, records exit timestamp, and marks reservation `COMPLETED`.
12. **Step 12 — Automated Double-Entry Host Payout Credit & Ops Ledger Audit:** Backend posts completed session journal; Host Anand’s payable balance (Account 2010) is credited with ₹65.84 (82.3% of base tariff) on his mobile earnings dashboard (`SCR-204`); driver rates stay 5 stars (`SCR-106`). Simultaneously, Operations Associate Deepa inspects the Operations Ledger Audit View (`SCR-402`), verifying zero ledger leakage ($\sum \text{Debits} = \sum \text{Credits} = ₹91.80$) across accounts.

### 14.3 The 6 Failure & Edge-Case Demonstration Scenarios

To prove structural robustness across all four marketplace roles, the demonstration executes six explicit edge-case scenarios:

* **Scenario A — Concurrency Collision (HTTP 409 Conflict):** Two mobile workers simultaneously tap "Book This Bay" for the exact same slot and interval at the same millisecond. The jury observes Worker 1 acquire the 480s hold while Worker 2 immediately receives a graceful HTTP 409 "Space Just Claimed" notification without database corruption.
* **Scenario B — Late Payment Arrival (LPRP Full Refund):** Driver initiates a hold, allows the 480-second TTL to elapse without paying, while a competing driver books the slot. The first driver’s late payment webhook arrives. The jury observes the system detect the conflict, mark the reservation `RELEASED_UNFULFILLABLE`, and dispatch an automated 100% full refund (`REFUND_ELIGIBLE` $\to$ `REFUND_REQUESTED`).
* **Scenario C — QR Token Replay / Screenshot Forgery:** A driver captures a screenshot of an active entry pass and scans it at the gate. The guard scanner immediately rejects the scan with a bold red alert: "ACCESS REJECTED: QR code already consumed at 14:05:22".
* **Scenario D — Arrival Obstruction & GPRP Reallocation:** A driver arrives at a reserved bay to find an unauthorized vehicle parked in the slot. The guard taps "Report Space Blocked". The jury watches GPRP search inventory within 500m, acquire an alternative bay, present the reassignment offer with a 180s countdown, and issue a new entry QR pass upon driver acceptance at zero additional charge.
* **Scenario E — Unauthorized Property Listing & Operations Rejection (`SCR-202` / `SCR-401`):** A property owner attempts to onboard a common society parking area without submitting an authorized Society NOC (`SCR-202`). Platform Operations Associate Deepa inspects the document upload queue in `SCR-401`, notes the missing authorization evidence, and rejects the listing with the structured code `NOC_MISSING`. The space is blocked from search publication, demonstrating authorization-aware inventory gating and PRD Acceptance Scenario 10.
* **Scenario F — Subterranean Basement Offline Admission & 7-Day Purge (`SCR-303` / `FD-03`):** Guard Ramesh on B2 basement duty loses cellular connectivity. Driver Rohan arrives for a confirmed booking. Guard opens Today's Schedule (`SCR-303`), searches vehicle plate `KA-01-AB-1234` in the local encrypted SQLite cache, captures a timestamped vehicle approach photo, and taps "Manual Admit". The barrier opens. Once 4G connectivity restores, the offline record syncs to the backend and the photo is automatically enrolled in the 7-day AWS S3 purge lifecycle (`FD-03`, `BASE-SEC-03`, PRD Acceptance Scenario 9).

---

## 15. Pilot Objective

### 15.1 Pilot Scope & Micro-Market Selection
* **Geographic Boundary:** Bengaluru Urban Metro, Karnataka.
* **Selected Micro-Markets:** Koramangala, Indiranagar, and HSR Layout.
* **Target Inventory Size:** **200 verified parking bays** across private residential driveways, gated housing societies (RWAs), and commercial basements.
* **Pilot Operating Window:** 90 days.

### 15.2 The 11 Core Pilot Validation Areas

```
+----------------------------------------------------------------------------------------------------+
|                                    11 PILOT VALIDATION DOMAINS                                     |
+----------------------------------------------------------------------------------------------------+
| [01] Spatial Density & Search Conversion    : Search-to-booking conversion within 3km radius.      |
| [02] Driver Punctuality & Grace Period      : Arrival distribution against 30-min grace period.    |
| [03] Host Schedule Reliability & Blackouts  : Frequency of owner schedule compliance vs conflicts. |
| [04] Security Guard Scanner Usability       : Real-world scan latency on low-cost Android handsets.|
| [05] Subterranean Basement Offline Sync     : Frequency and reconciliation of offline admissions.  |
| [06] GPRP Reroute Frequency & Acceptance   : Incident rate (<2% target) and driver acceptance.    |
| [07] Unit Economics & Margin Realization    : Realization of ₹19.83 platform operating contribution|
| [08] Weekly Batch Host Payout Execution     : IMPS transfer success rate and ₹500 balance rule.    |
| [09] Payment Gateway Webhook Latency        : Gateway processing speed and drop rates under load.  |
| [10] Physical Overstay Frequency & Penalties: Frequency of >15m overstays and 1.5x fee enforcement.|
| [11] Dispute Frequency & Ops Turnaround     : Volume of customer support escalations (<24h SLA).   |
+----------------------------------------------------------------------------------------------------+
```

### 15.3 Commercial Policies Marked for Founder Decision During Pilot
The following 8 operational policies and commercial parameters operate under proposed baseline defaults during the pilot and require formal executive signoff before commercial scaling:
1. `POL-COM-01`: Platform Commission Take-Rate (15.0% proposed default) — `PROPOSED (Pending Founder Approval)`.
2. `POL-DUR-01`: Global Minimum Booking Duration (30 Minutes proposed default) — `PROPOSED (Pending Founder Approval)`.
3. `POL-CAN-01`: Tiered Cancellation Refund Schedule (>2h: 100%, 30m–2h: 50%, <30m: 0%) — `PROPOSED (Pending Founder Approval)`.
4. `POL-ARR-02`: Driver No-Show Grace Period Window (30 Minutes proposed default) — `PROPOSED (Pending Founder Approval)`.
5. `POL-OST-01`: Overstay Penalty Tariff Structure (1.5× hourly rate in 30m blocks) — `PROPOSED (Pending Founder Approval)`.
6. `POL-SUB-01`: GPRP Alternative Space Platform Subsidy Cap (₹100 cap) — `PROPOSED (Pending Founder Approval)`.
7. `POL-POT-01`: Host Payout Frequency & Minimum Threshold (Weekly Tuesdays, ₹500 threshold) — `PROPOSED (Pending Founder Approval)`.
8. `ASM-002`: Driver Platform Convenience Fee (Flat ₹10.00 proposed default per completed reservation) — `PROPOSED (Pending Founder Approval)`.

---

## 16. Commercial Launch Objective

Commercial launch signifies the transition from a closed 200-bay pilot to an open commercial marketplace. Launch authorization is strictly gated on clearing **five operational domains**:

### 16.1 Legal & Regulatory Requirements
* **IT Act Section 79 Non-Bailment Protection:** Executed Terms of Service establishing that Gadispot is an information intermediary facilitating parking reservations, disclaiming bailment, custody, theft, fire, or vehicle damage.
* **Municipal Trade Clarity:** Formal municipal memorandum confirming private driveway monetization compliance under Karnataka Municipal Corporations Act / BBMP rules.
* **RWA / Society Bye-Law Compliance:** Standardized Society NOC templates compliant with cooperative housing society precedents (*Nahalchand* ruling).

### 16.2 Privacy & Data Protection Requirements (DPDPA 2023)
* **Bilingual Consent Architecture:** In-app consent notices presented in English and Kannada prior to collecting mobile phone and location data.
* **Automated 7-Day Gate Photo Purge:** AWS S3 automated lifecycle expiration policy active, permanently purging offline guard verification photos after 7 days.
* **Data Minimization:** Vehicle license plates masked in public views; driver phone numbers completely shielded from security guards.

### 16.3 Cybersecurity & Infrastructure Requirements
* **Zero Client-Side Application Secrets:** Clean static security scan (`trufflehog`) confirming zero payment secrets or cloud credentials in the Flutter binary.
* **Database Volume Encryption:** PostgreSQL storage volumes encrypted at rest using AWS KMS (AES-256).
* **Transport Layer Security:** All API endpoints strictly enforcing HTTPS over TLS 1.3 with HSTS headers.
* **Role-Based Object Authorization:** Scoped JWT authorization preventing Insecure Direct Object References (IDOR) on bookings and properties.

### 16.4 Financial & Banking Requirements
* **Indirect Taxation (GST):** Legal memorandum classifying operations under GST Section 9(1) (facilitation service) and establishing Ledger Account 2030 segregation.
* **Dual Payment Gateway Activation:** Active merchant underwriting accounts with Razorpay and Cashfree under `PaymentGatewayPort` abstraction.
* **Merchant of Record Batch Payout Agreement:** Operating corporate current account with automated API IMPS payout rails and strict owner KYC (PAN + Penny Drop).

### 16.5 Field Operations Requirements
* **On-Premise Physical Signage:** High-contrast metal or vinyl QR signage installed at all pilot property entrances.
* **Guard Training Protocol:** Completion of on-site guard onboarding ensuring guards can execute QR scans and offline admissions in <2 seconds.
* **24-Hour Dispute Escalation Desk:** Operations desk equipped to resolve customer arrival escalations and refund failures within 24 hours.

---

## 17. Long-Term Product Direction

The following strategic capabilities represent the long-term post-MVP evolution of Gadispot and are **explicitly labeled as NON-MVP COMMITMENTS (Phase 2+)**:

```
+----------------------------------------------------------------------------------------------------+
|                                 LONG-TERM ROADMAP (PHASE 2 & BEYOND)                               |
+----------------------------------------------------------------------------------------------------+
| 1. Automated Barrier Gate Relays    : IoT microcontroller relays triggering boom barriers via      |
|                                       sub-gigahertz RF or Bluetooth Low Energy (BLE) upon QR scan. |
| 2. Automated Number Plate Rec (ANPR): Edge-AI computer vision cameras verifying arrivals via optical|
|                                       character recognition, eliminating manual guard scanning.    |
| 3. EV Charging Infrastructure       : Dynamic reservation of EV charging bays with sub-metered     |
|                                       kilowatt-hour billing integrated into the general ledger.    |
| 4. Razorpay Route Split Payouts     : Automated linked-account marketplace split transfers upon    |
|                                       achieving annual platform turnover exceeding ₹40 Lakhs.     |
| 5. Corporate Fleet Accounts         : Centralized billing dashboards and monthly invoicing for     |
|                                       enterprise cab aggregators, delivery vans, and corporate fleets|
| 6. Dynamic Demand Surge Pricing     : Predictive machine learning models adjusting hourly tariffs   |
|                                       based on hyper-local event demand and historical occupancy.  |
| 7. Multi-Day & Monthly Leases       : Long-term recurring monthly subscription contracts for       |
|                                       permanent residential and commercial tenant parkers.         |
+----------------------------------------------------------------------------------------------------+
```

---

## 18. Product Risks and Assumptions

### 18.1 Comprehensive Residual Risk Register

| Risk ID | Domain | Risk Description & Failure Mode | Pre-Rating | Architectural & Operational Safeguard | Post-Rating | Validation Method | Evidence-Based Status |
|---|---|---|---|---|---|---|---|
| **RSK-001 (RR-REG-01)** | Regulatory (Tax) | Tax authorities classify platform under GST Sec 9(5) instead of Sec 9(1), creating gross tax liability. | **HIGH / MED** | Ledger Account 2030 isolates tax on commission; modular pricing engine allows overnight formula swap. Tax memo is launch gate. | **LOW / MED** | Written indirect tax opinion (`DEP-LEG-01`). | `LEGAL PENDING [PILOT LAUNCH GATE]` |
| **RSK-002 (RR-REG-02)** | Regulatory (DPDPA) | Guard photo uploads during offline exceptions violate DPDPA 2023 retention rules. | **HIGH / LOW** | Encrypted SQLite storage on handset; automated 7-day AWS S3 photo purge rule (`BASE-SEC-03`). | **LOW / LOW** | S3 lifecycle verification and privacy audit. | `EMPIRICALLY VERIFIED` |
| **RSK-003 (RR-REG-03)** | Regulatory (Municipal)| BBMP challenges commercial monetization of residential driveways under zoning bylaws. | **MED / MED** | Pilot geofenced to white-plate private vehicles with verified Society/Landlord NOCs. | **LOW / LOW** | Municipal law review (`DEP-LEG-02`). | `LEGAL PENDING [PILOT LAUNCH GATE]` |
| **RSK-004 (RR-FIN-01)** | Financial (Rails) | Primary Payment Aggregator delays or rejects marketplace underwriting (`DEP-PAY-01`). | **HIGH / MED** | Dual-application architecture (`FD-01`); fallback batch IMPS payout engine (`FD-05`). | **LOW / LOW** | Provider underwriting approval and sandbox test. | `FOUNDER APPROVED [PILOT LAUNCH GATE]` |
| **RSK-005 (RR-FIN-02)** | Financial (Refunds) | Bank network latency on UPI refunds causes driver chargeback complaints. | **MED / HIGH** | Customer UI displays authoritative multi-stage progress (`REFUND_ELIGIBLE` $\to$ `SETTLED`) with bank UTR. | **LOW / MED** | Pilot banking switch monitoring. | `PROPOSED (Pending Founder Approval)` |
| **RSK-006 (RR-FIN-03)** | Financial (Margins) | Frequent GPRP reroutes to expensive bays erode platform margin. | **MED / LOW** | GPRP alternative space subsidy is hard-capped at ₹100 (`POL-SUB-01`); offending hosts fined ₹100. | **LOW / LOW** | Pilot ledger Account 4020 audit. | `PROPOSED (Pending Founder Approval)` |
| **RSK-007 (RR-OPS-01)** | Operations (Obstruction)| Reserved bay physically occupied upon driver arrival. | **HIGH / MED** | GPRP: Atomic 8-step engine reallocates bay within 500m in $\le 180\text{s}$ or issues 100% full refund (`FD-02`). | **LOW / LOW** | Live acceptance test `TS-07`. | `FOUNDER_APPROVED` |
| **RSK-008 (RR-OPS-02)** | Operations (Collusion) | Guard admits unregistered vehicles for off-the-books cash. | **MED / LOW** | Every manual admission requires photo proof; instant push alert sent to host with vehicle plate. | **LOW / LOW** | Host notification verification. | `PROPOSED (Pending Founder Approval)` |
| **RSK-009 (RR-OPS-03)** | Operations (Overstay) | Driver overstays booking window, blocking incoming reservation. | **HIGH / MED** | 1.5× hourly penalty tariff (`POL-OST-01`); backend alerts at $t_{\text{end}}+15\text{m}$; GPRP reroutes next driver. | **LOW / MED** | Automated overstay test `TS-19`.| `PROPOSED (Pending Founder Approval)` |
| **RSK-010 (RR-TECH-01)** | Technical (Telecom) | TRAI DLT registration delay blocks transactional booking confirmation SMS. | **MED / HIGH** | Firebase Phone Auth SDK handles auth; push notifications (FCM/APNs) act as primary access alerts. | **LOW / LOW** | DLT application tracking (`DEP-TEL-01`). | `EXTERNAL DEPENDENCY [PILOT LAUNCH GATE]` |
| **RSK-011 (RR-TECH-02)** | Technical (Hardware) | Low-end guard Android handsets suffer camera overheating during continuous scanning. | **MED / MED** | Camera lifecycle pauses feed when screen is idle; high-contrast manual 6-character fallback code. | **LOW / LOW** | Device testing on Android Go handsets. | `EMPIRICALLY VERIFIED` |
| **RSK-012 (RR-TECH-03)** | Technical (Concurrency)| Peak flash bookings cause database lock contention on popular slots. | **MED / LOW** | GiST exclusion constraints (`23P01`) reject conflicting holds at database storage engine level. | **LOW / LOW** | 15/15 tests passing on PostgreSQL 16. | `EMPIRICALLY VERIFIED` |
| **RSK-013 (DEP-LEG-03)** | Regulatory (Bailment) | Platform sued for vehicle theft, damage, fire, or property injury on host premises (`DEP-LEG-03`). | **HIGH / MED** | Mandatory in-app clickwrap Terms of Service with explicit non-bailment and intermediary safe harbor disclaimers under IT Act Section 79. | **LOW / LOW** | Corporate litigator signoff on Terms of Service (`DEP-LEG-03`). | `LEGAL PENDING [PILOT LAUNCH GATE]` |

---

## 19. Definition of Product Success

To eliminate vague assertions of readiness, Gadispot defines five progressive, verifiable **Readiness Gates**:

```
+----------------------------------------------------------------------------------------------------+
|                                    THE 5 GATES OF PRODUCT SUCCESS                                  |
+----------------------------------------------------------------------------------------------------+
| GATE 1: SPECIFICATION READY (Gate A)                                                               |
| Concrete Evidence: All 50 PRD sections complete; zero uncanonical enums; zero relative link breaks;|
| python scripts/validate_spec.py passes 100% green; founder decisions cataloged.                   |
+----------------------------------------------------------------------------------------------------+
| GATE 2: DEVELOPMENT READY (Gate B)                                                                 |
| Concrete Evidence: Containerized modular monolith scaffolding; PostgreSQL 16 schema with PostGIS  |
| and btree_gist; Zero Child Lock ledger triggers; 15/15 tests passing in pytest tests/ -v.          |
+----------------------------------------------------------------------------------------------------+
| GATE 3: DEMO READY (Gate C)                                                                        |
| Concrete Evidence: 12-step jury golden path verified in sandbox; 4 edge-case failure scenarios     |
| execute with graceful handling (HTTP 409 conflict, LPRP full refund, QR replay burn, GPRP reroute).|
+----------------------------------------------------------------------------------------------------+
| GATE 4: PILOT READY (Gate D)                                                                       |
| Concrete Evidence: 200 verified parking bays onboarded in Koramangala/Indiranagar/HSR; 100% hosts  |
| pass Penny-Drop bank verification; guard signage installed; batch IMPS payout engine verified.    |
+----------------------------------------------------------------------------------------------------+
| GATE 5: LAUNCH READY (Gate E)                                                                      |
| Concrete Evidence: Written GST Section 9(1) tax memorandum signed (DEP-LEG-01); BBMP municipal    |
| legality memorandum confirmed (DEP-LEG-02); dual payment gateway underwriting approved (DEP-PAY-01);|
| TRAI DLT templates active (DEP-TEL-01); IT Act Sec 79 Terms of Service published (DEP-LEG-03).    |
+----------------------------------------------------------------------------------------------------+
```

---

## 20. Final Product North Star

### 20.1 North Star Statement
> **"Every driver who books a space on Gadispot gets their guaranteed spot in under 2 seconds at the gate, or is made completely whole within 180 seconds — mathematically, physically, and financially."**

### 20.2 The 5 Non-Negotiable Product Outcomes
1. **Zero Double-Bookings Guaranteed:** Enforced mathematically at the database engine layer via PostgreSQL GiST exclusion locks; two drivers can never hold or confirm the same physical bay for overlapping time intervals.
2. **Zero Speculative or Unverified Inventory:** No property is published to search without verified legal right-of-use evidence (sale deed, tax receipt, or society NOC); no slot is displayed unless all 7 MSAI operational signals confirm availability.
3. **Sub-2-Second Gate Admission Clearance:** Security guards validate access passes and render admission verdicts in under 2 seconds on standard smartphones, eliminating gate queues without CapEx hardware.
4. **100% Balanced and Auditable General Ledger:** Every rupee collected via UPI is balanced across double-entry debits and credits ($\sum \text{Debits} = \sum \text{Credits}$), backed by immutable database triggers and Penny-Drop verified weekly host payouts.
5. **Deterministic GPRP Recovery / 100% Full Refund Guarantee:** If physical obstruction occurs, the driver receives an alternative bay within 500m or an automated 100% full refund within 180 seconds.

### 20.3 The 5 Guiding Product Principles
1. **Pessimism Over Growth:** Better to show zero spots than send a driver to a phantom bay.
2. **Deterministic Over Eventual:** Database ACID serialization over optimistic application-level distributed locks.
3. **Hardware Agnostic Over Heavy CapEx:** Smartphone camera QR verification over brittle boom-barrier IoT.
4. **Transparent Accounting Over Loosely Tracked Balances:** Immutable double-entry ledger over floating balances.
5. **Honest Readiness Over Synthetic Scores:** Readiness measured by executed PostgreSQL test suites and signed legal documents, never by ungrounded declarations.

### 20.4 Unwavering Commercial Viability Focus
Gadispot is not a vanity mobility experiment. It is engineered from Day 1 to achieve sustainable unit economics. With a **net platform operating contribution of ₹19.83 (21.6% net take-rate)** and a **net host entitlement of ₹65.84 (82.3%)** on a standard 2-hour parking stay, Gadispot proves that urban mobility challenges can be solved through engineering discipline, regulatory compliance, and mutually rewarding economic incentives.
