# Gadispot (formerly SmartPark Exchange) — Unresolved Decisions & Open Questions Decision Register (V2.3)

> **Document Version:** 2.3.0  
> **Last Updated:** October 31, 2026  
> **Status:** Active Authoritative Decision Register (V2.3 Baselined)  
> **Audience:** Founders, Executive Leadership, Legal Counsel, Product Managers, Lead Architects  

---

## 1. Summary of Open Decisions by Domain

| Category Code | Domain | Total Questions | Decided / Resolved | External Dependency | Legal Pending | Proposed Default |
|---|---|---|---|---|---|---|
| **OQ-BIZ** | Business Model & Operational Policies | 16 | 5 | 0 | 0 | 11 |
| **OQ-LEG** | Legal & Indian Regulatory Compliance | 12 | 0 | 5 | 5 | 2 |
| **OQ-PAY** | Payment Aggregator & Marketplace Onboarding | 8 | 1 | 5 | 0 | 2 |
| **OQ-PRD** | Product Design & User Experience Rules | 12 | 3 | 0 | 0 | 9 |
| **OQ-TECH** | Engineering Architecture & Infrastructure | 10 | 4 | 2 | 0 | 4 |
| **OQ-OPS** | Field Operations, Guard Management & Support | 7 | 2 | 0 | 0 | 5 |
| **TOTAL** | | **65** | **15** | **12** | **5** | **33** |

---

## 2. Key Founder Decisions Recorded (V2.2 Baselines)

The founding team has established explicit policy decisions on the five primary product and operational choices:

1. **Payment Provider Strategy (Q1 / OQ-PAY-001):** **Dual Application (Razorpay Primary, Cashfree Secondary)**. Both applications are submitted simultaneously; final primary routing depends on written underwriting terms and Route account approval.
2. **Alternative Parking Failure (Q2 / OQ-OPS-004):** **100% Full Refund to Original Instrument**. If a GPRP alternative space cannot be secured atomically within 500m or is declined by the driver within 180s, the system automatically transitions the reservation to `REFUND_PENDING`.
3. **Offline Guard Verification (Q3 / OQ-TECH-010):** **Controlled Manual Exception Mode**. Offline entry in cellular dead zones requires physical plate matching against the cached shift schedule, mandatory photo proof, and asynchronous sync. Photos are permanently deleted 7 days post-reconciliation.
4. **Maximum Booking Duration (Q4 / OQ-BIZ-003):** **Configurable by Property (Default 24 Hours)**. Continuous multi-day or monthly leasing is deferred to Phase 2.
5. **MVP Marketplace Payout Approach (Q5 / OQ-PAY-002):** **Scheduled Batch Bank Transfers from Corporate Account**. If formal PA Route approval is gated on turnover thresholds during the pilot, owner settlements operate via scheduled batch IMPS transfers under corporate bank agreement, strict owner KYC (PAN + Penny Drop), and MoR liability.

---

## 3. Business Model Decisions (`OQ-BIZ-001` to `016`)

