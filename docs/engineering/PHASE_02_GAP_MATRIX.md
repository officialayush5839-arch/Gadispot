# Gadispot Phase 02 IAM Gap Matrix & Specification Register
## Identity, Authentication, Authorization & Role-Based Access Control

> **Document Identifier:** MATRIX-GSP-2026-PHASE-02-GAP-ANALYSIS-VERIFIED  
> **Document Title:** Phase 02 — Requirements R1–R8 & Acceptance Gates 1–8 Traceability & Gap Matrix  
> **Governing Baseline:** Master PRD V2.3.2-VERIFIED ([PRD.md](../../PRD.md)), Engineering Rules ([rules.md](../../rules.md)), Master Architecture ([architecture.md](../../architecture.md)), Master 15-Phase Strategic Roadmap ([phases.md](../../phases.md)), Master Backlog ([task.md](../../task.md)), Engineering Baseline ([PROJECT.md](../../PROJECT.md))  
> **Companion Discovery Report:** Phase 02 Discovery Report ([PHASE_02_IAM_DISCOVERY_REPORT.md](PHASE_02_IAM_DISCOVERY_REPORT.md))  
> **Target Pilot Geography:** Bengaluru Urban Metro, Karnataka, India (Koramangala, Indiranagar, HSR Layout — 200 Pilot Bays)  
> **Target Execution Platforms:** Mobile-Only (Single Cross-Platform Flutter Mobile Binary for Android & iOS)  
> **Backend Architecture:** In-Process Modular Monolith (Python 3.12 / FastAPI / PostgreSQL 16 + PostGIS / Redis 7.0+)  
> **Author:** Worker Stage 0 (`teamwork_worker`)  
> **Date of Evaluation:** November 6, 2026  
> **Integrity Mode:** Read-Only Audit & Traceability Synthesis  

---

## 1. Executive Summary

This document establishes the canonical **Requirements Traceability and Architectural Gap Matrix** for **Phase 02 (Identity, Authentication, Authorization & Role-Based Access Control)** of the Gadispot platform. It bridges the authoritative product specifications ([PRD.md](../../PRD.md), [phases.md](../../phases.md), [task.md](../../task.md), [PROJECT.md](../../PROJECT.md)) and the existing Phase 01 baseline codebase.

### Gate Evaluation Summary

| Acceptance Gate | Gate Focus | Baseline Status | Total Gaps | Critical | High | Medium | Low |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Gate 1** | Architecture & Baseline Integrity | **PASS** | 2 | 0 | 0 | 1 | 1 |
| **Gate 2** | Identity & Account Model Uniqueness | **FAIL** | 4 | 1 | 2 | 1 | 0 |
| **Gate 3** | Server-Side Firebase Authentication | **WARN** | 3 | 0 | 1 | 2 | 0 |
| **Gate 4** | Session Lifecycle, Rotation & Logout | **FAIL** | 4 | 2 | 2 | 0 | 0 |
| **Gate 5** | Server-Side Authorization & IDOR Shield | **FAIL** | 5 | 2 | 2 | 1 | 0 |
| **Gate 6** | Abuse Protection, Rate Limiting & Audit | **FAIL** | 5 | 2 | 2 | 1 | 0 |
| **Gate 7** | Database Migrations & Security Testing | **PENDING** | 4 | 1 | 2 | 1 | 0 |
| **Gate 8** | CI/CD Quality Pipeline & Documentation | **PENDING** | 3 | 0 | 1 | 2 | 0 |
| **Total** | | | **30** | **8** | **12** | **9** | **1** |

---

## 2. Requirement-by-Requirement Gap Matrix (R1–R8 vs Gates 1–8)

The table below catalogs every identified architectural, implementation, security, or configuration gap across Requirements R1 through R8 and Acceptance Gates 1 through 8.

