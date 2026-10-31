# Gadispot — V2.3.1 Residual Risk Register & Operational Contingency Plan

> **Document Version:** 2.3.1  
> **Release Date:** October 31, 2026  
> **Scope:** Repository-Wide Operational, Technical, Legal, and Financial Residual Risks  
> **Audience:** Executive Leadership, Risk & Compliance, Lead Architects, Operations Directors  

---

## 1. Executive Summary

This register details all identified residual risks following the **PRD V2.3.1 — Engineering Readiness Hardening** milestone. While the technical specification, database consistency, and financial accounting models have achieved complete internal rigor, real-world deployment incurs inherent external, operational, and regulatory dependencies that software code alone cannot eliminate.

Each residual risk is assigned an owner, an architectural or operational safeguard specified within V2.3.1, and an explicit runtime contingency protocol.

---

## 2. Residual Risk Severity & Likelihood Matrix

| Risk ID | Risk Domain | Description & Failure Mode | Pre-Mitigation Rating | V2.3.1 Architectural & Operational Safeguard | Post-Mitigation Residual Impact | Action Owner |
|---|---|---|---|---|---|---|
| **RR-REG-01** | Regulatory (Tax) | Tax authorities reclassify Gadispot under GST Section 9(5) as an ECO rather than a Section 9(1) facilitator, creating retroactive tax exposure on gross parking tariffs. | **HIGH / MEDIUM** | Ledger Account 2030 segregates GST on commission from base parking tariff. Tax calculation logic is fully isolated within `PricingEnginePort`, enabling overnight configuration change if reclassified. Legal tax memo (`DEP-LEG-01`) is a mandatory launch gate. | **LOW / MEDIUM** | Indirect Tax Counsel & Finance Lead |
| **RR-REG-02** | Regulatory (DPDPA) | Guard photo uploads during offline exceptions lead to unauthorized image retention or privacy claims under DPDPA 2023. | **HIGH / LOW** | Encrypted SQLite storage on guard device; AWS S3 automated lifecycle policy deletes all gate audit photos permanently after 7 days (`BASE-SEC-03`). Explicit data minimization (only vehicle license plate and gate captured). | **LOW / LOW** | Data Protection Officer (DPO) |
| **RR-REG-03** | Regulatory (Municipal) | Local civic authority (BBMP) challenges commercial monetization of private residential driveways under zoning or trade licensing rules. | **MEDIUM / MEDIUM** | Pilot geofenced to white-plate private vehicles in verified residential societies with written Society/Landlord NOCs (`OQ-LEG-004..006`). Municipal legal memo (`DEP-LEG-02`) commissioned prior to pilot expansion. | **LOW / LOW** | Municipal Law Counsel |
| **RR-FIN-01** | Payment Rails | Primary Payment Aggregator (Razorpay) delays or rejects Route marketplace onboarding due to parking category risk profile or turnover thresholds. | **HIGH / MEDIUM** | Dual-application architecture (`FD-01`); fallback scheduled batch IMPS payout engine from corporate account (`FD-05`) already fully specified with identical double-entry ledger accounts (`Account 2010`). | **LOW / LOW** | Payment Systems Architect |
| **RR-FIN-02** | Banking Friction | Banking switch latency or customer bank rejections on refunds lead to chargebacks or consumer forum complaints during the 5–7 business day settlement window. | **MEDIUM / HIGH** | Customer UI never advertises "instant refund". Displays authoritative multi-stage progress (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`) with bank UTR/ARN tracking numbers. Ops finance escalation queue for `REFUND_FAILED` events. | **LOW / MEDIUM** | Customer Support Lead & Finance Lead |
| **RR-FIN-03** | Margin Erosion | Frequent GPRP reroutes to higher-priced parking bays deplete platform margin via Account 4020 subsidies. | **MEDIUM / LOW** | GPRP alternative space subsidy is hard-capped at ₹100 per incident (`POL-SUB-01`). Consecutive false-availability hosts face ₹100 penalty deduction and automated listing suspension after 3 infractions (`OQ-BIZ-014`). | **LOW / LOW** | Marketplace Operations Lead |
| **RR-OPS-01** | Field Operations | Driver arrives at reserved bay to find it physically obstructed or occupied by an unauthorized vehicle. | **HIGH / MEDIUM** | Guaranteed Parking Replacement Protocol (GPRP): Automated atomic 8-step engine reallocates driver to an alternative bay within 500m in $\le 180\text{s}$, or dispatches a 100% full refund (`FD-02`) if unfulfillable. | **LOW / LOW** | Field Operations Lead |
| **RR-OPS-02** | Field Operations | Security guard collusion: Guard admits unregistered vehicle or performs unauthorized manual overrides without scanning. | **MEDIUM / LOW** | Every manual admission requires high-resolution photo proof and mandatory supervisor review queue in ops dashboard (`SCR-401`). Space owner receives instant push notification on check-in with vehicle registration plate. | **LOW / LOW** | Head of Operations |
| **RR-OPS-03** | Physical Overstay | Driver overstays booking window, blocking the bay for an incoming confirmed reservation. | **HIGH / MEDIUM** | 1.5× base hourly rate penalty in 30-min increments (`POL-OST-01`). Guard app and backend flag active overstay at $t_{\text{end}} + 15\text{m}$. Incoming driver is rerouted via GPRP before physical arrival if overstay is unresolvable. | **LOW / MEDIUM** | Field Operations Lead |
| **RR-TECH-01** | Telephony (TRAI) | TRAI DLT registration delay prevents transactional SMS delivery for booking confirmations or OTP fallbacks. | **MEDIUM / HIGH** | Primary authentication utilizes Firebase Phone Auth SDK directly; push notifications (FCM / APNs) and in-app dynamic QR act as primary access credentials, eliminating hard SMS dependency. | **LOW / LOW** | Mobile Application Architect |
| **RR-TECH-02** | Mobile Hardware | Low-end guard Android devices (Android 8/9, Go edition) suffer camera overheating or battery drain during continuous scanning. | **MEDIUM / MEDIUM** | `mobile_scanner` lifecycle binding automatically pauses camera feed when screen is unfocused or idle (`OQ-TECH-009`). Flashlight default is off. High-contrast fallback manual 6-character booking code entry. | **LOW / LOW** | Flutter Mobile Architect |
| **RR-TECH-03** | Concurrency Contention | Peak flash-demand booking events (e.g. sporting match or festival near pilot zone) cause database lock contention on hot slots. | **MEDIUM / LOW** | Engine-level GiST exclusion constraints (`23P01`) reject conflicting holds in sub-millisecond database execution without application-level distributed lock latency. Read-heavy search utilizes Redis read-through caching. | **LOW / LOW** | Backend Architect |

---

## 3. Operational Contingency & Incident Escalation Runbook

### 3.1 Severity 1 (S1) — Financial Settlement or Ledger Invariant Breach
- **Trigger:** Unbalanced journal entry detected, negative balance in liability accounts, or payment webhook processing failure $>1\%$.
- **Response:**
  1. Automated PagerDuty alert to Lead Backend Architect and On-Call FinTech Engineer.
  2. Transactional outbox temporarily halts automated payouts; incoming checkout holds continue unaffected.
  3. Database audit trail inspected via `transaction_reference`. Root cause identified and hotfixed within 60 minutes.
  4. Manual reversing journals posted per immutable ledger standard (`fn_prevent_posted_lines_modification`).

### 3.2 Severity 2 (S2) — GPRP Cluster Failure (Localized Physical Disruption)
- **Trigger:** $>3$ concurrent arrival failures reported in a single property or micro-market within 30 minutes.
- **Response:**
  1. Ops dashboard automatically triggers temporary property suspension (`status = 'BLOCKED'`).
  2. Affected drivers immediately issued alternative reservations within 500m or 100% full refunds.
  3. Field operations executive dispatched to physical location for site inspection.
  4. Property owner contacted for incident verification.

---

## 4. Residual Risk Signoff

The architecture team certifies that the above residual risks have been reduced to As Low As Reasonably Practicable (ALARP) through technical, architectural, and operational controls. Residual risks are managed through ongoing monitoring, SLA tracking, and formal executive policies documented in [FOUNDER_DECISION_CHECKLIST.md](../product/FOUNDER_DECISION_CHECKLIST.md).
