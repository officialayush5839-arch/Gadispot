# Gadispot (formerly SmartPark Exchange)

> **Mobile-First Real-Time Parking Marketplace for Urban India**  
> **Specification Baseline:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
> **Architecture:** In-Process Modular Monolith (FastAPI) + Single Cross-Platform Client (Flutter)  
> **Datastores:** PostgreSQL 16 + PostGIS 3.4 (Authoritative) & Redis 7+ (Ephemeral Cache)  
> **Initial Launch Market:** Bengaluru, Karnataka, India

---

## 1. Executive Summary & Overview

Gadispot is a high-concurrency, mobile-first parking marketplace platform operating in dense Indian metropolitan centers. The platform connects vehicle drivers seeking guaranteed, pre-booked parking with private property owners, residential society committees, and commercial lot operators possessing underutilized parking capacity.

The engineering foundation enforces mathematical zero double-booking exclusion at the database engine layer, balanced double-entry financial accounting with deadlock-free concurrency, separated cryptographic access passes, and resilient multi-stage Docker containerization.

---

## 2. System Architecture & Tech Stack

```
                              ┌──────────────────────────────────────────────┐
                              │           Single Flutter Client              │
                              │   (Driver | Space Owner | Guard | Ops)       │
                              └──────────────────────┬───────────────────────┘
                                                     │ HTTPS / WSS
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Gadispot Modular Monolith (Docker Container: gadispot_backend / Port 8000)                        │
│                                                                                                    │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────────────────────┐  │
│  │   FastAPI App Factory   │  │  Pydantic 2 Settings    │  │  Global Error Handler (RFC 7807)   │  │
│  │  & Lifespan Management  │  │  & Correlation ID X-Req │  │  Structured JSON Logging (Python)  │  │
│  └────────────┬────────────┘  └────────────┬────────────┘  └─────────────────┬──────────────────┘  │
│               │                            │                                 │                     │
│               ▼                            ▼                                 ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Domain Modules (Auth, Booking & Holds, Vehicle Compatibility, Ledger, Gate Access, Refunds)  │  │
│  └────────────────────────────┬─────────────────────────────┬───────────────────────────────────┘  │
│                               │                             │                                      │
│                               ▼                             ▼                                      │
│  ┌──────────────────────────────────────────────┐  ┌────────────────────────────────────────────┐  │
│  │ SQLAlchemy 2.x Async Engine & Alembic DDL    │  │ redis.asyncio Connection Pool              │  │
│  └──────────────────────┬───────────────────────┘  └─────────────────────┬──────────────────────┘  │
└─────────────────────────┼────────────────────────────────────────────────┼─────────────────────────┘
                          │                                                │
                          ▼ (Port 5432)                                    ▼ (Port 6379)
┌─────────────────────────────────────────────────┐      ┌───────────────────────────────────────────┐
│ PostgreSQL 16 + PostGIS 3.4 (gadispot_postgres) │      │ Redis 7 Alpine (gadispot_redis)           │
│  • GiST Temporal Exclusion Constraints          │      │  • Sliding-Window Rate Limiting           │
│  • PostGIS ST_DWithin Geospatial Radius Search  │      │  • Revoked JWT Blocklist (TTL Expired)    │
│  • Immutable Double-Entry Ledger Triggers       │      │  • Active Hold Presentation Counters      │
│  • Named Volume: gadispot_pgdata                │      │  • Named Volume: gadispot_redisdata       │
└─────────────────────────────────────────────────┘      └───────────────────────────────────────────┘
```

### Core Technology Stack:
- **Backend Framework:** Python 3.12, FastAPI 0.115+, Uvicorn (ASGI)
- **Data Validation & Settings:** Pydantic 2.10+, Pydantic Settings 2.6+
- **Database & Spatial:** PostgreSQL 16, PostGIS 3.4, SQLAlchemy 2.0+ (AsyncPG 0.30+)
- **Database Migrations:** Alembic 1.14+ (14 Declarative Models, 14 Postgres Enums)
- **Cache & Ephemeral Coordination:** Redis 7+ Alpine (`redis.asyncio` RESP2 protocol)
- **Mobile Client:** Flutter 3.19+ (Dart 3.3+) with Clean Architecture & Role Shells
- **Containerization:** Multi-stage Docker, Docker Compose v2+
- **Testing:** Pytest 8+, Pytest-Asyncio, HTTPX, PostGIS Live Container Suite

---

## 3. Core Architectural Invariants