| Gap ID | Req | Gate | Target File(s) | Current Implementation State | Required Phase 02 State | Severity | Stage Assignment |
|---|:---:|:---:|---|---|---|:---:|:---:|
| **GAP-01** | R1 | Gate 1 | `tests/` vs `backend/tests/` | Documentation mentions `backend/tests/`, but tests reside at repository root `tests/`. | Standardize on root `tests/` as the single authoritative test suite path across all docs. | Low | Stage 0 |
| **GAP-02** | R1 | Gate 1 | `mobile/lib/core/constants/api_endpoints.dart` | References `/api/v1/auth/firebase-exchange`, while backend router registers `/api/v1/auth/session`. | Reconcile endpoint constant to `/api/v1/auth/session`; add `/api/v1/auth/firebase-exchange` alias in backend. | Medium | Stage 0 / Stage 2 |
| **GAP-03** | R2 | Gate 2 | `backend/app/models/users.py` | `User` model lacks `firebase_uid` column. Token verification discards UID. | Add `firebase_uid = mapped_column(String(128), unique=True, index=True, nullable=True)`. | **High** | Stage 1 |
| **GAP-04** | R2 | Gate 2 | `backend/app/models/users.py`, `backend/app/models/enums.py` | `User` model relies on boolean `is_active`. Lacks account status enum. | Add `UserStatusEnum` (`ACTIVE`, `SUSPENDED`, `DISABLED`) and column `status` on `users` table. | **High** | Stage 1 |
| **GAP-05** | R2 | Gate 2 | `backend/app/services/auth_service.py` | Registration performs uncoordinated `SELECT` then `INSERT`, causing `IntegrityError` crashes on concurrency. | Implement PostgreSQL atomic UPSERT (`ON CONFLICT (phone_number) DO UPDATE/NOTHING`) or catch `IntegrityError`. | **Critical** | Stage 1 |
| **GAP-06** | R2 | Gate 2 | `backend/app/services/auth_service.py` | Default registration only provisions `DRIVER` role; lacks secure multi-role assignment. | Maintain `DRIVER` as immutable default for public registration; support administrative role grants. | Medium | Stage 1 |
| **GAP-07** | R3 | Gate 3 | `backend/app/services/auth_service.py` | `_init_firebase()` only checks `settings.FIREBASE_PROJECT_ID` with `ApplicationDefault()`. | Support `FIREBASE_CREDENTIALS_PATH` via `credentials.Certificate(path)` for service accounts. | Medium | Stage 2 |
| **GAP-08** | R3 | Gate 3 | `backend/app/services/auth_service.py` | Dev/test token verification accepts mock prefix `test-token-*` without strict environment check. | Guard mock token acceptance strictly behind `settings.ENVIRONMENT in ("development", "test")`. | Medium | Stage 2 |
| **GAP-09** | R3 | Gate 3 | `backend/app/api/v1/endpoints/auth.py` | Public session endpoint lacks client device metadata and IP capture. | Capture client IP, User-Agent, and optional device fingerprint during token exchange. | Low | Stage 2 |
| **GAP-10** | R3 | Gate 4 | `backend/app/models/users.py` | No database table or model exists for tracking active sessions or refresh tokens. | Create `UserSession` model with `id`, `user_id`, `refresh_token_hash`, `family_id`, `expires_at`, `is_revoked`. | **Critical** | Stage 1 / Stage 2 |
| **GAP-11** | R3 | Gate 4 | `backend/app/services/auth_service.py` | `refresh_session_tokens` re-returns the exact same refresh token (no rotation). | Issue fresh access token AND new rotating refresh token; invalidate old token in `user_sessions`. | **Critical** | Stage 2 |
| **GAP-12** | R3 | Gate 4 | `backend/app/services/auth_service.py` | No token reuse detection mechanism. Stolen refresh token replay is undetected. | Track cryptographic `family_id`; revoke entire session family immediately if a consumed token is replayed. | **High** | Stage 2 |
| **GAP-13** | R3 | Gate 4 | `backend/app/api/v1/endpoints/auth.py` | No `/api/v1/auth/logout` or `/api/v1/auth/me` endpoints exist in the backend. | Implement `POST /auth/logout` (revokes session/token in DB & Redis) and `GET /auth/me` (returns user profile). | **High** | Stage 2 |
| **GAP-14** | R4 | Gate 5 | `backend/app/api/v1/endpoints/bookings.py` | `GET /bookings/{reservation_id}` has no auth dependency or IDOR check. | Inject `get_current_user` and `verify_resource_ownership(user, reservation.driver_id)`. | **Critical** | Stage 3 |
| **GAP-15** | R4 | Gate 5 | `backend/app/api/v1/endpoints/access.py` | `POST /access/issue-tokens` has no auth dependency. Anyone can mint access passes. | Require `get_current_user` and verify caller is the reservation's confirmed driver. | **Critical** | Stage 3 |
| **GAP-16** | R4 | Gate 5 | `backend/app/api/v1/endpoints/access.py` | `POST /access/validate-scan` trusts client-supplied `guard_id` without role check. | Require `require_roles(UserRoleEnum.GUARD)` and derive guard ID strictly from `current_user.id`. | **High** | Stage 3 |
| **GAP-17** | R4 | Gate 5 | `backend/app/api/v1/endpoints/payments.py` | `POST /payments/refund/request` lacks auth dependency and resource ownership check. | Require `get_current_user` and verify reservation ownership or privileged `OPERATIONS` role. | **High** | Stage 3 |
| **GAP-18** | R4 | Gate 5 | `backend/app/api/v1/endpoints/payments.py` | `POST /payments/payouts/simulate` has `get_current_user` but lacks role dependency. | Inject `require_roles(UserRoleEnum.OPERATIONS, UserRoleEnum.ADMIN)`. | Medium | Stage 3 |
| **GAP-19** | R5 | Gate 6 | `backend/app/core/rate_limiter.py` | Blind fail-open (`return False, 0, 0`) on all Redis exceptions in `SlidingWindowRateLimiter`. | Implement `fail_closed: bool = True` on auth endpoints; fall back to in-memory sliding window or HTTP 503. | **Critical** | Stage 4 |
| **GAP-20** | R5 | Gate 6 | `backend/app/api/v1/endpoints/auth.py` | `login_rate_limiter` and `otp_rate_limiter` are unattached to auth endpoints. | Attach rate limiters as FastAPI dependencies to `/auth/session` and 2FA endpoints. | **High** | Stage 4 |
| **GAP-21** | R5 | Gate 6 | `backend/app/services/auth_service.py` | Auth error messages differentiate between unverified tokens, inactive users, and non-existent users. | Standardize external responses to eliminate account enumeration (uniform HTTP 401 Problem Details). | Medium | Stage 4 |
| **GAP-22** | R5 | Gate 6 | `backend/app/services/audit_service.py` | `AuditService.log_event` is never called across auth or security operations. | Emit structured security audit events on login, refresh, logout, 2FA, and IDOR violations. | **High** | Stage 4 |
| **GAP-23** | R5 | Gate 6 | `backend/app/core/logging.py` | Logging filter must guarantee zero plaintext secrets, OTPs, or customer PII in logs. | Verify and enforce `SensitiveDataFilter` scrubbing; mask phone numbers (`+91 98*** **345`). | Medium | Stage 4 |
| **GAP-24** | R6 | Gate 6 | `mobile/lib/features/auth/presentation/otp_view.dart` | Insecure client role dropdown allows users to self-assign `Operations` or `Guard` shells. | Eliminate client-side role dropdown; route shells strictly based on server-verified `roles` array. | **Critical** | Stage 6 |
| **GAP-25** | R6 | Gate 6 | `mobile/lib/core/network/api_client.dart` | Dio client lacks automatic 401 token refresh interceptor. Requests fail with raw 401. | Implement `RefreshTokenInterceptor` with request mutex queuing, storage update, and retry. | **High** | Stage 6 |
| **GAP-26** | R6 | Gate 6 | `mobile/lib/main.dart` | App boots unconditionally to `LoginView`, ignoring tokens in `SecureStorageService`. | Implement session restoration on startup; navigate directly to active role shell if session is valid. | **High** | Stage 6 |
| **GAP-27** | R6 | Gate 6 | `mobile/lib/` | Missing `RoleSwitcher` widget specified in `PROJECT.md` line 49. | Author `RoleSwitcher` widget allowing Driver/Owner users to switch active viewport dynamically. | Medium | Stage 6 |
| **GAP-28** | R7 | Gate 7 | `backend/alembic/versions/` | Alembic lineage at head `003_demo_payments`; lacks Phase 02 IAM schema changes. | Create `004_identity_and_sessions.py` adding `firebase_uid`, `status`, and `user_sessions`. | **High** | Stage 1 / Stage 7 |
| **GAP-29** | R7 | Gate 7 | `tests/` | Test suite lacks automated tests for token rotation, reuse detection, and Redis fail-closed. | Implement comprehensive automated tests covering concurrency races, rotation, IDOR, and audit trails. | **Critical** | Stage 7 |
| **GAP-30** | R8 | Gate 8 | `docs/engineering/` | Missing Threat Model, Role-Permission Matrix, and `PHASE_02_IMPLEMENTATION_REPORT.md`. | Author documentation deliverables and verify remote GitHub Actions CI pipeline passes 100% green. | Medium | Stage 9 / Stage 10 |