| ID | Decision Question | Criticality | Options Considered | Status & Approved / Proposed Value | Decision Owner | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-BIZ-001** | Platform commission percentage. | P0 | Flat 10%, Flat 15%, Flat 20%, Tiered | **DECIDED:** Flat 15.0% commission on base parking fee for Bengaluru pilot. | Founder / Business Lead | Signed | Base commission factor hardcoded in pricing engine. |
| **OQ-BIZ-002** | Global minimum booking duration. | P0 | 30 min, 1 hr, 2 hr | **DECIDED:** 30 Minutes (`POL-DUR-01`). | Product Manager | Signed | API check enforces minimum 30-min window. |
| **OQ-BIZ-003** | Maximum continuous booking duration. | P0 | 12 hr, 24 hr, Configurable | **DECIDED:** Configurable by property (default 24h) (`POL-DUR-02`). | Founder Decision Q4 | Signed | `properties.max_booking_hours` column added to DDL. |
| **OQ-BIZ-004** | Tiered cancellation policy. | P0 | Free up to 1h, Tiered, Non-refundable | **DECIDED:** Tiered (>2h: 100%, 30m-2h: 50%, <30m: 0%) (`POL-CAN-01..03`). | Founder / PM | Signed | Cancellation evaluation rules in `BookingService`. |
| **OQ-BIZ-005** | Gateway fee absorption on cancellation. | P1 | Platform absorbs, Deducted from driver, Charged to owner | **PROPOSED DEFAULT:** Platform absorbs gateway MDR on >2h cancellations as CAC. | Finance Lead | Sprint 1 | Cancellation reversal ledger journal template `JRN-CAN-100`. |
| **OQ-BIZ-006** | Arrival grace period before NO-SHOW. | P0 | 15 min, 30 min, 60 min | **DECIDED:** Exactly 30 Minutes past start (`POL-ARR-02`). | Operations Lead | Signed | Automated worker marks `NO_SHOW` at $t_{\text{start}} + 30\text{m}$. |
| **OQ-BIZ-007** | Overstay penalty structure. | P0 | Standard hourly, 1.5x Hourly, Flat ₹200 + rate | **DECIDED:** 1.5× Base Hourly Rate in 30-min blocks (`POL-OST-01`). | Founder / PM | Signed | Exit scan calculates overstay invoice `JRN-OST`. |
| **OQ-BIZ-008** | Owner payout frequency and threshold. | P1 | Daily T+1, Weekly batch, Bi-weekly | **PROPOSED DEFAULT:** Weekly batch (Tuesdays) for balances $\ge ₹500$ (`POL-POT-01`). | Finance Lead | Sprint 2 | Batch Celery/ARQ payout worker reading Account 2010. |
| **OQ-BIZ-009** | Customer dispute SLA. | P1 | 2 hr, 24 hr, 48 hr | **PROPOSED DEFAULT:** 24-Hour Resolution SLA with immediate in-app tracking. | Support Lead | Sprint 3 | Support ticket ticketing API and webhook notification. |
| **OQ-BIZ-010** | Field verification and signage costs. | P1 | Platform subsidizes, Owner pays, Split | **PROPOSED DEFAULT:** Platform subsidizes initial 200 pilot spaces. | Marketing Lead | Sprint 2 | Zero payment gate for pilot owner listing setup. |
| **OQ-BIZ-011** | Customer support channels in MVP. | P1 | Email only, In-app chat + SOS, Call center | **PROPOSED DEFAULT:** In-app priority chat + Emergency SOS phone button. | Operations Lead | Sprint 3 | Mobile screen `SCR-105` emergency button launches dialer. |
| **OQ-BIZ-012** | Discovery search radius. | P0 | 1 km, 3 km default (up to 5 km), 10 km | **DECIDED:** 3 km default, expandable to 5 km max (`POL-RAD-01`). | Product Manager | Signed | PostGIS query defaults to 3,000m, capped at 5,000m. |
| **OQ-BIZ-013** | GPRP alternative space price differential. | P1 | Driver pays, Platform subsidizes diff up to ₹100 | **PROPOSED DEFAULT:** Platform subsidizes up to ₹100 via Account 4020. | Finance Lead | Sprint 2 | Journal template `JRN-SUB` absorbs tariff gap. |
| **OQ-BIZ-014** | Host penalty for false availability. | P1 | None, ₹100 fine + suspension | **PROPOSED DEFAULT:** ₹100 fine deducted from next payout; 3 faults suspend. | Operations Lead | Sprint 2 | Incident review module in ops dashboard. |
| **OQ-BIZ-015** | Commercial vs residential commission. | P1 | Uniform 15%, Tiered commercial | **PROPOSED DEFAULT:** Uniform 15.0% for MVP pilot. | Business Lead | Sprint 2 | Single commission calculation logic. |
| **OQ-BIZ-016** | Parking fee block increments. | P1 | Exact minute, 30-min blocks, 1-hr blocks | **PROPOSED DEFAULT:** 30-Minute Blocks (minimum 30 min duration). | Finance Lead | Sprint 1 | Tariff rounding engine rounds up to 30m blocks. |