1. **Mathematical Double-Booking Exclusion (PostgreSQL GiST):**
   Checkout holds lock intervals for strictly **480 seconds (8 minutes)** (`POL-HLD-01`). Overlapping active holds or confirmed bookings are physically rejected by a PostgreSQL GiST temporal exclusion constraint:
   ```sql
   CONSTRAINT prevent_overlapping_active_reservations
   EXCLUDE USING gist (
       parking_space_id WITH =,
       time_window WITH &&
   ) WHERE (status IN ('ACTIVE_HOLD', 'CONFIRMED', 'ACTIVE_SESSION', 'MAINTENANCE_BLOCK', 'OWNER_BLACKOUT'));
   ```
   *Redis is non-authoritative for booking correctness.*

2. **Double-Entry General Ledger & Deadlock-Free Zero Child Lock Protocol:**
   Every posted financial transaction strictly balances ($\sum \text{Debits} = \sum \text{Credits}$, $\ge 2$ lines) across a 9-account Chart of Accounts. The Zero Child Lock protocol eliminates deadlocks by validating balance via an MVCC snapshot on parent journals without row locks on children. Posted entries and lines are permanently immutable.

3. **Separated Dynamic QR Lifecycles:**
   - **Payment QR:** Generated by payment gateway/switch encoding NPCI UPI URI (`upi://pay?pa=...`) with 480-second TTL.
   - **Parking Access QR:** High-entropy 128-bit CSPRNG token minted by backend (`ENTRY_TOKEN` and `EXIT_TOKEN`). Scanned by guard app and atomically burned (`CONSUMED`). Zero financial PII exposed to guards.

4. **Durable Webhook Idempotency:**
   Webhook events are deduplicated via unique constraint `(gateway_name, gateway_event_id)` on `payment_webhook_events`. Duplicates return HTTP 200 without database side effects.

5. **DPDPA 7-Day Gate Photo Data Minimization:**
   Offline admission photos in basement cellular dead zones are stored in private S3 buckets and permanently purged by lifecycle policies after 7 days, preserving only the immutable SHA-256 audit hash.

---

## 4. Prerequisites

Before running Gadispot locally, ensure your host system satisfies:

| Dependency | Minimum Version | Verification Command | Notes |
|---|---|---|---|
| **Docker Engine** | 24.0.0+ | `docker --version` | Required for containerized runtime |
| **Docker Compose** | 2.20.0+ | `docker compose version` | Docker Compose v2 plugin |
| **Python** | 3.11 or 3.12 | `python --version` | Required for local test suites & tooling |
| **pip** | 23.0+ | `pip --version` | Python package installer |
| **Flutter** | 3.19+ | `flutter --version` | Optional; required only for mobile client development |

---

## 5. Quickstart: One-Command Developer Environment

Gadispot provides automated one-command startup and teardown scripts that handle configuration initialization, container compilation, readiness polling, and database migration execution.

### On Linux / macOS (POSIX):
```bash
# 1. Clone repository
git clone https://github.com/officialayush5839-arch/Gadispot.git
cd Gadispot

# 2. Start all services and run migrations
chmod +x scripts/dev_up.sh scripts/dev_down.sh
./scripts/dev_up.sh
```

### On Windows (PowerShell):
```powershell
# 1. Clone repository
git clone https://github.com/officialayush5839-arch/Gadispot.git
cd Gadispot

# 2. Start all services and run migrations
.\scripts\dev_up.ps1
```

### What `dev_up` Automates:
1. Detects `.env` configuration; automatically copies `.env.example` to `.env` if not present.
2. Builds the multi-stage backend image and starts `postgres` (PostGIS 16-3.4), `redis` (7-alpine), and `backend` (FastAPI).
3. Polls the backend readiness probe (`http://localhost:8000/health/ready`) until PostgreSQL and Redis report `UP`.
4. Executes latest database migrations via `docker compose exec backend alembic upgrade head`.
5. Outputs a live dashboard banner with interactive API endpoints and connection credentials.

### Stopping the Stack:
```bash
# Graceful shutdown (preserves persistent database volumes)
./scripts/dev_down.sh           # Linux/macOS
.\scripts\dev_down.ps1          # Windows

# Complete teardown and clean database reset (wipes gadispot_pgdata volume)
./scripts/dev_down.sh -v        # Linux/macOS
.\scripts\dev_down.ps1 -Volumes # Windows
```

---

## 6. Manual Local Setup (Without Docker)

If you prefer running PostgreSQL, Redis, and FastAPI directly on your local workstation without Docker:

### 1. Configure Python Virtual Environment:
```bash
python -m venv .venv

# Activate on Linux/macOS:
source .venv/bin/activate

# Activate on Windows:
.\.venv\Scripts\Activate.ps1

# Install backend dependencies and test tools
pip install -r requirements.txt
pip install -r requirements-test.txt
pip install -e backend/
```