---

## 3. Comprehensive Role-Permission Matrix

The platform enforces strict Role-Based Access Control (RBAC) across five roles: four operational roles (`DRIVER`, `SPACE_OWNER`, `SECURITY_GUARD`, `OPERATIONS`) plus administrative superuser (`ADMIN`).

### 3.1 Role Hierarchy & System Identifiers

| Role Identifier | Database Enum | Principal Scope | Target Screen Shell | Operational Mandate |
|---|---|---|---|---|
| **`DRIVER`** | `UserRoleEnum.DRIVER` | Registered vehicle driver | `DriverShell` (`SCR-101..107`) | Search parking spaces, create 480s holds, pay via UPI, manage personal vehicles, present QR access passes, request extensions. |
| **`SPACE_OWNER`** | `UserRoleEnum.OWNER` | Host / Property Owner | `OwnerShell` (`SCR-201..205`) | Onboard parking properties, define bay dimensions, set recurring operating schedules, trigger emergency blackouts, view earnings. |
| **`SECURITY_GUARD`** | `UserRoleEnum.GUARD` | On-site Gate Security Guard | `GuardShell` (`SCR-301..304`) | Scan entry/exit QR codes, verify assigned property binding, execute offline manual admissions with 7-day photo proof, report obstructions. |
| **`OPERATIONS`** | `UserRoleEnum.OPERATIONS` | Internal Platform Operations | `OpsShell` (`SCR-401..402`) | Review property deeds via presigned URLs, approve/reject listings with 2FA, resolve GPRP disputes, trigger manual batch payouts. |
| **`ADMIN`** | `UserRoleEnum.ADMIN` | System Administrator / Engineering Lead | Backend CLI / API | System configuration, database migrations, security parameters, system-wide overrides. Supersedes non-financial restrictions. |

