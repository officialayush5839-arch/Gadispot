# Gadispot — Master Product & Technical Architecture Blueprint

> **Document Identifier:** ARCH-GSP-2026-V1.0-VERIFIED  
> **Document Title:** Comprehensive Master Product and Technical Architecture Blueprint  
> **Governing Baseline:** Master PRD V2.3.2-VERIFIED ([PRD.md](PRD.md)), Engineering Rules ([rules.md](rules.md)), Product Goals ([goal.md](goal.md))  
> **Target Pilot Geography:** Bengaluru Urban Metro, Karnataka, India (Koramangala, Indiranagar, HSR Layout — 200 Pilot Bays)  
> **Target Execution Platforms:** Mobile-First (Single Cross-Platform Flutter Codebase for Android & iOS)  
> **Backend Architecture:** In-Process Modular Monolith (Python 3.11+ / FastAPI / PostgreSQL 16 + PostGIS + `btree_gist` / Redis 7.0+)  
> **Enforcement Level:** Mandatory System Architecture & Engineering Standard across all components  
> **Status:** Authoritative Repository Architecture Blueprint (Implementation-Ready)  

---

## Section 1 — Document Identity and Architecture Governance

### 1.1 Document Purpose & Authority
This document, `architecture.md`, establishes the authoritative, binding, implementation-ready product and technical architecture blueprint for **Gadispot** (formerly SmartPark Exchange). It translates the product requirements defined in [PRD.md](PRD.md), the strategic objectives defined in [goal.md](goal.md), and the engineering governance constraints defined in [rules.md](rules.md) into concrete, verified software architectures, interface contracts, database schemas, and operational topologies.

All subsequent software engineering tasks—including Flutter client development, FastAPI application services, database migrations, security controls, and deployment manifests—MUST conform strictly to this blueprint.

### 1.2 Strict Source-of-Truth Hierarchy
When designing components, reconciling specifications, or evaluating competing proposals, all engineers and automated agents MUST observe the strict 8-level source-of-truth precedence hierarchy:

```
+---------------------------------------------------------------------------------------------------+
|                                  SOURCE-OF-TRUTH PRECEDENCE HIERARCHY                              |
+---------------------------------------------------------------------------------------------------+
| Level 1: Explicitly Approved Founder Decisions (FD-01 through FD-05 in FOUNDER_DECISION_CHECKLIST)|
| Level 2: Latest Authoritative Master PRD (PRD.md Version 2.3.2-VERIFIED)                          |
| Level 3: Current Decision Log (DECISION_LOG.md) and Founder Decision Checklist                    |
| Level 4: Product Goals and Governance Charters (goal.md, PROJECT.md, README.md)                   |
| Level 5: Approved Product & Technical Specifications (docs/product/*, docs/technical/*)          |
| Level 6: Existing Implementation & Verified Test Suite (tests/conftest.py, tests/database/*)      |
| Level 7: Audit Findings & Risk Registers (docs/audits/V2_3_2_FINAL_AUDIT.md, etc.)                |
| Level 8: Historical Recommendations & Older Document Versions (retained strictly for context)     |
+---------------------------------------------------------------------------------------------------+
```

### 1.3 Component Status Taxonomy
Every architectural module, operational policy, and technology decision is classified using a strict 6-tier status taxonomy:

1. **`APPROVED`**: Formally signed off by founders or established as verified baseline architecture (e.g., `FD-01` through `FD-05`, PostgreSQL 16 GiST exclusion constraints, FastAPI modular monolith, 480-second hold TTL, Zero Child Lock trigger protocol).
2. **`PROPOSED`**: Fully modeled in specification but awaiting formal founder signature (e.g., commercial policies `POL-COM-01`, `POL-DUR-01`, `POL-CAN-01`, `POL-ARR-02`, `POL-OST-01`, `POL-POT-01`, `POL-SUB-01`).
3. **`ASSUMPTION`**: Validated business or operational hypotheses subject to empirical pilot measurement (e.g., 500m maximum walking radius, smartphone ubiquity among security guards, 200 pilot bay inventory cap).
4. **`IMPLEMENTED`**: Concretely written and passing automated verification tests in the repository (e.g., PostgreSQL 16 database test schema, GiST exclusion constraints, Zero Child Lock balanced journal trigger, and 15 automated database tests in `tests/database/`).
5. **`NOT IMPLEMENTED`**: Fully designed in architecture and specifications, ready for Sprint 1 engineering implementation, but not yet present in repository source code (e.g., Flutter mobile application screens, FastAPI router endpoints, SQLAlchemy models, Alembic migrations, Redis caching layers, background Celery/ARQ workers).
6. **`BLOCKED`**: Architecture complete, but commercial or operational execution is gated on external third-party deliverables (e.g., `DEP-LEG-01` GST Section 9(1) vs 9(5) tax memo, `DEP-PAY-01` Razorpay Route PA underwriting, `DEP-TEL-01` TRAI DLT registration for transactional SMS).

### 1.4 Repository Inspection and Implementation State Determination
Per Requirement R1, an exhaustive inspection of the existing Gadispot repository filesystem was conducted across all major application subsystems. The determination for each target subsystem is recorded below:

| Subsystem / Component | Repository Evidence & Verification Target | Implementation Status | Technical Rationale & Sprint Mapping |
|---|---|---|---|
| **Flutter Mobile Application** | Root inspection: Zero `.dart` files or `pubspec.yaml` present in repository. | `NOT IMPLEMENTED` | Mobile client architecture is fully designed across Clean Architecture + BLoC layers, dynamic shells, and screens (`SCR-001..003`, `SCR-101..108`, `SCR-201..204`, `SCR-301..304`, `SCR-401..402`). Implementation begins in Sprint 1. |
| **FastAPI Backend Application** | Root inspection: Zero `src/` application files, `main.py`, or FastAPI app instances. | `NOT IMPLEMENTED` | In-process modular monolith architecture and Pydantic v2 schemas are fully specified across 8 domain modules. Service implementation begins in Sprint 1. |
| **Database Models** | Root inspection: No ORM model definitions (SQLAlchemy declarative models) in repository code. | `NOT IMPLEMENTED` | Complete physical DDL schemas and constraint specifications are established in [docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) and tested via fixtures in `tests/conftest.py`. |
| **Database Migrations** | Root inspection: No `alembic/` migration directory or revision scripts exist. | `NOT IMPLEMENTED` | Baseline migration scripts to generate the production PostgreSQL 16 schema will be authored and committed during Sprint 0 / Sprint 1 kickoff. |
| **API Routers** | Root inspection: No APIRouter definitions or HTTP endpoint handlers present. | `NOT IMPLEMENTED` | REST endpoint contracts and RFC 7807 problem detail payloads are fully specified in Section 21 and [docs/technical/API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md). |
| **Service Layers** | Root inspection: No domain business logic service classes present in repository. | `NOT IMPLEMENTED` | Domain service interfaces, state machine transitions, and concurrency locking rules are completely specified in Sections 11–20. |
| **Payment / Auth / QR Code** | Root inspection: No live gateway SDK integrations, Firebase Admin wrappers, or token minting code. | `NOT IMPLEMENTED` | `PaymentGatewayPort`, Firebase RS256 token exchange, and 128-bit CSPRNG token minting algorithms are fully defined and ready for adapter implementation. |
| **Automated Test Suite** | Filesystem inspection: 15 passing tests across 3 modules in `tests/database/` with `pytest.ini`. | `IMPLEMENTED` | Real automated test suite executing against live PostgreSQL 16: 4 booking exclusion tests, 2 concurrent posting tests, 9 ledger immutability tests (`pytest tests/ -v`). |
| **Deployment Configuration** | Root inspection: No `Dockerfile`, `docker-compose.yml`, Kubernetes manifests, or Terraform code. | `NOT IMPLEMENTED` | Production multi-AZ AWS Mumbai `ap-south-1` topology, ECS Fargate specifications, and WAF rules are completely modeled in Section 25. |

### 1.5 Master Component Classification Matrix
Every major platform architectural component, commercial policy, and external dependency is classified using the 6-tier taxonomy:

| Architectural Component | Category | Status Tier | Authority Baseline / Decision Ref |
|---|---|---|---|
| **GiST Temporal Exclusion Constraint** | Data Architecture | `APPROVED` & `IMPLEMENTED` | PRD §62, [docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md), `test_booking_exclusion.py` |
| **Zero Child Lock Ledger Posting Trigger** | FinTech Architecture | `APPROVED` & `IMPLEMENTED` | PRD §66, [docs/technical/PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md), `test_concurrent_posting.py` |
| **Immutable Posted Journal Enforcement** | FinTech Architecture | `APPROVED` & `IMPLEMENTED` | PRD §66, `test_ledger_immutability.py` |
| **Dual Payment Gateway Strategy** | Payment Architecture | `APPROVED` | Founder Decision `FD-01` (`PaymentGatewayPort` for Razorpay + Cashfree) |
| **GPRP 100% Full Refund Failover** | Recovery Architecture | `APPROVED` | Founder Decision `FD-02` (Automatic failover to `REFUND_ELIGIBLE`) |
| **Controlled Offline Guard Exception** | Field Access Architecture | `APPROVED` | Founder Decision `FD-03` (Encrypted SQLCipher queue + 7-day photo purge) |
| **Configurable Max Booking Duration (24h)**| Booking Policy | `APPROVED` | Founder Decision `FD-04` (`properties.max_booking_hours`) |
| **Corporate Bank IMPS Batch Payouts** | Treasury Architecture | `APPROVED` | Founder Decision `FD-05` (Direct scheduled batch payouts) |
| **480-Second (8-Minute) Checkout Hold** | Booking Architecture | `APPROVED` | PRD §61, Two-Tier Expiration Engine (ADR-007) |
| **In-Process Modular Monolith (FastAPI)** | Systems Architecture | `APPROVED` | ADR-001, PRD §55 |
| **Single Cross-Platform Flutter Client** | Mobile Architecture | `APPROVED` | ADR-008, PRD §56 |
| **Platform Commission Rate (15.0%)** | Commercial Policy | `PROPOSED` | `POL-COM-01` ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)) |
| **Minimum Booking Duration (30 Minutes)** | Commercial Policy | `PROPOSED` | `POL-DUR-01` ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)) |
| **Tiered Cancellation Refunds** | Commercial Policy | `PROPOSED` | `POL-CAN-01` (>2h: 100%, 30m–2h: 50%, <30m: 0%) |
| **Driver No-Show Grace Period (30 Min)** | Field Policy | `PROPOSED` | `POL-ARR-02` ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)) |
| **Overstay Penalty Tariff (1.5× Rate)** | Commercial Policy | `PROPOSED` | `POL-OST-01` ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)) |
| **Weekly Tuesday Host Payouts (₹500 Min)** | Treasury Policy | `PROPOSED` | `POL-POT-01` ([docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md)) |
| **GPRP Subsidy Absorption Cap (₹100)** | Commercial Policy | `PROPOSED` | `POL-SUB-01` (Absorbed via Account 4020) |
| **500m Maximum Walking Radius** | Discovery Geometry | `ASSUMPTION` | Pilot behavioral assumption for urban Bengaluru drivers |
| **Smartphone Ubiquity Among Guards** | Operational Infrastructure | `ASSUMPTION` | Operational assumption: 100% of pilot guards possess Android 10+ devices |
| **200 Pilot Bay Inventory Cap** | Pilot Operations | `ASSUMPTION` | Initial pilot boundary across Koramangala, Indiranagar, HSR Layout |
| **Flutter UI Screens (`SCR-101..402`)** | Mobile Client | `NOT IMPLEMENTED` | Designed to specification; scheduled for Sprint 1 |
| **FastAPI Routers and Service Handlers** | Backend Application | `NOT IMPLEMENTED` | Designed to specification; scheduled for Sprint 1 |
| **Alembic Database Migration Pipeline** | Data Pipeline | `NOT IMPLEMENTED` | DDL baselined; migrations scheduled for Sprint 0/1 |
| **Indirect Taxation Written Memo (GST)** | Legal / Tax Compliance | `BLOCKED` | `DEP-LEG-01` (Pending written opinion on GST 9(1) vs 9(5)) |
| **Payment Aggregator Route Underwriting**| Fintech Compliance | `BLOCKED` | `DEP-PAY-01` (Razorpay Route / Cashfree Split under risk review) |
| **TRAI DLT Transactional SMS Template** | Telecom Compliance | `BLOCKED` | `DEP-TEL-01` (DLT entity registration and sender ID filing) |
| **Municipal Parking Monetization Review**| Municipal Law | `BLOCKED` | `DEP-LEG-02` (Bengaluru BBMP private driveway monetization guidelines) |
| **Terms of Service & Non-Bailment Terms**| Corporate Litigation | `BLOCKED` | `DEP-LEG-03` (IT Act Section 79 liability and clickwrap terms) |

### 1.6 Source-of-Truth Conflict Analysis and Resolutions
To uphold the zero silent reconciliation rule, known divergences between project artifacts are formally documented alongside their root cause and resolution:

1. **Reservation Status Enum Discrepancy (`RELEASED_EXPIRED` vs `EXPIRED_HOLD`):**
   - *Conflict:* The test fixture schema in `tests/conftest.py` defines `RELEASED_EXPIRED` and `CANCELLED_BY_HOST`, whereas the authoritative DDL in [docs/technical/DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) and PRD V2.3.2 standardize on `EXPIRED_HOLD` and `CANCELLED_BY_OWNER`.
   - *Root Cause:* Historical test harness preserved earlier v2.1 naming conventions while validating GiST exclusion mechanics.
   - *Resolution & Impact:* `EXPIRED_HOLD` and `CANCELLED_BY_OWNER` are the authoritative production enum values. The test suite fixture in `tests/conftest.py` will be harmonized during Sprint 1 without impacting the proven exclusion logic.
2. **Scenario Count Harmonization:**
   - *Conflict:* Earlier documents mentioned differing numbers of test scenarios.
   - *Resolution:* Exactly three distinct counts exist and are verified: (a) 15 end-to-end user acceptance workflows in PRD §42, (b) 20 technical high-risk test scenarios (TS-01..TS-20) in [docs/quality/TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md), and (c) 15 executable database integration tests in `tests/database/`.
3. **Founder Commercial Decisions vs Technical Defaults:**
   - *Conflict:* Historical drafts claimed commercial policies were signed off, whereas founder checklist indicates pending status.
   - *Resolution:* All 7 commercial policies are strictly classified as `PROPOSED (Pending Founder Approval)`. The backend architecture parameterizes these values in configuration tables, ensuring zero code rewrites when founders execute formal signatures.
4. **External Regulatory Blockers vs Application Readiness:**
   - *Conflict:* Third-party dependencies (`DEP-LEG-01`, `DEP-PAY-01`, `DEP-TEL-01`) gate live commercial transactions.
   - *Resolution:* Technical architectures are fully decoupled via ports (`PaymentGatewayPort`, batch bank transfer fallback, modular GST ledger accounts). Application development (Sprint 1) proceeds unhindered; only live production traffic is gated on external clearances.

### 1.7 Architecture Governance and Change Management
- **Architectural Decision Records (ADRs):** Any modification to system topology, data storage engines, security boundaries, or interface protocols MUST be submitted as a numbered ADR in [docs/product/DECISION_LOG.md](docs/product/DECISION_LOG.md).
- **Zero Silent Reconciliation:** If technical specifications or business requirements diverge, the divergence MUST be explicitly documented as an open conflict rather than silently resolved by developer preference.
- **Verification-Gated Progression:** No architectural component can transition to `IMPLEMENTED` without passing regression tests (`pytest tests/ -v`) and specification validation (`python scripts/validate_spec.py`).

---

## Section 2 — Product and System Overview

### 2.1 Product Mission & Commercial Grounding
Gadispot is an authoritative hyper-local urban parking marketplace utility engineered to unlock underutilized private parking capacity in dense metropolitan hubs across India. Beginning with a bounded commercial pilot of 200 parking bays in the Bengaluru Urban Metro (Koramangala, Indiranagar, and HSR Layout), the platform connects space owners (residential driveways, gated apartment societies, commercial basements) with drivers seeking guaranteed, pre-booked parking bays.

Gadispot is architected as a commercial marketplace utility. It enforces statutory compliance with the Digital Personal Data Protection Act 2023 (DPDPA), the Information Technology Act 2000 (Section 79 non-bailment intermediary protection), the Central Goods and Services Tax Act 2017 (GST), and Reserve Bank of India (RBI) Payment Aggregator guidelines.

### 2.2 Core Market Problem & Solution Mechanics
Urban drivers in Indian Tier-1 cities waste 15 to 25 minutes per trip hunting for curb-side parking, causing congestion, fuel wastage, and unpredictable arrival delays. Concurrently, thousands of private residential driveways and gated apartment parking bays sit vacant during standard business hours (08:00 to 20:00).

Gadispot resolves this friction through four structural engineering pillars:
1. **Pessimistic Availability Intelligence (MSAI):** Synthesizing 7 operational signals to eliminate false positives.
2. **Mathematical Double-Booking Exclusion:** PostgreSQL GiST range constraints physically preventing conflicting reservations.
3. **Hardware-Agnostic Gate Access:** Smartphone-native QR scanning and controlled offline exception modes for security guards without requiring on-premise barrier hardware.
4. **Guaranteed Failure Recovery (GPRP):** An automated protocol providing alternative bay rerouting within 500m or full refunds if an arrival fails.

### 2.3 System Actors and Interaction Modes
- **Driver:** Discovers nearby parking bays via mobile map, filters by vehicle category, locks an 8-minute (480-second) checkout hold, completes UPI/card payment, presents a dynamic access pass QR at gate check-in, and tracks active parking duration.
- **Space Owner (Host):** Registers private property, uploads legal ownership/NOC documents, configures parking bays and operating schedules, views real-time occupancy and earnings, and receives weekly batch disbursements.
- **Security Guard:** Stationed at property gates, operates the dedicated guard scanner interface (`SCR-301..304`), validates driver QR credentials in under 500ms, manages gate entry/exit, executes manual exception overrides during basement network outages, and logs obstruction incidents.
- **Platform Operations / Admin:** Audits owner property onboarding submissions, inspects title documents, resolves GPRP reroute edge cases, manages banking reconciliation, and reviews operational audit logs.

### 2.4 System Context Diagram (Sequential Diagram 1 / Mandatory PRD Diagram 1)