### 2. Configure Environment:
```bash
cp .env.example .env
```
Ensure your local PostgreSQL 16 (with PostGIS extension) and Redis 7 are running and adjust `DATABASE_URL` and `REDIS_URL` in `.env` if needed:
```ini
DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/gadispot"
REDIS_URL="redis://127.0.0.1:6379/0"
```

### 3. Run Database Migrations:
```bash
cd backend
alembic upgrade head
cd ..
```

### 4. Start FastAPI ASGI Server:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 7. Database Migrations & Alembic Workflows

All database schema definition derives strictly from version-controlled Alembic migrations located in `backend/alembic/versions/`. Hand-written ad-hoc DDL strings in application code or tests are strictly prohibited.

| Command | Action |
|---|---|
| `alembic upgrade head` | Apply all pending migrations to the database |
| `alembic downgrade -1` | Roll back the single most recent migration |
| `alembic current` | Display the current applied revision hash |
| `alembic history --verbose` | Inspect complete migration history and lineage |
| `alembic revision --autogenerate -m "description"` | Generate new migration from SQLAlchemy models |

*When running inside Docker, execute migrations via:*
```bash
docker compose exec backend alembic upgrade head
```

---

## 8. Running Automated Test & Quality Suites

Gadispot maintains a strict test hierarchy covering database constraints, API endpoints, mobile clean architecture, specification harmonization, and infrastructure validation:

```bash
# 1. Run Backend Database & API Integration Pytest Suite (83/83 passing)
pytest tests/ -v

# 2. Run Document Harmonization & Markdown Link Integrity Suite
python scripts/validate_spec.py

# 3. Run Mobile Architecture, Anti-Slop & Spec Verification Suite
python scripts/validate_mobile_spec.py

# 4. Run Docker & Local Infrastructure Specification Suite
python scripts/validate_docker_spec.py
```

### Automated Test Coverage Highlights:
- **GiST Temporal Exclusion:** Verifies non-overlapping reservations succeed while overlapping active holds on the same bay raise exclusion violations.
- **Ledger Immutability & Balance:** Confirms balanced double-entry transactions post cleanly while unbalanced journals, single-line journals, or mutations to posted journals are blocked.
- **Deadlock Freedom:** Multi-worker concurrent posting tests confirm zero deadlocks under high volume.
- **RFC 7807 Problem Details:** All API exceptions and 404/422 errors return compliant Problem Details responses.
- **Cluster Health Probes:** Validates `/health/live` and `/health/ready` under simulated PostgreSQL/Redis availability and failure conditions.

---

## 9. API & Health Endpoints Reference

Once the stack is running on `http://localhost:8000`, the following diagnostic and operational endpoints are available:

| Endpoint | Method | Purpose | Response Format |
|---|---|---|---|
| `/health/live` | `GET` | Container / Kubernetes Liveness Probe | `{"status": "ALIVE", "timestamp": "..."}` |
| `/health/ready` | `GET` | Readiness Probe (Pings PostgreSQL & Redis) | `{"status": "READY", "checks": {"database": "UP", "redis": "UP"}}` |
| `/api/v1/health` | `GET` | Subsystem Health & Version Diagnostic | `{"status": "HEALTHY", "version": "2.3.0", "subsystems": {...}}` |
| `/docs` | `GET` | Interactive Swagger UI (OpenAPI 3.1) | Interactive Web Interface |
| `/redoc` | `GET` | ReDoc API Specification Reader | Interactive Web Interface |
| `/api/v1/openapi.json` | `GET` | Machine-Readable OpenAPI 3.1 JSON | OpenAPI 3.1 JSON Schema |

---

## 10. Troubleshooting & Common Issues

### Issue 1: Port Conflict on 5432 or 6379
- **Symptom:** `Bind for 0.0.0.0:5432 failed: port is already allocated`.
- **Cause:** A local PostgreSQL or Redis instance is already running on the host machine.
- **Resolution:** Stop host services (`sudo systemctl stop postgresql` / `net stop postgresql-x64-16`) or modify the host binding port in `docker-compose.yml` (e.g. `"5433:5432"`).

### Issue 2: Docker Daemon Not Running
- **Symptom:** `failed to connect to the docker API at npipe://...` or `Is the docker daemon running?`.
- **Cause:** Docker Desktop or the system Docker service has not been started.
- **Resolution:** Launch Docker Desktop from the Start menu / Applications, wait for the engine to initialize, and re-run `scripts/dev_up.ps1` or `scripts/dev_up.sh`.