### 3.2 Granular Permissions Matrix Across All Endpoints

| Functional Area | HTTP Route / Action | Allowed Roles | Prohibited Roles | Authorization Boundary & IDOR Invariant |
|---|---|---|---|---|
| **Auth** | `POST /api/v1/auth/session` | Public | None | Unauthenticated phone token exchange. Provisions strictly `DRIVER` role. |
| **Auth** | `POST /api/v1/auth/refresh` | Authenticated | None | Validates rotating refresh token and checks Redis revocation blocklist. |
| **Auth** | `POST /api/v1/auth/logout` | Authenticated | None | Revokes active session and adds token `jti` to Redis blocklist. |
| **Auth** | `GET /api/v1/auth/me` | Authenticated | None | Returns authenticated principal's profile, roles, and account status. |
| **Auth** | `POST /api/v1/auth/switch-role` | `DRIVER`, `OWNER` | `GUARD`, `OPERATIONS` | Toggles viewport between Driver and Owner; user must hold target role in `user_roles`. |
| **Auth** | `POST /api/v1/auth/2fa/setup` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Privileged staff only; generates RFC 6238 TOTP provisioning secret and QR. |
| **Auth** | `POST /api/v1/auth/2fa/verify` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Privileged staff only; verifies 6-digit TOTP code before sensitive operations. |
| **Search** | `POST /api/v1/spaces/search` | `DRIVER`, Public | None | PostGIS spatial radius search (3km default, 5km max). Rate-limited (60/min). |
| **Bookings** | `POST /api/v1/bookings/hold` | `DRIVER` | `OWNER`, `GUARD`, `OPERATIONS` | Driver-only; max 2 concurrent active holds; enforced 480-second TTL. |
| **Bookings** | `GET /api/v1/bookings/{id}` | `DRIVER`, `OPERATIONS`, `ADMIN` | `OWNER`, `GUARD` | **IDOR Check:** Driver must match `reservation.driver_id`. Operations/Admin bypass. |
| **Bookings** | `POST /api/v1/bookings/{id}/extend` | `DRIVER` | `OWNER`, `GUARD`, `OPERATIONS` | **IDOR Check:** Driver must match `reservation.driver_id`; max 2 extensions. |
| **Vehicles** | `POST /api/v1/vehicles` | `DRIVER` | None | Manage driver personal vehicles; validates Indian license plate regex. |
| **Vehicles** | `GET /api/v1/vehicles` | `DRIVER` | None | Returns vehicles where `driver_id == current_user.id`. |
| **Properties** | `POST /api/v1/properties` | `OWNER`, `ADMIN` | `DRIVER`, `GUARD` | Host onboarding; creates property in `DRAFT` status bound to `owner_id`. |
| **Properties** | `POST /api/v1/properties/{id}/spaces` | `OWNER` | `DRIVER`, `GUARD` | **IDOR Check:** Host must match `property.owner_id`. |
| **Properties** | `POST /api/v1/properties/{id}/schedules`| `OWNER` | `DRIVER`, `GUARD` | **IDOR Check:** Host must match `property.owner_id`. |
| **Spaces** | `POST /api/v1/spaces/{id}/blackout` | `OWNER` | `DRIVER`, `GUARD` | **IDOR Check:** Host must own space; cannot override confirmed bookings. |
| **Earnings** | `GET /api/v1/owner/earnings` | `OWNER` | `DRIVER`, `GUARD` | Returns host ledger balance and payout history for `current_user.id`. |
| **Access QR** | `POST /api/v1/access/issue-tokens` | `DRIVER` | `OWNER`, `GUARD`, `OPERATIONS` | **IDOR Check:** Driver must match `reservation.driver_id`; booking must be confirmed. |
| **Gate Scan** | `POST /api/v1/access/validate-scan` | `GUARD`, `ADMIN` | `DRIVER`, `OWNER` | **Property Binding:** Guard `token.property_id` must match `reservation.property_id`. |
| **Gate Shift** | `GET /api/v1/access/shift-schedule` | `GUARD` | `DRIVER`, `OWNER` | Returns cached 8-hour shift schedule for guard's assigned property. |
| **Admission** | `POST /api/v1/access/manual-admission` | `GUARD` | `DRIVER`, `OWNER` | Offline admission; requires vehicle plate and photo audit hash (7-day S3 purge). |
| **Obstruction**| `POST /api/v1/access/report-obstruction`| `GUARD` | `DRIVER`, `OWNER` | Reports bay obstructed; immediately suppresses bay from MSAI availability. |
| **Payments** | `POST /api/v1/payments/create-order` | `DRIVER` | None | Initiates payment order for active hold owned by caller. |
| **Payments** | `POST /api/v1/payments/generate-upi-qr` | `DRIVER` | None | Generates NPCI dynamic UPI QR for active hold owned by caller. |
| **Payments** | `POST /api/v1/payments/refund/request` | `DRIVER`, `OPERATIONS` | `OWNER`, `GUARD` | **IDOR Check:** Caller must own reservation or possess `OPERATIONS` role. |
| **Webhooks** | `POST /api/v1/webhooks/{gateway}` | Gateway / Public | None | Verified via raw HMAC-SHA256 signature; deduplicated by `gateway_event_id`. |
| **Admin** | `GET /api/v1/admin/properties/queue` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Review pending property listings and deed documents via presigned URLs. |
| **Admin** | `POST /api/v1/admin/properties/{id}/approve` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Requires valid 2FA TOTP code; transitions property to `APPROVED`. |
| **Admin** | `POST /api/v1/admin/properties/{id}/reject` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Requires valid 2FA TOTP code; logs structured rejection reason. |
| **Admin** | `POST /api/v1/admin/payouts/batch` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Requires 2FA; triggers batch bank payout run for balances $\ge ₹500$. |
| **Audit Logs**| `GET /api/v1/admin/audit-logs` | `OPERATIONS`, `ADMIN` | `DRIVER`, `OWNER`, `GUARD` | Reads immutable security audit log trail. |

