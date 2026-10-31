# Gadispot — V2.3.1 Baseline Repository Audit & Source-of-Truth Inventory

> **Document Identifier:** AUD-GSP-2026-V2.3.1-BASE  
> **Audit Date:** October 31, 2026  
> **Auditing Role:** Principal Software Architect & Lead Independent Technical Auditor  
> **Repository Target:** `https://github.com/officialayush5839-arch/Gadispot`  
> **Base Commit Inspected:** `3b62eb2` (`feat(spec): finalize PRD V2.3 specification suite and eliminate architectural defects`)  
> **Milestone Objective:** PRD V2.3.1 — Engineering Readiness Hardening  

---

## 1. Files Inspected

A complete file tree audit was conducted across all 23 files in the repository:

| # | File Path | File Size | Last Modified | Canonical Authority Domain |
|---|---|---|---|---|
| 1 | `PRD.md` | 83,175 B | 2026-10-31 | **Master Source of Truth:** Product requirements, policy tables, user journeys. |
| 2 | `README.md` | 5,019 B | 2026-10-31 | Repository entrypoint, architectural pillars, document directory. |
| 3 | `.gitignore` | 466 B | 2026-10-31 | Version control exclusions. |
| 4 | `.github/workflows/spec-validation.yml` | 2,455 B | 2026-10-31 | CI automated specification integrity pipeline. |
| 5 | `docs/audits/PRD_FINAL_AUDIT.md` | 7,711 B | 2026-10-31 | Historical V2.2 audit review. |
| 6 | `docs/audits/PRD_V2_3_FINAL_AUDIT.md` | 17,386 B | 2026-10-31 | Historical V2.3 audit evaluation. |
| 7 | `docs/audits/PRD_V2_3_CHANGELOG.md` | 13,419 B | 2026-10-31 | Historical V2.3 changes summary. |
| 8 | `docs/audits/TECHNICAL_AUDIT.md` | 11,820 B | 2026-10-31 | Historical V1.0/V2.0 technical deficit audit. |
| 9 | `docs/product/BUSINESS_ASSUMPTIONS.md` | 9,517 B | 2026-10-31 | Commercial model, unit economics, fee structures. |
| 10 | `docs/product/DECISION_LOG.md` | 12,845 B | 2026-10-31 | Architectural Decision Records (ADR-001 through ADR-010). |
| 11 | `docs/product/OPEN_QUESTIONS.md` | 21,310 B | 2026-10-31 | Decision register covering 65 governance items. |
| 12 | `docs/product/OPEN_SOURCE_INTEGRATIONS.md`| 20,245 B | 2026-10-31 | OSS package licenses, provider adapters, TCO. |
| 13 | `docs/product/REQUIREMENTS_TRACEABILITY.md`| 23,022 B | 2026-10-31 | Traceability matrix (70 legacy rows mapped). |
| 14 | `docs/product/SCREEN_REQUIREMENTS.md` | 10,968 B | 2026-10-31 | Flutter screen inventory (`SCR-001..402`), 5 UX states. |
| 15 | `docs/product/SECURITY_AND_PRIVACY_REVIEW.md`| 12,590 B | 2026-10-31 | STRIDE threat model, DPDPA 2023 compliance matrix. |
| 16 | `docs/product/USER_FLOWS.md` | 22,063 B | 2026-10-31 | Mermaid flowcharts, state transitions, sequence diagrams. |
| 17 | `docs/quality/TEST_STRATEGY.md` | 17,124 B | 2026-10-31 | Test pyramid, 20 high-risk scenarios (`TS-01..20`). |
| 18 | `docs/technical/API_SPECIFICATION.md` | 9,222 B | 2026-10-31 | OpenAPI 3.1 endpoints, RFC 7807 problem details. |
| 19 | `docs/technical/ARCHITECTURE.md` | 9,579 B | 2026-10-31 | Modular monolith topology, network boundaries. |
| 20 | `docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md` | 22,610 B | 2026-10-31 | Concurrency mechanics, MSAI rules, LPRP protocol. |
| 21 | `docs/technical/DATABASE_DESIGN.md` | 19,485 B | 2026-10-31 | Authoritative PostgreSQL DDL, PostGIS queries, triggers. |
| 22 | `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`| 22,680 B | 2026-10-31 | Double-entry journal templates, MoR settlement. |
| 23 | `docs/technical/QR_ACCESS_DESIGN.md` | 10,747 B | 2026-10-31 | Credential lifecycles, offline manual exception. |

---

## 2. Missing Expected Files

The following expected governance and technical files were identified as missing or deferred:
1. `docs/audits/V2_3_1_CHANGELOG.md` — Required for tracking V2.3.1 hardening changes.
2. `docs/audits/V2_3_1_FINAL_AUDIT.md` — Required for independent final scoring.
3. `docs/audits/V2_3_1_RESIDUAL_RISK_REGISTER.md` — Required for engineering operations risk management.
4. `docs/product/FOUNDER_DECISION_CHECKLIST.md` — Required executive decision document separating founder-only commercial choices.