### Issue 3: Backend Waiting for Readiness Timeout
- **Symptom:** `dev_up` times out after 30 attempts waiting for `/health/ready`.
- **Cause:** PostgreSQL or Redis container failed healthcheck during initialization.
- **Resolution:** Run `docker compose ps` to inspect service status, followed by `docker compose logs postgres` and `docker compose logs backend` to inspect database connection logs.

### Issue 4: Corrupted Database State / Dirty Migrations
- **Symptom:** Migration errors or constraint mismatch after modifying local models.
- **Resolution:** Perform a clean reset by tearing down containers and purging persistent data volumes:
  ```bash
  ./scripts/dev_down.sh -v          # POSIX
  .\scripts\dev_down.ps1 -Volumes   # PowerShell
  ```
  Then re-launch via `dev_up`.

---

## 11. Authoritative Documentation Suite

| Document | Path | Purpose |
|---|---|---|
| **Master Product Specification** | [PRD.md](PRD.md) | Authoritative 50-section PRD (V2.3.2) |
| **Engineering Baseline** | [PROJECT.md](PROJECT.md) | Architectural invariants, milestones, interface contracts |
| **Implementation Task Tracker** | [IMPLEMENTATION_TASK_TRACKER.md](docs/engineering/IMPLEMENTATION_TASK_TRACKER.md) | 11-phase end-to-end task roadmap |
| **Implementation Readiness Report** | [IMPLEMENTATION_READINESS_REPORT.md](docs/engineering/IMPLEMENTATION_READINESS_REPORT.md) | Empirical readiness audit and maturity scores |
| **Architecture Decision Log** | [DECISION_LOG.md](docs/engineering/DECISION_LOG.md) | ADR repository (ADR-001..010, FD-01..05) |
| **Requirements Traceability Matrix** | [TRACEABILITY_MATRIX.md](docs/engineering/TRACEABILITY_MATRIX.md) | PRD requirement mapping (`FR-AUTH-001` to `FR-GPRP-001`) |
| **Open-Source Dependency Register** | [OPEN_SOURCE_DEPENDENCY_REGISTER.md](docs/engineering/OPEN_SOURCE_DEPENDENCY_REGISTER.md) | Third-party OSS licensing and architecture audit |
| **Database Blueprint** | [DATABASE_DESIGN.md](docs/technical/DATABASE_DESIGN.md) | Complete PostgreSQL DDL, PostGIS queries, triggers |
| **Booking & Availability Design** | [BOOKING_AND_AVAILABILITY_DESIGN.md](docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md) | MSAI 7-signal engine, 480s hold lifecycle, LPRP |
| **Payment & Ledger Design** | [PAYMENT_AND_LEDGER_DESIGN.md](docs/technical/PAYMENT_AND_LEDGER_DESIGN.md) | Double-entry accounting, webhooks, 6-stage refunds |
| **QR & Cyber-Physical Access** | [QR_ACCESS_DESIGN.md](docs/technical/QR_ACCESS_DESIGN.md) | 128-bit CSPRNG passes, guard gate scanner, offline audit |
| **RESTful API Specification** | [API_SPECIFICATION.md](docs/technical/API_SPECIFICATION.md) | Endpoints, RFC 7807 problem details, idempotency headers |
| **System Architecture Topology** | [ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) | System boundaries, sequence diagrams, deployment topology |
| **Founder Decision Checklist** | [FOUNDER_DECISION_CHECKLIST.md](docs/product/FOUNDER_DECISION_CHECKLIST.md) | Executive signoff register separating commercial defaults |
| **User Flows & Journeys** | [USER_FLOWS.md](docs/product/USER_FLOWS.md) | Sequence and state transition diagrams |
| **Open Questions Register** | [OPEN_QUESTIONS.md](docs/product/OPEN_QUESTIONS.md) | 65-question Decision Register (`DEC-01` to `DEC-65`) |
| **Security & Privacy Review** | [SECURITY_AND_PRIVACY_REVIEW.md](docs/product/SECURITY_AND_PRIVACY_REVIEW.md) | STRIDE threat model & DPDPA 2023 compliance matrix |
| **Quality & Test Strategy** | [TEST_STRATEGY.md](docs/quality/TEST_STRATEGY.md) | 20 core test scenarios (`TS-01` to `TS-20`) |
| **Final V2.3.2 Audit Report** | [V2_3_2_FINAL_AUDIT.md](docs/audits/V2_3_2_FINAL_AUDIT.md) | Verified audit with live PostgreSQL 16 test logs |

---

## 12. Governance & License

- **Repository:** `officialayush5839-arch/Gadispot`
- **Specification Status:** `PRD-GSP-2026-V2.3.2-VERIFIED` (Phase 4 Local Infrastructure Complete)
- **Copyright:** © 2026 Gadispot Engineering Team. All rights reserved.
