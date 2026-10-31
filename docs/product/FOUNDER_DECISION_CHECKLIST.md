# Gadispot — Founder Decision & Executive Signoff Checklist (V2.3.1)

> **Document Version:** 2.3.1  
> **Last Updated:** October 31, 2026  
> **Target Milestone:** Implementation Freeze Signoff  
> **Audience:** Founders, Executive Leadership, Legal Counsel, Technical Leads  

---

## 1. Executive Summary & Purpose

This document provides a consolidated executive signoff checklist for Gadispot (formerly SmartPark Exchange). It isolates commercial policies, business risk tolerances, and external contractual dependencies from technical defaults so founders and legal counsel can review and sign off on key operational parameters before application code deployment.

The architecture and engineering specifications are complete to V2.3.1 standards. Implementation of commercial workflows proceeds under the proposed defaults documented herein until formal founder signature.

---

## 2. Foundational Founder Decisions (Already Established in Baseline)

The founding team has reviewed and confirmed the following 5 core architectural and operational baselines:

| Decision Ref | Operational Question | Baseline Decision | Architectural Impact | Status |
|---|---|---|---|---|
| **FD-01** (Q1 / `OQ-PAY-001`) | Payment Gateway Strategy | **Dual Application (Razorpay Primary, Cashfree Secondary)**. Both underwritten simultaneously. | Abstracted behind `PaymentGatewayPort` for runtime hot-swapping. | `FOUNDER_APPROVED` |
| **FD-02** (Q2 / `OQ-OPS-004`) | GPRP Alternative Space Failover | **100% Full Refund to Original Payment Instrument**. If alternative space within 500m cannot be secured or driver declines in 180s, refund full amount. | Transitions reservation to `REFUND_ELIGIBLE` $\to$ canonical 6-stage refund. | `FOUNDER_APPROVED` |
| **FD-03** (Q3 / `OQ-TECH-010`) | Underground / Offline Gate Verification | **Controlled Manual Exception Mode**. Guard matches plate against cached shift schedule, captures timestamped photo proof, syncs when reconnected. | Guard app stores encrypted SQLite queue; photos permanently purged after 7 days. | `FOUNDER_APPROVED` |
| **FD-04** (Q4 / `OQ-BIZ-003`) | Maximum Booking Duration | **Configurable by Property (Default 24 Hours)**. Continuous multi-day and monthly leasing deferred to Phase 2. | `properties.max_booking_hours` enforced at API and database layers. | `FOUNDER_APPROVED` |
| **FD-05** (Q5 / `OQ-PAY-002`) | Marketplace Host Payout Mechanism | **Scheduled Batch Bank Transfers from Corporate Account**. If PA Route onboarding is gated on turnover during pilot, execute batch IMPS via corporate banking API. | Dual-entry ledger accounts remain identical; owner KYC enforced prior to release. | `FOUNDER_APPROVED` |

---

## 3. Commercial & Product Policies Awaiting Formal Founder Signoff

The following operational policies are modeled in the specification as **`PROPOSED (Pending Founder Approval)`**. Founders must confirm or adjust each parameter before commercial pilot launch:

| Policy ID | Policy Description | Proposed Baseline Specification | Rationale & Trade-offs | Founder Action Required | Decision Status |
|---|---|---|---|---|---|
| **POL-CAN-01** | Cancellation Refund Tiers (`OQ-BIZ-004`) | • **>2 Hours before start:** 100% parking fee refunded.<br>• **30m – 2 Hours before start:** 50% parking fee refunded.<br>• **<30m before start / Post-start:** 0% refund (100% forfeited).<br>*Platform convenience fee is non-refundable across all tiers.* | Balances driver flexibility with host schedule certainty. Aligns with major mobility platforms in India. | Sign off on refund percentage thresholds and convenience fee retention. | `PROPOSED` |
| **POL-DUR-01** | Minimum Booking Duration (`OQ-BIZ-002`) | **30 Minutes**. | Accommodates short quick errands (drop-offs, bank visits). 1-hour minimum would increase driver drop-off friction. | Approve 30-minute minimum increment vs 1-hour minimum. | `PROPOSED` |
| **POL-COM-01** | Platform Commission Rate (`OQ-BIZ-001`) | **Flat 15.0%** of gross parking fee for Bengaluru pilot. | Covers payment gateway MDR (2.36%), cloud infrastructure, customer support, and pilot acquisition subsidies. | Approve 15% rate or adjust for pilot launch incentives. | `PROPOSED` |
| **POL-SUB-01** | GPRP Alternative Parking Subsidy Cap (`OQ-BIZ-013`) | **Up to ₹100** absorbed by platform (Account 4020) if alternative bay has higher hourly rate. | Prevents driver price shock when displaced through no fault of their own. Caps platform financial exposure per incident. | Approve ₹100 maximum subsidy per reroute incident. | `PROPOSED` |
| **POL-OST-01** | Overstay Penalty Tariff (`OQ-BIZ-007`) | **1.5× Base Hourly Rate**, billed in 30-minute blocks. | Discourages parking hogging that disrupts subsequent reservations without being punitive enough to trigger chargebacks. | Approve 1.5× multiplier vs flat penalty. | `PROPOSED` |
| **POL-POT-01** | Host Payout Schedule & Minimum Balance (`OQ-BIZ-008`) | **Weekly batch payouts (Tuesdays)** for accumulated balances $\ge ₹500$. | Minimizes bank payout IMPS API charges (₹3–₹5 per transfer) and operational reconciliation overhead. | Approve weekly Tuesday batch and ₹500 payout threshold. | `PROPOSED` |
| **POL-ARR-02** | Driver No-Show Grace Period (`OQ-BIZ-006`) | **Exactly 30 Minutes** past scheduled booking start time before marking `NO_SHOW`. | Accommodates Bengaluru peak traffic delays while freeing up the bay if driver abandons booking. | Approve 30-minute grace window. | `PROPOSED` |

