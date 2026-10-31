# SmartPark Exchange (Codename: Gadispot)

> **Mobile-First Real-Time Parking Marketplace for India**  
> **Specification Baseline:** V2.2 (Sprint 0/1 Implementation Ready)  
> **Architecture:** In-Process Modular Monolith (FastAPI) + Single Cross-Platform Binary (Flutter)

---

## Overview

SmartPark Exchange connects drivers searching for parking in congested Indian urban centers with private property owners, housing society committees, and commercial parking operators possessing underutilized parking capacity.

The system is engineered as a mobile-first platform operating under strict concurrency constraints, zero-loss double-entry accounting, and cyber-physical access controls.

---

## Core Architecture Principles

1. **Strict Mobile Binary with Dynamic Role Shells**: A single Flutter codebase deploying to Android and iOS dynamically rendering Driver (`SCR-100s`), Owner (`SCR-200s`), Guard (`SCR-301..304`), and Ops (`SCR-400s`) shells based on verified server JWT claims.
2. **Interval-Based Concurrency**: Universal 480-second (8-minute) checkout holds backed by PostgreSQL `btree_gist` temporal exclusion constraints (`EXCLUDE USING gist (parking_space_id WITH =, time_window WITH &&)`).
3. **Double-Entry General Ledger**: Mathematical equality ($\sum \text{Debits} = \sum \text{Credits}$) enforced via append-only PostgreSQL triggers across 12 distinct financial event templates.
4. **Separated Dynamic QR Lifecycles**: Strict isolation between Razorpay UPI payment collection QRs and high-entropy 128-bit CSPRNG gate access passes (`ENTRY_TOKEN` and `EXIT_TOKEN`).
5. **Controlled Offline Guard Fallback**: Deterministic manual check-in workflow for cellular-dead basement garages with an automated 7-day S3 privacy purge policy for verification photos.

---

## Documentation Suite

### Master Product Specification
* [PRD.md](PRD.md) — Comprehensive 50-section Product Requirements Document (V2.2).

### Technical Blueprints
* [BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) — Multi-Source Availability Intelligence (MSAI), two-tier hold expiration engine, and Late Payment Resolution Protocol (LPRP).
* [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) — Durable webhook idempotency, journal templates, chart of accounts, and unit economics.
* [DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) — Complete PostgreSQL DDL, PostGIS spatial queries, triggers, and indices.
* [QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md) — 5-stage credential lifecycle, offline verification protocol, and camera scanner specifications.
* [API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md) — RESTful API schemas with RFC 7807 problem details and idempotency headers.
* [ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) — System boundaries, data flow diagrams, and AWS ECS/Fargate deployment topology.

### Product & Operations
* [USER_FLOWS.md](docs/product/USER_FLOWS.md) — End-to-end Mermaid journey sequence and state transition diagrams.
* [OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md) — 65-question Decision Register (`DEC-01` to `DEC-65`) with assigned ownership and delivery milestones.
* [SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md) — STRIDE threat analysis and DPDPA 2023 compliance matrix.
* [DECISION_LOG.md](docs/product/DECISION_LOG.md) — Architecture Decision Records (ADR-001 through ADR-010).
* [BUSINESS_ASSUMPTIONS.md](docs/product/BUSINESS_ASSUMPTIONS.md) — Reconciled unit economics and revenue models.
* [SCREEN_REQUIREMENTS.md](docs/product/SCREEN_REQUIREMENTS.md) — UI/UX screen specifications and interactive state contracts.
* [REQUIREMENTS_TRACEABILITY.md](docs/product/REQUIREMENTS_TRACEABILITY.md) — Requirements traceability matrix from business goals to engineering tests.
* [OPEN_SOURCE_INTEGRATIONS.md](docs/product/OPEN_SOURCE_INTEGRATIONS.md) — Third-party OSS licensing and dependency audits.

### Quality Assurance & Audits
* [TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md) — Test matrix detailing 20 critical scenarios (`TS-01` to `TS-20`) with executable Python test harness code.
* [PRD_FINAL_AUDIT.md](docs/audits/PRD_FINAL_AUDIT.md) — Final readiness audit scoring 98/100 with Sprint 0/1 sign-off.
* [TECHNICAL_AUDIT.md](docs/audits/TECHNICAL_AUDIT.md) — Historical audit analysis resolving foundational V1.0/V2.0 defects.

---

## Status

* **Specification Maturity:** 10/10 Engineering Baseline.
* **Current Phase:** Sprint 0 Core Infrastructure & Data Layer Scaffolding.