---

## 4. Token & Session Lifecycle Specification Table

### 4.1 Token Specification Comparison

| Token Type | Issuing Authority | Signing Algorithm | Secret / Key Source | Lifespan / TTL | Storage Location (Server) | Storage Location (Mobile) | Mandatory Claims / Payload |
|---|---|---|---|:---:|---|---|---|
| **Firebase ID Token** | Google Firebase Identity Platform | RS256 | Google Public Key Certificates | 60 minutes (3600s) | Stateless (never persisted) | Ephemeral in Firebase Auth SDK | `iss`, `aud`, `sub` (UID), `exp`, `iat`, `phone_number` |
| **Internal Access Token** | Gadispot FastAPI Modular Monolith | HS256 | `settings.SECRET_KEY` | **60 minutes** (3600s) | Stateless (verified via signature + Redis blocklist) | Hardware Keystore (`FlutterSecureStorage`) | `sub` (UUID), `phone_number`, `role`, `roles`, `jti`, `iat`, `exp`, `type="access"` |
| **Internal Refresh Token** | Gadispot FastAPI Modular Monolith | HS256 | `settings.SECRET_KEY` | **30 days** (2,592,000s) | SHA-256 hash in `user_sessions` table | Hardware Keystore (`FlutterSecureStorage`) | `sub` (UUID), `roles`, `jti`, `iat`, `exp`, `type="refresh"`, `family_id` |
| **Session Record** | Gadispot PostgreSQL Database | N/A (Database Row) | PostgreSQL Engine | 30 days | Persisted in `user_sessions` | N/A | `id`, `user_id`, `refresh_token_hash`, `family_id`, `is_revoked`, `expires_at` |