---

## 4. Legal & Regulatory Decisions (`OQ-LEG-001` to `012`)

| ID | Legal Question | Criticality | Statutory Context & Evidence Required | Interim Posture / Status | Review Authority | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-LEG-001** | GST Section 9(5) E-Commerce Operator classification. | P0 | If classified under Sec 9(5), SmartPark pays GST on parking service directly. | **LEGAL PENDING:** Model under Section 9(1) marketplace facilitation. Written tax memo required. | Indirect Tax Partner | Pre-Launch | Ledger segregates GST on commission (2030) from base. |
| **OQ-LEG-002** | Direct bank transfers vs RBI PA Guidelines. | P0 | Payouts from corporate current account without PA escrow require compliance review. | **EXTERNAL DEPENDENCY:** Dual apply for PA Route. Execute batch transfers under bank advice. | Banking Legal Counsel| Pre-Launch | Ledger uses identical schema regardless of rail. |
| **OQ-LEG-003** | DPDPA 2023 compliance scope. | P0 | Consent notices, data principal rights, retention schedules. | **LEGAL PENDING:** Implement bilingual consent, masked phone numbers, 7-day photo purge. | Privacy Counsel | Pre-Launch | S3 automated expiration lifecycle on gate photos. |
| **OQ-LEG-004** | Title verification for residential parking. | P0 | Preventing unauthorized monetization of common areas. | **PROPOSED DEFAULT:** Require property tax receipt or registered sale deed + society NOC. | Real Estate Counsel | Sprint 1 | Document uploader requires tax receipt / deed. |
| **OQ-LEG-005** | Tenant subletting restrictions. | P0 | Standard tenancy agreements forbid commercial subleasing. | **PROPOSED DEFAULT:** Prohibit tenant listings without written landlord counter-signature. | Real Estate Counsel | Sprint 1 | Onboarding checkbox: "I am registered property owner". |
| **OQ-LEG-006** | Cooperative Housing Society (CHS/AOA) bye-laws. | P0 | Supreme Court precedents (*Nahalchand*) on common area parking rights. | **PROPOSED DEFAULT:** Pilot restricted to independent driveways and societies with formal NOC. | Urban Law Counsel | Sprint 1 | Society verification workflow in ops review queue. |
| **OQ-LEG-007** | Platform liability for vehicle damage, fire, or theft. | P0 | Shielding platform from bailment claims. | **EXTERNAL DEPENDENCY:** Draft robust Terms of Service disclaiming bailment under IT Act Sec 79. | Corporate Litigator | Pre-Launch | In-app booking confirmation disclaimer modal. |
| **OQ-LEG-008** | Consumer Protection (E-Commerce) Rules 2020. | P1 | Resident Grievance Officer, disclosure of origin, refund matrix. | **PROPOSED DEFAULT:** Appoint Resident Grievance Officer; publish details in app settings. | Consumer Law Counsel | Sprint 2 | In-app legal disclosure screen with grievance email. |
| **OQ-LEG-009** | Municipal parking trade license requirements (BBMP). | P1 | Private driveway monetization legality in Bengaluru. | **EXTERNAL DEPENDENCY:** Commission municipal legal memorandum on private vehicle parking. | Municipal Law Partner| Pre-Launch | Whitelist pilot PIN codes based on municipal review. |
| **OQ-LEG-010** | Owner KYC under PMLA regulations. | P0 | Preventing money laundering through fake parking payouts. | **EXTERNAL DEPENDENCY:** Mandatory PAN card validation + Penny Drop bank verification. | Compliance Officer | Sprint 2 | Payouts blocked if `pan_verified = FALSE`. |
| **OQ-LEG-011** | Zoning regulations: Residential vs Commercial vehicles. | P1 | Residential zones restrict commercial vehicle staging. | **PROPOSED DEFAULT:** MVP restricted strictly to White-Plate Private Vehicles. | Urban Planning Counsel | Sprint 1 | Vehicle registration plate input regex validation. |
| **OQ-LEG-012** | Law enforcement data disclosure (Sec 91 CrPC). | P2 | Responding to police investigation notices for vehicle logs. | **DEFERRED TO P2:** Internal compliance workflow requiring signed judicial notice. | Criminal Law Advisor | Phase 2 | Manual database query tool for ops compliance lead. |

