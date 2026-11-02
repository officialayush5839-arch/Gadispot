# Project: Gadispot PRD V2.3.2 Final Verification Patch

## Architecture
Gadispot is a high-concurrency parking marketplace platform. Version 2.3.2 is the Final Verification Patch establishing real, empirically verified implementation readiness on PostgreSQL 16.

### Architectural Invariants:
1. **Ledger Immutability & Deadlock Freedom**:
   - Double-entry accounting with zero-sum balanced entries.
   - `fn_verify_journal_balance` on `journal_entries` relies on the parent exclusive row lock from the posting `UPDATE` without acquiring redundant child `FOR UPDATE` line locks, eliminating lock-order inversion deadlocks.
   - `fn_prevent_posted_lines_modification` on `journal_lines` enforces immutability by acquiring parent row lock `FOR SHARE`.
2. **Double-Booking Prevention**:
   - GiST exclusion constraints on `(parking_space_id WITH =, time_window WITH &&)` utilizing PostgreSQL's native `tstzrange` and `btree_gist` extension.
3. **Harmonized Commercial Policy Governance**:
   - Unsigned commercial parameters (commission, grace periods, overstay tariffs, duration limits) are consistently designated as `PROPOSED (Pending Founder Approval)`.
4. **Honest Quality Assurance**:
   - Specifications, CI verification scripts, and test suites are aligned with exact execution evidence rather than ungrounded claims.

---

## Feature Inventory
| # | Feature / Issue | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Founder Decision Reconciliation (P0-01) | Reconcile decision statuses across OPEN_QUESTIONS.md, FOUNDER_DECISION_CHECKLIST.md, PRD.md, and REQUIREMENTS_TRACEABILITY.md to `PROPOSED (Pending Founder Approval)`. Remove unverified "Signed" claims. | M1 | ORIGINAL_REQUEST §P0-01, Survey 1 |
| 2 | Test Scenario Count Harmonization (P0-05) | Harmonize the 15 PRD §42 acceptance scenarios and 20 TEST_STRATEGY.md technical scenarios across PRD.md, TEST_STRATEGY.md, README.md, and audit reports. | M1 | ORIGINAL_REQUEST §P0-05, Survey 1 |
| 3 | DECISION_LOG.md Update (P1-01) | Update DECISION_LOG.md header, status, and baseline references to V2.3.2 Harmonized. | M1 | ORIGINAL_REQUEST §P1-01, Survey 1 |
| 4 | asyncpg Parameter & Exception Fix (P0-04 Part A) | Correct `:jid` named placeholders to positional `$1, $2` and `RaiseException` to `RaiseError` in TEST_STRATEGY.md. | M1 | ORIGINAL_REQUEST §P0-04, Survey 2 & 3 |
| 5 | CI Validation Script Fix (P0-03) | Add `\bREFUNDED\b` check, remove blanket exclusion of BOOKING_AND_AVAILABILITY_DESIGN.md (use line 345 filter), exclude `.agents`, and rename output messages honestly. | M2 | ORIGINAL_REQUEST §P0-03, Survey 3 |
| 6 | Deadlock-Free Ledger Trigger Design (P0-02 Part A) | Document the mathematical lock-order analysis and update DATABASE_DESIGN.md & PAYMENT_AND_LEDGER_DESIGN.md with the zero-child-lock posting trigger. | M3 | ORIGINAL_REQUEST §P0-02, Survey 2 |
| 7 | Executable PostgreSQL Test Suite (P0-02 & P0-04 Part B) | Create tests/conftest.py, test_ledger_immutability.py, test_booking_exclusion.py, test_concurrent_posting.py, and requirements-test.txt; execute and pass 100% against local PostgreSQL. | M4 | ORIGINAL_REQUEST §P0-02, P0-04, Survey 2 & 3 |
| 8 | Readiness Recalculation & Evaluation Personas (P1-02) | Recalculate readiness scores based on actual PostgreSQL test execution; relabel signatories as role-based evaluation personas. | M5 | ORIGINAL_REQUEST §P1-02, Survey 1 |
| 9 | GitHub CI/CD Pipeline Verification | Update README to V2.3.2, commit all changes, push to GitHub remote, and verify remote GitHub Actions pipeline is 100% green. | M5 | ORIGINAL_REQUEST §Deliverables, AGENTS.md |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Specification & Decision Harmonization | P0-01, P0-05, P1-01, P0-04 (Part A) | none | DONE |
| M2 | CI Validation Script & Spec Tooling | P0-03 (`scripts/validate_spec.py`) | M1 | DONE |
| M3 | Ledger Concurrency & Schema Corrections | P0-02 (Part A) (`DATABASE_DESIGN.md`, `PAYMENT_AND_LEDGER_DESIGN.md`) | M1 | DONE |
| M4 | Real Executable PostgreSQL 16 Test Suite | P0-02 (Part B), P0-04 (Part B) (`tests/` directory) | M2, M3 | IN_PROGRESS |
| M5 | Final Verification, Readiness Recalculation & CI Pipeline Push | P1-02, README, Git commit, Push & GitHub Actions verification | M4 | PLANNED |

