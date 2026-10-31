# Gadispot (formerly SmartPark Exchange) — Comprehensive User Flow & System Journey Diagrams

> **Document Version:** 2.3.0  
> **Last Updated:** 2026-10-31  
> **Status:** Approved Architecture Reference (V2.3 Harmonized)  
> **Audience:** Engineering, Product, QA, Architecture  

---

## Table of Contents

1. [Complete Driver Journey](#1-complete-driver-journey)
2. [Owner Onboarding and Property Verification](#2-owner-onboarding-and-property-verification)
3. [Parking Listing Creation and Publication](#3-parking-listing-creation-and-publication)
4. [Availability Calculation — MSAI Engine](#4-availability-calculation--msai-engine)
5. [Booking and Payment Lifecycle (with LPRP Concurrency)](#5-booking-and-payment-lifecycle-with-lprp-concurrency)
6. [QR Entry, Exit and Offline Fallback Lifecycle](#6-qr-entry-exit-and-offline-fallback-lifecycle)
7. [Arrival Failure and Recovery — GPRP Protocol](#7-arrival-failure-and-recovery--gprp-protocol)
8. [Refund Workflow (Authoritative Tiers)](#8-refund-workflow-authoritative-tiers)
9. [Owner Payout Workflow (Route & Batch IMPS Fallback)](#9-owner-payout-workflow-route--batch-imps-fallback)
10. [High-Level Modular Monolith Architecture](#10-high-level-modular-monolith-architecture)

---

## 1. Complete Driver Journey

The driver journey covers the full lifecycle from first opening the app through registration, finding and booking a parking space, completing payment, using the space, and finally rating the experience. The backend is the sole authority for state transitions.

```mermaid
flowchart TD
    A["Open SmartPark App"] --> B{"Authenticated?"}
    B -- No --> C["Enter Phone Number (+91)"]
    C --> D["Receive OTP via Firebase Auth"]
    D --> E["Submit OTP on Handset"]
    E --> F{"Firebase OTP Valid?"}
    F -- No --> G["Show Error / Retry (Rate Limited: 3 req/15m)"]
    G --> C
    F -- Yes --> H["Submit Firebase ID Token to Backend: POST /auth/session"]
    H --> I["Backend Verifies Signature via Admin SDK -> Mints Internal JWT"]
    I --> J{"Profile Complete?"}
    J -- No --> K["Enter Name, Add Vehicle (Plate, Category)"]
    K --> L["Save Profile: POST /vehicles"]
    L --> M["Profile Confirmed"]
    J -- Yes --> M
    B -- Yes --> M

    M --> N["Search Parking: Destination, Arrival Time, Duration, Vehicle"]
    N --> O["Backend PostGIS & MSAI Returns Available Bays"]
    O --> P["Browse Results on Map and Carousel"]
    P --> Q["Select a Space & Review Details (Price, Photos, Amenities)"]
    Q --> R{"Vehicle Category Compatible?"}
    R -- No --> S["Show Incompatibility Alert (e.g., SUV in Compact Bay)"]
    S --> P
    R -- Yes --> T["Tap 'Book This Bay'"]

    T --> U["Backend: POST /bookings/hold (Atomic PostgreSQL GiST Lock)"]
    U --> V{"Exclusion Conflict?"}
    V -- Yes --> W["Show HTTP 409 Conflict: Space Just Claimed"]
    W --> P
    V -- No --> X["Hold Active (480s Countdown) -> Razorpay Order Created"]

    X --> Y["Flutter Launches Razorpay Checkout SDK (UPI Intent)"]
    Y --> Z["Driver Switches to PhonePe/GPay & Authorizes UPI PIN"]
    Z --> AA["Bank Debits Driver Account"]
    AA --> AB["Razorpay Dispatches Webhook: payment.captured"]
    AB --> AC["Backend Verifies Raw HMAC Signature & Amount"]
    AC --> AD["Reservation Transitions to CONFIRMED"]
    AD --> AE["Backend Issues Opaque One-Time Access QR Token"]
    AE --> AF["Driver Receives Push Alert: Booking Confirmed with Pass"]

    AF --> AG["Driver Arrives at Property Gate"]
    AG --> AH["Present QR Pass to Security Guard"]
    AH --> AI["Guard Scans QR via Guard App (mobile_scanner)"]
    AI --> AJ{"Online Validation Passes?"}
    AJ -- No --> AK["Show Red Screen with Reason / Launch Fallback"]
    AJ -- Yes --> AL["Gate Opens -> Entry Recorded -> Session Active"]

    AL --> AM["Driver Parks Vehicle"]
    AM --> AN{"Need Extension?"}
    AN -- Yes --> AO["Request Extension in App (Checks Future Availability)"]
    AO --> AP{"Future Slot Free?"}
    AP -- No --> AQ["Show 'Cannot Extend: Booked by Next Driver'"]
    AP -- Yes --> AR["Pay Extension -> Duration Extended"]
    AR --> AM

    AN -- No --> AS["Driver Returns to Vehicle at Departure Time"]
    AS --> AT["Guard Scans Exit / Confirms Departure"]
    AT --> AU["Backend Records Exit Timestamp -> Marks COMPLETED"]
    AU --> AV["Push Notification: Session Closed & Receipt Available"]
    AV --> AW["Driver Rates Experience (1-5 Stars)"]
    AW --> AX["Session Archived in History"]
```

---

## 2. Owner Onboarding and Property Verification

Property owners must register, submit property details, and provide verifiable legal authorization documents before any listing can become bookable.

```mermaid
flowchart TD
    A["Owner Opens SmartPark App"] --> B["Phone Auth via Firebase OTP -> Internal JWT"]
    B --> C["Navigate to 'My Properties' -> 'Add Property'"]
    C --> D["Enter Property Details: Name, Address, Type"]
    D --> E["Drop Precise Map Pin (Latitude/Longitude Coordinates)"]
    E --> F["Add Parking Bays: Identifier, Covered/Open, EV, Vehicle Category"]
    F --> G["Upload 3 Mandatory Photos: Gate, Bay, Driveway Approach"]
    G --> H["Select Ownership Entity Type"]

    H --> I{"Entity Type"}
    I -- Individual Freehold --> J1["Upload Property Tax Receipt OR Sale Deed + Utility Bill"]
    I -- Residential Tenant --> J2["Upload Lease Agreement + Landlord Subletting NOC"]
    I -- Society Resident --> J3["Upload Society Share Certificate + Management Committee NOC"]
    I -- Commercial Operator --> J4["Upload Business Registration (GSTIN) + Concession/Lease Contract"]

    J1 --> K["Submit for Audit: Status = PENDING_REVIEW"]
    J2 --> K
    J3 --> K
    J4 --> K

    K --> L["Platform Operations Staff Reviews Evidence Queue"]
    L --> M{"Reviewer Verification Decision"}
    
    M -- "Rejected (Defects Found)" --> N["Record Structured Rejection Reason (Name Mismatch, Illegible)"]
    N --> O["Status = REJECTED -> Push Alert to Owner with Guidance"]
    O --> P["Owner Corrects & Re-submits Evidence"]
    P --> K

    M -- "Approved (Legally Valid)" --> Q["Status = APPROVED"]
    Q --> R["Owner Configures Operating Schedule (Weekly Hours) & Base Rates"]
    R --> S["Bays Transition to PUBLISHED"]
    S --> T["Bays Immediately Discoverable in Driver Search"]
```

---

## 3. Parking Listing Creation and Publication

Illustrates the state gatekeeper preventing unverified spaces from becoming bookable.

```mermaid
flowchart TD
    A["Owner Profile Active"] --> B["Add Space Bay to Property"]
    B --> C["Set Base Hourly Rate (e.g., ₹40/hr)"]
    C --> D["Set Weekly Operating Schedule (e.g., Mon-Fri 08:00 - 18:00)"]
    D --> E["Set Vehicle Compatibility (e.g., Hatchback, Sedan, SUV)"]
    E --> F["System Evaluates Property Authorization Status"]
    
    F --> G{"Property Status = APPROVED?"}
    G -- No: DRAFT / PENDING / REJECTED --> H["Bay Status Locked in UNVERIFIED"]
    H --> I["Bay Hidden from PostGIS Search Queries"]
    H --> J["Owner UI Displays: 'Pending Property Legal Verification'"]
    
    G -- Yes: APPROVED --> K["Bay Status Transitions to PUBLISHED"]
    K --> L["MSAI Engine Ingests Bay Schedule & Constraints"]
    L --> M["Bay Active & Instantly Bookable by Drivers"]
```

---

## 4. Availability Calculation — MSAI Engine

Multi-Source Availability Intelligence combines 7 operational signals to determine whether a bay is bookable.

```mermaid
flowchart TD
    subgraph Inputs["7 Input Signals"]
        S1["1. Owner Operating Schedule (Weekly Intervals)"]
        S2["2. Owner Manual Blackout Intervals"]
        S3["3. Confirmed Reservations in space_reservations"]
        S4["4. Active 480s Temporary Holds (GiST Constraint)"]
        S5["5. Active Sessions (Vehicle Checked In)"]
        S6["6. Guard Incident Reports (Obstruction in Last 4h)"]
        S7["7. Mandatory 15-Minute Turnover Buffers"]
    end

    Inputs --> ENGINE["MSAI Conflict Synthesizer"]
    
    ENGINE --> COMPAT{"Vehicle Compatible?"}
    COMPAT -- No --> OUT_UNAVAIL["UNAVAILABLE: Incompatible Vehicle Dimensions"]
    
    COMPAT -- Yes --> AUTH_CHK{"Property Approved?"}
    AUTH_CHK -- No --> OUT_UNVERIF["UNVERIFIED: Property Verification Pending"]
    
    AUTH_CHK -- Yes --> SCHED_CHK{"Within Operating Schedule?"}
    SCHED_CHK -- No --> OUT_CLOSED["UNAVAILABLE: Outside Operating Hours"]
    
    SCHED_CHK -- Yes --> BLACK_CHK{"Owner Blackout Active?"}
    BLACK_CHK -- Yes --> OUT_BLOCKED["BLOCKED: Space Withdrawn by Owner"]
    
    BLACK_CHK -- No --> INC_CHK{"Guard Reported Blocked Bay?"}
    INC_CHK -- Yes --> OUT_UNCERTAIN["UNCERTAIN: Active Obstruction Reported"]
    
    INC_CHK -- No --> DB_CHK{"Overlaps Active Hold or Booking in DB?"}
    DB_CHK -- Overlaps Active Hold --> OUT_HELD["TEMPORARILY_HELD: In Driver Checkout"]
    DB_CHK -- Overlaps Booking/Session --> OUT_BOOKED["BOOKED: Confirmed for this window"]
    
    DB_CHK -- Clean Interval --> OUT_AVAIL["AVAILABLE: Instantly Searchable & Bookable"]
```

---

## 5. Booking and Payment Lifecycle (with LPRP Concurrency)

Details the complete transaction loop and handles the late-arriving payment webhook edge case.

```mermaid
flowchart TD
    A["Driver Selects Space & Time Window [t_start, t_end]"] --> B["App Sends: POST /api/v1/bookings/hold"]
    B --> C["Backend Begins Transaction: READ COMMITTED"]
    C --> D["Lazy Cleanup: UPDATE space_reservations SET status='EXPIRED_HOLD' WHERE hold_expires_at < NOW()"]
    D --> E["INSERT INTO space_reservations (ACTIVE_HOLD, hold_expires_at=NOW()+480s)"]
    
    E --> F{"Exclusion Conflict (23P01)?"}
    F -- Yes --> G["ROLLBACK -> Return HTTP 409 Conflict"]
    G --> H["Driver Alerted: Slot claimed. Pick another space."]
    
    F -- No --> I["COMMIT -> Call Razorpay: POST /v1/orders"]
    I --> J["Return Order ID, Amount, 480s Expiration to Mobile App"]
    J --> K["Flutter Launches Razorpay Checkout SDK"]
    K --> L["Driver Authorizes Payment in UPI App"]

    L --> M{"Webhook Delivery Timing vs Hold Expiration"}
    
    M -- "Webhook Arrives Within 480s (Happy Path)" --> N["Verify Raw HMAC Signature & Amount"]
    N --> O["UPDATE space_reservations SET status='CONFIRMED'"]
    O --> P["Post Balanced Double-Entry Ledger (Debits=Credits)"]
    P --> Q["Issue Opaque Access QR Token (Valid Start-15m to End+15m)"]
    Q --> R["Driver Confirmed!"]

    M -- "Hold Expires (480s) BEFORE Payment Received" --> S["Background/Lazy Query Marks: EXPIRED_HOLD"]
    S --> T["Competing Driver Reserves Bay (New ACTIVE_HOLD)"]
    T --> U["Late Webhook Arrives from Razorpay: payment.captured"]
    U --> V["Backend Attempts Atomic Reclaim: UPDATE status='CONFIRMED'"]
    V --> W{"Did Exclusion Conflict (23P01) Occur?"}
    
    W -- "No: Slot was still empty!" --> O
    
    W -- "Yes: Competing driver won the slot!" --> X["Catch ExclusionViolation (23P01)"]
    X --> Y["Mark Reservation: RELEASED_UNFULFILLABLE"]
    Y --> Z["Automatically Invoke Razorpay Refund API: 100% Full Refund"]
    Z --> AA["Post Reversal Entries to Double-Entry Ledger"]
    AA --> AB["Push Alert to Driver: 'Payment received after hold expired. 100% refund initiated. UTR: [ARN]'"]
```

---

## 6. QR Entry, Exit and Offline Fallback Lifecycle

Details online authoritative gate validation and the controlled manual fallback protocol for underground basements.

```mermaid
flowchart TD
    subgraph GateArrival["Driver Gate Arrival"]
        A["Driver Arrives at Gate"] --> B["Displays Access QR on Smartphone (SCR-104)"]
        B --> C["Guard Opens Guard Scanner (SCR-301) via mobile_scanner"]
        C --> D["Camera Decodes Opaque Token: spx_XXXXXXXX"]
    end

    D --> E{"Guard Device Cellular Reception?"}
    
    subgraph OnlineValidation["Online Authoritative Validation"]
        E -- Connected (4G/5G/Wi-Fi) --> F["POST /api/v1/access/validate-scan"]
        F --> G["DB SELECT FOR UPDATE: Verify Token, Property, Expiry, Vehicle"]
        G --> H{"Validation Result?"}
        
        H -- "Token Status == CONSUMED" --> I["REJECT: Red Screen 'QR Already Used at [Time]'"]
        H -- "Wrong Property ID" --> J["REJECT: Red Screen 'Pass is for [Other Property]'"]
        H -- "Current Time < Start - 15m" --> K["REJECT: Red Screen 'Early Arrival: Opens at [Time]'"]
        H -- "All Checks Valid" --> L["UPDATE access_credentials SET status='CONSUMED'"]
        L --> M["UPDATE space_reservations SET status='ACTIVE_SESSION'"]
        M --> N["Guard Screen Flashes BOLD GREEN: 'ADMIT VEHICLE KA-01-AB-1234'"]
        N --> O["Driver Parks Vehicle"]
    end

    subgraph OfflineFallback["Underground Basement Fallback Protocol"]
        E -- Dead Zone (Network Timeout > 3s) --> P["App Displays: 'Offline Mode - Manual Gate Verification'"]
        P --> Q["Guard Opens 'Today's Shift Schedule' (Cached Locally)"]
        Q --> R["Guard Physically Inspects Metallic Vehicle License Plate"]
        R --> S{"Plate Matches Expected Shift Reservation?"}
        S -- No Match --> T["Refuse Entry: 'Vehicle not registered on today's schedule'"]
        S -- Verified Match --> U["Guard Taps: 'Manual Entry Confirmation'"]
        U --> V["Save Local Offline Record (SQLite): Plate, Time, Guard ID"]
        V --> W["Open Gate & Admit Vehicle"]
        W --> X["Device Re-connects to Network (At Surface / End of Shift)"]
        X --> Y["Execute POST /api/v1/access/sync-offline-entries"]
        Y --> Z["Backend Reconciles Session & Logs Security Audit Override"]
    end

    subgraph ExitSession["Session Exit Flow"]
        O --> EX1["Driver Prepares to Exit at Scheduled Time"]
        EX1 --> EX2["Guard Scans QR or Taps 'Record Exit' on Active Sessions"]
        EX2 --> EX3{"Exit Timestamp <= Scheduled End + 15m Grace?"}
        EX3 -- Yes --> EX4["Mark COMPLETED -> Zero Extra Charge"]
        EX3 -- No --> EX5["Calculate Overstay Penalty (1.5x Hourly Rate in 30m blocks)"]
        EX5 --> EX6["Log Unbilled Overstay Invoice -> Mark COMPLETED"]
        EX4 --> EX7["Bay Enters 15-Minute Turnover Buffer"]
        EX6 --> EX7
    end
```

---

## 7. Arrival Failure and Recovery — GPRP Protocol

Structured, automated failover protocol when a bay is physically obstructed.

```mermaid
flowchart TD
    FAIL["Driver Arrives: Reserved Bay Obstructed / Gate Inaccessible"] --> REPORT["Guard or Driver Taps 'Report Space Blocked'"]
    REPORT --> INCIDENT["Create Incident Record in DB"]
    INCIDENT --> LOCK_ORIGINAL["MSAI Engine Marks Original Bay: BLOCKED"]
    
    INCIDENT --> SEARCH_ALT["GPRP Spatial Search Algorithm"]
    SEARCH_ALT --> FILTER["Query Active Inventory within 500m Walking Radius"]
    FILTER --> CHK_COMPAT["Filter: Approved Authorization + Compatible Vehicle + Available Now"]
    
    CHK_COMPAT --> ALT_FOUND{"Eligible Alternative Found?"}
    
    ALT_FOUND -- Yes --> PRESENT_OFFER["Present Alternative Offer on Driver App (SCR-108)"]
    PRESENT_OFFER --> DETAILS["Show: Property Name, Photo, Walking Distance (e.g., 180m), Map"]
    
    DETAILS --> DRIVER_DECISION{"Driver Decision"}
    
    DRIVER_DECISION -- "Accepts Alternative" --> ATOMIC_TRANSFER["Execute Atomic DB Transfer to New Bay"]
    ATOMIC_TRANSFER --> CHECK_PRICE{"Alternative More Expensive?"}
    CHECK_PRICE -- Yes --> SUBSIDY["Platform Subsidizes Difference up to ₹100 (Proposed Policy)"]
    CHECK_PRICE -- No --> NO_EXTRA["No Extra Charge"]
    SUBSIDY --> MINT_NEW_PASS["Burn Old Token -> Mint New Access QR Token"]
    NO_EXTRA --> MINT_NEW_PASS
    MINT_NEW_PASS --> NOTIFY_NEW_GUARD["Push Alert to New Property Guard: Incoming Recovery Arrival"]
    NOTIFY_NEW_GUARD --> MAP_NAV["Driver App Launches Navigation to Alternative Space"]
    
    DRIVER_DECISION -- "Declines Alternative" --> TRIGGER_REFUND["Initiate 100% Full Refund via Razorpay Refund API"]
    ALT_FOUND -- "No Alternative within 500m" --> TRIGGER_REFUND
    
    TRIGGER_REFUND --> APOLOGY["Post Reversal Ledger -> Send ₹100 Apology Credit Voucher"]
    APOLOGY --> PENALIZE_HOST["Log Fault Event on Offending Property Owner Ledger"]
```

---

## 8. Refund Workflow (Authoritative Tiers)

Authoritative cancellation refund policy tiers and automated gateway execution.

```mermaid
flowchart TD
    subgraph Triggers["Refund Triggers"]
        T1["Driver Self-Cancellation"]
        T2["GPRP Alternative Unavailable or Declined"]
        T3["Late Payment Received After Hold Expiry (LPRP)"]
        T4["Owner Emergency Cancellation"]
        T5["Operations Dispute Override"]
    end

    T1 --> EVAL
    T2 --> EVAL
    T3 --> EVAL
    T4 --> EVAL
    T5 --> EVAL

    EVAL["Evaluate Refund Eligibility & Tiers"] --> TYPE{"Trigger Type"}

    TYPE -- "Driver Self-Cancellation" --> TIERS["Authoritative Policy Tiers"]
    
    subgraph CancellationTiers["Cancellation Policy Tiers"]
        TIERS --> C1{"> 2 Hours Before Arrival Time?"}
        C1 -- Yes --> R100["100% Parking Fee Refund (Net of Gateway Fee)"]
        C1 -- No --> C2{"1 to 2 Hours Before Arrival?"}
        C2 -- Yes --> R50["50% Parking Fee Refund"]
        C2 -- No --> C3{"< 1 Hour Before Arrival?"}
        C3 -- Yes --> R0["0% Refund (Host Retains 100% Payout)"]
    end

    TYPE -- "GPRP / Host Cancel / LPRP" --> FULL["100% Full Immediate Refund (Including Fees & Taxes)"]

    R100 --> DISPATCH["Call Razorpay Refund API: client.payment.refund"]
    R50 --> DISPATCH
    FULL --> DISPATCH
    R0 --> NO_ACTION["Notify Driver: Non-Refundable Window -> No Funds Dispatched"]

    DISPATCH --> TRACK["Record Refund Record: Status = INITIATED"]
    TRACK --> WH_WAIT["Wait for Gateway Webhook: refund.processed"]
    WH_WAIT --> WH_RECV{"Webhook Received?"}
    
    WH_RECV -- Yes --> POST_LEDGER["Post Reversal Entries to Double-Entry Ledger"]
    POST_LEDGER --> NOTIFY_D["Push Notification to Driver: ₹[Amount] Credited. UTR: [ARN]"]
    
    WH_RECV -- Failed --> RETRY_Q["Queue in Dead-Letter Queue -> Exponential Retry (Max 3)"]
    RETRY_Q --> DISPATCH
```

---

## 9. Owner Payout Workflow (Route & Batch IMPS Fallback)

Illustrates the two-phased marketplace payout model resolving the ₹40L turnover barrier.

```mermaid
flowchart TD
    A["Weekly Settlement Schedule: Tuesdays 02:00 IST"] --> B["Query Un-disbursed Ledger Entries where Account = 'OWNER_PAYABLE'"]
    B --> C["Filter Completed Sessions with Status = 'COMPLETED'"]
    C --> D["Group by Space Owner -> Aggregate Net Payable (Paise)"]
    
    D --> E{"Cumulative Net Payable >= ₹500 Minimum Threshold?"}
    E -- No --> F["Roll Over Balance to Next Weekly Settlement Cycle"]
    
    E -- Yes --> G{"Check Verified Bank Account"}
    G --> H{"Penny-Drop Verification Completed?"}
    H -- No --> I["Alert Owner: 'Add & Verify Bank Account to Receive Payout' -> Hold"]
    
    H -- Yes --> J{"Marketplace Scale Phase"}
    
    subgraph PayoutExecution["Two-Phased Execution Architecture"]
        J -- "Phase 1: Day 1 Launch (Turnover < ₹40L)" --> K1["Direct Bank Transfer Engine (RazorpayX / Cashfree Payouts)"]
        K1 --> K2["Execute IMPS Batch API with Idempotency Key"]
        
        J -- "Phase 2: Scale Phase (Turnover > ₹40L)" --> L1["Razorpay Route Transfers API"]
        L1 --> L2["Execute Programmatic Split to Linked Account ID"]
    end

    K2 --> M{"Transfer Webhook Status"}
    L2 --> M
    
    M -- "transfer.processed / payout.processed" --> N["Post Balanced Settlement Journal Entry in Ledger"]
    N --> O["Record UTR Number & Disbursed Timestamp in owner_payouts"]
    O --> P["Push Notification to Owner: '₹[Amount] credited to account ending in [Last 4]'"]

    M -- "transfer.failed" --> Q["Flag Owner Bank Account: PAYOUT_FAILED_INVALID_DETAILS"]
    Q --> R["Alert Owner to Update Bank Details -> Balance Retained in Ledger"]
```

---

## 10. High-Level Modular Monolith Architecture

The complete system topology, network boundaries, and database storage architecture.

```mermaid
flowchart TD
    subgraph ClientDevices["Mobile Client Layer (Flutter Android & iOS)"]
        DRV["Driver Mobile Viewport (SCR-100s)"]
        OWN["Owner Mobile Viewport (SCR-200s)"]
        GRD["Guard Mobile Viewport (SCR-301..304)"]
        OPS["Restricted Operations View (SCR-400s)"]
    end

    subgraph SecurityPerimeter["Cloud Security Perimeter (AWS Mumbai ap-south-1)"]
        WAF["AWS WAF & CloudFront CDN (DDoS Shield & Geo-Restriction)"]
        ALB["Application Load Balancer (HTTPS / TLS 1.3)"]
    end

    subgraph MonolithBackend["FastAPI In-Process Modular Monolith (ECS Fargate)"]
        AUTH_MOD["Auth & Users Module (Firebase Admin Token Verifier)"]
        PROP_MOD["Properties & Bays Module (CRUD & S3 Media Links)"]
        AVAIL_MOD["MSAI Availability Engine (Spatial PostGIS Queries)"]
        BOOK_MOD["Unified Booking Engine (480s Holds & GiST Exclusions)"]
        PAY_MOD["Payment & Ledger Engine (Razorpay HMAC Webhooks & Double-Entry)"]
        ACC_MOD["Access Management Module (Opaque Tokens & Guard Scan Verifier)"]
        REC_MOD["GPRP Recovery Module (500m Failover & Auto-Refunds)"]
    end

    subgraph DataStorage["Authoritative Storage Tier (VPC Private Subnet)"]
        PG[("PostgreSQL 15+ Primary DB<br/>- PostGIS Spatial Extension<br/>- btree_gist Concurrency Lock<br/>- Append-Only double-entry ledger")]
        RD[("Redis 7.0+ Cluster<br/>- Idempotency Keys (24h TTL)<br/>- 480s Hold Presentations<br/>- Token Bucket Rate Limiters")]
        S3[("Encrypted AWS S3 Bucket<br/>- Property Authorization Deeds<br/>- Bay Photos (CloudFront CDN)")]
    end

    subgraph ExternalSaaS["Third-Party Managed Services"]
        FB_AUTH["Firebase Auth (Telecom SMS OTP Gateway)"]
        RZP["Razorpay / Cashfree (UPI Gateway & Payout Rails)"]
        FCM["Firebase Cloud Messaging (APNs & FCM Push)"]
    end

    ClientDevices -- "HTTPS API Requests" --> WAF
    WAF --> ALB
    ALB --> MonolithBackend

    ClientDevices -- "Phone OTP Request" --> FB_AUTH

    MonolithBackend --> DataStorage
    MonolithBackend -- "Webhook Verification & Orders" --> RZP
    MonolithBackend -- "Transactional Push Alerts" --> FCM
    MonolithBackend -- "Verify Phone JWT" --> FB_AUTH
```