---

## 5. Payment Provider Decisions (`OQ-PAY-001` to `008`)

| ID | Decision Question | Criticality | Dependencies & Evidence Required | Interim Posture / Status | Review Authority | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-PAY-001** | Razorpay / Cashfree marketplace model approval under risk policy. | P0 | Underwriting approval for parking marketplace category. | **EXTERNAL DEPENDENCY:** Dual application submitted simultaneously. | Payment Specialist | Pre-Launch | `PaymentGatewayPort` supports runtime provider switch. |
| **OQ-PAY-002** | Razorpay Route ₹40L turnover requirement & fallback viability. | P0 | Written confirmation of onboarding threshold and Route eligibility. | **DECIDED:** Launch pilot with batch transfers from corporate current account under bank agreement. | Finance Lead | Signed | Batch IMPS payout worker reading Account 2010. |
| **OQ-PAY-003** | Introductory MDR rates (0% or discounted). | P1 | Promotional credit program confirmation. | **PROPOSED DEFAULT:** Model unit economics at standard 2.0% + GST (2.36% net). | Finance Lead | Sprint 1 | Ledger Account 4010 accrues 2.36% on gross inflow. |
| **OQ-PAY-004** | Contractual settlement turnaround time (T+1 vs T+2). | P1 | Gateway cashflow cycle. | **PROPOSED DEFAULT:** Accept standard T+2 settlement to avoid premium instant fees. | Finance Lead | Sprint 1 | Account 1010 clears to 1020 on T+2 schedule. |
| **OQ-PAY-005** | Owner KYC requirements for linked accounts / direct payouts. | P0 | Provider-specific linked account KYC documentation list. | **EXTERNAL DEPENDENCY:** Enforce PAN + Verified Bank Account (Penny Drop API). | Payment Specialist | Pre-Launch | Penny Drop API integration before owner payout. |
| **OQ-PAY-006** | Contingency plan for gateway outage or webhook latency. | P1 | Gateway redundancy. | **PROPOSED DEFAULT:** Single primary gateway with manual failover script for MVP. | Backend Architect | Sprint 2 | Client polling endpoint `/payments/verify-status`. |
| **OQ-PAY-007** | NPCI UPI transaction limits for dynamic QR. | P1 | Bank merchant category limits. | **PROPOSED DEFAULT:** Verified SmartPark values (₹30–₹500) fall well below limits. | Finance Lead | Verified | Zero custom limit handling needed for MVP. |
| **OQ-PAY-008** | International cards and NRI visitor transactions. | P2 | High chargeback risk and 3% MDR. | **PROPOSED DEFAULT:** Disabled for MVP. Domestic Indian UPI and cards only. | Product Manager | Sprint 1 | Payment gateway checkout config sets `currency: "INR"`. |

---

## 6. Product Design & UX Decisions (`OQ-PRD-001` to `012`)