---

## 3. Version and Revision Information

- Current Document Version across repository: **2.3.0**
- Target Document Version for Hardening: **2.3.1**
- Baseline Status: Sprint 0/1 Architecture & Data Invariants Baselined; Pilot Gated on External Rails.

---

## 4. Existing Requirements Count

- In `PRD.md` Section 12: **22 formal requirement blocks** under stable IDs (`FR-AUTH-001..002`, `FR-DRIVER-001..002`, `FR-OWNER-001..002`, `FR-INVENTORY-001`, `FR-AVAIL-001`, `FR-BOOK-001..002`, `FR-PAY-001..002`, `FR-REFUND-001`, `FR-QR-001..002`, `FR-SESSION-001`, `FR-LEDGER-001`, `FR-PAYOUT-001`, `FR-ADMIN-001`, `FR-SEC-001`, `FR-NOTIFY-001`, `FR-GPRP-001`).
- In `REQUIREMENTS_TRACEABILITY.md`: **70 granular requirements** using legacy classification IDs (`AUTH-001..007`, `DRV-001..014`, `OWN-001..011`, `GRD-001..003`, `ACC-001..008`, `AVAIL-001..006`, `PAY-001..005`, `LEDG-001..002`, `REF-001`, `POUT-001..002`, `REC-001..005`, `SEC-001..004`, `NFR-001..005`).
- *Hardening Deficit:* RTM uses legacy IDs that do not match the `FR-<DOMAIN>-<NUM>` stable taxonomy in `PRD.md`. Needs full normalization.

---

## 5. Existing Unresolved Decision Count

As recorded in `docs/product/OPEN_QUESTIONS.md`:
- Total Items Tracked: **65**
- Formally Decided / Resolved: **15** (23.1%)
- Proposed Defaults (Safe Technical Defaults): **33** (50.8%)
- External Dependencies (Payment Gateway / Bank Underwriting): **12** (18.5%)
- Pending Formal Legal/Tax Review: **5** (7.6%)
- *Hardening Deficit:* Statuses were loosely documented as "Signed" or "Pre-Launch". They must be formalized using the rigorous status taxonomy: `FOUNDER_APPROVED`, `PROPOSED`, `EXTERNALLY_CONFIRMED`, `LEGALLY_REVIEWED`, `TECHNICALLY_VERIFIED`, `BLOCKED`, `SUPERSEDED`.

---

## 6. Baseline Findings Matrix (P0 / P1 / P2 / P3)