```mermaid
flowchart TD
    subgraph Users ["System Actors"]
        Driver["Driver\n(Flutter iOS / Android)"]
        Owner["Space Owner\n(Flutter iOS / Android)"]
        Guard["Security Guard\n(Flutter Scanner SCR-301..304)"]
        Ops["Platform Operations\n(Admin Console / Mobile)"]
    end

    subgraph GadispotSystem ["Gadispot Platform Boundary"]
        FastAPIMonolith["FastAPI Modular Monolith\n(In-Process Python 3.11 Backend)"]
        PostgresDB[("PostgreSQL 16 + PostGIS\n+ btree_gist Engine")]
        RedisCluster[("Redis 7.0+\nCache, Rate Limits, Outbox")]
    end

    subgraph ExternalSaaS ["External SaaS & Regulatory Infrastructure"]
        Firebase["Firebase Phone Auth\n(OTP Verification)"]
        Razorpay["Razorpay Payment Gateway\n(UPI / Cards / NetBanking)"]
        Cashfree["Cashfree Payments\n(Secondary Standby Gateway)"]
        CorporateBank["Corporate Banking Rail\n(Batch IMPS Host Disbursements)"]
        AWS_S3["AWS S3 (Mumbai ap-south-1)\n(Encrypted Proof Storage)"]
        DLT_SMS["TRAI DLT SMS Gateway\n(Gupshup / Twilio)"]
        FCM["Firebase Cloud Messaging\n(Push Notifications)"]
    end

    Driver -->|"HTTPS / TLS 1.3\nSearch, Hold, Pay"| FastAPIMonolith
    Owner -->|"HTTPS / TLS 1.3\nListing, Schedule, Earnings"| FastAPIMonolith
    Guard -->|"HTTPS / TLS 1.3\nValidate Scan, Offline Sync"| FastAPIMonolith
    Ops -->|"HTTPS / TLS 1.3 + 2FA\nProperty Audit, Finance"| FastAPIMonolith

    FastAPIMonolith <-->|"ACID SQL / GiST Exclusion\nZero Child Lock Ledger"| PostgresDB
    FastAPIMonolith <-->|"Ephemeral Cache\nIdempotency TTL"| RedisCluster

    FastAPIMonolith -->|"ID Token Validation"| Firebase
    FastAPIMonolith -->|"Order Creation & Refunds"| Razorpay
    Razorpay -.->|"Raw HMAC Webhooks"| FastAPIMonolith
    FastAPIMonolith -->|"Secondary Standby Port"| Cashfree
    FastAPIMonolith -->|"Weekly Tuesday Batch Payouts"| CorporateBank
    FastAPIMonolith -->|"Presigned Uploads & 7-Day Purge"| AWS_S3
    FastAPIMonolith -->|"Transactional SMS"| DLT_SMS
    FastAPIMonolith -->|"Push Alerts"| FCM
```

---

## Section 3 — Architecture Goals and Non-Goals

### 3.1 Architecture Goals
1. **Engine-Level Concurrency Safety:** Guarantee zero double-bookings under arbitrary concurrent loads using PostgreSQL storage-engine GiST exclusion constraints (`tstzrange`), rejecting reliance on application-layer locks or Redis counters for authoritative concurrency.
2. **Immutable Double-Entry Ledger:** Track all financial movements across balanced journal headers and journal lines satisfying $\sum \text{Debits} = \sum \text{Credits}$ with minimum two lines, protected against concurrent posting deadlocks via the Zero Child Lock protocol.
3. **Sub-500ms Gate Scan Verification:** Ensure gate access check-in latency is strictly below 500ms on standard 4G networks to eliminate vehicle queuing at residential gates.
4. **Deep Basement Offline Resilience:** Support controlled manual exception workflows with local encrypted storage (SQLCipher AES-256) and tamper-evident event hashing when guards operate in underground basements without cellular connectivity.
5. **Decoupled Multi-Vendor Adapters:** Isolate core domain logic from external payment, payout, SMS, and cloud storage providers using strict abstract port interfaces (`PaymentGatewayPort`, `PayoutEnginePort`, `SMSPort`).
6. **Regulatory Compliance & Data Localization:** Ensure 100% data residency within India (AWS Mumbai `ap-south-1`), enforce DPDPA 2023 data minimization, and implement automated 7-day cryptographic purging of gate surveillance photos.

### 3.2 Architecture Non-Goals (Explicit Exclusions)
1. **No Microservices Decomposition for MVP:** Rejection of multi-repo microservices, distributed transaction sagas (e.g., across booking and payment), and service meshes during the initial commercial pilot.
2. **No Hardware Infrastructure Dependencies:** Zero reliance on on-premise boom barriers, RFID tags, inductive loops, ultrasonic ceiling sensors, or ANPR cameras. All interactions run on existing consumer mobile hardware.
3. **No In-App Stored-Value Wallet:** Gadispot acts strictly as a payment facilitator routing transactions to verified UPI and banking rails. No proprietary closed or semi-closed prepaid wallet (PPI) is operated, avoiding RBI PPI licensing overhead.
4. **No Algorithmic Surge Pricing in Pilot:** Tariffs are explicitly configured as static hourly rates per bay by property owners. Real-time dynamic algorithmic surge pricing is deferred to post-pilot phases.
5. **No Multi-Day or Continuous Monthly Leasing in MVP:** Bookings are bounded to a maximum duration of 24 hours (`max_booking_hours`). Multi-week and monthly lease contracts are deferred to Phase 2.

---

## Section 4 — Architecture Style and System Topology

### 4.1 Architectural Style: The Pragmatic In-Process Modular Monolith
Gadispot adopts an **In-Process Modular Monolith** architecture built on **Python 3.11+** and **FastAPI**. Microservice architectures at seed stage introduce catastrophic failure modes: distributed consensus latencies, network partition vulnerabilities during checkout, out-of-order event sagas, and massive DevOps overhead.

In Gadispot:
- All domain modules (`iam`, `inventory`, `search`, `msai`, `booking`, `payment_ledger`, `gate_access`, `gprp`) execute within a single containerized FastAPI process.
- Cross-domain calls execute via strongly typed Python asynchronous method invocations (`async def`), achieving near-zero latency (<0.1ms) and eliminating network serialization hops.
- Multi-domain transactional workflows (e.g., Hold Creation -> Ledger Line Reservation -> Exclusion Constraint Validation) execute inside a **single ACID database transaction** on PostgreSQL.
- Each domain module strictly encapsulates its database tables. Direct cross-domain SQL joins are forbidden at the application layer; data exchange occurs via domain Data Transfer Objects (DTOs).

### 4.2 System Topology and Network Perimeter
The production topology is hosted in the **AWS Mumbai (`ap-south-1`)** region across three Availability Zones (AZs):
1. **Edge Ingress Layer:** AWS CloudFront CDN terminates client TLS 1.3 connections, applies AWS WAF rules (DDoS mitigation, rate-limiting at 100 requests/minute per IP, and India geo-fencing), and routes dynamic API requests to an Application Load Balancer (ALB).
2. **Compute Tier (VPC Private Subnet):** Stateless FastAPI application tasks run on AWS ECS Fargate across multiple AZs. Tasks autoscale horizontally based on CPU utilization (>60%) and concurrent request count.
3. **Data Tier (VPC Isolated Database Subnet):** AWS RDS PostgreSQL 16 Multi-AZ instance (primary writer and read replica) and AWS ElastiCache for Redis Cluster reside in private subnets with zero public internet routing. All egress to external SaaS APIs (Razorpay, Firebase) routes through managed AWS NAT Gateways.

### 4.3 High-Level Component Architecture (Sequential Diagram 2 / Mandatory PRD Diagram 2)

```mermaid
flowchart TD
    subgraph ClientLayer ["Mobile Client Layer (Single Flutter Binary)"]
        DriverUI["Driver Shell\n(SCR-101..108)"]
        OwnerUI["Owner Shell\n(SCR-201..204)"]
        GuardUI["Guard Scanner\n(SCR-301..304)"]
        OpsUI["Ops Console\n(SCR-401..402)"]
    end

    subgraph IngressLayer ["Ingress & Perimeter Security"]
        CloudFront["AWS CloudFront + WAF\n(TLS 1.3, Geo-Fencing, Rate Limiting)"]
        ALB["Application Load Balancer\n(VPC Ingress, SSL Offload)"]
    end

    subgraph BackendApp ["FastAPI Modular Monolith (ECS Fargate Tasks)"]
        APIRouter["API Router & Middleware\n(Auth, CORS, Idempotency, RFC 7807)"]
        
        subgraph DomainModules ["In-Process Domain Modules"]
            IAM["IAM & Auth\nModule"]
            Inventory["Property & Inventory\nModule"]
            SearchMod["Geospatial Search\nModule"]
            MSAIMod["MSAI Availability\nEngine"]
            BookingMod["Booking & Hold\nEngine (480s TTL)"]
            PayLedger["Payment & Double-Entry\nLedger Module"]
            GateAccess["QR Access & Guard\nSession Module"]
            GPRPMod["GPRP Recovery\nEngine"]
        end

        subgraph Adapters ["Decoupled Provider Adapters"]
            PayAdapter["PaymentGatewayPort\n(Razorpay / Cashfree)"]
            PayoutAdapter["PayoutEnginePort\n(Corporate Bank IMPS)"]
            SMSAdapter["SMSPort\n(TRAI DLT Gupshup/Twilio)"]
            PushAdapter["PushNotificationPort\n(Firebase Cloud Messaging)"]
            StorageAdapter["StoragePort\n(AWS S3 Presigned URLs)"]
        end
    end

    subgraph DataStorage ["Persistent Data Storage Tier"]
        PostgresPrimary[("AWS RDS PostgreSQL 16\nPrimary Writer (ACID, GiST, Triggers)")]
        PostgresReplica[("AWS RDS PostgreSQL 16\nRead Replica (Search Discovery)")]
        RedisCache[("AWS ElastiCache Redis 7.0\nCache, Rate Limits, Outbox Streams")]
        S3Bucket[("AWS S3 Private Bucket\nEncrypted KYC, 7-Day Purge Photos")]
    end

    ClientLayer -->|"HTTPS / TLS 1.3"| CloudFront
    CloudFront --> ALB
    ALB --> APIRouter
    APIRouter --> DomainModules

    DomainModules --> Adapters
    BookingMod -->|"Mutating Writes (GiST Locks)"| PostgresPrimary
    PayLedger -->|"Balanced Journal Entries"| PostgresPrimary
    SearchMod -->|"Read-Heavy Spatial Queries"| PostgresReplica
    PostgresPrimary -.->|"Async Streaming Replication"| PostgresReplica

    DomainModules <-->|"Ephemeral TTLs & Idempotency"| RedisCache
    Adapters --> S3Bucket
```

---

## Section 5 — Technology Stack and Decision Register

### 5.1 Technology Stack Matrix

| Layer / Subsystem | Technology Selection | Version | Approval Status | Architectural Rationale & Trade-offs |
|---|---|---|---|---|
| **Mobile Client** | Flutter / Dart | Flutter 3.24+ / Dart 3.5+ | `APPROVED` | Single cross-platform codebase compiling to native ARM binaries for Android and iOS. Eliminates dual-team drift. |
| **Mobile State** | flutter_bloc | 8.1+ | `APPROVED` | Predictable, event-driven reactive state machine separating UI rendering from business logic. |
| **Mobile Barcode Engine** | mobile_scanner | 5.2+ | `APPROVED` | Hardware-accelerated camera scanner utilizing Google ML Kit on Android and AVFoundation on iOS. Sub-500ms decode. |
| **Mobile Local DB** | sqflite_sqlcipher | 2.3+ | `APPROVED` | 256-bit AES encrypted local SQLite database for guard offline exception queues and shift schedules. |
| **Backend Framework** | Python / FastAPI | Python 3.11+ / FastAPI 0.115+ | `APPROVED` | Asynchronous high-performance async/await framework with native Pydantic v2 data validation and OpenAPI 3.1 generation. |
| **Async DB Driver** | asyncpg | 0.29+ | `APPROVED` | High-throughput binary protocol driver for PostgreSQL, bypassing heavy ORM serialization overhead for GiST locking. |
| **Data Mapping / Core** | SQLAlchemy (Core Async) | 2.0+ | `APPROVED` | Type-safe SQL query builder used for schema definition and complex analytical aggregations; avoids ORM state bloat. |
| **Primary Database** | PostgreSQL + PostGIS | PostgreSQL 16.4+ / PostGIS 3.4+ | `APPROVED` | Industry standard relational database providing GiST exclusion constraints (`btree_gist`), ACID transactions, and spatial queries. |
| **Caching & Fast Buffer** | Redis | 7.2+ | `APPROVED` | In-memory key-value store for API rate limiting, driver hold countdown timers, and distributed outbox dispatch. |
| **Background Processing**| ARQ / Celery | ARQ 0.25+ / Celery 5.4+ | `APPROVED` | Asynchronous worker pool for 5-second hold expiration sweeps, 30-minute no-show sweeps, and outbox event dispatch. |
| **Primary Payment Gateway**| Razorpay API & SDK | Standard V1 REST | `APPROVED` (`FD-01`) | Primary payment gateway in India with robust UPI intent support and automated webhooks. |
| **Secondary Payment Gateway**| Cashfree Payments | V3 REST API | `APPROVED` (`FD-01`) | Underwritten secondary gateway configured as hot-standby behind `PaymentGatewayPort`. |
| **Marketplace Payouts** | Corporate Banking API | Direct IMPS Batch | `APPROVED` (`FD-05`) | Scheduled batch bank transfers executed from platform corporate current account under strict KYC. |
| **Identity / Phone Auth**| Firebase Authentication | Admin SDK 6.5+ | `APPROVED` | Managed carrier-grade phone OTP delivery across Indian telecom operators with high reliability. |
| **Object Storage** | AWS S3 (Mumbai) | S3 Standard + Lifecycle | `APPROVED` | Private encrypted bucket with automated 7-day lifecycle purge rule for guard surveillance photos. |

### 5.2 Architectural Decision Records (ADR Register)

| ADR Ref | Decision Title | Decision Status | Summary of Architectural Choice |
|---|---|---|---|
| **ADR-001** | In-Process Modular Monolith Architecture | `APPROVED` | Deploy all domain modules inside a single containerized FastAPI process, eliminating distributed sagas. |
| **ADR-002** | Storage-Engine GiST Concurrency Locks | `APPROVED` | Enforce reservation interval exclusion exclusively at the database layer using PostgreSQL `btree_gist`. |
| **ADR-003** | Zero Child Lock Double-Entry Trigger Protocol | `APPROVED` | Eliminate ledger posting deadlocks by locking parent journal entries exclusively without child row locks. |
| **ADR-004** | Dual Payment Gateway Port Abstraction (`FD-01`) | `APPROVED` | Interface-abstract Razorpay (Primary) and Cashfree (Secondary) behind `PaymentGatewayPort`. |
| **ADR-005** | Hardware-Agnostic QR Gate Access | `APPROVED` | Enforce entry and exit validation via guard smartphone cameras, rejecting on-premise boom barriers. |
| **ADR-006** | Controlled Offline Manual Exception Mode (`FD-03`) | `APPROVED` | Support underground basement check-ins via local encrypted SQLCipher queues with 7-day photo purges. |
| **ADR-007** | Strict 480-Second (8-Minute) Hold TTL | `APPROVED` | Bounded checkout hold lifespan enforced uniformly across API, mobile timers, and database sweeps. |
| **ADR-008** | Single Cross-Platform Flutter Codebase | `APPROVED` | Single mobile binary with dynamic role-based shells for Drivers, Owners, Guards, and Operations. |
| **ADR-009** | PostGIS Geospatial Spatial Indexing | `APPROVED` | Store property coordinates in WGS 84 (`Point, 4326`) and query availability via `ST_DWithin` spatial indexes. |
| **ADR-010** | Canonical 6-Stage Multi-Stage Refund Lifecycle | `APPROVED` | Track refunds across `REFUND_ELIGIBLE` through `REFUND_SETTLED`, informing drivers of 5–7 business day banking timelines. |

### 5.3 Commercial and Operational Policy Register (Awaiting Founder Signoff)
Per [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md), exactly seven operational and commercial policies are modeled as **`PROPOSED (Pending Founder Approval)`**. The technical architecture implements these parameters as configurable values in application settings and database columns, ensuring zero code alterations upon founder signature:

| Policy ID | Policy Description | Proposed Parameter Value | Operational Rationale & Trade-offs | Architectural Implementation & Impact | Decision Status |
|---|---|---|---|---|---|
| **POL-COM-01** | Platform Commission Rate | **Flat 15.0%** of gross parking fee | Covers payment gateway MDR (2.36%), cloud infrastructure, customer support, and pilot subsidies. | Configured in pricing calculation engine; splits gross tariff into Accounts 2010 (85%) and 3010 (15%). | `PROPOSED (Pending Founder Approval)` |
| **POL-DUR-01** | Minimum Booking Duration | **30 Minutes** | Accommodates short quick errands (drop-offs, bank visits). 1-hour minimum would increase driver drop-off friction. | Enforced in API request validation (`time_window` duration check $\ge 30\text{m}$). | `PROPOSED (Pending Founder Approval)` |
| **POL-CAN-01** | Cancellation Refund Tiers | • **>2 Hours before start:** 100% refund.<br>• **30m – 2 Hours before start:** 50% refund.<br>• **<30m before start / Post-start:** 0% refund.<br>*Convenience fee non-refundable.* | Balances driver flexibility with host schedule certainty. Standard mobility marketplace practice in India. | Evaluated in `BookingService.cancel_booking()`; initiates refund outbox and reversal journal `JRN-CAN`. | `PROPOSED (Pending Founder Approval)` |
| **POL-ARR-02** | Driver No-Show Grace Period | **Exactly 30 Minutes** past scheduled start time | Accommodates peak Bengaluru traffic congestion while freeing bay if driver abandons trip. | Periodic 60-second sweeper queries confirmed reservations where $t > t_{\text{start}} + 30\text{m}$ without check-in. | `PROPOSED (Pending Founder Approval)` |
| **POL-OST-01** | Overstay Penalty Tariff | **1.5× Base Hourly Rate** in 30-minute increments | Discourages parking hogging that disrupts subsequent reservations without triggering credit card chargebacks. | Guard exit scan validates departure time; overstay invoice journal `JRN-OST` generated if grace window exceeded. | `PROPOSED (Pending Founder Approval)` |
| **POL-POT-01** | Host Payout Schedule & Minimum Balance | **Weekly Batch (Tuesdays)** for accumulated balance $\ge ₹500$ | Minimizes bank payout IMPS API charges (₹3–₹5 per transfer) and operational reconciliation overhead. | Celery/ARQ worker executes Tuesdays 02:00 IST; queries Account 2010 balances $\ge ₹500$ under verified KYC. | `PROPOSED (Pending Founder Approval)` |
| **POL-SUB-01** | GPRP Alternative Parking Subsidy Cap | **Up to ₹100** absorbed by platform | Prevents driver price shock when displaced through arrival obstruction; caps platform goodwill exposure. | Absorb rate delta via Account 4020 (Customer Recovery Subsidy Expense) in journal `JRN-SUB`. | `PROPOSED (Pending Founder Approval)` |

### 5.4 Critical External & Regulatory Dependencies Register
Commercial operations in the Bengaluru pilot are gated on five external third-party deliverables, classified as **`BLOCKED`**. In each case, technical decoupling ensures Sprint 1 application engineering proceeds unhindered:

| Dependency Ref | Subject Area | Required External Deliverable | Responsible Party | Current Status | Hardening Architecture Mitigation |
|---|---|---|---|---|---|
| **DEP-LEG-01** | Indirect Taxation (GST) | Written tax opinion classifying Gadispot under GST Section 9(1) (Facilitator) vs Section 9(5) (E-Commerce Operator). | Indirect Tax Counsel | `BLOCKED (Pending Memo)` | Ledger Account 2030 segregates GST on commission from base parking tariff. Modular tax engine enables instantaneous toggle if 9(5) applies. |
| **DEP-PAY-01** | Payment Aggregator Underwriting | Formal merchant onboarding approval for parking marketplace and Razorpay Route / Cashfree Split accounts. | Aggregator Risk Teams | `BLOCKED (Under Review)` | Dual gateway port abstraction (`PaymentGatewayPort`) active. Corporate bank batch IMPS fallback (`FD-05`) fully specified. |
| **DEP-TEL-01** | Transactional SMS Compliance | TRAI DLT registration for entity, sender ID (e.g., `GDSPOT`), and SMS OTP templates with Indian telecom operators. | Mobile / Telecom Lead | `BLOCKED (Filing)` | Firebase Phone Auth handles login OTP verification out of the box; DLT templates required only for transactional booking SMS. |
| **DEP-LEG-02** | Municipal Parking Regulations | Legal clarity on monetizing private residential driveways under Bengaluru BBMP / Karnataka Municipal guidelines. | Municipal Law Counsel | `BLOCKED (Reviewing)` | Pilot geofenced strictly to private residential driveways and gated layouts with verified Society/Landlord NOCs. |
| **DEP-LEG-03** | Platform Bailment & Liability | Finalization of Terms of Service disclaiming bailment, vehicle damage, fire, and theft under IT Act 2000 Section 79. | Corporate Litigator | `BLOCKED (Drafting)` | Mandatory clickwrap terms acceptance on signup and prominent non-bailment disclaimer modal prior to booking checkout. |

---

## Section 6 — Mobile Application Architecture

### 6.1 Single Cross-Platform Codebase Strategy
Gadispot implements a single, unified Flutter codebase delivering native iOS and Android binaries. Rather than maintaining disparate applications for drivers, space owners, and security guards, the application uses a **Dynamic Role-Based Shell Architecture**. Upon phone authentication, the application queries the user's assigned roles and renders the appropriate UI shell while maintaining complete sandboxing between operational modes.

### 6.2 Mobile Layered Architecture (Clean Architecture + BLoC)
The mobile client follows Clean Architecture with three strictly segregated layers:
1. **Presentation Layer:** Flutter Widgets and Pages consuming reactive state from BLoCs. Views are strictly stateless or reactive listeners; no business logic or raw HTTP calls exist in widget classes.
2. **Domain Layer:** Pure Dart entities, value objects, and Use Cases (interactors). This layer has zero dependencies on Flutter UI frameworks or third-party SDKs.
3. **Data Layer:** Repositories implementing domain interfaces, handling remote REST communication (via `Dio` with interceptors for JWT injection and exponential backoff retry), and managing local encrypted storage (`sqflite_sqlcipher` and `flutter_secure_storage`).

### 6.3 Screen Inventory by Role Shell
The mobile application comprises four role-specific screen flows:
- **Common & Authentication Flow:**
  - `SCR-001`: Splash Screen & Environment Integrity Verification.
  - `SCR-002`: Phone Number Entry (E.164 format validation).
  - `SCR-003`: 6-Digit OTP Verification (Auto-fill via SMS Retriever API).
- **Driver Role Shell (`SCR-101` through `SCR-108`):**
  - `SCR-101`: Interactive Discovery Map & Proximity Filter Carousel.
  - `SCR-102`: Parking Bay Details, Height Clearance & Property Amenities.
  - `SCR-103`: Checkout Review & 480-Second Hold Countdown Timer.
  - `SCR-104`: Confirmed Pass & Dynamic High-Contrast Entry QR (`spx_ent_`).
  - `SCR-105`: Active Session Tracker & Parking Extension Trigger.
  - `SCR-106`: Completed Session Summary, Receipt & Host Rating.
  - `SCR-107`: Arrival Issue Reporting (Obstruction / Closed Gate).
  - `SCR-108`: GPRP Alternative Space Offer & 180-Second Acceptance Card.
- **Space Owner Shell (`SCR-201` through `SCR-204`):**
  - `SCR-201`: Real-Time Bay Occupancy & Today's Earnings Dashboard.
  - `SCR-202`: Property Scaffolding & Title Deed Upload Wizard.
  - `SCR-203`: Financial Ledger, Undisbursed Balance & Settlement History.
  - `SCR-204`: Emergency Bay Blackout & Schedule Management.
- **Security Guard Scanner Shell (`SCR-301..304`):**
  - `SCR-301`: Full-Screen Camera Viewfinder with Laser Reticle (`mobile_scanner`).
  - `SCR-302`: Scan Result Modal (Big Green "ADMIT" / Bold Red "DENY").
  - `SCR-303`: Today's Shift Schedule (Offline Encrypted Cache).
  - `SCR-304`: Manual Exception Override Entry with Photo Proof.
- **Platform Operations Shell (`SCR-401` through `SCR-402`):**
  - `SCR-401`: Property Authorization Verification Queue & Document Viewer.
  - `SCR-402`: Incident Management & GPRP Manual Override Console.

### 6.4 Battery-Safe Scanner Lifecycle Management
To prevent device overheating and rapid battery depletion on guard devices during 8-hour shifts:
- The camera engine in `SCR-301` pauses processing immediately upon successfully detecting a barcode and resumes only after the guard dismisses the result modal (`SCR-302`).
- Frame rate is throttled to 15 frames per second within a centered region-of-interest (ROI) bounding box, reducing GPU/CPU power consumption by 45%.
- A screen wake-lock is acquired during active scanning shifts and automatically released after 60 seconds of device inactivity.

### 6.5 Mobile-to-Backend Request Flow (Sequential Diagram 3 / Mandatory PRD Diagram 3)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver Mobile App (Flutter)
    participant CloudFront as CloudFront / WAF
    participant ALB as Application Load Balancer
    participant AuthMiddleware as FastAPI Auth & Idempotency Middleware
    participant BookingService as Booking Domain Service
    participant Postgres as PostgreSQL 16 (Primary)

    Driver->>CloudFront: POST /api/v1/bookings/hold<br/>Headers: Authorization: Bearer <JWT>, Idempotency-Key: <UUID>
    CloudFront->>CloudFront: Verify WAF Rate Limits & TLS 1.3
    CloudFront->>ALB: Forward Request
    ALB->>AuthMiddleware: Dispatch to FastAPI ECS Container
    AuthMiddleware->>AuthMiddleware: Validate JWT signature & expiry (sub, role=DRIVER)
    AuthMiddleware->>Postgres: Check Idempotency Key in space_reservations
    Note over AuthMiddleware,Postgres: If existing key found, return cached response
    AuthMiddleware->>BookingService: Execute create_booking_hold(dto)
    BookingService->>Postgres: BEGIN TRANSACTION (READ COMMITTED)
    BookingService->>Postgres: Inline Sweep: Clear expired holds for target space
    BookingService->>Postgres: INSERT INTO space_reservations (hold_expires_at = NOW() + 480s)
    Note over BookingService,Postgres: GiST Exclusion Constraint Checked: parking_space_id WITH =, time_window WITH &&
    Postgres-->>BookingService: Reservation Created (ACTIVE_HOLD, hold_expires_at)
    BookingService->>Postgres: COMMIT TRANSACTION
    BookingService-->>AuthMiddleware: Return BookingHoldResponseDTO
    AuthMiddleware-->>Driver: HTTP 201 Created<br/>{ reservation_id, booking_ref, hold_expires_at, razorpay_order_id }
```

---

## Section 7 — Backend Architecture

### 7.1 Layered Backend Structure
The FastAPI modular monolith enforces a strict 4-layer internal separation within each domain package (`src/modules/<domain>/`):

```
+---------------------------------------------------------------------------------------------------+
|                                  FASTAPI APPLICATION LAYERING                                     |
+---------------------------------------------------------------------------------------------------+
| 1. Router Layer (Presentation) : FastAPI APIRouter endpoints, Pydantic v2 schemas, OpenAPI specs. |
| 2. Controller / Dependency     : Authentication validation, Idempotency-Key handling, DTO mapping.|
| 3. Domain Service Layer (Logic): Pure business logic, state machines, financial balance checks.   |
| 4. Repository Layer (Data)     : Async database queries (SQLAlchemy Core / asyncpg), transactions.|
+---------------------------------------------------------------------------------------------------+
```

### 7.2 Dependency Injection & Transaction Boundaries
- All controllers declare dependencies explicitly via FastAPI's `Depends()` mechanism (e.g., `get_current_user`, `get_db_session`, `get_payment_gateway`).
- Database transactions use async context managers (`async with db.transaction()`). Mutating operations commit only upon reaching the final exit of the service method. Unhandled exceptions trigger an automatic rollback.

### 7.3 Standard Error Format (RFC 7807 Problem Details)
All API errors adhere to RFC 7807 Problem Details. Error payloads are structured, machine-parsable, and predictable:

```json
{
  "type": "https://api.gadispot.in/errors/EXCLUSION_CONFLICT",
  "title": "Time Slot Already Reserved",
  "status": 409,
  "detail": "The requested parking space is currently held or booked for the specified interval.",
  "instance": "/api/v1/bookings/hold",
  "code": "SLOT_INTERVAL_CONFLICT",
  "timestamp": "2026-11-03T10:14:22Z"
}
```

### 7.4 Decoupled Provider Adapter Pattern
All external vendor integrations sit behind strict abstract port interfaces to prevent vendor lock-in and enable zero-downtime provider failover:

```python
class PaymentGatewayPort(ABC):
    @abstractmethod
    async def create_payment_order(self, amount_paise: int, currency: str, receipt: str) -> PaymentOrderResult:
        pass

    @abstractmethod
    async def verify_webhook_signature(self, raw_body: bytes, signature: str, event_id: str) -> bool:
        pass

    @abstractmethod
    async def initiate_refund(self, payment_id: str, amount_paise: int, reason: str) -> RefundDispatchResult:
        pass
```

Concrete implementations (`RazorpayAdapter`, `CashfreeAdapter`) implement this interface. The runtime resolves the active adapter dynamically based on configuration or automated health checks.

---

## Section 8 — Domain Module Boundaries

### 8.1 Inventory of Domain Modules
The system is partitioned into 8 core domain modules:

1. **`iam` (Identity & Access Management):** User registration, phone OTP authentication, JWT minting/refresh, RBAC scoping (`DRIVER`, `OWNER`, `GUARD`, `OPERATIONS`, `ADMIN`), and vehicle registrations.
2. **`inventory` (Property & Bay Inventory):** Property setup, geospatial pin-dropping, bay dimensional metadata, operating schedules, legal title deed uploads, and administrative verification queues.
3. **`search` (Geospatial Discovery & Search):** PostGIS spatial radius queries, bounding box filters, dimensional compatibility matching (`fn_check_vehicle_bay_compatibility`), and read-replica routing.
4. **`msai` (Multi-Source Availability Intelligence):** Synthesis of 7 discrete operational signals, pessimistic availability rules, and negative override enforcement.
5. **`booking` (Booking & Concurrency Engine):** 480-second checkout holds, two-tier deterministic expiration sweeps, GiST exclusion constraint enforcement, and Late Payment Resolution Protocol (LPRP).
6. **`payment_ledger` (Payment & Financial Ledger):** Gateway webhook ingestion, durable database deduplication, multi-stage refund management, and immutable double-entry ledger bookkeeping under the Zero Child Lock protocol.
7. **`gate_access` (QR Access & Guard Operations):** 128-bit CSPRNG access credential issuance (`spx_ent_` and `spx_ext_`), sub-500ms gate scan validation, and controlled offline exception queue reconciliation.
8. **`gprp` (Guaranteed Parking Recovery Protocol):** 8-step atomic arrival obstruction recovery, 500m spatial alternative search, 180-second driver decision timer, and 100% full refund failover.

### 8.2 Inter-Module Dependency Rules
- **Acyclic Dependency Graph:** Module dependencies flow in a strict directed acyclic graph (DAG). Cyclic imports are categorically prohibited.
- **Table Isolation:** Each database table is owned exclusively by exactly one domain module. A module cannot execute direct DML statements on another module's tables.
- **Cross-Domain Communication:** Inter-module requests occur strictly via published Python service methods returning typed DTOs.

### 8.3 Domain Module Dependency Diagram (Sequential Diagram 4 / Mandatory PRD Diagram 4)

```mermaid
flowchart TD
    IAM["IAM & Auth\n(Users, Roles, Vehicles)"]
    Inventory["Inventory\n(Properties, Spaces, Schedules)"]
    MSAI["MSAI\n(Availability Intelligence)"]
    Search["Search\n(Spatial PostGIS Engine)"]
    Booking["Booking\n(480s Holds, GiST Locks)"]
    PayLedger["Payment & Ledger\n(Webhooks, Double-Entry)"]
    GateAccess["Gate Access\n(QR Tokens, Guard Scans)"]
    GPRP["GPRP\n(Arrival Recovery & Swap)"]

    Inventory --> IAM
    MSAI --> Inventory
    Search --> Inventory
    Search --> MSAI
    Booking --> Inventory
    Booking --> IAM
    Booking --> MSAI
    PayLedger --> Booking
    GateAccess --> Booking
    GateAccess --> IAM
    GPRP --> Booking
    GPRP --> Search
    GPRP --> PayLedger
    GPRP --> GateAccess
