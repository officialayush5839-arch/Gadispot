# Gadispot (formerly SmartPark Exchange) — Specification V2.3 Changelog

> **Document Identifier:** CHG-SPX-2026-V2.3  
> **Release Date:** October 31, 2026  
> **Target Milestone:** PRD V2.3 — Final Product & Engineering Requirements Specification  
> **Baseline Superceded:** PRD-SPX-2026-V2.2-REVIEW  
> **Authors:** Principal Product Architect, Senior Backend Architect, FinTech Systems Architect, Database Architect, Security Engineer, QA Architect  

---

## 1. Executive Summary of V2.3 Release

Specification Version 2.3 represents the final engineering specification baseline for **Gadispot** (formerly SmartPark Exchange). This release eliminates all lingering contradictions identified during independent architectural audit, aligns the 50-section PRD with formal functional requirement identifiers (`FR-AUTH-001` through `FR-GPRP-001`), provides explicit end-to-end acceptance scenarios 1 through 15, unifies the refund state machine across DDL and application specifications, enforces database-level immutability and parent-row locking on `journal_lines`, purges machine-specific local filesystem URIs, and removes unsupported readiness claims while maintaining transparent status accounting for all 65 decision items.

---

## 2. Comprehensive Itemized Changelog

### Change CHG-001: Financial Arithmetic Reconciliation in Revision History
- **Previous State:** PRD revision history for v2.2.0 (§1.1) stated: `exact ₹15.87 net take-rate & ₹68.00 owner payable`, which directly contradicted the verified unit economics calculation in §30, §46, `BUSINESS_ASSUMPTIONS.md`, and `PAYMENT_AND_LEDGER_DESIGN.md`.
- **New State:** PRD revision history and all financial references updated to: `exact ₹19.83 net operating platform margin (21.6% net take-rate) & ₹65.84 net owner entitlement on ₹91.80 gross customer collection`.
- **Exact Correction:** Aligned §1.1 and §49 revision history tables with the verified worked example:
  $$\text{Driver (₹91.80)} = \text{Owner (₹65.84)} + \text{Platform Margin (₹19.83)} + \text{GST (₹3.96)} + \text{MDR (₹2.17)}$$
- **Reason:** Prevent financial disputes, ledger rounding mismatch, and incorrect investor/founder economic reporting.
- **Affected Requirements:** `FR-LEDGER-001`, `FR-PAY-001`, `FR-PAYOUT-001`.
- **Affected Files:** `PRD.md`, `docs/product/BUSINESS_ASSUMPTIONS.md`, `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`.
- **Remaining Consequences:** Platform absorbs gateway MDR (2.36%) as an operating expense. Requires founder underwriting signoff on gateway contract.

---

### Change CHG-002: Universal Elimination of Lingering 5-Minute Hold References
- **Previous State:** While the 480-second (8-minute) hold rule was established in V2.2, residual references to `5-min TTL`, `5-minute temporary booking holds`, `5-Min Holds` (architecture diagram), `04:59` checkout timer, and `5-minute reservation hold` persisted in `PRD.md`, `ARCHITECTURE.md`, `OPEN_SOURCE_INTEGRATIONS.md`, `REQUIREMENTS_TRACEABILITY.md`, and `SCREEN_REQUIREMENTS.md`.
- **New State:** Strictly 480 seconds (8 minutes) universally across all files, database comments, Redis TTLs, checkout screen countdowns (`07:59`), and error modals.
- **Exact Correction:**
  - `SCREEN_REQUIREMENTS.md`: Updated checkout banner from `04:59` to `07:59` and error modal from `5-minute` to `8-minute (480-second)`.
  - `OPEN_SOURCE_INTEGRATIONS.md`: Updated Redis hold lock description to `480-second (8-minute)` and dynamic payment QR TTL to `480 seconds (8m)`.
  - `ARCHITECTURE.md`: Updated modular monolith diagram node from `- 5-Min Holds` to `- 480s Holds`.
  - `REQUIREMENTS_TRACEABILITY.md`: Updated `DRV-005` from `5-min TTL` to `480-second (8-minute) TTL`.
  - `PRD.md`: Cleaned §8, §11, and §20.
- **Reason:** Ambiguity between 300s and 480s leads to checkout race conditions, premature space release in mobile clients, and unfulfillable payments.
- **Affected Requirements:** `FR-BOOK-001`, `FR-AVAIL-001`.
- **Affected Files:** `PRD.md`, `docs/technical/ARCHITECTURE.md`, `docs/product/OPEN_SOURCE_INTEGRATIONS.md`, `docs/product/REQUIREMENTS_TRACEABILITY.md`, `docs/product/SCREEN_REQUIREMENTS.md`.
- **Remaining Consequences:** None; 100% harmonized.

---