| ID | Decision Question | Criticality | Options Considered | Status & Approved / Proposed Value | Decision Owner | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-PRD-001** | Dual role (Driver/Owner) in single app. | P0 | Separate apps vs Role switcher | **DECIDED:** Single Flutter app with Role Switcher (`SCR-002`). | Mobile Architect | Signed | Dynamic shell switching based on active role JWT. |
| **OQ-PRD-002** | Guard account provisioning. | P0 | Self-registration vs Owner invite | **PROPOSED DEFAULT:** Property Owner invites Guard via mobile number. | Backend Architect | Sprint 2 | `guard_assignments` table links guard user to property. |
| **OQ-PRD-003** | Number of session extensions allowed. | P1 | Unlimited, Max 2, None | **PROPOSED DEFAULT:** Maximum 2 extensions, subject to slot availability. | Product Manager | Sprint 2 | Extension API enforces `extension_count < 2`. |
| **OQ-PRD-004** | User reviews and ratings moderation. | P1 | Auto-publish vs Manual review | **PROPOSED DEFAULT:** Automated profanity filter + report flag queue. | Product Manager | Sprint 3 | Text moderation filter on review submission. |
| **OQ-PRD-005** | Space photo upload requirements. | P0 | 1 photo, 3 mandatory photos | **PROPOSED DEFAULT:** Exactly 3 mandatory photos (Entrance, Bay, Approach). | UX Lead | Sprint 1 | Form validator requires 3 photo uploads before save. |
| **OQ-PRD-006** | Push notification channel toggles. | P1 | All toggleable vs Transactional locked | **PROPOSED DEFAULT:** Transactional notifications non-disableable. | Product Manager | Sprint 2 | Notification preferences UI excludes transactional types. |
| **OQ-PRD-007** | Checkout hold lifespan. | P0 | 3 min, 5 min, 8 min (480s) | **DECIDED:** Strictly 480 Seconds (8 Minutes) (`POL-HLD-01`). | Lead Architect | Signed | PostgreSQL `hold_expires_at = now() + 480s`. |
| **OQ-PRD-008** | Max concurrent bookings per driver. | P1 | Unlimited, Max 2 concurrent | **PROPOSED DEFAULT:** Maximum 2 active concurrent bookings. | Product Manager | Sprint 2 | Hold creation queries active bookings count. |
| **OQ-PRD-009** | Max spaces for residential profile. | P1 | Unlimited, Max 4 spaces | **PROPOSED DEFAULT:** Maximum 4 spaces; >4 triggers commercial KYC. | Operations Lead | Sprint 1 | Owner space creation validates count $\le 4$. |
| **OQ-PRD-010** | Re-entry during single booking session. | P0 | Allowed vs Single entry/exit | **DECIDED:** Single Entry, Single Exit for MVP. | Lead Architect | Signed | Entry token burned on check-in; exit token closes session. |
| **OQ-PRD-011** | Advance booking window. | P1 | Max 24h, Max 7 days, Max 30 days | **DECIDED:** Maximum 7 Days in advance (`POL-DUR-03`). | Product Manager | Signed | Search and hold endpoints reject start > now + 7 days. |
| **OQ-PRD-012** | Ops portal without public web app. | P0 | Web dashboard vs Restricted mobile | **DECIDED:** Restricted Mobile Ops View (`SCR-401/402`) in Flutter app. | Lead Architect | Signed | Ops role shell compiled inside Flutter binary. |

---

## 7. Technical & Infrastructure Decisions (`OQ-TECH-001` to `010`)

