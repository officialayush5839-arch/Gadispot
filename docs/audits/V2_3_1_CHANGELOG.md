# Gadispot — V2.3.1 Engineering Readiness Hardening Changelog

> **Document Version:** 2.3.1  
> **Release Date:** October 31, 2026  
> **Milestone:** Implementation Readiness Hardening & Specification Freeze Verification  
> **Audit Team:** Principal Software Architect, Database & Concurrency Specialist, FinTech Systems Engineer, Security Architect, Lead QA Architect  
> **Repository Baseline:** `https://github.com/officialayush5839-arch/Gadispot`  

---

## 1. Executive Summary

Milestone **PRD V2.3.1 — Engineering Readiness Hardening** upgrades the Gadispot specification from the V2.3 baseline to an independently verifiable, mathematically sound, and operationally rigorous state.

This release does not invent new product concepts or modify application business goals. Instead, it systematically eliminates lingering implementation ambiguities, resolves concurrency and database trigger vulnerabilities, aligns requirements traceability matrices, and establishes an executive decision checklist separating commercial policy signoffs from technical defaults.

---

## 2. Comprehensive Inventory of Changes

### 2.1 Database Trigger Hardening (Ledger Immutability & Deadlock Prevention)
- **Target Files:**
  - `docs/technical/DATABASE_DESIGN.md`
  - `docs/technical/PAYMENT_AND_LEDGER_DESIGN.md`
- **Identified Defect (`BASE-P0-02`):**
  - In V2.3, `fn_prevent_posted_lines_modification` used `v_parent_id := COALESCE(NEW.journal_id, OLD.journal_id)`.
  - On `UPDATE journal_lines SET journal_id = new_id`, the trigger evaluated only `NEW.journal_id`. If `OLD.journal_id` belonged to an already `POSTED` journal, reassigning a line *out* of an immutable journal succeeded without exception.
  - Furthermore, concurrent transactions updating journal lines between shared journals in opposite directions lacked deterministic locking order, creating a deadlock hazard under high transactional throughput.
- **V2.3.1 Remediation:**
  - Hardened `fn_prevent_posted_lines_modification` across both DDL definitions:
    1. Evaluates operation type: `INSERT` locks `NEW.journal_id`, `DELETE` locks `OLD.journal_id`.
    2. On `UPDATE`: If `OLD.journal_id = NEW.journal_id`, locks the single parent.
    3. On cross-journal `UPDATE` (`OLD.journal_id != NEW.journal_id`): Acquires `FOR SHARE` locks on parent entries in deterministic UUID sort order (`IF OLD.journal_id < NEW.journal_id THEN ... ELSE ...`), mathematically eliminating deadlock cycles.
    4. Explicitly verifies that *neither* `OLD.journal_id` nor `NEW.journal_id` is in `POSTED` status, raising `Immutable Ledger Violation` if violated.
    5. Verifies foreign key existence before checking immutability.

### 2.2 Purging Residual Refund Enum Values
- **Target Files:**
  - `docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md`
  - `docs/quality/TEST_STRATEGY.md`
  - `docs/product/OPEN_QUESTIONS.md`
- **Identified Defect (`BASE-P0-01`):**
  - Residual 5-stage enum references (`REFUND_PENDING`, `REFUNDED`) persisted in design text and test assertions, contradicting the canonical 6-stage lifecycle (`REFUND_ELIGIBLE`, `REFUND_REQUESTED`, `GATEWAY_ACCEPTED`, `REFUND_PROCESSING`, `REFUND_SETTLED`, `REFUND_FAILED`).
- **V2.3.1 Remediation:**
  - `BOOKING_AND_AVAILABILITY_DESIGN.md`: Updated partial index definition (line 135), transition logic (line 317), function call (line 324), 6-stage lifecycle documentation (lines 331–338), and fallback handling (line 432) to strictly use `REFUND_ELIGIBLE`.
  - `TEST_STRATEGY.md`: Updated test scenario TS-04 (line 71) to canonical 6 stages and TS-06 (line 88) to `ACTIVE_HOLD -> REFUND_SETTLED`.
  - `OPEN_QUESTIONS.md`: Updated founder decision Q2 (line 29) to specify transition to `REFUND_ELIGIBLE`.

### 2.3 Requirements Traceability Reconciliation
- **Target Files:**
  - `docs/product/REQUIREMENTS_TRACEABILITY.md`
  - `PRD.md`