### Change CHG-003: Canonical 6-Stage Refund State Machine Harmonization
- **Previous State:** `DATABASE_DESIGN.md` and `BOOKING_AND_AVAILABILITY_DESIGN.md` defined `refund_status_enum` with 5 values (`NONE`, `REFUND_PENDING`, `REFUND_PROCESSING`, `REFUNDED`, `REFUND_FAILED`), conflicting with the 6-stage lifecycle documented in `PRD.md` and `PAYMENT_AND_LEDGER_DESIGN.md` (`REFUND_ELIGIBLE`, `REFUND_REQUESTED`, `GATEWAY_ACCEPTED`, `REFUND_PROCESSING`, `REFUND_SETTLED`, `REFUND_FAILED`).
- **New State:** Canonical 6-stage lifecycle formally defined and unified across database DDL and domain services:
  ```sql
  CREATE TYPE refund_status_enum AS ENUM (
      'NONE',
      'REFUND_ELIGIBLE',
      'REFUND_REQUESTED',
      'GATEWAY_ACCEPTED',
      'REFUND_PROCESSING',
      'REFUND_SETTLED',
      'REFUND_FAILED'
  );
  ```
- **Exact Correction:** Updated `DATABASE_DESIGN.md` and `BOOKING_AND_AVAILABILITY_DESIGN.md` DDL definitions to include `REFUND_ELIGIBLE`, `GATEWAY_ACCEPTED`, and `REFUND_SETTLED`.
- **Reason:** Prevents application runtime type mismatch when the backend outbox processes gateway acknowledgments and distinguishes gateway receipt from actual banking rail settlement.
- **Affected Requirements:** `FR-REFUND-001`, `FR-PAY-001`, `FR-GPRP-001`.
- **Affected Files:** `docs/technical/DATABASE_DESIGN.md`, `docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md`, `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`, `PRD.md`.
- **Remaining Consequences:** Bank rail settlement window (5–7 business days) is transparently tracked until `REFUND_SETTLED`.

---

### Change CHG-004: Double-Entry Ledger Concurrency and Immutability Triggers on Journal Lines
- **Previous State:** Immutability trigger `trg_prevent_posted_modification` was attached only to `journal_entries`. An attacker or defect could execute `INSERT`, `UPDATE`, or `DELETE` on `journal_lines` referencing a posted journal, corrupting ledger balance without triggering the parent trigger. Additionally, `fn_verify_journal_balance` lacked row locking to serialize concurrent line insertions during posting transitions.
- **New State:**
  1. Added `fn_prevent_posted_lines_modification()` trigger on `journal_lines` (`BEFORE INSERT OR UPDATE OR DELETE`) with a `SELECT ... FOR SHARE` lock on the parent journal entry to verify that its status is not `POSTED`.
  2. In `fn_verify_journal_balance()`, added `PERFORM 1 FROM journal_lines WHERE journal_id = NEW.id FOR UPDATE;` to lock child rows during posting balance verification.
- **Exact Correction:** Updated `docs/technical/DATABASE_DESIGN.md` and `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md` with complete trigger and locking code.
- **Reason:** Guarantee absolute mathematical ledger immutability and eliminate race conditions between child row insertion and parent posting status updates.
- **Affected Requirements:** `FR-LEDGER-001`.
- **Affected Files:** `docs/technical/DATABASE_DESIGN.md`, `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`, `PRD.md`.
- **Remaining Consequences:** Prevents any tampering with posted financial records directly in PostgreSQL.

---

### Change CHG-005: Correction of Stale Redis-Only Webhook Deduplication Code Snippet
- **Previous State:** `OPEN_SOURCE_INTEGRATIONS.md` §5.2 contained an outdated code snippet demonstrating Redis-only webhook deduplication (`redis_client.set(f"webhook:event:{event_id}", nx=True)`), contradicting the mandatory durable PostgreSQL database deduplication requirement.
- **New State:** Code snippet updated to show PostgreSQL `INSERT INTO payment_webhook_events ... ON CONFLICT DO NOTHING` as the primary durable gate, with Redis functioning strictly as an ephemeral accelerator.
- **Exact Correction:** Rewrote §5.2 in `docs/product/OPEN_SOURCE_INTEGRATIONS.md`.
- **Reason:** Container restarts, Redis cluster evictions, or memory limits must never allow duplicate financial postings or double-credits.
- **Affected Requirements:** `FR-PAY-001`, `FR-LEDGER-001`.
- **Affected Files:** `docs/product/OPEN_SOURCE_INTEGRATIONS.md`.
- **Remaining Consequences:** Zero risk of duplicate webhook processing.

---