| ID | Technical Question | Criticality | Options Considered | Status & Approved / Proposed Value | Technical Lead | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-TECH-001** | Firebase Phone Auth pricing vs MAU. | P0 | 10k free tier; ~$0.015/verification | **PROPOSED DEFAULT:** Budgeted for MVP; MSG91/Twilio evaluated for fallback. | Backend Architect | Signed | Budgeted ₹1.12L/mo at 100k MAU. |
| **OQ-TECH-002** | Transactional SMS DLT registration. | P1 | TRAI DLT registration required | **EXTERNAL DEPENDENCY:** DLT entity & template filing with telecom operators. | Mobile Architect | Pre-Launch | Sender ID headers whitelist approved in Indian telcos. |
| **OQ-TECH-003** | Mobile mapping SDK. | P0 | Google Maps vs Mapbox vs flutter_map | **PROPOSED DEFAULT:** `google_maps_flutter` with marker clustering. | Mobile Architect | Sprint 1 | Integrated into Driver Explore Map `SCR-101`. |
| **OQ-TECH-004** | Cloud hosting datacenter region. | P0 | AWS Mumbai (`ap-south-1`) vs GCP | **DECIDED:** AWS Mumbai (`ap-south-1`) for sub-40ms latency and reliability. | Backend Architect | Signed | Infrastructure provisioned via Terraform in Mumbai. |
| **OQ-TECH-005** | Background task execution engine. | P0 | FastAPI BackgroundTasks vs ARQ/Celery | **DECIDED:** ARQ (Async Redis Queue) + Celery for scheduled tasks. | Backend Architect | Signed | ARQ workers handle hold expiry and push notifications. |
| **OQ-TECH-006** | Mobile crash reporting framework. | P1 | Sentry vs Firebase Crashlytics | **PROPOSED DEFAULT:** Firebase Crashlytics configured in Flutter. | Mobile Architect | Sprint 1 | Crashlytics SDK initialized in `main.dart`. |
| **OQ-TECH-007** | Database migration pipeline. | P0 | Alembic committed to git | **DECIDED:** Alembic migration scripts run via CI/CD pre-start hook. | Database Architect | Signed | Version-controlled DDL migrations in `/alembic`. |
| **OQ-TECH-008** | Storage for verification documents. | P0 | Public vs Private S3 buckets | **DECIDED:** Private S3 bucket with 15-minute presigned URLs for ops. | Lead Architect | Signed | Document uploader generates private S3 keys. |
| **OQ-TECH-009** | Camera lifecycle on low-end Android. | P1 | Continuous stream vs Auto-pause | **PROPOSED DEFAULT:** Camera hardware pauses when screen unfocused. | Mobile Architect | Sprint 2 | `mobile_scanner` lifecycle binding in `SCR-301`. |
| **OQ-TECH-010** | Offline basement gate verification. | P0 | Cryptographic burn vs Controlled manual | **DECIDED:** Controlled Manual Exception Mode per Founder Decision Q3. | Lead Architect | Signed | Encrypted SQLite queue with 7-day photo purge rule. |

---

## 8. Field Operations Decisions (`OQ-OPS-001` to `007`)

| ID | Operational Question | Criticality | Options Considered | Status & Approved / Proposed Value | Operations Lead | Target Date | Engineering Impact |
|---|---|---|---|---|---|---|---|
| **OQ-OPS-001** | Listing document audit process. | P0 | Human ops review vs AI OCR | **PROPOSED DEFAULT:** Pure human operations review for MVP pilot (<50 listings/wk). | Head of Operations | Sprint 1 | Ops queue screen `SCR-401` with document preview. |
| **OQ-OPS-002** | Property listing review SLA. | P1 | 4 hr, 24 hr, 48 hr | **PROPOSED DEFAULT:** 24-Hour Review SLA with automated push notification. | Operations Lead | Sprint 1 | SLA breach alerts sent to ops Slack channel. |
| **OQ-OPS-003** | Guard onboarding & training. | P0 | Video only vs In-person training | **PROPOSED DEFAULT:** In-person 20-min training + laminated reference card. | Field Ops Lead | Sprint 3 | Physical setup checklist completed before activation. |
| **OQ-OPS-004** | GPRP alternative space failover. | P0 | Manual reallocation vs Atomic 8-step | **DECIDED:** Atomic 8-Step Workflow per Founder Decision Q2 (100% refund if failed). | Product Manager | Signed | GPRP engine transitions reservation and posts journals. |
| **OQ-OPS-005** | Physical signage at partner properties. | P1 | Digital only vs Metal signboard | **PROPOSED DEFAULT:** Reflective all-weather entrance signboard with Property ID. | Field Ops Lead | Sprint 2 | Signboard installed during property field verification. |
| **OQ-OPS-006** | Initial pilot micro-market. | P0 | Bengaluru vs Mumbai vs Delhi-NCR | **DECIDED:** Bengaluru (Koramangala / Indiranagar / HSR Layout). | Founders | Signed | Initial property onboarding restricted to pilot bounds. |
| **OQ-OPS-007** | Owner fake booking collusion defense. | P1 | Device fingerprinting, Payment BIN | **PROPOSED DEFAULT:** Block bookings sharing device, UPI VPA, or bank with owner. | Fraud Lead | Sprint 2 | Anti-collusion validation on `POST /bookings/hold`. |