- **Identified Defect (`BASE-P0-03` & `BASE-P0-04`):**
  - Line 50 of `REQUIREMENTS_TRACEABILITY.md` stated cancellation tiers as `>2h=100%, 1-2h=50%, <1h=0%`, contradicting `PRD.md` §27 (`>2h: 100%, 30m-2h: 50%, <30m: 0%`).
  - Line 67 of `REQUIREMENTS_TRACEABILITY.md` stated minimum booking duration as `1 hour`, contradicting `PRD.md` §14 and `OPEN_QUESTIONS.md` (`30 minutes`).
- **V2.3.1 Remediation:**
  - Updated `REQUIREMENTS_TRACEABILITY.md` line 50 to canonical tiers: `>2h: 100% parking fee; 30m–2h: 50% parking fee; <30m: 0% refund; convenience fee non-refundable; marked PROPOSED pending founder approval`.
  - Updated `REQUIREMENTS_TRACEABILITY.md` line 67 to canonical duration: `30 minutes, marked PROPOSED pending founder approval`.
  - Synchronized `PRD.md` §14 and §27 with explicit policy reference callouts to `POL-CAN-01` and `POL-DUR-01`.

### 2.4 Standalone Executive Decision Checklist
- **Target File:**
  - `docs/product/FOUNDER_DECISION_CHECKLIST.md` (New File)
- **V2.3.1 Implementation:**
  - Created an authoritative executive signoff artifact.
  - Summarizes the 5 foundational founder decisions (FD-01 through FD-05).
  - Explicitly itemizes the 7 commercial policies marked `PROPOSED (Pending Founder Approval)` (`POL-CAN-01` cancellation tiers, `POL-DUR-01` 30m minimum duration, `POL-COM-01` 15% commission, `POL-SUB-01` ₹100 GPRP subsidy cap, `POL-OST-01` 1.5× overstay multiplier, `POL-POT-01` weekly Tuesday payouts, `POL-ARR-02` 30m no-show grace).
  - Summarizes the 5 external legal and aggregator dependencies (`DEP-LEG-01` through `DEP-LEG-03`, `DEP-PAY-01`, `DEP-TEL-01`).
  - Provides a formal 4-signature executive signoff grid.

### 2.5 Baseline Audit Inventory & Defect Tracking
- **Target File:**
  - `docs/audits/V2_3_1_BASELINE_INVENTORY.md` (New File)
- **V2.3.1 Implementation:**
  - Documented file-by-file inventory of all 23 repository files with line counts, byte sizes, checksums, and verification status.
  - Formulated baseline findings matrix (`BASE-P0-01` to `BASE-P2-01`) detailing root causes and verified remedies.
  - Established canonical documentation hierarchy and exit criteria for specification freeze.

---

## 3. Verification & Compliance Matrix

| Audit Finding ID | Category | Target Component | V2.3 Status | V2.3.1 Hardened State | Verification Method |
|---|---|---|---|---|---|
| `BASE-P0-01` | State Machine | Multi-stage refund enums across docs | Lingering `REFUND_PENDING` / `REFUNDED` references | 100% unified to canonical 6-stage lifecycle (`REFUND_ELIGIBLE` $\to$ `REFUND_SETTLED`) | Global repository regex scan: 0 discrepancies |
| `BASE-P0-02` | Database Concurrency | Journal lines immutability trigger | Vulnerable to cross-journal line reassignment & deadlock | Implemented deterministic parent ID order locking (`FOR SHARE`) and dual parent posted status checks | DDL inspection across `DATABASE_DESIGN.md` & `PAYMENT_AND_LEDGER_DESIGN.md` |
| `BASE-P0-03` | Business Policy | Cancellation policy tiers | Conflict in `REQUIREMENTS_TRACEABILITY.md` (1-2h vs 30m-2h) | Reconciled to `>2h: 100%, 30m-2h: 50%, <30m: 0%`, marked `PROPOSED` | Text inspection and cross-file diff |
| `BASE-P0-04` | Business Policy | Minimum booking duration | Conflict in `REQUIREMENTS_TRACEABILITY.md` (1h vs 30m) | Reconciled to `30 minutes`, marked `PROPOSED` | Text inspection and cross-file diff |
| `BASE-P0-05` | Governance | Decision provenance and checklist | Unconsolidated executive approval requirements | Created `FOUNDER_DECISION_CHECKLIST.md` with explicit signoff matrix | Document verification |