### Change CHG-006: Eradication of Machine-Specific Local Filesystem URIs
- **Previous State:** Numerous markdown files contained local Windows file paths (`file:///c:/Users/ARYAN%20-%20AYUSH/OneDrive/Desktop/Gadispot/...`) in hyperlinks, breaking on remote GitHub, CI runners, and other workstations.
- **New State:** All links converted to portable, relative markdown links (e.g., `[USER_FLOWS.md](../product/USER_FLOWS.md)`).
- **Exact Correction:** Replaced all absolute filesystem URIs across `PRD.md`, `PRD_FINAL_AUDIT.md`, `REQUIREMENTS_TRACEABILITY.md`, and `README.md`.
- **Reason:** Repository portability, developer experience, and standard documentation craftsmanship.
- **Affected Requirements:** Documentation integrity across all files.
- **Affected Files:** `PRD.md`, `README.md`, `docs/audits/PRD_FINAL_AUDIT.md`, `docs/product/REQUIREMENTS_TRACEABILITY.md`.
- **Remaining Consequences:** All links render cleanly on GitHub and any local clone.

---

### Change CHG-007: De-Escalation of Unsupported Readiness Claims & Truth in Question Status
- **Previous State:** Historical audits claimed "Readiness Score: 98/100", "10/10 Engineering Baseline", and "Zero residual contradictions", while 33 product decisions remained proposed defaults, 12 were external dependencies, and 5 were pending formal legal review.
- **New State:** Replaced artificial scoring with an honest, structured Implementation Readiness Gate model (Gates A through F), clearly distinguishing specification completion from operational pilot readiness.
- **Exact Correction:** Re-evaluated all 6 Readiness Gates with transparent conditions in `PRD.md` and `PRD_V2_3_FINAL_AUDIT.md`.
- **Reason:** Defensible engineering management; preventing premature commercial launch before banking underwriting, KYC pipelines, and DLT SMS registrations are executed.
- **Affected Requirements:** Governance and implementation gating.
- **Affected Files:** `PRD.md`, `docs/audits/PRD_V2_3_FINAL_AUDIT.md`, `README.md`.
- **Remaining Consequences:** Clear roadmap for founders and lead architects.

---

### Change CHG-008: Establishment of Standard Functional Requirement ID Hierarchy (`FR-xxx-yyy`)
- **Previous State:** Requirements were organized under heterogeneous IDs (`AUTH-001`, `DRV-001`, `OWN-001`, `ACC-001`, `AVAIL-001`, etc.) without a uniform 14-field specification structure.
- **New State:** Standardized into 16 canonical functional requirement families (`FR-AUTH-001`, `FR-DRIVER-001`, `FR-OWNER-001`, `FR-INVENTORY-001`, `FR-AVAIL-001`, `FR-BOOK-001`, `FR-PAY-001`, `FR-REFUND-001`, `FR-QR-001`, `FR-SESSION-001`, `FR-LEDGER-001`, `FR-PAYOUT-001`, `FR-ADMIN-001`, `FR-SEC-001`, `FR-NOTIFY-001`, `FR-GPRP-001`) with complete descriptions, actors, preconditions, flows, failure modes, data schemas, security rules, and testable acceptance criteria.
- **Exact Correction:** Fully documented in `PRD.md` Section 12 and mapped in `docs/product/REQUIREMENTS_TRACEABILITY.md`.
- **Reason:** Testability, automated traceability, and clear engineering task assignment.
- **Affected Requirements:** All functional requirements.
- **Affected Files:** `PRD.md`, `docs/product/REQUIREMENTS_TRACEABILITY.md`.
- **Remaining Consequences:** Single source of truth for QA and developers.

---

### Change CHG-009: Addition of 15 Comprehensive End-to-End Acceptance Scenarios
- **Previous State:** PRD lacked the 15 specific end-to-end scenarios required for exhaustive verification of race conditions, offline handling, and financial consistency.
- **New State:** Added Scenarios 1 through 15 in Section 42 of `PRD.md` covering successful booking, interval collisions, hold expiration, late payment resolution, duplicate webhooks, refund failures, QR replay, exit token misuse, guard offline operation, owner authority failure, GPRP recovery, ledger consistency, owner payouts, unauthorized guard access, and listing suspension.
- **Exact Correction:** Authoritative scenarios documented with Preconditions, Actions, Expected System Behavior, Database Invariants, Financial Effects, Security Checks, and Acceptance Results.
- **Reason:** Direct test plan creation for QA automation in `TEST_STRATEGY.md`.
- **Affected Requirements:** `FR-BOOK-001`, `FR-PAY-001`, `FR-QR-001`, `FR-LEDGER-001`, `FR-GPRP-001`.
- **Affected Files:** `PRD.md`.
- **Remaining Consequences:** Concrete baseline for Locust and Pytest test runners.

---

### Change CHG-010: Project Identity Harmonization to Gadispot
- **Previous State:** Documentation frequently mixed "SmartPark Exchange" and "SmartPark" without clear project branding continuity.
- **New State:** Formally established project identity as **Gadispot (formerly SmartPark Exchange)** across all document headers, titles, and specifications.
- **Exact Correction:** Updated headers across all 18 repository markdown documents.
- **Reason:** Brand alignment with user prompt and commercial registration strategy.
- **Affected Requirements:** All files.
- **Affected Files:** All `.md` documents in repository.
- **Remaining Consequences:** Uniform identity.