### 4.2 Token Rotation & Reuse Detection Algorithm

```
Mobile Client                  FastAPI Backend                 PostgreSQL / Redis
      |                               |                                |
      |--- POST /auth/refresh ------->|                                |
      |    (refresh_token)            |                                |
      |                               |--- Compute SHA-256 Hash ------>|
      |                               |--- Query user_sessions ------->|
      |                               |<-- Return Session Record ------|
      |                               |                                |
      |                        [Is Token Revoked?]                     |
      |                        /                 \                     |
      |                     (YES)               (NO)                   |
      |                      /                     \                   |
      |         [REUSE DETECTED!]             [VALID REFRESH]          |
      |         - Revoke entire family        - Mark old token revoked |
      |         - Add family to Redis block   - Mint new Access JWT    |
      |         - Log critical audit event    - Mint new Refresh JWT   |
      |         - Return HTTP 401             - Insert new session row |
      |                                       - Return TokenResponse   |
      |                                                |               |
      |<-- HTTP 401 (FORCE LOGIN) ---------------------|               |
      |<-- HTTP 200 (NEW TOKENS) ----------------------|               |
```

1. **Rotation on Use:** Every call to `POST /api/v1/auth/refresh` invalidates the submitted refresh token in `user_sessions` (`is_revoked = True`) and issues a new access token and new refresh token under the same `family_id`.
2. **Reuse Detection:** If an incoming refresh token's SHA-256 hash matches a session record where `is_revoked == True`, a token replay or interception is detected:
   - The backend immediately executes:
     ```sql
     UPDATE user_sessions SET is_revoked = TRUE WHERE family_id = :family_id;
     ```
   - All active tokens for the family are added to Redis revocation keys (`jwt:family:revoked:{family_id}`).
   - An immutable security audit log `AUTH_TOKEN_REUSE_DETECTED` is emitted.
   - The endpoint returns HTTP 401 `TOKEN_REVOKED`, forcing full phone OTP re-authentication on the mobile client.
3. **Explicit Logout:** Calling `POST /api/v1/auth/logout` sets `is_revoked = True` for the session and pushes the access token's `jti` to Redis key `jwt:blocklist:{jti}` with TTL matching the remaining token lifetime.

---

## 5. Abuse Protection, Rate Limiting & Redis Failure Mode

### 5.1 Authentication-Specific Rate Limiting Policies

| Protected Route | Protected Action | Rate Limit Quota | Sliding Window | Cache Key Pattern | Action on Limit Exceeded |
|---|---|:---:|:---:|---|---|
| `POST /api/v1/auth/session` | Phone Token Exchange / Login | 5 requests | 15 minutes (900s) | `ratelimit:login:{ip_or_phone}` | HTTP 429 `RATE_LIMIT_EXCEEDED` + `Retry-After` header |
| `POST /api/v1/auth/refresh` | Token Refresh | 10 requests | 1 minute (60s) | `ratelimit:refresh:{user_id}` | HTTP 429 `RATE_LIMIT_EXCEEDED` |
| `POST /api/v1/auth/2fa/verify` | Operations 2FA Verification | 3 attempts | 5 minutes window | `ratelimit:2fa:{user_id}` | HTTP 429 + lockout + Security Audit Event |
| `POST /api/v1/bookings/hold` | 480s Hold Reservation Creation | 5 attempts | 30 minutes (1800s) | `ratelimit:hold:{user_id}` | HTTP 429 + enforce max 2 active concurrent holds |
| `POST /api/v1/spaces/search` | Spatial PostGIS Discovery | 60 queries | 1 minute (60s) | `ratelimit:search:{ip_or_user}` | HTTP 429 `RATE_LIMIT_EXCEEDED` |

### 5.2 Redis Failure Policy: Fail-Closed vs Fail-Safe Decision Matrix