---

## 4. Critical External & Regulatory Dependencies Checklist

The engineering architecture is fully specified to support these workflows; however, live commercial deployment is gated on external approvals:

| Dependency Ref | Subject Area | Required External Deliverable | Responsible Party | Current Status | Hardening Mitigation in Place |
|---|---|---|---|---|---|
| **DEP-LEG-01** | Indirect Taxation (GST) | Written legal/tax memorandum classifying Gadispot under GST Section 9(1) (Marketplace facilitator) vs Section 9(5) (Electronic Commerce Operator). | Indirect Tax Counsel | `BLOCKED (Pending Memo)` | Ledger Account 2030 segregates GST on commission from base parking tariff. Modular tax calculation logic allows immediate switch if 9(5) applies. |
| **DEP-PAY-01** | Payment Aggregator Underwriting | Formal merchant onboarding approval for parking marketplace category and Razorpay Route / Cashfree Split Marketplace account setup. | Payment Aggregator Risk Team | `BLOCKED (Under Review)` | Dual application strategy active. Batch bank transfer fallback from corporate account fully specified and ledger-compatible. |
| **DEP-TEL-01** | Transactional SMS Compliance | TRAI DLT (Distributed Ledger Technology) registration for entity, sender ID (e.g., `GDSPOT`), and SMS OTP templates with Indian telecom operators. | Mobile/Telecom Specialist | `BLOCKED (Filing)` | Firebase Phone Auth handles login OTP verification out of the box; DLT templates required for transactional booking confirmation SMS. |
| **DEP-LEG-02** | Municipal Parking Regulations | Legal clarity on monetizing private residential driveways under Bengaluru BBMP / Karnataka Municipal Corporations Act guidelines. | Municipal Law Counsel | `BLOCKED (Reviewing)` | Pilot geofenced strictly to private residential driveways and gated layouts with verified Society/Landlord NOCs. |
| **DEP-LEG-03** | Platform Bailment & Liability | Finalization of Terms of Service disclaiming bailment, vehicle damage, fire, and theft under Section 79 of Information Technology Act 2000. | Corporate Litigator | `BLOCKED (Drafting)` | In-app mandatory clickwrap terms acceptance on signup and prominent non-bailment disclaimer modal prior to booking checkout. |

---

## 5. Formal Executive Signoff Table

Upon review by the executive leadership, signatures below convert `PROPOSED` defaults to `FOUNDER_APPROVED` authoritative policy:

| Role | Signatory Name | Decision Scope | Signature | Approval Date |
|---|---|---|---|---|
| **Chief Executive Officer / Founder** | _______________________ | Commercial Policies, Commission (15%), Cancellation Tiers, Minimum Duration (30m) | _______________________ | _____ / _____ / 2026 |
| **Chief Technology Officer / Co-Founder** | _______________________ | Architecture V2.3.1 Freeze, Hosting Mumbai `ap-south-1`, Offline Guard Exception | _______________________ | _____ / _____ / 2026 |
| **Head of Legal & Compliance** | _______________________ | GST 9(1) vs 9(5) Memo, IT Act Sec 79 Non-Bailment Terms, DPDPA 2023 Consent | _______________________ | _____ / _____ / 2026 |
| **Head of Finance & Operations** | _______________________ | Weekly Batch Payouts (₹500 threshold), GPRP Subsidy Cap (₹100), Bank KYC | _______________________ | _____ / _____ / 2026 |