| Finding ID | Severity | Affected File | Section / Ref | Existing Behavior | Defect & Operational Risk | Required Correction | Verification Method |
|---|---|---|---|---|---|---|---|
| **BASE-P0-01** | **P0** | `DATABASE_DESIGN.md`, `PAYMENT_AND_LEDGER_DESIGN.md` | Trigger `fn_prevent_posted_lines_modification` | Checks only `COALESCE(OLD.journal_id, NEW.journal_id)`. | If a transaction updates `journal_lines SET journal_id = new_id`, it moves a line between journals. If moved into a POSTED journal or out of a POSTED journal, the trigger fails to check the secondary journal! Risk: Corrupting immutable ledger balance. | Update trigger to check BOTH `OLD.journal_id` AND `NEW.journal_id` on UPDATE. Acquire row-level locks on both parent journals in deterministic ID order to prevent deadlocks. | Concurrency SQL unit test moving line between draft and posted journal. |
| **BASE-P0-02** | **P0** | `REQUIREMENTS_TRACEABILITY.md` vs `PRD.md` | `RTM` §3 `DRV-009` vs `PRD.md` §27 | `DRV-009` states cancellation tiers: `>2h=100%, 1-2h=50%, <1h=0%`. `PRD.md` §27 states: `>2h=100%, 30m-2h=50%, <30m=0%`. | Contradictory cancellation refund window between 1 hour and 30 minutes! Risk: Financial dispute with driver, ledger reversal imbalance. | Standardize to provisional default `>2h: 100%`, `30m-2h: 50%`, `<30m: 0%` across all files, explicitly marked `PROPOSED (Pending Founder Approval)`. | Text scan across all files. |
| **BASE-P0-03** | **P0** | `REQUIREMENTS_TRACEABILITY.md` vs `PRD.md` | `RTM` §4 `OWN-005` vs `PRD.md` §14 | `OWN-005` states `minimum booking duration (1 hour)`. `PRD.md` §14 & `OPEN_QUESTIONS.md` state `minimum booking duration (default 30 min)`. | Contradictory minimum booking duration! Risk: Driver unable to book 30m slots; host configuration rejection. | Standardize to `30 minutes` universally, marked `PROPOSED (Pending Founder Approval)`. | Text search. |
| **BASE-P0-04** | **P0** | `PRD.md`, `OPEN_QUESTIONS.md` | Section 1.2, Decision Register | Statuses used loose terms like "Signed" without distinguishing founder approval from technical recommendation. | Regulatory & financial risk: AI recommendation masquerading as binding business policy. | Implement 7-status taxonomy: `FOUNDER_APPROVED`, `PROPOSED`, `EXTERNALLY_CONFIRMED`, `LEGALLY_REVIEWED`, `TECHNICALLY_VERIFIED`, `BLOCKED`, `SUPERSEDED`. | Audit matrix review. |
| **BASE-P1-01** | **P1** | `REQUIREMENTS_TRACEABILITY.md` | Throughout | RTM uses legacy IDs (`AUTH-001`, `DRV-001`, etc.) while `PRD.md` uses `FR-<DOMAIN>-<NUM>`. | Broken traceability between PRD stable requirements and test scenarios. | Normalize RTM to cross-reference stable `FR-xxx` IDs with legacy test refs. | RTM schema validation. |
| **BASE-P1-02** | **P1** | `API_SPECIFICATION.md` | §2 | API endpoint specs lack explicit request/response schemas for GPRP alternative space acceptance, offline batch sync, and overstay calculation. | Engineers will have to improvise API schemas during Sprint 1. | Provide complete JSON schemas and RFC 7807 error responses for these flows. | Schema validation. |
| **BASE-P1-03** | **P1** | `USER_FLOWS.md` | Section 7 | Mermaid sequence diagram for cancellation shows older terminology. | Minor confusion during developer walkthrough. | Align Mermaid nodes with canonical refund enum (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`). | Visual inspection. |
| **BASE-P2-01** | **P2** | `.github/workflows/spec-validation.yml` | Step 3 | Script prints "Validate V2.3 Specification Suite" and checks only banned regex patterns. | CI does not validate link integrity, requirement ID uniqueness, or JSON schema validity. | Strengthen CI script to check link validity and requirement ID uniqueness. | GitHub Actions run. |

---

## 7. Canonical Source-of-Truth Hierarchy

To eliminate ambiguity across 23 documents, the repository enforces this strict precedence:

```
+---------------------------------------------------------------------------------------+
|                         SOURCE-OF-TRUTH HIERARCHY MATRIX                              |
+---------------------------------------------------------------------------------------+
| LEVEL 1: Master Specification (What the product must do)                             |
|          -> PRD.md                                                                    |
+---------------------------------------------------------------------------------------+
| LEVEL 2: Technical Blueprints (How the system is architected and stored)              |
|          -> DATABASE_DESIGN.md (DDL, Constraints, Triggers)                           |
|          -> PAYMENT_AND_LEDGER_DESIGN.md (Financial Rules, Double-Entry Accounting)   |
|          -> BOOKING_AND_AVAILABILITY_DESIGN.md (MSAI Signals, GiST Concurrency, LPRP) |
|          -> API_SPECIFICATION.md (REST API Schemas, Idempotency, Errors)              |
|          -> ARCHITECTURE.md (Modular Monolith Boundaries, Network Perimeters)         |
|          -> QR_ACCESS_DESIGN.md (Tokens, Scanning, Offline Fallback)                  |
+---------------------------------------------------------------------------------------+
| LEVEL 3: Product & UX Contracts (User Journeys, Screens, Threat Models)               |
|          -> SCREEN_REQUIREMENTS.md (Mobile Screens SCR-001..402)                      |
|          -> USER_FLOWS.md (Mermaid Sequence & Flow Diagrams)                          |
|          -> SECURITY_AND_PRIVACY_REVIEW.md (STRIDE & DPDPA)                           |
|          -> BUSINESS_ASSUMPTIONS.md (Unit Economics Calculations)                     |
+---------------------------------------------------------------------------------------+
| LEVEL 4: Governance & Quality Assurances (Decisions, Traceability, Tests)             |
|          -> OPEN_QUESTIONS.md (Authoritative 65-Item Decision Register)               |
|          -> REQUIREMENTS_TRACEABILITY.md (RTM Mapping)                                |
|          -> TEST_STRATEGY.md (20 Mandatory High-Risk Scenarios)                       |
|          -> FOUNDER_DECISION_CHECKLIST.md (Executive Signoff Checklist)               |
+---------------------------------------------------------------------------------------+
```

---

## 8. Verification Strategy & Exit Criteria for V2.3.1

The engineering hardening milestone V2.3.1 will be approved only when:
1. All P0 findings (`BASE-P0-01` through `BASE-P0-04`) are resolved and verified.
2. The ledger immutability trigger in `DATABASE_DESIGN.md` and `PAYMENT_AND_LEDGER_DESIGN.md` correctly handles `OLD.journal_id != NEW.journal_id` with deterministic row locking.
3. Cancellation and minimum booking duration policies are 100% harmonized across `PRD.md`, `REQUIREMENTS_TRACEABILITY.md`, and `OPEN_QUESTIONS.md`.
4. `FOUNDER_DECISION_CHECKLIST.md` is authored with clear separation between founder decisions, provider dependencies, and technical defaults.
5. The CI pipeline `.github/workflows/spec-validation.yml` is upgraded and runs 100% green on remote GitHub Actions.