```
+---------------------------------------------------------------------------------------------------------+
|                                    REDIS FAILURE DECISION MATRIX                                        |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Subsystem / Endpoint     | Criticality           | Failure Policy      | Rationale & Mitigation         |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Phone Token Exchange     | Critical Security     | **FAIL-CLOSED**     | Failing open exposes system    |
| (`/auth/session`)        | (Abuse & Toll Fraud)  | (In-Memory Fallback)| to brute-force and SMS spam.   |
|                          |                       |                     | Falls back to local in-memory  |
|                          |                       |                     | sliding window cache.          |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Token Revocation Check   | High Security         | **FAIL-CLOSED**     | Failing open allows revoked or |
| (`get_current_user`)     | (Gate 4 Invariant)    | (Strict)            | compromised tokens to execute. |
|                          |                       |                     | Queries `user_sessions` DB.    |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Operations 2FA           | High Security         | **FAIL-CLOSED**     | Replay attacks must be blocked.|
| (`/auth/2fa/verify`)     | (Gate 5 Invariant)    | (Strict)            | Rejects on Redis drop.         |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Spatial Search           | Medium Availability   | **FAIL-SAFE**       | Read-only discovery. Failing   |
| (`/spaces/search`)       | (Driver Experience)   | (Fail-Open)         | open preserves app usability.  |
+--------------------------+-----------------------+---------------------+--------------------------------+
| Hold Presentation Cache  | Low Presentation      | **FAIL-SAFE**       | Redis cache is non-authorita-  |
| (`hold:presentation:*`)  | (UI Countdown)        | (Fail-Open)         | tive; PostgreSQL GiST is truth.|
+--------------------------+-----------------------+---------------------+--------------------------------+
```

### 5.3 Anti-Enumeration Error Normalization Standard
To prevent attackers from enumerating registered phone numbers or user identities:
- Requests to `POST /api/v1/auth/session` with invalid, malformed, or forged Firebase tokens return an identical RFC 7807 response:
  ```json
  {
    "type": "https://api.gadispot.in/errors/unauthorized",
    "title": "Invalid Authentication Token",
    "status": 401,
    "detail": "Authentication token could not be verified.",
    "code": "INVALID_TOKEN",
    "instance": "/api/v1/auth/session",
    "timestamp": "2026-11-06T12:00:00Z"
  }
  ```
- The backend never discloses whether the phone number was previously registered or newly created.
- Endpoints fetching resources return HTTP 404 `NOT_FOUND` when the requested resource belongs to another user, preventing IDOR resource enumeration.

---

## 6. Security Audit Event Schema & Data Minimization

### 6.1 Database Schema (`audit_events` Table)
Provisioned via Alembic migration `002_audit_events.py`:
```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID,                         -- User UUID performing the action (nullable for unauth/system)
    action VARCHAR(64) NOT NULL,            -- Canonical event identifier (e.g. 'AUTH_SESSION_EXCHANGED')
    resource_type VARCHAR(64) NOT NULL,     -- Domain entity ('USER', 'SESSION', 'RESERVATION', etc.)
    resource_id VARCHAR(128) NOT NULL,      -- ID of the affected resource
    details JSONB NOT NULL DEFAULT '{}',    -- Structured metadata (strictly sanitized)
    ip_address VARCHAR(45),                 -- Client IPv4 or IPv6 address
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_events_created ON audit_events(created_at);
CREATE INDEX idx_audit_events_resource ON audit_events(resource_type, resource_id);
```

### 6.2 Canonical IAM Audit Event Catalogue

| Event Identifier | Triggering Condition | Captured Details (JSONB) | Actor ID |
|---|---|---|---|
| **`AUTH_SESSION_EXCHANGED`** | Successful phone token exchange | `{"phone_masked": "+91 98*** **345", "roles": ["DRIVER"]}` | User UUID |
| **`AUTH_LOGIN_FAILED`** | Invalid/forged token presented | `{"reason": "INVALID_SIGNATURE", "ip_address": "..."}` | `null` |
| **`AUTH_TOKEN_REFRESHED`** | Valid refresh token rotated | `{"family_id": "...", "session_id": "..."}` | User UUID |
| **`AUTH_TOKEN_REUSE_DETECTED`** | Replay of revoked refresh token | `{"family_id": "...", "replayed_jti": "..."}` | User UUID |
| **`AUTH_LOGOUT`** | User explicitly terminates session | `{"session_id": "..."}` | User UUID |
| **`ROLE_SWITCHED`** | Dual-role user swaps viewport | `{"previous_role": "DRIVER", "new_role": "OWNER"}` | User UUID |
| **`ROLE_ASSIGNED`** | Admin provisions role to user | `{"granted_role": "GUARD", "granted_by": "admin_uuid"}` | Admin UUID |
| **`ACCOUNT_SUSPENDED`** | Admin suspends user account | `{"reason": "DISPUTE_PENALTY", "suspended_by": "..."}` | Admin UUID |
| **`IDOR_VIOLATION_ATTEMPT`** | Caller attempts cross-tenant access | `{"target_resource": "RESERVATION", "target_id": "..."}` | Attacker UUID |
| **`ADMIN_2FA_VERIFIED`** | Operations staff passes TOTP check | `{"action": "PROPERTY_APPROVAL", "property_id": "..."}` | Staff UUID |