```

---

## Section 9 — Domain Model and Entity Relationships

### 9.1 Core Domain Entities & Ownership
- **User (`users`):** Master identity representing individuals in the ecosystem. Bound to roles (`user_roles`) and vehicles (`vehicles`).
- **Property (`properties`):** Physical location containing parking spaces. Requires verification (`property_authorizations`) before spaces become active.
- **Parking Space (`parking_spaces`):** Discrete physical bay with specific dimensions (length, width, height clearance), bay type, EV charging availability, and hourly tariff.
- **Space Reservation (`space_reservations`):** Authoritative booking interval (`time_window`) on a specific parking space. Tracks lifecycle status, 480-second hold TTL, gateway payment correlation, and multi-stage refund progress.
- **Access Credential (`access_credentials`):** Opaque 128-bit CSPRNG tokens issued for entry (`spx_ent_`) and exit (`spx_ext_`), bound to an explicit reservation and property.
- **Offline Manual Admission (`offline_manual_admissions`):** Audited fallback record created by guards in deep basements during network outages, featuring timestamped gate photo proof and SHA-256 event chaining.
- **Journal Entry (`journal_entries`):** Financial transaction header grouping balanced journal lines.
- **Journal Line (`journal_lines`):** Individual debit or credit entry in paise referencing a standard ledger account (`ledger_accounts`).

### 9.2 State Machines and Lifecycle Transitions
- **Reservation Lifecycle:**
  `ACTIVE_HOLD` $\to$ `CONFIRMED` $\to$ `ACTIVE_SESSION` $\to$ `COMPLETED`  
  *Alternative Terminations:* `EXPIRED_HOLD` (TTL elapsed), `CANCELLED_BY_DRIVER` (driver initiated), `NO_SHOW` (30m grace window elapsed), `ARRIVAL_FAILED` (bay obstructed), `REPLACED` (GPRP alternative accepted), `RELEASED_UNFULFILLABLE` (late webhook lost race).
- **Canonical Multi-Stage Refund Lifecycle:**
  `NONE` $\to$ `REFUND_ELIGIBLE` $\to$ `REFUND_REQUESTED` $\to$ `GATEWAY_ACCEPTED` $\to$ `REFUND_PROCESSING` $\to$ `REFUND_SETTLED`  
  *Exception Path:* `REFUND_FAILED` (bank rail rejection; requires manual ops review).
- **Access Token Lifecycle:**
  `ISSUED` $\to$ `ACTIVE` $\to$ `CONSUMED`  
  *Alternative Terminations:* `EXPIRED` (window elapsed), `REVOKED` (cancellation or GPRP swap).

### 9.3 Conceptual Entity Relationship Diagram (Sequential Diagram 5 / Mandatory PRD Diagram 5)

```mermaid
erDiagram
    users ||--o{ user_roles : "assigned"
    users ||--o{ vehicles : "registers"
    users ||--o{ properties : "owns"
    users ||--o{ space_reservations : "books"
    users ||--o{ guard_assignments : "performs"

    properties ||--|| property_authorizations : "requires"
    properties ||--o{ authorization_documents : "contains"
    properties ||--o{ parking_spaces : "contains"
    properties ||--o{ operating_schedules : "follows"
    properties ||--o{ guard_assignments : "assigns"

    parking_spaces ||--o{ space_reservations : "allocates"
    parking_spaces ||--o{ space_incidents : "experiences"

    space_reservations ||--o{ access_credentials : "mints"
    space_reservations ||--o{ access_scan_logs : "audits"
    space_reservations ||--o{ offline_manual_admissions : "reconciles"
    space_reservations ||--o{ journal_entries : "generates"

    journal_entries ||--|{ journal_lines : "contains"
    journal_lines }o--|| ledger_accounts : "references"
    payment_webhook_events ||--o| space_reservations : "fulfills"
```

---

## Section 10 — Database Architecture

### 10.1 PostgreSQL Engine Configuration
The database tier runs **PostgreSQL 16.4+** on AWS RDS Multi-AZ. Required PostgreSQL extensions:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "postgis";
```

### 10.2 Complete Physical DDL Specifications

```sql
-- Enums
CREATE TYPE user_role_enum AS ENUM ('DRIVER', 'OWNER', 'GUARD', 'OPERATIONS', 'ADMIN');
CREATE TYPE property_type_enum AS ENUM ('RESIDENTIAL_DRIVEWAY', 'APARTMENT_SOCIETY', 'COMMERCIAL_BUILDING', 'OPEN_PLOT');
CREATE TYPE authorization_status_enum AS ENUM ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED');
CREATE TYPE document_type_enum AS ENUM ('PROPERTY_TAX_RECEIPT', 'SALE_DEED', 'ELECTRICITY_BILL', 'SOCIETY_NOC', 'LEASE_AGREEMENT', 'COMMERCIAL_CONCESSION');
CREATE TYPE vehicle_category_enum AS ENUM ('TWO_WHEELER', 'HATCHBACK', 'SEDAN', 'SUV', 'EV_FOUR_WHEELER', 'EV_TWO_WHEELER');
CREATE TYPE space_type_enum AS ENUM ('COVERED', 'OPEN', 'BASEMENT');
CREATE TYPE reservation_type_enum AS ENUM ('TEMPORARY_HOLD', 'CONFIRMED_BOOKING', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT');
CREATE TYPE reservation_status_enum AS ENUM (
    'ACTIVE_HOLD', 'EXPIRED_HOLD', 'CONFIRMED', 'ACTIVE_SESSION',
    'COMPLETED', 'CANCELLED_BY_DRIVER', 'CANCELLED_BY_OWNER',
    'NO_SHOW', 'ARRIVAL_FAILED', 'REPLACED', 'RELEASED_UNFULFILLABLE'
);
CREATE TYPE refund_status_enum AS ENUM (
    'NONE', 'REFUND_ELIGIBLE', 'REFUND_REQUESTED', 'GATEWAY_ACCEPTED',
    'REFUND_PROCESSING', 'REFUND_SETTLED', 'REFUND_FAILED'
);
CREATE TYPE token_type_enum AS ENUM ('ENTRY', 'EXIT');
CREATE TYPE token_status_enum AS ENUM ('ISSUED', 'ACTIVE', 'CONSUMED', 'REVOKED', 'EXPIRED');
CREATE TYPE account_type_enum AS ENUM ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE');
CREATE TYPE journal_status_enum AS ENUM ('DRAFT', 'POSTED', 'VOIDED');
CREATE TYPE entry_side_enum AS ENUM ('DEBIT', 'CREDIT');

-- 1. Users & Roles
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(16) NOT NULL UNIQUE,
    full_name VARCHAR(128) NOT NULL,
    email VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);
CREATE INDEX idx_users_phone ON users(phone_number);

CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role user_role_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    UNIQUE(user_id, role)
);

CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registration_plate VARCHAR(32) NOT NULL,
    vehicle_category vehicle_category_enum NOT NULL,
    make_model VARCHAR(64),
    is_ev BOOLEAN NOT NULL DEFAULT FALSE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    UNIQUE(driver_id, registration_plate)
);
CREATE INDEX idx_vehicles_driver ON vehicles(driver_id);

-- 2. Properties & Spaces
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(128) NOT NULL,
    property_type property_type_enum NOT NULL,
    address_line TEXT NOT NULL,
    city VARCHAR(64) NOT NULL DEFAULT 'Bengaluru',
    postal_code VARCHAR(16) NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    max_advance_days INT NOT NULL DEFAULT 7,
    max_booking_hours INT NOT NULL DEFAULT 24,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);
CREATE INDEX idx_properties_location ON properties USING gist (location);
CREATE INDEX idx_properties_owner ON properties(owner_id);

CREATE TABLE property_authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL UNIQUE REFERENCES properties(id) ON DELETE CASCADE,
    status authorization_status_enum NOT NULL DEFAULT 'DRAFT',
    pan_number VARCHAR(16),
    gstin VARCHAR(32),
    reviewer_notes TEXT,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);

CREATE TABLE parking_spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    space_label VARCHAR(32) NOT NULL,
    space_type space_type_enum NOT NULL DEFAULT 'COVERED',
    vehicle_category vehicle_category_enum NOT NULL,
    length_meters NUMERIC(4,2) NOT NULL DEFAULT 4.80,
    width_meters NUMERIC(4,2) NOT NULL DEFAULT 2.40,
    height_clearance_meters NUMERIC(4,2) NOT NULL DEFAULT 2.10,
    has_ev_charging BOOLEAN NOT NULL DEFAULT FALSE,
    base_hourly_rate_paise BIGINT NOT NULL CHECK (base_hourly_rate_paise > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    UNIQUE(property_id, space_label)
);
CREATE INDEX idx_spaces_property ON parking_spaces(property_id);

-- 3. Space Reservations with GiST Exclusion
CREATE TABLE space_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parking_space_id UUID NOT NULL REFERENCES parking_spaces(id) ON DELETE RESTRICT,
    driver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    time_window TSTZRANGE NOT NULL,
    reservation_type reservation_type_enum NOT NULL,
    status reservation_status_enum NOT NULL,
    hold_expires_at TIMESTAMPTZ,
    payment_order_id VARCHAR(64),
    payment_transaction_id VARCHAR(64),
    booking_reference VARCHAR(32) NOT NULL UNIQUE,
    idempotency_key VARCHAR(64) UNIQUE,
    refund_status refund_status_enum NOT NULL DEFAULT 'NONE',
    refund_gateway_id VARCHAR(64),
    refund_arn_utr VARCHAR(64),
    refund_initiated_at TIMESTAMPTZ,
    refund_completed_at TIMESTAMPTZ,
    refund_failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    CONSTRAINT chk_hold_expiration CHECK (
        (status != 'ACTIVE_HOLD') OR (hold_expires_at IS NOT NULL)
    ),
    CONSTRAINT chk_positive_time_window CHECK (
        lower(time_window) < upper(time_window)
    ),
    CONSTRAINT prevent_overlapping_active_reservations
    EXCLUDE USING gist (
        parking_space_id WITH =,
        time_window WITH &&
    ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
);
CREATE INDEX idx_reservations_space_time ON space_reservations USING gist (parking_space_id, time_window);
CREATE INDEX idx_reservations_status ON space_reservations(status);
CREATE INDEX idx_reservations_hold_expiry ON space_reservations(hold_expires_at) WHERE status = 'ACTIVE_HOLD';
CREATE INDEX idx_reservations_driver ON space_reservations(driver_id);

-- 4. Access Credentials
CREATE TABLE access_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID NOT NULL REFERENCES space_reservations(id) ON DELETE CASCADE,
    token_type token_type_enum NOT NULL,
    opaque_token VARCHAR(64) NOT NULL UNIQUE,
    status token_status_enum NOT NULL DEFAULT 'ISSUED',
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    consumed_by_guard_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);
CREATE INDEX idx_access_credentials_lookup ON access_credentials(opaque_token);
CREATE INDEX idx_access_credentials_res ON access_credentials(reservation_id, token_type);

-- 5. Double-Entry General Ledger
CREATE TABLE ledger_accounts (
    account_code VARCHAR(16) PRIMARY KEY,
    account_name VARCHAR(128) NOT NULL,
    account_type account_type_enum NOT NULL,
    normal_balance VARCHAR(8) NOT NULL CHECK (normal_balance IN ('DEBIT', 'CREDIT')),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP()
);

CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_number VARCHAR(32) NOT NULL UNIQUE,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_reference VARCHAR(64) NOT NULL,
    transaction_type VARCHAR(32) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    posting_status journal_status_enum NOT NULL DEFAULT 'DRAFT',
    reversal_of_journal_id UUID REFERENCES journal_entries(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CLOCK_TIMESTAMP(),
    posted_at TIMESTAMPTZ
);

CREATE TABLE journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE RESTRICT,
    line_number INT NOT NULL,
    account_code VARCHAR(16) NOT NULL REFERENCES ledger_accounts(account_code),
    entry_side entry_side_enum NOT NULL,
    amount_in_paise BIGINT NOT NULL CHECK (amount_in_paise > 0),
    description TEXT,
    CONSTRAINT uq_journal_line UNIQUE (journal_id, line_number)
);
CREATE INDEX idx_journal_lines_journal ON journal_lines(journal_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_code);
CREATE INDEX idx_journal_entries_reference ON journal_entries(transaction_reference);
```

### 10.3 Hardened Trigger Functions (Zero Child Lock Protocol)

```sql
-- Trigger 1: Balanced Journal Posting Verification Trigger
CREATE OR REPLACE FUNCTION fn_verify_journal_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_total_debits BIGINT;
    v_total_credits BIGINT;
    v_line_count INT;
BEGIN
    IF NEW.posting_status = 'POSTED' AND (OLD.posting_status IS NULL OR OLD.posting_status != 'POSTED') THEN
        -- Zero Child Lock: No FOR UPDATE lock on journal_lines!
        SELECT 
            COALESCE(SUM(CASE WHEN entry_side = 'DEBIT' THEN amount_in_paise ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN entry_side = 'CREDIT' THEN amount_in_paise ELSE 0 END), 0),
            COUNT(*)
        INTO v_total_debits, v_total_credits, v_line_count
        FROM journal_lines
        WHERE journal_id = NEW.id;

        IF v_line_count < 2 THEN
            RAISE EXCEPTION 'Cannot post journal entry %: Must contain at least 2 lines (found %)', NEW.id, v_line_count;
        END IF;

        IF v_total_debits != v_total_credits THEN
            RAISE EXCEPTION 'Journal entry % does not balance! Total Debits: % paise, Total Credits: % paise',
                NEW.id, v_total_debits, v_total_credits;
        END IF;

        NEW.posted_at := CLOCK_TIMESTAMP();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_verify_journal_balance
BEFORE UPDATE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_verify_journal_balance();

-- Trigger 2: Immutability of Posted Journals
CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.posting_status = 'POSTED' THEN
        RAISE EXCEPTION 'Immutable Ledger Violation: Posted journal % cannot be updated or deleted. Post a reversing entry instead.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_modification
BEFORE UPDATE OR DELETE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_journal_modification();

-- Trigger 3: Immutability of Posted Lines & Deterministic Parent Locking
CREATE OR REPLACE FUNCTION fn_prevent_posted_lines_modification()
RETURNS TRIGGER AS $$
DECLARE
    v_status journal_status_enum;
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT posting_status INTO v_status FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
        IF v_status IS NULL THEN
            RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', NEW.journal_id;
        ELSIF v_status = 'POSTED' THEN
            RAISE EXCEPTION 'Immutable Ledger Violation: Cannot insert lines into POSTED journal %', NEW.journal_id;
        END IF;
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        SELECT posting_status INTO v_status FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
        IF v_status IS NULL THEN
            RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', OLD.journal_id;
        ELSIF v_status = 'POSTED' THEN
            RAISE EXCEPTION 'Immutable Ledger Violation: Cannot delete lines from POSTED journal %', OLD.journal_id;
        END IF;
        RETURN OLD;

    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.journal_id = NEW.journal_id THEN
            SELECT posting_status INTO v_status FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
            IF v_status IS NULL THEN
                RAISE EXCEPTION 'Foreign Key Violation: Parent journal entry % does not exist', NEW.journal_id;
            ELSIF v_status = 'POSTED' THEN
                RAISE EXCEPTION 'Immutable Ledger Violation: Cannot update lines on POSTED journal %', NEW.journal_id;
            END IF;
        ELSE
            -- Deterministic parent locking order check
            IF OLD.journal_id < NEW.journal_id THEN
                PERFORM 1 FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
                PERFORM 1 FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
            ELSE
                PERFORM 1 FROM journal_entries WHERE id = NEW.journal_id FOR SHARE;
                PERFORM 1 FROM journal_entries WHERE id = OLD.journal_id FOR SHARE;
            END IF;

            IF EXISTS (SELECT 1 FROM journal_entries WHERE id IN (OLD.journal_id, NEW.journal_id) AND posting_status = 'POSTED') THEN
                RAISE EXCEPTION 'Immutable Ledger Violation: Cannot move line into or out of POSTED journal (% -> %)', OLD.journal_id, NEW.journal_id;
            END IF;
        END IF;
        RETURN NEW;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_lines_mod
BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_lines_modification();
```

---

## Section 11 — Identity, Authentication and Authorization Architecture

### 11.1 Authentication Mechanics (Firebase Phone Auth Integration)
Driver and space owner authentication is mobile-native via **Firebase Phone Authentication**. Phone numbers are formatted in E.164 (`+91XXXXXXXXXX`).
1. The Flutter client invokes Firebase SDK to send an SMS OTP.
2. Upon OTP verification, Firebase returns a signed RS256 Firebase ID token.
3. The Flutter client submits the ID token to `POST /api/v1/auth/session`.
4. FastAPI verifies the Firebase ID token cryptographically via the Firebase Admin SDK, identifies or creates the user in the `users` table, and issues an internal Gadispot Access JWT (60-minute TTL) and opaque Refresh Token (30-day sliding TTL).

### 11.2 Scoped JWT Claims & Role Hierarchy
Internal JWTs are signed with HMAC-SHA256 (or RSA-256) and contain explicit claims:
```json
{
  "sub": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "phone_number": "+919876543210",
  "role": "DRIVER",
  "available_roles": ["DRIVER", "OWNER"],
  "property_id": null,
  "iss": "https://api.gadispot.in",
  "exp": 1793540000,
  "iat": 1793536400
}
```

Role scoping rules:
- `DRIVER`: Can search spaces, hold bays, execute payments, view personal bookings, and present access QRs.
- `OWNER`: Can configure owned properties, manage bay inventory, toggle emergency blackout, and inspect settlement ledgers.
- `GUARD`: Scoped strictly to an assigned `property_id` and active 8-hour shift. Can validate scan tokens and reconcile offline admissions. Cannot view financial revenue.
- `OPERATIONS`: Can audit pending property documents and inspect GPRP incident logs. Mutating approvals require 2FA TOTP.
- `ADMIN`: Global configuration and user management.

### 11.3 Object-Level Authorization (IDOR Defense)
Under zero circumstances do endpoints rely on user-supplied query parameters to infer data ownership. The backend extracts `sub` strictly from the validated JWT:
- A driver requesting `/access/credentials/{reservation_id}` must match `space_reservations.driver_id == token.sub`.
- A guard validating a scan at `POST /access/validate-scan` must have `token.property_id == target_reservation.property_id`.

### 11.4 Authentication Sequence (Sequential Diagram 6 / Mandatory PRD Diagram 6)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver App (Flutter)
    participant Firebase as Firebase Phone Auth
    participant Backend as FastAPI Auth Controller
    participant UsersDB as PostgreSQL users Table

    Driver->>Firebase: Request Phone OTP (+919876543210)
    Firebase-->>Driver: SMS OTP Delivered
    Driver->>Firebase: Submit 6-Digit OTP
    Firebase-->>Driver: Return Signed Firebase ID Token (RS256)
    Driver->>Backend: POST /api/v1/auth/session<br/>{ "firebase_id_token": "..." }
    Backend->>Firebase: Verify Token Authenticity & Claims
    Firebase-->>Backend: Token Valid (Phone Verified)
    Backend->>UsersDB: SELECT OR INSERT users WHERE phone_number = '+919876543210'
    UsersDB-->>Backend: User Record (id, roles)
    Backend->>Backend: Generate Scoped Gadispot JWT (role=DRIVER, 60m TTL)
    Backend-->>Driver: HTTP 200 OK<br/>{ "access_token": "...", "refresh_token": "...", "user": {...} }
```

---

## Section 12 — Property Onboarding and Verification Architecture

### 12.1 Property Scaffolding Lifecycle
To prevent fraudulent or dispute-prone parking bays from entering the marketplace, space owners execute a structured 4-step onboarding wizard (`SCR-202`):
1. **Physical Metadata:** Property Title, Address, Pincode, and Property Type (`RESIDENTIAL_DRIVEWAY`, `APARTMENT_SOCIETY`, `COMMERCIAL_BUILDING`, `OPEN_PLOT`).
2. **Geospatial Pin Drop:** Interactive map placement capturing precise WGS 84 latitude and longitude.
3. **Bay Scaffolding:** Bay label, dimensions (length, width, clearance height in meters), EV charger status, and hourly tariff in paise.
4. **Legal Evidence Upload:** Mandatory legal documents uploaded via presigned S3 URLs.

### 12.2 Mandatory Legal Evidence Matrix
Every property MUST provide at least one verified legal entitlement document:
- Residential Driveway: Recent Municipal Property Tax Receipt or Electricity Bill matching owner name.
- Gated Apartment Society: Managing Committee / Society NOC and assigned bay allotment deed.
- Commercial Plot / Building: Commercial concession agreement or registered lease deed.
- Mandatory 3 Photographic Angles: (1) Main entrance gate, (2) exact bay demarcations, (3) approach driveway.

### 12.3 Operations Review Queue & State Transitions
Submissions enter `property_authorizations` with `status = 'PENDING_REVIEW'`. An Operations Auditor inspects documents in `SCR-401`. Upon audit:
- **`APPROVED`:** Property is activated (`is_active = TRUE`); bays become eligible for MSAI search indexing.
- **`REJECTED`:** Structured rejection reason logged (e.g., *Name mismatch on tax receipt*, *Gate obstructed*); owner notified via push.
- **Invariant:** Spaces belonging to unapproved properties are hidden from spatial search queries at the database layer.

### 12.4 Property Onboarding Sequence (Sequential Diagram 7 / Mandatory PRD Diagram 7)

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Space Owner (Flutter)
    participant Backend as FastAPI Inventory Service
    participant S3 as AWS S3 Private Bucket
    participant DB as PostgreSQL properties Table
    actor Ops as Operations Admin (SCR-401)

    Owner->>Backend: POST /api/v1/properties (Metadata, Pin, Bays)
    Backend->>DB: INSERT INTO properties (status='DRAFT', is_active=FALSE)
    DB-->>Backend: Property Created (id)
    Owner->>Backend: POST /api/v1/properties/{id}/documents/presign
    Backend-->>Owner: Return S3 Presigned Upload URLs
    Owner->>S3: PUT Legal Title Deeds & Photos (Encrypted)
    Owner->>Backend: POST /api/v1/properties/{id}/submit-review
    Backend->>DB: UPDATE property_authorizations SET status='PENDING_REVIEW'
    Ops->>Backend: GET /api/v1/operations/verification-queue
    Backend-->>Ops: List Pending Properties & Secure S3 Links
    Ops->>Ops: Verify Deed Title & Driveway Clearance
    Ops->>Backend: POST /api/v1/operations/properties/{id}/approve (2FA TOTP)
    Backend->>DB: UPDATE property_authorizations SET status='APPROVED'<br/>UPDATE properties SET is_active=TRUE
    Backend-->>Owner: Push Notification: "Property Approved & Live!"
```

---

## Section 13 — Search and Geospatial Discovery Architecture

### 13.1 Geospatial Engine Mechanics (PostGIS Spatial Queries)
Search discovery queries (`POST /api/v1/spaces/search`) locate available parking spaces within a defined walking radius (default 3,000m, capped at 5,000m) of destination coordinates $(\text{lat}, \text{lng})$ for a target time window $[t_{\text{start}}, t_{\text{end}})$.

The query executes in the spatial domain using PostGIS geometry:
```sql
SELECT 
    ps.id AS space_id,
    p.id AS property_id,
    p.title AS property_name,
    ps.space_label,
    ST_Distance(p.location, ST_SetSRID(ST_MakePoint(:target_lng, :target_lat), 4326)::geography) AS distance_meters,
    ps.base_hourly_rate_paise
FROM parking_spaces ps
JOIN properties p ON ps.property_id = p.id
JOIN property_authorizations pa ON p.id = pa.property_id
WHERE p.is_active = TRUE
  AND pa.status = 'APPROVED'
  AND ps.is_active = TRUE
  AND ST_DWithin(p.location, ST_SetSRID(ST_MakePoint(:target_lng, :target_lat), 4326)::geography, :radius_meters)
  AND fn_check_vehicle_bay_compatibility(
      :driver_vehicle_category,
      ps.space_type::text,
      ps.length_meters,
      ps.width_meters,
      ps.height_clearance_meters,
      ps.has_ev_charging,
      :driver_requires_ev
  ) = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM space_reservations sr
      WHERE sr.parking_space_id = ps.id
        AND sr.status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT')
        AND sr.time_window && tstzrange(:req_start_time, :req_end_time)
  )
ORDER BY distance_meters ASC
LIMIT 50;
```

### 13.2 Read Replica Routing Strategy
Geospatial search queries represent 90% of platform traffic. To safeguard primary writer throughput, discovery queries are routed exclusively to read replicas via an asyncpg read pool managed behind PgBouncer.

### 13.3 Search and Availability Sequence (Sequential Diagram 8 / Mandatory PRD Diagram 8)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver App (SCR-101)
    participant SearchAPI as FastAPI Search Controller
    participant ReadReplica as PostgreSQL Read Replica (PostGIS)
    participant MSAI as MSAI Service Layer

    Driver->>SearchAPI: POST /api/v1/spaces/search<br/>{ lat, lng, radius=3000m, window, vehicle_category='SEDAN' }
    SearchAPI->>ReadReplica: Execute Spatial ST_DWithin Query + GiST Filter
    ReadReplica-->>SearchAPI: Candidate Spaces (Filtered by Distance & Physical Bounds)
    SearchAPI->>MSAI: Synthesize Operational Signals (Schedules, Buffers, Incidents)
    MSAI-->>SearchAPI: Filtered Bookable Spaces
    SearchAPI->>SearchAPI: Compute Tariff Estimates & Format Carousel DTO
    SearchAPI-->>Driver: HTTP 200 OK<br/>{ total_found: 3, spaces: [ { space_id, price, distance } ] }
```

---

## Section 14 — Multi-Source Availability Intelligence (MSAI) Architecture

### 14.1 The 7 Operational Signals & Precedence Hierarchy
MSAI synthesizes 7 discrete operational signals using a strict pessimistic precedence cascade:

| Precedence | Signal Name | Authority Level | Freshness Window | Precedence Rule | Resolution Behavior |
|---|---|---|---|---|---|
| **Level 1 (Highest)** | Active GiST Reservations | Absolute | Real-time DB | Concurrency Lock | Slot locked (`23P01`); marked `BOOKED`. |
| **Level 2** | Active 480-Second Holds | Absolute | 480 Seconds | Concurrency Lock | Slot unexpired; marked `HELD`. |
| **Level 3** | Guard Obstruction Reports | High (Negative) | 4 Hours | Negative Override | Slot marked `BLOCKED` immediately. |
| **Level 4** | Owner Manual Blackouts | High (Negative) | Window Bound | Negative Override | Slot marked `UNAVAILABLE`. |
| **Level 5** | Operating Hours Schedule | Baseline | Weekly Rule | Operating Gate | Outside hours; marked `CLOSED`. |
| **Level 6** | Property Authorization Status| Baseline | Real-time DB | Eligibility Gate | If not `APPROVED`, suppressed from search. |
| **Level 7** | 15-Minute Turnover Buffer | Policy | Continuous | Spacing Gate | 15-minute buffers prepended/appended. |

### 14.2 Pessimistic Availability Invariant
In urban parking marketplaces, an inaccurate availability signal resulting in a driver navigating to an obstructed bay permanently destroys customer retention. Under the pessimistic availability invariant:
$$\text{If any negative signal conflicts with an open calendar} \implies \text{Negative signal wins unconditionally}.$$

### 14.3 Dimensional Vehicle Compatibility Evaluation
Parking bay compatibility cannot be evaluated with scalar comparisons (`ps.compatibility >= driver_vehicle`). Space matching MUST evaluate physical bay dimensions ($\text{length} \ge L$, $\text{width} \ge W$, $\text{height} \ge H$), permitted bay type, and active EV charger status (`fn_check_vehicle_bay_compatibility()` in [docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md)). An oversized vehicle MUST NEVER be routed to an undersized bay.

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
    IF p_driver_req_ev AND NOT p_bay_has_ev THEN
        RETURN FALSE;
    END IF;

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

### 14.4 MSAI Evidence Evaluation Flow (Sequential Diagram 9 / Mandatory PRD Diagram 13)

```mermaid
flowchart TD
    Start([Incoming Space Availability Query]) --> CheckAuth{Is Property Status APPROVED?}
    CheckAuth -- No --> DenyAuth[SUPPRESSED: Property Not Approved]
    CheckAuth -- Yes --> CheckSchedule{Within Property Operating Hours?}
    CheckSchedule -- No --> DenySchedule[UNAVAILABLE: Outside Operating Schedule]
    CheckSchedule -- Yes --> CheckOwnerBlackout{Active Owner Blackout?}
    CheckOwnerBlackout -- Yes --> DenyBlackout[UNAVAILABLE: Blocked by Space Owner]
    CheckOwnerBlackout -- No --> CheckGuardObstruction{Active Guard Obstruction Report?}
    CheckGuardObstruction -- Yes --> DenyObstruction[BLOCKED: Physical Obstruction Reported]
    CheckGuardObstruction -- No --> CheckCompatibility{Meets Vehicle Dimensions & EV?}
    CheckCompatibility -- No --> DenyCompat[INCOMPATIBLE: Vehicle Exceeds Dimensions]
    CheckCompatibility -- Yes --> CheckGiST{Overlaps Existing Reservation or Active Hold?}
    CheckGiST -- Yes --> DenyGiST[BOOKED / HELD: Storage Engine GiST Lock Active]
    CheckGiST -- No --> Allow[AVAILABLE: Eligible for Driver Hold]
```

---

## Section 15 — Booking and Reservation Architecture

### 15.1 Unified Reservation Concurrency Model
To eliminate split-brain states between temporary checkout holds, confirmed reservations, and active parking sessions, all states reside in a unified table: `space_reservations`. Storage-engine concurrency exclusion is enforced via:
```sql
CONSTRAINT prevent_overlapping_active_reservations
EXCLUDE USING gist (
    parking_space_id WITH =,
    time_window WITH &&
) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'))
```

### 15.2 Authoritative 480-Second Hold Lifespan
During checkout, the bay is reserved under `status = 'ACTIVE_HOLD'` for strictly **480 seconds (8 minutes)** (`hold_expires_at = CLOCK_TIMESTAMP() + INTERVAL '480 seconds'`). Application timers, mobile checkout progress bars (`SCR-103`), and backend validation enforce this exact 480-second window.

### 15.3 Two-Tier Deterministic Expiration Engine
Because PostgreSQL partial exclusion constraints filter rows based on static column values (`WHERE status IN ('ACTIVE_HOLD', ...)`), **a row does not automatically leave the exclusion index when its timestamp passes in wall-clock time**. Expired holds MUST have their `status` mutated away from `ACTIVE_HOLD` to release the GiST lock. This is achieved via an authoritative two-tier engine:

- **Tier 1 (Active Periodic Sweeper):** A dedicated Celery/ARQ background worker executes every 5 seconds globally across all properties:
  ```sql
  WITH expired_candidates AS (
      SELECT id FROM space_reservations
      WHERE status = 'ACTIVE_HOLD' 
        AND hold_expires_at <= CLOCK_TIMESTAMP()
      FOR UPDATE SKIP LOCKED LIMIT 100
  )
  UPDATE space_reservations r 
  SET status = 'EXPIRED_HOLD', updated_at = CLOCK_TIMESTAMP()
  FROM expired_candidates c 
  WHERE r.id = c.id;
  ```
  The `FOR UPDATE SKIP LOCKED` clause ensures worker threads never block user-facing transactions or each other, processing batches with zero lock contention.

- **Tier 2 (Inline Opportunistic Sweep on Hold Creation):** When a driver initiates a hold (`POST /api/v1/bookings/hold`), the backend executes an inline sweep specifically targeting the requested space within the **same atomic database transaction** immediately before executing the new `INSERT`:
  ```sql
  -- Step 1: Inline opportunistic purge of stale hold on target space
  UPDATE space_reservations
  SET status = 'EXPIRED_HOLD', updated_at = CLOCK_TIMESTAMP()
  WHERE parking_space_id = :target_space_id
    AND status = 'ACTIVE_HOLD'
    AND hold_expires_at <= CLOCK_TIMESTAMP();

  -- Step 2: Atomic insert of new hold protected by GiST exclusion lock
  INSERT INTO space_reservations (
      parking_space_id, driver_id, vehicle_id, time_window,
      reservation_type, status, hold_expires_at, booking_reference, idempotency_key
  ) VALUES (
      :target_space_id, :driver_id, :vehicle_id, :target_window,
      'TEMPORARY_HOLD', 'ACTIVE_HOLD', CLOCK_TIMESTAMP() + INTERVAL '480 seconds',
      :generated_ref, :client_idempotency_key
  );
  ```
  This guarantees that even if the Tier-1 background worker is delayed by worker pool saturation, an expired hold on the target space is cleared in the identical transaction that reserves it, eliminating false-positive 409 conflict errors.

### 15.4 Late Payment Resolution Protocol (LPRP) & Concurrent Millisecond Race Analysis

#### The 3-Way Millisecond Race Scenario
A high-risk concurrency edge case arises when three independent threads collide on the same physical parking space within the exact same millisecond window ($t = 480.001\text{s}$):
1. **Thread A (Worker Sweep):** Celery worker attempts to expire Driver 1's hold (`status = 'ACTIVE_HOLD'`).
2. **Thread B (Competing Driver 2):** Driver 2 executes `POST /api/v1/bookings/hold` on the same bay, running the Tier-2 inline sweep and inserting a new `ACTIVE_HOLD`.
3. **Thread C (Payment Webhook):** Payment gateway delivers `payment.captured` for Driver 1 whose 480-second hold expired an instant earlier.

#### PostgreSQL Transaction Abortion & Subtransaction (SAVEPOINT) Requirement
**Critical Database Invariant:** In PostgreSQL, executing an `UPDATE` that violates a GiST exclusion constraint (`EXCLUDE USING gist`) triggers SQLSTATE `23P01` (`exclusion_violation`). Under standard PostgreSQL transaction semantics, an unhandled database error immediately puts the transaction block into an **aborted error state** (`ERROR: current transaction is aborted, commands ignored until end of transaction block`).

If the webhook service simply attempts `UPDATE space_reservations SET status = 'CONFIRMED' ...` without subtransaction isolation, catching the exception in Python does NOT reset the PostgreSQL connection state! Any subsequent SQL query—such as updating Driver 1 to `RELEASED_UNFULFILLABLE` or recording payment details—will crash the session, leaving Driver 1 charged by the gateway but untracked in the platform database!

To guarantee atomic recovery, the LPRP slot reclaim MUST be executed inside a database **SAVEPOINT** (`async with db.begin_nested():` in SQLAlchemy / asyncpg):

```python
async def process_payment_captured_webhook(
    db: AsyncSession, 
    payment_order_id: str, 
    gateway_payment_id: str,
    event_id: str
) -> ConfirmationResult:
    # 1. Deduplicate webhook event idempotently
    inserted = await db.execute(
        """
        INSERT INTO payment_webhook_events (event_id, gateway_name, event_type)
        VALUES (:event_id, 'RAZORPAY', 'payment.captured')
        ON CONFLICT (event_id) DO NOTHING
        """,
        {"event_id": event_id}
    )
    if not inserted.rowcount:
        return ConfirmationResult(status="DUPLICATE_IGNORED")

    # 2. Acquire exclusive row lock on reservation record
    res = await db.fetch_one(
        """
        SELECT id, parking_space_id, time_window, status, hold_expires_at
        FROM space_reservations
        WHERE payment_order_id = :p
        FOR UPDATE
        """,
        {"p": payment_order_id}
    )
    if not res:
        raise ReservationNotFoundError(f"Order {payment_order_id} not mapped to reservation")

    # Idempotent replay: already confirmed
    if res["status"] == "CONFIRMED":
        return ConfirmationResult(status="ALREADY_CONFIRMED", reservation_id=res["id"])

    # Normal Path: Hold is still active
    if res["status"] == "ACTIVE_HOLD":
        await db.execute(
            """
            UPDATE space_reservations
            SET status = 'CONFIRMED', 
                payment_transaction_id = :tx_id,
                updated_at = CLOCK_TIMESTAMP()
            WHERE id = :id
            """,
            {"id": res["id"], "tx_id": gateway_payment_id}
        )
        await issue_access_credentials(db, res["id"])
        await post_booking_ledger_journal(db, res["id"])
        return ConfirmationResult(status="CONFIRMED", reservation_id=res["id"])

    # LPRP Path: Hold was expired by Tier-1 worker or Tier-2 inline sweep
    elif res["status"] == "EXPIRED_HOLD":
        reclaim_succeeded = False
        
        # MUST wrap reclaim in a SAVEPOINT to isolate ExclusionViolation (23P01)
        try:
            async with db.begin_nested():  # Emits SAVEPOINT sp_lprp_reclaim
                await db.execute(
                    """
                    UPDATE space_reservations
                    SET status = 'CONFIRMED',
                        payment_transaction_id = :tx_id,
                        updated_at = CLOCK_TIMESTAMP()
                    WHERE id = :id AND status = 'EXPIRED_HOLD'
                    """,
                    {"id": res["id"], "tx_id": gateway_payment_id}
                )
            # Reclaim succeeded: no competing hold was placed during the gap
            reclaim_succeeded = True
        except ExclusionViolation:  # PostgreSQL SQLSTATE 23P01
            # SAVEPOINT automatically rolled back to sp_lprp_reclaim!
            # Outer transaction remains healthy and usable!
            reclaim_succeeded = False

        if reclaim_succeeded:
            # Slot was successfully re-acquired
            await issue_access_credentials(db, res["id"])
            await post_booking_ledger_journal(db, res["id"])
            return ConfirmationResult(status="CONFIRMED_LATE_RECLAIM", reservation_id=res["id"])
        else:
            # Competing Driver 2 claimed the bay; Driver 1 loses race
            # Atomically update Driver 1 to RELEASED_UNFULFILLABLE and queue full refund
            await db.execute(
                """
                UPDATE space_reservations
                SET status = 'RELEASED_UNFULFILLABLE',
                    payment_transaction_id = :tx_id,
                    refund_status = 'REFUND_ELIGIBLE',
                    refund_failure_reason = 'LPRP_RACE_LOST_SPACE_REALLOCATED',
                    updated_at = CLOCK_TIMESTAMP()
                WHERE id = :id
                """,
                {"id": res["id"], "tx_id": gateway_payment_id}
            )
            # Enqueue automated 100% full refund via transactional outbox
            await enqueue_outbox_event(
                db, 
                event_type="REFUND_REQUESTED", 
                payload={"reservation_id": str(res["id"]), "reason": "LPRP_SPACE_COLLISION"}
            )
            return ConfirmationResult(status="RELEASED_UNFULFILLABLE_REFUND_QUEUED", reservation_id=res["id"])
```

#### 3-Way Millisecond Race Resolution Matrix

| Concurrency Permutation | Lock Sequencing & Interleaving | PostgreSQL GiST Behavior | Final State of Driver 1 | Final State of Driver 2 | Financial & Safety Integrity |
|---|---|---|---|---|---|
| **Case 1: Webhook arrives before sweep ($t = 479.999\text{s}$)** | Thread C acquires row `FOR UPDATE` while status is `ACTIVE_HOLD`. Worker sweep Thread A evaluates `SKIP LOCKED` and skips row. | Normal UPDATE to `CONFIRMED`. GiST partial index maintains lock. | `CONFIRMED` with valid QR tokens. | Driver 2 hold request rejected with HTTP 409 (GiST exclusion lock held by Driver 1). | **Zero Double-Booking.** Driver 1 parks; Driver 2 charged ₹0. |
| **Case 2: Worker sweep commits, bay remains vacant ($t = 480.002\text{s}$)** | Thread A updates status to `EXPIRED_HOLD` and commits. Thread C acquires lock, detects `EXPIRED_HOLD`, executes reclaim inside `SAVEPOINT`. | UPDATE to `CONFIRMED` succeeds because no competing reservation exists in time window. | `CONFIRMED` via LPRP reclaim. Access QR minted. | Space booked by Driver 1; Driver 2 later sees space as unavailable. | **Zero Double-Booking.** Slot utilized efficiently; driver protected. |
| **Case 3: Competing Driver 2 holds bay during gap ($t = 480.005\text{s}$)** | Thread B executes Tier-2 sweep, inserts Driver 2 `ACTIVE_HOLD`, and commits. Thread C attempts LPRP reclaim inside `SAVEPOINT`. | PostgreSQL evaluates GiST exclusion constraint against Driver 2's `ACTIVE_HOLD`, detects temporal overlap, throws `23P01`. | `RELEASED_UNFULFILLABLE` with `REFUND_ELIGIBLE`. | `ACTIVE_HOLD` maintained. Driver 2 proceeds to payment. | **Zero Double-Booking.** `SAVEPOINT` rolls back cleanly; Driver 1 receives 100% full refund. |
| **Case 4: Webhook Reclaim races uncommitted Driver 2 INSERT** | Thread C runs reclaim UPDATE at exact same microsecond Thread B runs INSERT. | PostgreSQL GiST index locks both transactions; secondary transaction waits for primary to commit or abort. | Winner commits to `CONFIRMED`; loser receives `23P01`. | If Driver 2 wins, Driver 1 refunded. If Driver 1 wins, Driver 2 receives HTTP 409. | **Zero Split-Brain.** Deterministic engine-level exclusion; zero uncoordinated states. |

### 15.5 Booking and Hold Lifecycle (Sequential Diagram 10 / Mandatory PRD Diagram 9)

```mermaid
stateDiagram-v2
    [*] --> ACTIVE_HOLD: Driver Initiates Hold (480s TTL)
    
    ACTIVE_HOLD --> EXPIRED_HOLD: 480s Elapsed (Two-Tier Sweep)
    ACTIVE_HOLD --> CONFIRMED: Payment Webhook Verified
    
    EXPIRED_HOLD --> CONFIRMED: LPRP Race Won (Bay Still Vacant)
    EXPIRED_HOLD --> RELEASED_UNFULFILLABLE: LPRP Race Lost (Exclusion Violation 23P01)
    
    RELEASED_UNFULFILLABLE --> REFUND_ELIGIBLE: Multi-Stage Refund Dispatched
    
    CONFIRMED --> ACTIVE_SESSION: Guard Validates Entry QR (SCR-301)
    CONFIRMED --> CANCELLED_BY_DRIVER: Driver Cancels per Policy
    CONFIRMED --> NO_SHOW: 30-Minute Grace Window Elapses
    CONFIRMED --> ARRIVAL_FAILED: Bay Obstructed (GPRP Triggered)
    
    ARRIVAL_FAILED --> REPLACED: Driver Accepts Alternative (SCR-108)
    ARRIVAL_FAILED --> REFUND_ELIGIBLE: Alternative Declined / Unavailable
    
    ACTIVE_SESSION --> COMPLETED: Guard Validates Exit QR
```

---

## Section 16 — Payment Processing Architecture

### 16.1 Decoupled Payment Gateway Strategy (`FD-01`)
Per founder decision `FD-01`, Gadispot implements a **Dual Payment Gateway Strategy** with **Razorpay** as primary and **Cashfree** as secondary standby. Both gateways are underwritten simultaneously and sit behind `PaymentGatewayPort`:
- **Circuit Breaker Failover:** The port adapter monitors outbound gateway requests. If the primary gateway generates 3 consecutive 5xx errors or network timeouts exceeding $5000\text{ms}$, the circuit breaker trips to `OPEN` status, immediately routing subsequent checkout sessions to Cashfree standby without user disruption.
- **Unified Transaction Abstraction:** Both gateways emit standardized event domain objects to the application layer, ensuring the booking and ledger modules remain completely decoupled from gateway-specific API quirks.

### 16.2 Webhook Ingestion & Durable Database Idempotency
- **Never Trust Client Callbacks:** Confirmation strictly requires authoritative server-to-server webhook verification with raw HMAC-SHA256 signature validation (`X-Razorpay-Signature`) or server-to-gateway REST status polling. Signatures are verified over unparsed raw request bytes using constant-time comparison (`hmac.compare_digest`).
- **Durable Deduplication:** Webhook payloads are deduplicated via a unique constraint on `(gateway_name, gateway_event_id)` in `payment_webhook_events`. Redis acts as an ephemeral cache, never the sole deduplication authority.
- **Late Payment Resolution Protocol (LPRP) Execution:** When an authoritative captured payment webhook arrives for an expired hold (`EXPIRED_HOLD`), the webhook handler executes LPRP within a subtransaction (`async with db.begin_nested():`). If the original parking bay is still vacant, the slot is atomically reclaimed. If another driver secured the bay during the delay (`ExclusionViolation 23P01`), the subtransaction cleanly rolls back to the `SAVEPOINT`, mutates the reservation to `RELEASED_UNFULFILLABLE`, and immediately queues a 100% full refund through the canonical multi-stage refund outbox.

### 16.3 Multi-Stage Refund Lifecycle (Canonical 6-Stage Lifecycle)
Refunds are tracked across 6 canonical stages (`refund_status_enum`):
1. `REFUND_ELIGIBLE`: Qualification verified against policy.
2. `REFUND_REQUESTED`: Queued in outbox for gateway dispatch.
3. `GATEWAY_ACCEPTED`: Gateway API acknowledged refund with gateway identifier.
4. `REFUND_PROCESSING`: Processing on banking switch rails.
5. `REFUND_SETTLED`: Confirmed via gateway webhook with bank UTR/ARN.
6. `REFUND_FAILED`: Bank rail rejected; routed to ops queue.

*Customer Communication Invariant:* Customer returns are never promised as immediate or real-time. In-app status displays: *"Settlement initiated. Bank settlement typically completes in 5–7 business days per banking switch standards."*

### 16.4 Payment and Webhook Sequence (Sequential Diagram 11 / Mandatory PRD Diagram 10)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver App (SCR-103)
    participant Backend as FastAPI Payment Service
    participant Razorpay as Razorpay Gateway
    participant DB as PostgreSQL 16 (Primary)

    Driver->>Backend: POST /api/v1/bookings/hold
    Backend->>Razorpay: create_order(amount=9180 paise, receipt=SPX-982143)
    Razorpay-->>Backend: Return order_id (order_MNb7654321)
    Backend->>DB: INSERT INTO space_reservations (payment_order_id, status=ACTIVE_HOLD)
    Backend-->>Driver: Return order_id & Razorpay Key ID
    Driver->>Razorpay: Pay ₹91.80 via UPI Intent SDK
    Razorpay-->>Driver: Payment Successful Screen
    Razorpay->>Backend: POST /api/v1/webhooks/razorpay<br/>Header: X-Razorpay-Signature: <HMAC_HEX>
    Backend->>Backend: Verify Raw HMAC-SHA256 Signature
    Backend->>DB: INSERT INTO payment_webhook_events (event_id) ON CONFLICT DO NOTHING
    Note over Backend,DB: If duplicate event, return HTTP 200 OK immediately
    Backend->>DB: BEGIN TRANSACTION (READ COMMITTED)
    Backend->>DB: SELECT * FROM space_reservations WHERE payment_order_id FOR UPDATE
    Backend->>DB: UPDATE space_reservations SET status='CONFIRMED', payment_transaction_id
    Backend->>DB: INSERT INTO access_credentials (ENTRY_TOKEN, EXIT_TOKEN)
    Backend->>DB: Post Balanced Journal Entry (Ledger Accounts 1010, 2010, 2030, 3010, 3020)
    Backend->>DB: COMMIT TRANSACTION
    Backend-->>Razorpay: HTTP 200 OK (Processed)
    Backend-->>Driver: Push Notification: "Booking Confirmed! Access Pass Ready."
```

### 16.5 Payment Sandbox vs. Live Gateway Credential Gating & Mock Testing Architecture
Live third-party payment gateway integration with Razorpay and Cashfree requires production and sandbox credentials (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, `CASHFREE_WEBHOOK_SECRET`) gated under external merchant aggregator underwriting (`DEP-PAY-01`).
- **Local Development & Automated CI Execution:** To eliminate external network dependencies, flakiness, and credential leakage during automated test execution, all payment and webhook tests operate against synthetic in-memory test doubles implementing `PaymentGatewayPort`. Automated test fixtures generate deterministically signed HMAC-SHA256 payloads (`tests/helpers/webhook_signer.py`), verifying duplicate rejection, LPRP subtransaction rollbacks, and double-entry postings without outbound HTTP calls.
- **Aggregator Sandbox Verification Phase:** Once merchant sandbox access is provisioned under `DEP-PAY-01`, live webhook delivery is verified on staging environments via AWS API Gateway / WAF endpoints (`POST /api/v1/webhooks/razorpay`, `POST /api/v1/webhooks/cashfree`). Public reverse-tunnels (e.g., ngrok / Cloudflare Tunnels) are authorized exclusively in dedicated non-production developer sandboxes for interactive end-to-end payment intent testing.

---

## Section 17 — Ledger, Commission and Owner Payout Architecture

### 17.1 Relational Double-Entry Chart of Accounts
All financial movements balance across 9 standard ledger accounts (`ledger_accounts`):
- `1010` (Asset, Debit): Gateway Transit Account (Driver funds captured awaiting aggregator settlement).
- `1020` (Asset, Debit): Operating Bank Account (Platform primary current account).
- `2010` (Liability, Credit): Owner Payable Liability (Accumulated net earnings owed to space hosts).
- `2020` (Liability, Credit): Customer Refund Payable (Pending customer refunds).
- `2030` (Liability, Credit): GST Output Tax Payable (18% GST collected on platform fees).
- `3010` (Revenue, Credit): Platform Commission Revenue (15% marketplace facilitation fee per `POL-COM-01`).
- `3020` (Revenue, Credit): Driver Convenience Fee Revenue (Fixed platform fee).
- `4010` (Expense, Debit): Payment Gateway MDR Expense (Aggregator processing fee).
- `4020` (Expense, Debit): GPRP Customer Recovery Subsidy Expense (Goodwill absorption up to ₹100 per `POL-SUB-01`).

### 17.2 Mathematical Balancing & Zero Child Lock Protocol
Every posted journal must strictly satisfy:
$$\sum_{\text{lines}} \text{Debits} = \sum_{\text{lines}} \text{Credits} \quad \text{with Line Count} \ge 2.$$

**Zero Child Lock Protocol:** In `fn_verify_journal_balance()`, child `journal_lines` are read without acquiring `FOR UPDATE` locks. Concurrency serialization is guaranteed by the parent row exclusive lock on `journal_entries` acquired during `UPDATE ... SET posting_status = 'POSTED'`. Child line modifications acquire `FOR SHARE` on the parent. When lines are moved across journals, deterministic locking order `OLD.journal_id < NEW.journal_id` completely eliminates deadlocks.

**Compensating Reversal Journal Specifications:** Because posted journals and lines are strictly immutable under database trigger `fn_prevent_posted_lines_modification()`, any operational cancellation, refund, or settlement requires posting a balanced compensating journal entry:
1. **Full Driver Cancellation / GPRP Failover Refund Journal:**
   - Debit `2010` (Owner Payable Liability): ₹68.00 (reverses host allocation)
   - Debit `3010` (Platform Commission Revenue): ₹12.00 (reverses commission)
   - Debit `3020` (Driver Convenience Fee Revenue): ₹10.00 (reverses convenience fee)
   - Debit `2030` (GST Output Tax Payable): ₹1.80 (reverses GST liability)
   - Credit `2020` (Customer Refund Payable): ₹91.80 (records obligation to driver)
2. **Gateway Bank Settlement Journal (Upon Aggregator Webhook Confirmation):**
   - Debit `2020` (Customer Refund Payable): ₹91.80 (clears refund liability)
   - Credit `1010` (Gateway Transit Account): ₹91.80 (deducts transit funds)
3. **Weekly Host Batch Payout Journal (`FD-05`):**
   - Debit `2010` (Owner Payable Liability): Total disbursement amount ($\ge ₹500$)
   - Credit `1020` (Operating Bank Account): Total corporate funds transferred via IMPS

### 17.3 Weekly Host Batch Payouts (`FD-05`)
Host payouts are disbursed via **Scheduled Batch Bank Transfers** from the platform corporate bank account on **Tuesdays** for hosts with accumulated balances $\ge ₹500$ (`POL-POT-01`), under prior bank KYC verification.

### 17.4 Ledger and Payout Flow (Sequential Diagram 12 / Mandatory PRD Diagram 11)

```mermaid
flowchart TD
    DriverPay["Driver Pays ₹91.80\n(Base: ₹80.00, Conv Fee: ₹10.00, GST: ₹1.80)"] --> BookingCommit["Booking Confirmation Trigger"]
    
    subgraph DoubleEntryPost ["Double-Entry Balanced Journal (PostgreSQL)"]
        Line1["Debit 1010 (Gateway Transit Asset): ₹91.80"]
        Line2["Credit 2010 (Owner Payable Liability): ₹68.00\n(Base ₹80 minus 15% Commission ₹12)"]
        Line3["Credit 3010 (Platform Commission Revenue): ₹12.00"]
        Line4["Credit 3020 (Driver Convenience Fee Revenue): ₹10.00"]
        Line5["Credit 2030 (GST Output Tax Payable): ₹1.80"]
    end

    BookingCommit --> DoubleEntryPost
    DoubleEntryPost --> TriggerVerify{"fn_verify_journal_balance()\nDebits == Credits && Lines >= 2\n(Zero Child Lock Protocol)"}
    
    TriggerVerify -- Pass --> PostedJournal[("POSTED Journal Entry\n(Immutable)")]
    TriggerVerify -- Fail --> RejectRollback["Transaction Aborted & Rolled Back"]

    PostedJournal --> Accumulate["Accumulate in Owner Balance\n(Account 2010)"]
    Accumulate --> TuesdayBatch{"Weekly Tuesday Batch\nBalance >= ₹500 & KYC Verified"}
    TuesdayBatch -- Yes --> BankIMPS["Corporate Bank IMPS API\nDisbursement to Host Account"]
    TuesdayBatch -- No --> Rollover["Rollover to Next Tuesday Batch"]
    
    BankIMPS --> SettlementEntry["Post Settlement Journal:\nDebit 2010 (Owner Liability)\nCredit 1020 (Operating Bank Account)"]
```

---

## Section 18 — QR Access and Parking Session Architecture

### 18.1 Cryptographic Separation of the Two QR Systems
A critical design invariant is the complete separation between Payment QRs and Access QRs:
- **Dynamic Payment QR:** Financial domain, generated by payment gateway, consumed by driver UPI apps, expires in 480 seconds, bound to NPCI settlement.
- **Parking Access QR:** Physical security domain, generated by Gadispot cryptographic service, consumed by guard camera scanner (`SCR-301`), opaque 128-bit CSPRNG token (`secrets.token_hex(16)`), bound to physical property and reservation interval.

### 18.2 Entry and Exit Token Binding Rules & Replay Attack Defense
1. **`ENTRY_TOKEN` (`spx_ent_` + 32-char hex):** Valid from $[t_{\text{start}} - 15\text{m}, t_{\text{start}} + 30\text{m})$. Consumed atomically upon successful guard scan; transitions reservation to `ACTIVE_SESSION`.
   - **Check-in Window Validation:** Scans attempted earlier than $t_{\text{start}} - 15\text{m}$ are rejected with RFC 7807 code `TOO_EARLY_FOR_CHECKIN`. Scans attempted later than $t_{\text{start}} + 30\text{m}$ (where reservation was swept to `NO_SHOW`) are rejected with `RESERVATION_CANCELLED_NO_SHOW`.
   - **Atomic Consumption & Replay Prevention:** Verified via `UPDATE access_credentials SET status = 'CONSUMED', consumed_at = NOW() WHERE opaque_token = :token AND status = 'ACTIVE'`. If 0 rows are updated, the scan attempt is flagged as `REPLAY_ATTACK_REJECTED`, logging guard ID and device fingerprint in `access_scan_logs`, and displaying a bold red rejection screen on the guard scanner (`SCR-302`).
2. **`EXIT_TOKEN` (`spx_ext_` + 32-char hex):** Pre-cached locally on driver app upon check-in to ensure accessibility in offline basements. Valid until $[t_{\text{checkin}}, t_{\text{end}} + 15\text{m})$. Consumed upon departure scan; transitions reservation to `COMPLETED`.
   - **Overstay Assessment:** If departure scan occurs after the 15-minute grace window ($> t_{\text{end}} + 15\text{m}$), the guard scanner automatically displays overstay tariff calculation per `POL-OST-01` before clearing departure.

### 18.3 Controlled Manual Exception Protocol in Deep Basements (`FD-03`)
In underground commercial basements (B1/B2/B3) where mobile networks drop to zero, guards cannot execute online QR validation. Offline admission is handled as a **Controlled Manual Exception**:
1. Guard switches app to Offline Exception Mode (`SCR-304`).
2. Guard matches vehicle plate against local encrypted shift cache (read-only reference).
3. Guard captures timestamped gate photo proof and driver phone last 4 digits.
4. Guard taps "ADMIT ON CONDITIONAL MANUAL EXCEPTION".
5. Record is signed with a SHA-256 tamper-evident hash and queued in local SQLCipher (AES-256) storage.
6. Upon surface network reconnection, the queue flushes via `POST /api/v1/access/reconcile-offline-admissions`.
7. Photos are uploaded to private S3 and permanently deleted after 7 days via automated S3 lifecycle rules.

### 18.4 QR Entry and Exit Sequence (Sequential Diagram 13 / Mandatory PRD Diagram 12)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Driver Mobile App
    actor Guard as Security Guard (SCR-301)
    participant Backend as FastAPI Access Service
    participant DB as PostgreSQL 16 (Primary)

    Driver->>Guard: Present Dynamic Entry Pass QR (spx_ent_...)
    Guard->>Guard: Scan via mobile_scanner Viewport (Sub-500ms decode)
    Guard->>Backend: POST /api/v1/access/validate-scan<br/>{ token, property_id, guard_id }
    Backend->>DB: BEGIN TRANSACTION (READ COMMITTED)
    Backend->>DB: SELECT * FROM access_credentials WHERE opaque_token FOR UPDATE
    Backend->>DB: Verify token status is ACTIVE and within arrival window
    Backend->>DB: UPDATE access_credentials SET status='CONSUMED', consumed_at=NOW()
    Backend->>DB: UPDATE space_reservations SET status='ACTIVE_SESSION'
    Backend->>DB: INSERT INTO access_scan_logs (audit record)
    Backend->>DB: COMMIT TRANSACTION
    Backend-->>Guard: HTTP 200 OK: ADMIT VEHICLE (Green Screen, Bay A-1, Plate KA-01-AB-1234)
    Backend-->>Driver: Transition to Active Session Tracker (SCR-105) with Exit QR
    Note over Driver,Guard: Driver occupies bay until scheduled departure
    Driver->>Guard: Present Pre-Cached Exit QR Pass (spx_ext_...)
    Guard->>Backend: POST /api/v1/access/validate-exit
    Backend->>DB: Check Overstay (<15m Grace) & Burn Exit Token
    Backend-->>Guard: HTTP 200 OK: DEPARTURE CLEARED
    Backend-->>Driver: Transition to Session Summary & Receipt (SCR-106)
```

---

## Section 19 — GPRP Architecture

### 19.1 Arrival Obstruction Scenario (`ARRIVAL_FAILED`)
When a driver arrives and finds their reserved bay physically blocked, unauthorizedly occupied, or inaccessible, the driver or guard triggers the Guaranteed Parking Recovery Protocol (`SCR-107`).

### 19.2 The 8-Step Atomic Recovery Workflow
1. **Status Transition:** Original reservation is marked `status = 'ARRIVAL_FAILED'`.
2. **Spatial Inventory Query:** System queries vacant inventory within a **500m walking radius** matching the vehicle category.
3. **Atomic Alternative Hold:** If an alternative space is found, it is atomically locked under a temporary hold with an explicit **180-second decision timer**.
4. **Driver Proposal:** In-app card (`SCR-108`) displays alternative walking distance, bay label, and photo.
5. **Driver Acceptance:** Driver accepts within 180 seconds.
6. **Booking Confirmation & Original Release:** Alternative reservation is confirmed; original reservation transitions to `status = 'REPLACED'`.
7. **Tariff Goodwill Adjustment:** If the alternative space has a higher tariff, the platform absorbs the price difference up to ₹100 (`POL-SUB-01`) via Account `4020` (Customer Recovery Subsidy Expense). The spatial query strictly excludes bays requiring $>₹100$ subsidy from automated proposals to guarantee bounded platform liability and zero unexpected driver charges. If the alternative bay has a lower tariff, the original tariff difference is credited as a partial refund.
8. **Credential Swap:** A new `ENTRY_TOKEN` is minted for the alternative bay; original QR is revoked.

### 19.3 Automated Full Refund Fallback (`FD-02`)
If no alternative space is available within 500m (or if available spaces require $>₹100$ subsidy), or if the driver declines the proposal or the 180-second decision timer elapses, the system immediately releases any temporary hold, transitions the reservation to `status = 'REFUND_ELIGIBLE'`, and dispatches an automated **100% full refund** to the original payment instrument across the canonical 6-stage lifecycle (`FD-02`).

### 19.4 GPRP Recovery Flow (Sequential Diagram 14 / Mandatory PRD Diagram 14)

```mermaid
flowchart TD
    Report["Driver / Guard Reports Bay Obstructed\n(SCR-107: ARRIVAL_FAILED)"] --> QuerySpatial["GPRP Engine Queries Vacant Inventory\nWithin 500m Walking Radius"]
    
    QuerySpatial --> CheckFound{Alternative Space Found?}
    
    CheckFound -- Yes --> AtomicHold["Atomic Hold on Alternative Space\n(180-Second Decision Timer)"]
    AtomicHold --> OfferCard["Present Alternative Card (SCR-108)\nto Driver with Walking Route"]
    
    OfferCard --> DriverDecision{Driver Decision\nin 180 Seconds?}
    
    DriverDecision -- Accepted --> SwapReservations["Atomically Confirm Alternative Space\nMark Original as REPLACED\nAbsorb Rate Delta up to ₹100 (Account 4020)\nMint New Entry QR Pass"]
    
    DriverDecision -- Declined / Expired --> TriggerRefund["Release Alternative Hold"]
    CheckFound -- No --> TriggerRefund
    
    TriggerRefund --> FullRefund["Transition to REFUND_ELIGIBLE (FD-02)\nInitiate 100% Full Refund to Original Instrument\n(Canonical 6-Stage Refund Lifecycle)"]
```

---

## Section 20 — Notifications and Background Processing

### 20.1 Background Worker Architecture (ARQ / Celery)
Asynchronous background workloads are executed by a pool of stateless workers consuming task queues backed by Redis:
- **Hold Expiration Sweeper (Every 5 Seconds):** Executes Tier-1 batch sweep releasing expired holds (`hold_expires_at <= NOW()`).
- **No-Show Sweeper (Every 60 Seconds):** Identifies confirmed reservations where check-in did not occur within 30 minutes of scheduled start (`POL-ARR-02`), transitions status to `NO_SHOW`, and releases bay.
- **Refund Dispatch Worker:** Consumes `outbox_events` for `REFUND_REQUESTED` and invokes payment aggregator refund APIs.
- **Photo Purge Lifecycle Worker (Daily):** Identifies reconciled offline admission photos older than 7 days and permanently purges S3 objects.
- **Weekly Host Payout Worker (Tuesdays 02:00 IST):** Generates settlement batches for host balances $\ge ₹500$.

### 20.2 Transactional Outbox Pattern
To prevent distributed transaction failures between database commits and external messaging dispatch, events are written to the `outbox_events` table within the primary ACID transaction and asynchronously polled by background workers.

### 20.3 Multi-Channel Notification Routing
- **Firebase Cloud Messaging (FCM):** High-priority push notifications for booking confirmations, 15-minute departure reminders, and GPRP recovery offers.
- **TRAI DLT-Compliant SMS:** Transactional booking references and OTPs delivered via registered DLT templates (`DEP-TEL-01`).

### 20.4 Dead-Letter Queue (DLQ) & Worker Fault Tolerance
- **Consumer Group Acknowledgements:** Background tasks use Redis Stream consumer groups with explicit acknowledgements (`XACK`).
- **Retry Backoff Schedule:** Transient worker failures (e.g. gateway rate limits, SMS provider timeouts) retry up to 3 times with exponential backoff (1s, 5s, 25s).
- **Dead-Letter Queue (`stream:dlq:dead_letters`):** Poison messages failing after 3 attempts are automatically moved to the DLQ stream, preserving the original payload, exception stack trace, and execution context, and emitting an automated P1 CloudWatch alarm to SecOps.
- **Worker Crash Recovery:** Orphaned tasks from crashed worker processes are reclaimed via background `XAUTOCLAIM` scanning the Pending Entries List (PEL) for messages idle $>60\text{s}$.

---

## Section 21 — API Architecture and Contracts

### 21.1 Global API Standards
- **Protocol:** HTTPS / TLS 1.3 only.
- **Base URL:** `https://api.gadispot.in/api/v1`
- **Authentication:** `Authorization: Bearer <JWT>`
- **Idempotency:** Mutating endpoints (`POST`, `PUT`, `DELETE`) require `Idempotency-Key: <UUIDv4>`.
- **Payload Format:** JSON (`Content-Type: application/json`). Date/time strings use ISO 8601 with timezone offset (`2026-11-03T14:00:00+05:30`).
- **Cursor Pagination Standard:** List endpoints (`/spaces/search`, `/operations/queue`) use opaque cursor pagination (`cursor=<base64_encoded_sort_key_and_uuid>`, `limit` default 20, max 100). Offset-based pagination is forbidden on large datasets.
- **Rate Limiting Headers:** All HTTP responses provide rate-limit feedback:
  - `X-RateLimit-Limit`: Maximum requests permitted in window.
  - `X-RateLimit-Remaining`: Remaining requests in current window.
  - `X-RateLimit-Reset`: UTC epoch seconds when window resets.
- **RFC 7807 Problem Details Error Schema:** All API errors return `Content-Type: application/problem+json` matching the standard structure:
  ```json
  {
    "type": "https://api.gadispot.in/errors/holding-conflict",
    "title": "Space Allocation Conflict",
    "status": 409,
    "detail": "The requested parking space is currently held by another checkout session.",
    "instance": "/api/v1/bookings/hold",
    "code": "SLOT_CURRENTLY_HELD",
    "invalid_params": []
  }
  ```

### 21.2 Canonical API Endpoint Inventory

| HTTP Method | Endpoint Path | Role Scoping | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/session` | Public | Exchange verified Firebase ID token for Gadispot JWT & refresh token. |
| `POST` | `/api/v1/auth/refresh` | Authenticated | Refresh expired access JWT using sliding refresh token. |
| `POST` | `/api/v1/auth/switch-role` | Authenticated | Switch active persona between Driver and Owner. |
| `GET` | `/api/v1/users/me` | Authenticated | Retrieve authenticated user profile and registered vehicles. |
| `POST` | `/api/v1/users/vehicles` | Driver | Register new vehicle (plate, vehicle category, EV flag). |
| `POST` | `/api/v1/spaces/search` | Public / Driver | Spatial PostGIS discovery query with dimensional compatibility filter. |
| `POST` | `/api/v1/bookings/hold` | Driver | Atomically create 480-second checkout hold (`ACTIVE_HOLD`). |
| `GET` | `/api/v1/payments/verify/{order_id}` | Driver | Polling fallback for payment verification when webhook is delayed. |
| `POST` | `/api/v1/webhooks/razorpay` | Public (HMAC) | Authoritative raw HMAC-SHA256 verified payment webhook ingestion. |
| `GET` | `/api/v1/access/credentials/{res_id}` | Driver | Retrieve active vector Entry/Exit QR pass tokens. |
| `POST` | `/api/v1/access/validate-scan` | Guard | Guard camera entry scan validation (sub-500ms admit/deny). |
| `POST` | `/api/v1/access/validate-exit` | Guard | Guard departure scan validation and overstay tariff assessment. |
| `POST` | `/api/v1/access/reconcile-offline` | Guard | Flush signed offline manual admissions from underground basements. |
| `POST` | `/api/v1/properties` | Owner | Scaffolding new property and parking bay dimensions. |
| `POST` | `/api/v1/properties/{id}/documents` | Owner | Obtain presigned S3 URLs for legal deed and photo uploads. |
| `GET` | `/api/v1/owner/dashboard` | Owner | Retrieve live occupancy gauge and today's accumulated earnings. |
| `POST` | `/api/v1/gprp/report-obstruction` | Driver / Guard | Report bay blocked and initiate 8-step recovery workflow. |
| `POST` | `/api/v1/gprp/accept-alternative` | Driver | Accept 500m alternative parking bay within 180 seconds. |
| `GET` | `/api/v1/operations/queue` | Operations | Retrieve pending property authorization queue. |

---

## Section 22 — Security Architecture and Threat Boundaries

### 22.1 Threat Modeling (STRIDE Matrix)

| Threat Category | Potential Attack Vector | Architectural Mitigation & Hardening Control |
|---|---|---|
| **Spoofing** | Forged guard scan verification or identity theft. | Scoped JWT validation; cryptographic binding of guard tokens to property IDs. |
| **Tampering** | Modifying offline admission queues on rooted devices. | SHA-256 event chaining; SQLCipher 256-bit AES encryption on guard devices. |
| **Repudiation** | Driver denying physical parking check-in. | Explicit audit logging of guard ID, timestamp, and device fingerprint in `access_scan_logs`. |
| **Information Disclosure**| Data leakage of property title deeds or host earnings. | Private encrypted S3 buckets with IAM least privilege; presigned URLs with 15-minute validity window. |
| **Denial of Service** | Exhausting connection pools via search request flooding. | CloudFront WAF rate limiting (100 req/min/IP); PgBouncer connection pooling. |
| **Elevation of Privilege**| Driver invoking administrative property approvals. | Server-side RBAC validation; administrative approvals require 2FA TOTP. |

### 22.2 Network Security & Ingress Filtering
- **Zero Public Database Exposure:** RDS PostgreSQL and ElastiCache Redis instances have zero public IP addresses and sit strictly within isolated VPC database subnets.
- **Egress-Only NAT Gateway:** Backend workers reach third-party APIs (Razorpay, Firebase) through AWS NAT Gateways with static EIPs.
- **Raw Webhook Security:** Webhook handlers compute raw HMAC-SHA256 signatures over unparsed request bodies using constant-time comparison (`hmac.compare_digest`).
- **Strict CORS Origin Whitelisting:** Cross-Origin Resource Sharing is strictly constrained to approved production origins (`https://gadispot.in`, `https://admin.gadispot.in`, `https://app.gadispot.in`). Wildcard origins (`*`) are disallowed across all environments.

### 22.3 Authentication & Cryptographic Key Management
- **Access Tokens:** JWT access tokens have a 60-minute TTL (harmonized with Section 11.1, Diagram 6, and PRD V2.3.2), signed via asymmetric RS256 / Ed25519 private keys managed in AWS Secrets Manager.
- **Sliding Refresh Tokens & Reuse Detection:** 30-day refresh tokens stored in platform keystores (iOS Keychain / Android Keystore) issue new token pairs on each refresh. If a revoked or previously used refresh token is presented, the entire token family is immediately revoked, forcing re-authentication.
- **KMS Customer Managed Keys (CMKs):** All persistent data at rest (RDS PostgreSQL storage, ElastiCache Redis, S3 buckets, EBS volumes) is encrypted via AWS KMS Customer Managed Keys with automated annual rotation. All transit traffic enforces TLS 1.3.

---

## Section 23 — Privacy and Data Architecture

### 23.1 DPDPA 2023 Statutory Compliance
Gadispot complies with India's Digital Personal Data Protection Act 2023 (DPDPA):
1. **Notice & Consent (Sections 5 & 6):** Unambiguous bilingual (English & Kannada) consent modals presented at user registration detailing data collection purposes. Consent records are audited and persisted in `privacy_consent_logs` with `user_id`, `consent_version_id`, `ip_address`, `timestamp`, and affirmative consent flags.
2. **Purpose Limitation (Section 7):** Personal data is collected strictly for physical gate access verification and financial billing. PII is never sold, shared, or brokered to external advertising networks.
3. **Data Minimization (Section 8):** Zero collection of Aadhaar numbers, driving licenses, or banking passwords. Only operational data necessary for parking fulfillment is collected (phone number, name, vehicle plate). Driver live GPS tracking is terminated immediately upon gate check-in.
4. **Storage Limitation (Section 8):** Search coordinates and route traces are automatically purged after 180 days via scheduled worker (`purge_stale_search_coordinates`). Surveillance photos captured during offline basement admissions are automatically purged after 7 days.
5. **Right to Erasure (Section 12):** Users can request account deletion via mobile settings. Personal identifiers are anonymized within 30 days while preserving financial double-entry ledger entries for statutory 7-year tax audit periods.

### 23.2 Automated 7-Day S3 Photo Purge Rule
Surveillance photos of vehicle registration plates captured by security guards during manual exception admissions represent sensitive personal data. Under AWS S3 lifecycle policy:
- Photos uploaded to `s3://gadispot-audit-photos/` are automatically and permanently deleted 7 days after upload.
- The backend retains only the non-reversible SHA-256 cryptographic event hash for audit integrity.

### 23.3 Data Residency & Zero Cross-Border Telemetry Invariant
- **Indian Data Localization:** All primary databases, read replicas, Redis clusters, and S3 object stores are physically hosted within the **AWS Mumbai (`ap-south-1`)** region in strict compliance with Indian data localization requirements.
- **Zero Cross-Border Telemetry Invariant:** In accordance with DPDPA 2023 Section 23 and RBI data localization directives, all CloudWatch log groups, Prometheus metrics, distributed traces, and audit logs are pinned strictly to `ap-south-1`. No logs, metrics, or telemetry may cross international boundaries or be exported to overseas SaaS observability platforms (e.g., Datadog US/EU, Sentry US) unless routed through an in-country dedicated collector.

### 23.4 Statutory Grievance Redressal Architecture
In accordance with Rule 3(2) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 and Section 13 DPDPA 2023:
- **Designation:** Resident Grievance Officer, Gadispot Technologies Private Limited.
- **Physical Address:** Gadispot Operations HQ, 5th Block, Koramangala, Bengaluru, Karnataka 560095.
- **Direct Redressal Email:** `grievance@gadispot.in`.
- **Statutory SLA:** Grievance acknowledgment within 48 hours; final dispute resolution within 30 days. Contact details are permanently accessible in mobile app settings.

---

## Section 24 — Observability and Operational Architecture

### 24.1 Structured Logging & PII Scrubbing Engine
All application logs are formatted as structured JSON emitted to `stdout` and collected via AWS CloudWatch. To prevent personal data leakage into observability stores, all logging output passes through an in-memory `PIIFilter`:
- **Phone Numbers:** Masked via regex `r'(\+91\s*)?(\d{2})\d{6}(\d{2})'` $\to$ `+91 \2******\3`.
- **Vehicle Registration Plates:** Masked via regex `r'([A-Z]{2}[-\s]?\d{2})[-\s]?[A-Z]{1,2}[-\s]?(\d{4})'` $\to$ `\1-**-****`.
- **Bank Accounts & VPAs:** Masked except for the final 4 alphanumeric characters.
- **Credentials & Headers:** `Authorization: Bearer <JWT>`, `X-Razorpay-Signature`, and payment tokens are completely stripped or cryptographically hashed.

```json
{
  "timestamp": "2026-11-03T10:14:22.105Z",
  "level": "INFO",
  "logger": "modules.booking.service",
  "request_id": "c1f2e3d4-b5a6-4789-0123-abcdef456789",
  "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "vehicle_plate_masked": "KA-01-**-****",
  "event": "HOLD_CREATED",
  "reservation_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
  "parking_space_id": "c3d9a1f2-7b8c-4e5a-9f1d-2b3c4d5e6f7a",
  "duration_ms": 14.2
}
```

### 24.2 Metrics & Prometheus Instrumentation
Key performance indicators instrumented via Prometheus:
- `gadispot_search_latency_seconds`: Histogram of PostGIS spatial discovery latencies.
- `gadispot_active_holds_gauge`: Real-time gauge of active 480-second holds.
- `gadispot_gist_exclusion_conflicts_total`: Counter of concurrent hold collision errors (`23P01`).
- `gadispot_scan_validation_duration_ms`: Latency of guard QR scan verifications.

### 24.3 Health Check Endpoints
- `/health/liveness`: Returns HTTP 200 if FastAPI process is responsive.
- `/health/readiness`: Queries `SELECT 1` on PostgreSQL and executes `PING` on Redis; returns HTTP 503 if downstream storage is unreachable.

---

## Section 25 — Deployment and Environment Architecture

### 25.1 Cloud Infrastructure Specification (AWS Mumbai)
- **Container Orchestration:** AWS ECS Fargate running multi-stage Docker containers based on `python:3.11-slim`.
- **Connection Pooling & Database Proxy:** Dedicated PgBouncer High-Availability Cluster deployed in the Isolated Database Subnets in transaction pooling mode (`pool_mode = transaction`). Exposes split endpoints: `gadispot_writer:6432` routing to RDS Primary Writer, and `gadispot_reader:6433` routing to RDS Read Replica.
- **Database:** AWS RDS PostgreSQL 16 Multi-AZ (`db.t4g.xlarge` for primary, `db.t4g.xlarge` for read replica) with 100GB GP3 storage autoscaling to 500GB.
- **Cache:** AWS ElastiCache for Redis (`cache.t4g.medium` Multi-AZ with auto-failover).
- **Secrets Management:** Secrets (database credentials, payment API keys, JWT secrets) are stored in AWS Secrets Manager and mounted as environment variables at container boot.

### 25.2 Deployment and Environment Diagram (Sequential Diagram 15 / Mandatory PRD Diagram 15)

```mermaid
flowchart TD
    subgraph PublicInternet ["Public Internet"]
        MobileUsers["Flutter Mobile Clients\n(Drivers, Owners, Guards)"]
    end

    subgraph AWSCloud ["AWS Cloud (Region: ap-south-1 Mumbai)"]
        WAF["AWS WAF\n(DDoS, Rate Limiting, Geo-Restriction)"]
        CloudFront["AWS CloudFront CDN\n(TLS 1.3 Termination)"]
        
        subgraph VPC ["Virtual Private Cloud (10.0.0.0/16)"]
            subgraph PublicSubnets ["Public Subnets (Multi-AZ)"]
                ALB["Application Load Balancer"]
                NATGateway["Managed NAT Gateway\n(Static EIP for Outbound APIs)"]
            end

            subgraph PrivateAppSubnets ["Private App Subnets (Multi-AZ)"]
                ECS1["ECS Fargate Task 1\n(FastAPI Monolith)"]
                ECS2["ECS Fargate Task 2\n(FastAPI Monolith)"]
                Worker1["ECS Fargate Worker\n(ARQ / Celery)"]
            end

            subgraph IsolatedDBSubnets ["Isolated Database Subnets (Multi-AZ)"]
                PgBouncer["PgBouncer HA Cluster\n(Transaction Pooling\nDual Writer/Reader Pools)"]
                RDSPri[("RDS PostgreSQL 16\nPrimary Writer")]
                RDSReplica[("RDS PostgreSQL 16\nRead Replica")]
                RedisCluster[("ElastiCache Redis\nCluster Multi-AZ")]
            end
        end

        S3Bucket[("AWS S3 Bucket\n(KMS Encrypted, 7-Day Purge)")]
        SecretsManager["AWS Secrets Manager"]
    end

    MobileUsers --> CloudFront
    CloudFront --> WAF
    WAF --> ALB
    ALB --> ECS1
    ALB --> ECS2

    ECS1 --> PgBouncer
    ECS2 --> PgBouncer
    Worker1 --> PgBouncer
    PgBouncer -->|"Writer Pool (Port 6432)"| RDSPri
    PgBouncer -->|"Reader Pool (Port 6433)"| RDSReplica
    ECS1 --> RedisCluster
    ECS2 --> RedisCluster
    Worker1 --> RedisCluster

    ECS1 -.->|"Presigned URLs"| S3Bucket
    ECS1 --> NATGateway
    Worker1 --> NATGateway
    NATGateway -->|"Outbound HTTPS"| ExternalSaaS["External SaaS APIs\n(Razorpay, Firebase)"]
    SecretsManager -.->|"Boot Injection"| ECS1
    SecretsManager -.->|"Boot Injection"| ECS2
```

---

## Section 26 — Testing Architecture

### 26.1 Testing Pyramid Strategy
- **Unit Tests:** Business logic functions (e.g., `fn_check_vehicle_bay_compatibility`, tariff estimators, HMAC verifiers).
- **Database Integration Tests (`tests/database/`):** Real PostgreSQL 16 integration tests verifying GiST exclusion constraints, Zero Child Lock trigger behaviors, and immutable ledger triggers.
- **API Contract Tests:** Verifying request/response schemas against OpenAPI 3.1 specifications.
- **Load & Concurrency Tests:** Multi-threaded asyncpg workers simulating 50 concurrent checkouts on identical parking bays to verify zero double-booking violations.

### 26.2 Empirical Verification Record (Existing Repository Test Suite)
The repository contains 15 verified automated database tests in `tests/database/` running against PostgreSQL 16:
- `test_booking_exclusion.py` (4 tests): Verifies non-overlapping reservations succeed, overlapping active reservations fail with exclusion errors, different bays succeed in parallel, and cancelled/completed reservations do not block future holds.
- `test_concurrent_posting.py` (2 tests): Empirically proves that concurrent journal posting and line mutations execute with **zero deadlocks** under the Zero Child Lock protocol, and cross-journal line movements adhere to deterministic locking order.
- `test_ledger_immutability.py` (9 tests): Proves balanced journal entries post cleanly, unbalanced entries are rejected, single-line journals are rejected, posted journals cannot be updated or deleted, and lines cannot be inserted, updated, deleted, or moved on posted journals.

**Empirical Result:** 15 passed in 11.58s (`pytest tests/ -v`).

---

## Section 27 — Performance and Scalability Architecture

### 27.1 Latency Budgets & Target SLAs
- **Geospatial Discovery Search (`POST /spaces/search`):** P95 $\le$ 200ms across 50,000 indexed bays.
- **Hold Creation (`POST /bookings/hold`):** P99 $\le$ 150ms.
- **Guard Scan Validation (`POST /access/validate-scan`):** P99 $\le$ 500ms over 4G connections.
- **Payment Webhook Processing (`POST /webhooks/razorpay`):** P99 $\le$ 300ms.

### 27.2 Scaling Mechanics & Connection Pool Sizing under Festival Surge Peaks
- **Stateless Monolith Autoscaling:** Fargate tasks scale from a minimum of 2 tasks up to 10 tasks based on CPU utilization (>60%) and request latency targets.
- **Connection Pool Sizing (Baseline vs. Festival Surge Peaks):**
  During major urban surge events in Bengaluru (e.g., Diwali shopping peaks in Commercial Street/Jayanagar, New Year's Eve in Koramangala/Indiranagar, or IPL match days at M. Chinnaswamy Stadium):
  - *Baseline Load (2 ECS Tasks):* $2 \text{ tasks} \times 80 \text{ max asyncpg connections} = 160$ client pool connections.
  - *Peak Festival Surge Load (10 ECS Tasks):* $10 \text{ tasks} \times 80 \text{ max asyncpg connections} = 800$ client pool connections.
  - *Background Workers (2 ARQ/Celery Tasks):* $2 \text{ tasks} \times 20 \text{ connections} = 40$ client connections.
  - *Total Peak Inbound Client Connections:* 840 concurrent client connections fronting the database tier.
- **PgBouncer Configuration Matrix (`/etc/pgbouncer/pgbouncer.ini`):**
  PgBouncer operates strictly in transaction pooling mode (`pool_mode = transaction`), decoupling inbound client connection spikes from PostgreSQL physical backend processes:
  ```ini
  [databases]
  gadispot_writer = host=rds-primary.ap-south-1.rds.amazonaws.com port=5432 dbname=gadispot auth_user=gadispot_app
  gadispot_reader = host=rds-replica.ap-south-1.rds.amazonaws.com port=5432 dbname=gadispot auth_user=gadispot_app

  [pgbouncer]
  listen_port = 6432
  listen_addr = *
  auth_type = scram-sha-256
  auth_file = /etc/pgbouncer/userlist.txt
  pool_mode = transaction
  max_client_conn = 5000
  default_pool_size = 100
  min_pool_size = 20
  reserve_pool_size = 25
  reserve_pool_timeout = 2.0
  max_db_connections = 400
  server_fast_close = 1
  dns_max_ttl = 3
  query_timeout = 15.0
  idle_transaction_timeout = 30.0
  ```
  *Capacity Verification:* The RDS instance class (`db.t4g.xlarge` with 16GB RAM) supports a PostgreSQL engine ceiling of ~1,700 `max_connections`. By capping PgBouncer `max_db_connections = 400`, the primary database writer maintains predictable memory consumption (<35% RAM allocated to backend processes) while easily multiplexing 840+ peak ECS connections with sub-millisecond connection acquisition latency.
- **Mandatory `asyncpg` Driver Setting with Transaction Pooling:**
  Because PgBouncer transaction pooling reassigns physical PostgreSQL server connections across distinct client transactions, server-side prepared statements cannot be cached across transactions. Client pools MUST configure `statement_cache_size = 0`:
  ```python
  pool = await asyncpg.create_pool(
      dsn="postgresql://gadispot_app:***@gadispot-db-writer.internal:6432/gadispot_writer",
      min_size=20,
      max_size=80,
      statement_cache_size=0,  # CRITICAL: Prevents 'prepared statement does not exist' in transaction pooling
      command_timeout=10.0,
  )
  ```
- **Failover Mode & Recovery under Peak Load:**
  If the RDS primary writer experiences hardware failure or degradation, AWS RDS Multi-AZ promotes the standby replica in $<60$ seconds. PgBouncer handles the switchover transparently:
  1. `server_fast_close = 1` immediately terminates dead backend server sockets, purging broken connections.
  2. `dns_max_ttl = 3` forces PgBouncer to re-resolve the RDS primary DNS CNAME within 3 seconds, discovering the newly promoted writer endpoint.
  3. Inbound client queries from ECS during the brief failover window queue harmlessly within PgBouncer client queues (up to `max_client_conn = 5000`) rather than terminating with TCP socket resets or HTTP 500 crashes.
  4. If the read replica experiences an outage, read queries gracefully fail over to the primary writer pool via application-level circuit breaker fallback.

---

## Section 28 — Failure Modes and Recovery Architecture

### 28.1 Failure Mode and Effects Analysis (FMEA Matrix)

| Subsystem | Failure Scenario | Impact | Detection Mechanism | Automated Recovery Workflow |
|---|---|---|---|---|
| **Primary DB** | RDS primary writer crashes or hardware fails. | Mutating writes fail temporarily. | CloudWatch RDS health probe; AWS multi-AZ monitor. | AWS RDS promotes standby replica in <60s; PgBouncer flushes dead sockets via server_fast_close=1, re-resolves RDS primary DNS CNAME in 3s (dns_max_ttl=3), preserving active client sessions. |
| **Payment Gateway**| Primary gateway (Razorpay) experiences outage. | Driver UPI checkouts fail. | Consecutive 5xx responses or circuit breaker trips (>5 failures in 30s). | Dynamic runtime failover switches `PaymentGatewayPort` to Cashfree standby adapter. |
| **Network (Basement)**| Guard phone enters underground dead zone. | Online QR validation fails. | Guard app detects network timeout (>3 seconds). | App switches to Controlled Manual Exception mode; queues signed photo proof in SQLCipher. |
| **Payment Webhook**| Gateway webhook dropped or delayed by congestion. | Booking remains in ACTIVE_HOLD. | Driver polling fallback (`GET /payments/verify/{order_id}`); outbox monitor. | Driver app polls backend; backend actively queries gateway REST API to confirm payment and finalize booking. |
| **Gate Arrival**| Reserved bay is occupied by unauthorized car. | Driver arrives but cannot park (`ARRIVAL_FAILED`). | Driver or guard reports obstruction via `SCR-107`. | GPRP triggers: searches 500m radius, holds alternative for 180s; if unavailable, issues 100% full refund. |
| **Driver No-Show** | Driver fails to arrive within 30 minutes of start time. | Space remains idle; host revenue trapped. | Background No-Show Sweeper runs every 60s. | Sweeper transitions reservation to `NO_SHOW`; releases bay for instant search re-indexing. |

### 28.2 Critical Failure Recovery Flow (Sequential Diagram 16 / Mandatory PRD Diagram 16)

```mermaid
flowchart TD
    DetectFailure[Failure Event Detected] --> ClassifyFailure{Classify Failure Mode}

    ClassifyFailure -- Primary DB Outage --> DBOp["AWS RDS Multi-AZ Auto-Failover\nPromotes Standby Replica in <60s\nPgBouncer Flushes & Re-Resolves CNAME (3s)\nFastAPI Preserves Active Sessions"]
    
    ClassifyFailure -- Payment Gateway Outage --> GateOp["Circuit Breaker Detects 5xx Spike\nHot-Swap PaymentGatewayPort\nfrom Razorpay to Cashfree Standby"]
    
    ClassifyFailure -- Basement Offline (Dead Zone) --> OfflineOp["Switch Guard App to Offline Mode (SCR-304)\nMatch Local SQLCipher Schedule\nCapture Plate Photo Proof\nQueue Tamper-Evident Record\nFlush upon Surface 4G Reconnect"]
    
    ClassifyFailure -- Delayed Webhook Race --> LPRPOp["LPRP Triggered\nAttempt Atomic Slot Reclaim\nIf Exclusion Conflict 23P01 Lost:\nMark RELEASED_UNFULFILLABLE\nDispatch Multi-Stage Refund"]
    
    ClassifyFailure -- Bay Obstructed at Arrival --> GPRPOp["GPRP 8-Step Protocol Triggered\nQuery 500m Inventory Radius\nLock Alternative for 180s Decision\nIf Declined/Unavailable: 100% Full Refund"]

    DBOp --> RestoreNormal[System Restores Normal Operation]
    GateOp --> RestoreNormal
    OfflineOp --> RestoreNormal
    LPRPOp --> RestoreNormal
    GPRPOp --> RestoreNormal
```

---

## Section 29 — Architecture Decisions and Open Questions

### 29.1 Architecture Decisions Register
The foundational architecture decisions (`ADR-001` through `ADR-010`) are documented in Section 5.2. All foundational decisions reflect approved baselines aligned with PRD V2.3.2.

### 29.2 Commercial & Product Policies Pending Founder Signoff
Per [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md), the following 7 commercial policies are currently modeled as `PROPOSED (Pending Founder Approval)` and await formal executive signature before commercial pilot launch:
1. `POL-COM-01`: Platform Commission Rate proposed at flat 15.0%.
2. `POL-DUR-01`: Minimum Booking Duration proposed at 30 minutes.
3. `POL-CAN-01`: Cancellation Tiers (>2h: 100% refund; 30m–2h: 50% refund; <30m: 0% refund; convenience fee non-refundable).
4. `POL-ARR-02`: Driver No-Show Grace Period proposed at exactly 30 minutes.
5. `POL-OST-01`: Overstay Penalty Tariff proposed at 1.5× base hourly rate in 30-minute increments.
6. `POL-POT-01`: Weekly Host Batch Payout schedule proposed for Tuesdays with ₹500 minimum threshold.
7. `POL-SUB-01`: GPRP Alternative Parking Subsidy Cap proposed at ₹100 absorbed by platform.

### 29.3 Open Questions & Proposed Technical Defaults
From [docs/product/OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md):
- **OQ-TECH-001 (Map Provider Costs):** Proposed default uses Google Maps SDK for mobile map rendering and Google Places Autocomplete. Fallback evaluates Mapbox / OpenStreetMap if API billing exceeds budget during pilot.
- **OQ-OPS-002 (Guard Smartphone Specs):** Guard app target baseline specified for Android 10+ devices with minimum 2GB RAM and 8MP autofocus camera.
- **OQ-PAY-003 (PA Route vs Batch Bank Transfers):** Architecture fully implements dual-entry ledger compatibility for both Razorpay Route automated splits and corporate banking IMPS batch transfers.

### 29.4 Critical External Dependency Gates (`BLOCKED`)
Live commercial monetization is gated on 5 external third-party dependencies recorded in Section 5.4:
1. `DEP-LEG-01`: Written legal/tax opinion on GST Section 9(1) vs 9(5) marketplace classification (`BLOCKED (Pending Memo)`).
2. `DEP-PAY-01`: Formal underwriting for marketplace split account by Razorpay Route / Cashfree Split (`BLOCKED (Under Review)`).
3. `DEP-TEL-01`: TRAI DLT registration for transactional SMS headers and templates (`BLOCKED (Filing)`).
4. `DEP-LEG-02`: BBMP municipal private driveway monetization guidance (`BLOCKED (Reviewing)`).
5. `DEP-LEG-03`: Platform Terms of Service and non-bailment statutory liability disclaimers under IT Act Section 79 (`BLOCKED (Drafting)`).

---

## Section 30 — Architecture Roadmap

### 30.1 Roadmap Phase Overview

```
+---------------------------------------------------------------------------------------------------+
|                                  GADISPOT ARCHITECTURE ROADMAP                                    |
+------------------------------------+----------------------------------+---------------------------+
| Phase 0: Verification Freeze       | Phase 1: Commercial MVP Pilot    | Phase 2: Post-Pilot Scale |
| (COMPLETED - V2.3.2)               | (Target: Sprints 1–4)            | (Target: Post-Pilot)      |
+------------------------------------+----------------------------------+---------------------------+
| • Mathematical GiST Concurrency    | • Flutter Mobile Application     | • Multi-Day & Monthly     |
| • Zero Child Lock Ledger Triggers  | • FastAPI Monolith Backend       | • Commercial Garage Mgmt  |
| • 15 Passing DB Automated Tests    | • 200 Bays in Koramangala/HSR    | • EV Charger Automation   |
| • Specification Suite Alignment    | • Dual Gateway & Guard App       | • Dynamic Demand Tariffs  |
+------------------------------------+----------------------------------+---------------------------+
```

### 30.2 Phase 1 Execution Gates (Commercial Pilot)
Execution of Phase 1 application source code proceeds under the verified architecture blueprint. Commercial pilot launch is gated on:
- Execution of founder signatures on [docs/product/FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md).
- Formal receipt of external legal tax memorandum regarding GST Section 9(1) vs 9(5) (`DEP-LEG-01`).
- Merchant aggregator underwriting approval (`DEP-PAY-01`).
- TRAI DLT registration for transactional SMS sender ID (`DEP-TEL-01`).

---

## Section 31 — Traceability Matrix

### 31.1 Traceability Mapping Table
The following matrix connects PRD functional requirements, architecture components, UI screens, database entities, test cases, and approval statuses:

| PRD Req ID | Requirement Summary | Architecture Module | Mobile Screen | DB Entity & Constraint | Verification Test Case | Approval Status |
|---|---|---|---|---|---|---|
| **FR-AUTH-001** | Phone OTP Authentication | `iam` | `SCR-002`, `SCR-003` | `users`, `user_roles` | Contract / Schema | `APPROVED` |
| **FR-AUTH-002** | Scoped Role Switching | `iam` | `SCR-101`, `SCR-201` | `user_roles` | Unit Test | `APPROVED` |
| **FR-PROP-001** | Property Onboarding Wizard | `inventory` | `SCR-202` | `properties`, `property_authorizations` | DDL Schema | `APPROVED` |
| **FR-PROP-002** | Legal Title Deed Upload | `inventory` | `SCR-202` | `properties.location` (PostGIS) | S3 Presign Test | `APPROVED` |
| **FR-SRCH-001** | Spatial Radius Discovery | `search` | `SCR-101` | PostGIS `ST_DWithin` on `properties` | Query Harness | `APPROVED` |
| **FR-SRCH-002** | Vehicle Dimensional Match | `search` | `SCR-101` | `fn_check_vehicle_bay_compatibility` | Unit Test | `APPROVED` |
| **FR-MSAI-001** | 7-Signal Availability Check | `msai` | `SCR-101` | Dynamic Signal Precedence Cascade | Unit Test | `APPROVED` |
| **FR-BOOK-001** | 480s Atomic Checkout Hold | `booking` | `SCR-103` | `space_reservations` (GiST Lock) | `test_booking_exclusion.py` | `APPROVED` |
| **FR-BOOK-002** | Two-Tier Hold Expiration | `booking` | `SCR-103` | `chk_hold_expiration`, Periodic Sweeper | Integration Test | `APPROVED` |
| **FR-PAYM-001** | Dual Gateway Orchestration | `payment_ledger` | `SCR-103` | `PaymentGatewayPort` (Razorpay/Cashfree)| Adapter Test | `APPROVED` (`FD-01`) |
| **FR-PAYM-002** | Durable Webhook Idempotency| `payment_ledger` | Background | `payment_webhook_events` (`uq_gateway_event`)| Integration Test | `APPROVED` |
| **FR-PAYM-003** | Multi-Stage Refund Lifecycle| `payment_ledger` | `SCR-106` | `refund_status_enum` (6 stages) | Lifecycle Test | `APPROVED` |
| **FR-LEDG-001** | Double-Entry General Ledger| `payment_ledger` | `SCR-203` | `journal_entries`, `journal_lines` | `test_ledger_immutability.py`| `APPROVED` |
| **FR-LEDG-002** | Zero Child Lock Trigger | `payment_ledger` | Background | `fn_verify_journal_balance` | `test_concurrent_posting.py` | `APPROVED` |
| **FR-ACCS-001** | Dual QR Code Separation | `gate_access` | `SCR-104` | `access_credentials` (128-bit CSPRNG) | Unit Test | `APPROVED` |
| **FR-ACCS-002** | Sub-500ms Guard Entry Scan | `gate_access` | `SCR-301`, `SCR-302` | `access_credentials.status = 'CONSUMED'` | Performance Harness | `APPROVED` |
| **FR-ACCS-003** | Controlled Offline Exception| `gate_access` | `SCR-304` | `offline_manual_admissions`, SQLCipher | Audit Test | `APPROVED` (`FD-03`) |
| **FR-ACCS-004** | 7-Day S3 Photo Purge Rule | `gate_access` | Storage | `photo_purge_at`, S3 Lifecycle | DDL Schema | `APPROVED` |
| **FR-GPRP-001** | 8-Step Arrival Recovery | `gprp` | `SCR-107`, `SCR-108` | `ARRIVAL_FAILED` $\to$ `REPLACED` / Refund | Workflow Test | `APPROVED` (`FD-02`) |

---

## Section 32 — Final Architecture Summary

### 32.1 Architecture Invariant Synthesis
The Gadispot architecture is governed by seven non-negotiable core invariants:
1. **Booking Concurrency Invariant:** Overlapping active bookings and holds for the same physical bay are mathematically impossible at the database engine layer via PostgreSQL GiST exclusion constraints on `tstzrange`.
2. **Hold TTL Invariant:** The checkout hold duration is strictly 480 seconds (8 minutes), cleared deterministically via two-tier expiration.
3. **Ledger Immutability & Concurrency Invariant:** All financial movements are tracked across double-entry journal entries and lines satisfying $\sum \text{Debits} = \sum \text{Credits}$ with minimum two lines. Under the Zero Child Lock protocol, posting serializes against concurrent line modifications exclusively via parent row locking without child line locks, completely eliminating lock-order inversion deadlocks.
4. **Payment Integrity Invariant:** Under zero circumstances are bookings confirmed based on client-side callbacks. Confirmation strictly requires raw HMAC-SHA256 verified gateway webhooks or direct server-to-gateway polling.
5. **Access Control Invariant:** Payment credentials and gate access credentials are strictly decoupled. Access tokens are 128-bit CSPRNG tokens with single-use atomic consumption.
6. **Availability Invariant:** Negative signals (obstructions, blackouts, closed hours) unconditionally override open schedules. Inventory is never optimistically sold.
7. **Recovery Invariant:** Drivers experiencing arrival obstruction are provided alternative parking within 500m (with up to ₹100 platform rate difference absorption) or an automated 100% full refund through the canonical 6-stage lifecycle.

### 32.2 Implementation Handoff Readiness
The architecture blueprint is complete, internally consistent, validated against repository constraints, and empirically verified against PostgreSQL 16. Development teams are authorized to proceed with Sprint 1 application code implementation across Flutter mobile interfaces and FastAPI services in strict compliance with this document.