---

## Interface Contracts

### 1. Ledger Posting & Mutation Concurrency Contract
- **Posting Transaction**:
  - Executes `UPDATE journal_entries SET posting_status = 'POSTED', posted_at = NOW() WHERE id = $1`.
  - Trigger `fn_verify_journal_balance` executes BEFORE UPDATE.
  - Locks row in `journal_entries` with row-exclusive lock.
  - Queries `journal_lines` for sum balance WITHOUT acquiring line locks (`FOR UPDATE` is forbidden in posting trigger).
- **Line Mutation Transaction**:
  - Executes INSERT, UPDATE, or DELETE on `journal_lines`.
  - Trigger `fn_prevent_posted_lines_modification` executes BEFORE INSERT/UPDATE/DELETE.
  - Queries parent `journal_entries` row `FOR SHARE`.
  - If parent is locked by posting transaction, mutation blocks cleanly until posting commits or rolls back. No circular wait-for deadlock can occur.

### 2. Test Suite Fixtures & Runner Contract (`tests/conftest.py`)
- Fixture `pg_pool`: Creates an asyncpg connection pool to the test database (`gadispot_test` on port 5432 or port 5433 fallback).
- Tables created: `parking_spaces`, `bookings`, `journal_entries`, `journal_lines`, `accounts`.
- Extensions: `btree_gist`, `uuid-ossp`.
- Pytest invocation: `pytest tests/ -v`.

---

## Code Layout
```
Gadispot/
├── .github/
│   └── workflows/
│       └── spec-validation.yml               # GitHub Actions CI workflow
├── docs/
│   ├── audits/
│   │   └── V2_3_1_FINAL_AUDIT.md             # Recalibrated audit & personas
│   ├── product/
│   │   ├── DECISION_LOG.md                   # Updated to V2.3.2
│   │   ├── FOUNDER_DECISION_CHECKLIST.md     # Harmonized decision status
│   │   └── OPEN_QUESTIONS.md                 # Harmonized decision status
│   ├── quality/
│   │   └── TEST_STRATEGY.md                  # Corrected asyncpg examples & scenario counts
│   └── technical/
│       ├── BOOKING_AND_AVAILABILITY_DESIGN.md
│       ├── DATABASE_DESIGN.md                # Deadlock-free trigger DDL
│       └── PAYMENT_AND_LEDGER_DESIGN.md      # Mathematical locking proof & trigger DDL
├── scripts/
│   └── validate_spec.py                      # Harmonization validator script
├── tests/
│   ├── conftest.py                           # Asyncpg DB fixtures & schema setup
│   ├── database/
│   │   ├── test_booking_exclusion.py         # GiST exclusion tests
│   │   ├── test_concurrent_posting.py        # Deadlock-freedom multi-connection tests
│   │   └── test_ledger_immutability.py       # Trigger balance & immutability tests
│   └── pytest.ini
├── requirements-test.txt                     # Test dependencies
├── PRD.md                                    # Harmonized PRD V2.3.2
└── README.md                                 # V2.3.2 summary & verification results
```