### 6.3 DPDPA 2023 Data Minimization Invariants
- **Zero Raw Tokens:** Raw Firebase ID tokens, internal access tokens, and refresh tokens are NEVER logged or written to `audit_events`.
- **Zero Raw Secrets:** OTP codes, payment gateway secret keys, TOTP secrets, and database passwords are NEVER logged.
- **Masked PII:** Phone numbers are masked (`+91 98*** **345`) and vehicle registration plates are masked (`KA-01-**-1234`).
- **7-Day Gate Photo Expiration:** Offline guard admission photos are purged by an automated S3 lifecycle expiration rule after **7 days**, retaining strictly the SHA-256 audit hash in database records.

---

## 7. Stage-by-Stage Implementation Roadmap

| Stage | Target Scope | Core Deliverables & Remediations | Addressed Gaps |
|:---:|---|---|---|
| **Stage 0** | Discovery & Gap Matrix | Produce `PHASE_02_IAM_DISCOVERY_REPORT.md` and `PHASE_02_GAP_MATRIX.md`; reconcile historical discrepancies. | GAP-01, GAP-02 |
| **Stage 1** | Identity & Account Model | Author Alembic migration `004_identity_and_sessions.py` (`firebase_uid`, `status`, `user_sessions`); implement atomic UPSERT for user registration. | GAP-03, GAP-04, GAP-05, GAP-06, GAP-10 |
| **Stage 2** | Auth & Session Lifecycle | Implement refresh token rotation, token reuse detection with family invalidation, `POST /auth/logout`, `GET /auth/me`, and Firebase credentials file loading. | GAP-07, GAP-08, GAP-09, GAP-11, GAP-12, GAP-13 |
| **Stage 3** | Server-Side RBAC & IDOR | Inject `get_current_user` and `verify_resource_ownership` into booking, access, and payment endpoints; enforce guard property binding. | GAP-14, GAP-15, GAP-16, GAP-17, GAP-18 |
| **Stage 4** | Abuse Protection & Audit | Implement `fail_closed` policy in `SlidingWindowRateLimiter`; attach rate limiters to auth endpoints; instrument `AuditService` across auth events. | GAP-19, GAP-20, GAP-21, GAP-22, GAP-23 |
| **Stage 5** | Mobile Data & Domain IAM | Implement `FirebaseAuthPort` with `MockAuthRemoteDataSource` and `ProductionFirebaseAuthDataSource`; wire `AuthRepository` and `AuthNotifier`. | GAP-24, GAP-25 |
| **Stage 6** | Mobile Presentation & Routing | Author `RoleSwitcher` widget; wire `SecureStorageService`; implement 401 refresh interceptor in Dio; restore session on boot in `main.dart`. | GAP-26, GAP-27 |
| **Stage 7** | Database Migrations & Security Tests | Add automated tests for migration 004 upgrade/downgrade, user creation concurrency stress, token rotation, reuse detection, and IDOR shielding. | GAP-28, GAP-29 |
| **Stage 8** | Mobile Testing & Integration | Add Flutter unit and widget tests for `AuthRepository`, `RoleSwitcher`, phone entry, OTP submission, and session restoration. | GAP-29 |
| **Stage 9** | Documentation & Reporting | Author Threat Model, Permission Matrix, and comprehensive `PHASE_02_IMPLEMENTATION_REPORT.md`. | GAP-30 |
| **Stage 10** | CI/CD Pipeline Verification | Commit and push authorized changes; monitor and verify remote GitHub Actions CI pipeline runs 100% green. | GAP-30 |

---

## 8. Conclusion

This Gap Matrix establishes the authoritative contract for Phase 02. All 30 identified gaps across Requirements R1–R8 and Acceptance Gates 1–8 are scoped, categorized by severity, and assigned to concrete execution stages. By executing this staged roadmap, the engineering team will deliver a hardened, enterprise-grade IAM subsystem while maintaining 100% compliance with the Phase 01 baseline and frozen governance specifications.
