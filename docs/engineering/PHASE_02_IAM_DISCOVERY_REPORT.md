# Gadispot Phase 02 IAM Discovery & Architecture Synthesis Report
## Identity, Authentication, Authorization & Role-Based Access Control

> **Document Identifier:** REPORT-GSP-2026-PHASE-02-STAGE-0-DISCOVERY-VERIFIED  
> **Document Title:** Phase 02 Stage 0 — Comprehensive IAM Discovery, Baseline Verification & Architectural Synthesis Report  
> **Governing Baseline:** Master PRD V2.3.2-VERIFIED ([PRD.md](../../PRD.md)), Engineering Rules ([rules.md](../../rules.md)), Master Architecture ([architecture.md](../../architecture.md)), Master 15-Phase Strategic Roadmap ([phases.md](../../phases.md)), Master Backlog ([task.md](../../task.md)), Engineering Baseline ([PROJECT.md](../../PROJECT.md))  
> **Target Pilot Geography:** Bengaluru Urban Metro, Karnataka, India (Koramangala, Indiranagar, HSR Layout — 200 Pilot Bays)  
> **Target Execution Platforms:** Mobile-Only (Single Cross-Platform Flutter Mobile Binary for Android & iOS)  
> **Backend Architecture:** In-Process Modular Monolith (Python 3.12 / FastAPI / PostgreSQL 16 + PostGIS / Redis 7.0+)  
> **Author:** Worker Stage 0 (`teamwork_worker`)  
> **Investigation Date:** November 6, 2026  
> **Integrity Mode:** Read-Only Discovery & Spec Harmonization (Zero production code mutations)  

---

## 1. Executive Summary

### 1.1 Mission & Scope
In accordance with **Requirement R1** and **Stage 0** of Phase 02, this report provides the authoritative architectural synthesis and empirical baseline verification for **Phase 02: Identity, Authentication, Authorization & Role-Based Access Control (IAM-RBAC)** across the Gadispot platform. 

The scope encompasses:
1. Empirical verification of the Phase 01 engineering foundation (backend automated tests, Flutter mobile tests, code style formatting, static analysis, Docker infrastructure, and specification immutability).
2. A comprehensive component-by-component survey of all IAM-related subsystems across both the FastAPI backend modular monolith (`backend/app/`) and the Flutter mobile client (`mobile/lib/`).
3. Explicit reconciliation of historical documentation, naming, routing, and directory discrepancies between foundation specifications, sprint execution trackers, and current repository code.
4. Identification of all architectural, security, and operational gaps that must be resolved across Stages 1 through 10 of Phase 02.

### 1.2 Baseline Verification Status: 100% Green
Empirical verification confirms that the Phase 01 engineering baseline is completely healthy, reproducible, and uncorrupted:
- **Specification Immutability & Harmonization (`python scripts/validate_spec.py`):** **PASSED (100% Green)**. The 6 canonical frozen governance files ([PRD.md](../../PRD.md), [goal.md](../../goal.md), [rules.md](../../rules.md), [architecture.md](../../architecture.md), [phases.md](../../phases.md), [task.md](../../task.md)) match their frozen SHA-256 baseline checksums with zero modifications. Zero obsolete patterns (e.g. 300-second holds) or broken relative markdown links exist.
- **Docker Infrastructure Spec (`python scripts/validate_docker_spec.py`):** **PASSED (100% Green)**. Multi-stage Dockerfile, compose services (PostGIS 16-3.4, Redis 7-alpine, FastAPI), and developer scripts are fully compliant.
- **Mobile Foundation Spec (`python scripts/validate_mobile_spec.py`):** **PASSED (100% Green)**. All 36 clean architecture files verified; anti-slop styling rules and RFC 7807 error mappings verified.
- **Backend Code Quality (`python -m ruff check backend`):** **PASSED (0 lint errors)**. All Python files adhere to project lint rules.
- **Backend Formatting (`python -m ruff format --check backend`):** **PASSED (56 files verified clean)**. Zero formatting violations.
- **Backend Test Suite (`python -m pytest tests/ -v`):** **PASSED (84/84 passed in 33.06s)**. 100% passing across database GiST exclusion constraints, Zero Child Lock general ledger MVCC triggers, compatibility math, and health probes.
- **Flutter Test Suite (`flutter test`):** **PASSED (37/37 passed green)**. Verified across Clean Architecture layers, RFC 7807 problem details parsing, secure storage mocks, monochromatic theme tokens, and dynamic role shells via CI workflow run `42198676676`.

### 1.3 Key Architectural Findings
While Phase 01 established a rock-solid infrastructure foundation, the existing IAM implementation contains significant architectural and security gaps when measured against the full Phase 02 specification:
1. **Identity Uniqueness & Lifecycle:** The `User` database model lacks a `firebase_uid` column (Firebase tokens are validated, but the UID is discarded) and lacks an explicit account lifecycle status enum (`ACTIVE`, `SUSPENDED`, `DISABLED`), relying on a single boolean `is_active`.
2. **Concurrency Race Condition:** First-time user creation in `exchange_firebase_token_for_session` performs an uncoordinated `SELECT` followed by `INSERT`, exposing the registration endpoint to `IntegrityError` crashes under concurrent authentication bursts from the same user.
3. **Session Lifecycle & Token Security:** Refresh tokens are stateless JWTs without database tracking, token rotation, reuse detection, or revocation capabilities. There is no session table and no `/api/v1/auth/logout` endpoint.
4. **Endpoint Authorization & IDOR Exposure:** Critical booking, payment, and QR access endpoints (`GET /api/v1/bookings/{id}`, `POST /api/v1/access/issue-tokens`, `POST /api/v1/access/validate-scan`, `POST /api/v1/payments/refund/request`) lack authentication dependencies and object-level ownership checks, exposing the system to Insecure Direct Object References (IDOR).
5. **Abuse Protection & Redis Failure Policy:** Sliding-window rate limiters are defined but not attached as FastAPI dependencies to auth endpoints. Crucially, the rate limiter's error handler blindly fails open (`return False, 0, 0`) on Redis connection loss, violating Requirement R5 for fail-closed protection on critical authentication paths.
6. **Audit Trail Disconnect:** `AuditService` is implemented but disconnected from auth endpoints; zero audit records are emitted on token exchanges, refresh operations, logouts, 2FA operations, or IDOR blocks.
7. **Mobile Client Disconnect:** The Flutter client's authentication view (`OtpView`) is a non-functional mock that features an unauthenticated client-side role dropdown allowing any user to select privileged roles (`Operations`, `Security Guard`) and navigate directly into privileged shells without server authorization. Furthermore, the mobile client references `/api/v1/auth/firebase-exchange` whereas the backend exposes `/api/v1/auth/session`.

---

## 2. Phase 01 Baseline Empirical Verification Evidence

A rigorous verification pass was executed to prove that the starting codebase meets all baseline quality, governance, and test invariants.

| Verification Target | Execution Command | Prescribed Baseline Criteria | Observed Result | Status |
|---|---|---|---|:---:|
| **Governance Immutability** | `python scripts/validate_spec.py` | 6 frozen files match SHA-256; zero broken links; zero banned hold TTLs | PASSED: 6/6 SHA-256 matches verified; zero link defects | **100% PASS** |
| **Docker Infrastructure** | `python scripts/validate_docker_spec.py` | 4/4 checks pass (multi-stage build, compose dependencies, health checks) | PASSED: 4/4 checks green | **100% PASS** |
| **Mobile Clean Architecture** | `python scripts/validate_mobile_spec.py` | 6/6 checks pass (36 files, pubspec, anti-slop, RFC 7807 error parsing) | PASSED: 6/6 checks green | **100% PASS** |
| **Backend Code Quality** | `python -m ruff check backend` | 0 lint violations across backend modules | `All checks passed!` (0 errors) | **100% PASS** |
| **Backend Code Formatting** | `python -m ruff format --check backend` | Clean formatting across all Python files | `56 files already formatted` (0 modified) | **100% PASS** |
| **Backend Integration Suite** | `python -m pytest tests/ -v` | 84/84 passing tests in `<45s` with zero deadlocks or socket exhaustion | `84 passed in 33.06s` | **100% PASS** |
| **Mobile Automated Test Suite** | GitHub Actions CI Run `42198676676` (`mobile-quality`) | 37/37 Flutter unit/widget tests passing; 0 analyzer warnings; debug APK build | 37 passed, 0 analyzer errors (`flutter analyze`), APK compiled | **100% PASS** |
| **Git Working Tree State** | `git status -s` | Clean working tree; zero unstaged files; zero tracked secrets | `nothing to commit, working tree clean` | **100% PASS** |

### Frozen Governance File Checksums Verified:
- `PRD.md`: `fc71555b76301d7fb66bf6ec0582924b2c3b12c90dc0d7cc45a00e6bc338a25e`
- `goal.md`: `4e3ff39382a1c5e87a273b0e3a7b2c183afa457ecb9e6e72a25b4e51a77140ca`
- `rules.md`: `7997d0cda7e38024470e01aa19645a6f827af9a5a63c114cee3db21f47e4b446`
- `architecture.md`: `3fcaa833254a666d547558f7d154f30f1776bd5a1955134a515000f7f21d3144`
- `phases.md`: `39124e9f65d1cbfcecaa017a2bc44b15a96b49c1e21c6a3f3eb6a722cae2906b`
- `task.md`: `c240878f5000a314466f7a5048ef1e5f6b349d688358dde63692efa14d71b637`

---

## 3. Comprehensive IAM Component-by-Component Survey

### 3.1 PostgreSQL Data Models (`backend/app/models/`)

#### Inspection: `backend/app/models/users.py`
The `User` model represents the primary identity entity:
```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
```

The `UserRole` model supports multi-role associations:
```python
class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_id_role"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(ENUM(UserRoleEnum, name="user_role_enum", create_type=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

#### Deficiencies Identified:
1. **Missing `firebase_uid`:** There is no column to persist the Firebase User UID. In `auth_service.py`, Firebase token verification validates the `sub` (UID) claim, but discards it, looking up users strictly by `phone_number`. This prevents account linking, provider migration, and reliable multi-device session binding.
2. **Missing Account Lifecycle Enum:** The model uses a binary boolean `is_active: bool`. Master PRD §12.1 and Acceptance Gate 2 mandate three explicit lifecycle states: `ACTIVE`, `SUSPENDED`, and `DISABLED`.
3. **No Session Entity:** No model exists for tracking active refresh tokens, token families, device fingerprints, or revocation status.

---

### 3.2 Alembic Database Migrations (`backend/alembic/versions/`)

The migration lineage currently contains 3 applied revisions:
1. `001_initial_schema.py`: Provisions PostgreSQL extensions (`uuid-ossp`, `btree_gist`, `postgis`), 14 core domain enums (including `user_role_enum` with values `'DRIVER'`, `'OWNER'`, `'GUARD'`, `'OPERATIONS'`, `'ADMIN'`), tables `users`, `user_roles`, `vehicles`, `properties`, `parking_spaces`, `space_reservations`, `access_credentials`, and double-entry ledger structures with Zero Child Lock triggers.
2. `002_audit_events.py`: Creates table `audit_events` with composite indices on `created_at` and `(resource_type, resource_id)`.
3. `003_demo_payments.py`: Adds payment enums and tables `payments` and `payment_webhook_events`.

#### Deficiencies Identified:
- Alembic lineage has no migration for Phase 02 IAM structures.
- A new migration `004_identity_and_sessions.py` is required to non-destructively alter `users` (adding `firebase_uid` and `user_status_enum`) and create table `user_sessions` with complete downgrade capability.

---

### 3.3 Security & Cryptographic Primitives (`backend/app/core/security.py`)

#### Inspection:
`security.py` provides symmetric HS256 JWT encoding and decoding using `python-jose`:
- `create_access_token(subject, claims, expires_delta)`: Issues JWT with `sub`, `iat`, `exp` (default 60 minutes), `jti` (UUIDv4), `type="access"`.
- `create_refresh_token(subject, claims, expires_delta)`: Issues JWT with `sub`, `iat`, `exp` (default 30 days), `jti` (UUIDv4), `type="refresh"`.
- `decode_token(token)`: Verifies signature against `settings.SECRET_KEY` and algorithm `HS256`. Raises `UnauthorizedException` with codes `TOKEN_EXPIRED` or `INVALID_TOKEN`.
- `constant_time_compare(val1, val2)`: Safe digest comparison via `hmac.compare_digest`.

#### Deficiencies Identified:
- Refresh tokens are completely stateless. The backend does not verify whether a refresh token has been revoked, rotated, or previously used.
- Refresh tokens lack a `family_id` claim, preventing cryptographic family tracking required for token reuse detection.

---

### 3.4 Authorization & RBAC Architecture (`backend/app/core/authorization.py`)

#### Inspection:
`authorization.py` provides foundational security dependencies:
- `get_current_user`: Extracts Bearer token from `Authorization` header, decodes JWT, validates `type == "access"`, fetches `User` from PostgreSQL with eager-loaded `roles`, checks `user.is_active` (raises HTTP 403 `ACCOUNT_DEACTIVATED` if False), and stores the user on `request.state.user`.
- `RoleChecker`: Enforces role intersection (`user_roles & allowed_roles`). Grants automatic superuser bypass to `ADMIN`. Raises HTTP 403 `FORBIDDEN_ROLE` on mismatch.
- `require_roles(*roles)`: Factory creating `RoleChecker` instances.
- `verify_resource_ownership(user, resource_owner_id, allow_privileged=True)`: Enforces object-level ownership. Bypasses check for `ADMIN` and `OPERATIONS`; raises HTTP 403 `IDOR_ACCESS_DENIED` if `user.id != resource_owner_id`.

#### Critical Security Gaps & Unprotected Endpoints Audit:
A scan across all API routers revealed that several critical mutating and read endpoints completely lack authentication dependencies or object ownership checks:
1. `GET /api/v1/bookings/{reservation_id}` (`bookings.py:121`): **CRITICAL IDOR**. Has zero authentication dependency. Any caller who knows or guesses a reservation UUID can read personal details, booking windows, vehicle plates, and space locations.
2. `POST /api/v1/access/issue-tokens` (`access.py:33`): **CRITICAL**. Missing authentication. Any caller can trigger entry/exit pass issuance for any confirmed reservation.
3. `POST /api/v1/access/validate-scan` (`access.py:100`): **CRITICAL PRIVILEGE ESCALATION**. The endpoint accepts `guard_id` as an untrusted field in the request JSON payload without authenticating the caller or verifying that the caller possesses the `GUARD` role.
4. `POST /api/v1/payments/create-order` (`payments.py:223`): Missing authentication dependency.
5. `POST /api/v1/payments/refund/request` (`payments.py:306`): Missing authentication dependency.
6. `POST /api/v1/payments/payouts/simulate` (`payments.py:201`): Authenticates `current_user` but lacks role dependency `require_roles(UserRoleEnum.OPERATIONS, UserRoleEnum.ADMIN)`.

---

### 3.5 Redis Rate Limiting & Abuse Protection (`backend/app/core/rate_limiter.py`)

#### Inspection:
`rate_limiter.py` implements a sorted-set sliding window rate limiter:
- Algorithms: `ZADD` current timestamp, `ZREMRANGEBYSCORE` to prune entries outside the window, `ZCARD` to count attempts.
- Configured instances:
  - `otp_rate_limiter`: 3 requests per 900s (15m).
  - `login_rate_limiter`: 5 requests per 900s (15m).
  - `search_rate_limiter`: 60 requests per 60s (1m).

#### Critical Vulnerability: Blind Fail-Open on Redis Error
Lines 76–79 contain:
```python
except Exception as exc:
    logger.warning("Redis rate limiter unavailable (%s); failing open for %s", exc, key)
    return False, 0, 0
```
**Violation of Requirement R5 & Gate 6:** If Redis becomes unavailable, the rate limiter fails open unconditionally. On critical authentication endpoints (`/auth/session`, OTP issuance), an attacker could flood the SMS gateway or brute-force credentials. 
**Required Architecture:** The rate limiter must support an explicit `fail_closed` policy on authentication paths, falling back to an in-memory sliding window cache or returning HTTP 503 `SERVICE_UNAVAILABLE` to protect upstream statutory rails.

---

### 3.6 Security Audit Logging (`backend/app/services/audit_service.py`)

#### Inspection:
`AuditService.log_event` inserts structured audit rows into PostgreSQL `audit_events` and emits log entries:
```python
await AuditService.log_event(
    db=db,
    actor_id=user.id,
    action="AUTH_LOGIN_SUCCESS",
    resource_type="USER",
    resource_id=str(user.id),
    details={"ip_address": ip},
    ip_address=ip
)
```

#### Deficiencies Identified:
- `AuditService.log_event` is completely uncalled in `auth_service.py` and `auth.py`. Zero security audit records are created during authentication, token refresh, role changes, or IDOR violations.
- Privacy filter (`SensitiveDataFilter` in `core/logging.py`) must be audited to ensure zero raw tokens, OTPs, or customer PII are logged.

---

### 3.7 Authentication Service & Firebase Integration (`backend/app/services/auth_service.py`, `app/api/v1/endpoints/auth.py`)

#### Inspection:
1. `_init_firebase()`: Initializes `firebase_admin` with `credentials.ApplicationDefault()`. It does not check `settings.FIREBASE_CREDENTIALS_PATH`, failing in environments without system ADC.
2. `verify_firebase_token(id_token)`: In production, calls `fb_auth.verify_id_token(id_token, check_revoked=True)`. In test/dev, accepts mock prefixes (`test-token-*`). Returns `{"uid": uid, "phone_number": phone, "email": email}`.
3. `exchange_firebase_token_for_session(db, id_token)`:
   - Queries user by `phone_number`.
   - If not found, instantiates `User(phone_number=..., full_name="Driver User", is_active=True)` and creates `UserRole(role=UserRoleEnum.DRIVER)`.
   - Issues access token and refresh token.
4. `refresh_session_tokens(db, refresh_token)`: Decodes refresh token, checks `user.is_active`, issues new access token, but re-returns the exact same refresh token.

#### Critical Vulnerability: Registration Race Condition
In `exchange_firebase_token_for_session`:
```python
stmt = select(User).where(User.phone_number == phone_number)
user = (await db.execute(stmt)).scalar_one_or_none()
if not user:
    user = User(phone_number=phone_number, full_name="Driver User", is_active=True)
    db.add(user)
    await db.flush()
```
If a mobile client retries rapidly or fires two concurrent requests on network reconnection, both transactions see `user is None`. The second transaction crashes with `IntegrityError: duplicate key value violates unique constraint "uq_users_phone"`, returning an unhandled HTTP 500 error instead of a session.

---

### 3.8 Flutter Mobile Network & Security (`mobile/lib/core/`)

#### Inspection:
- `ApiClient` (`mobile/lib/core/network/api_client.dart`): Wraps Dio with `RequestIdInterceptor`, `AuthInterceptor` (attaching Bearer token from secure storage), and `ProblemDetailsInterceptor` (parsing RFC 7807 Problem Details).
- `SecureStorageService` (`mobile/lib/core/security/secure_storage_service.dart`): Wraps `flutter_secure_storage` with Android Keystore (`encryptedSharedPreferences`) and iOS Keychain (`first_unlock`). Defines explicit methods `saveAccessToken`, `getAccessToken`, `saveRefreshToken`, `clearTokens`, `wipeAllOnLogout`.

#### Deficiencies Identified:
1. **Unwired in Production:** `FlutterSecureStorageServiceImpl` is never instantiated or wired into the UI or application lifecycle.
2. **Missing 401 Refresh Interceptor:** When an access token expires (HTTP 401), `ProblemDetailsInterceptor` throws an `AuthFailure.unauthorized()`. There is no interceptor that pauses queued requests, calls `/api/v1/auth/refresh`, updates secure storage, and retries the original request.
3. **No Session Expiration Handler:** Unrecoverable 401 errors do not clear storage or navigate the user to `/login`.

---

### 3.9 Flutter Mobile Auth Presentation & Role Shells (`mobile/lib/features/`)

#### Inspection:
- `mobile/lib/features/auth/presentation/login_view.dart`: Form for Indian phone numbers with regex formatting (`+91`). Submits to OTP view.
- `mobile/lib/features/auth/presentation/otp_view.dart`:
  - 6-digit OTP field with 60-second cooldown timer.
  - Role dropdown selector allowing users to choose `Driver`, `Owner`, `Guard`, or `Operations`.
  - Submitting executes:
    ```dart
    final initialRoute = AppRouter.resolveInitialRoute(_selectedRole);
    Navigator.of(context).pushNamedAndRemoveUntil(initialRoute, (route) => false);
    ```
- Role Shells: Four dedicated navigation shells exist (`DriverShell`, `OwnerShell`, `GuardShell`, `OpsShell`).

#### Critical Vulnerability: Client-Side Role Self-Assignment
`OtpView` allows unauthenticated public users to assign themselves privileged roles (`Operations`, `Security Guard`) via a client-side dropdown. This violates Acceptance Gate 5: *"Public registration requests cannot assign privileged roles (OPS, SECURITY_GUARD, SPACE_OWNER)."* Mobile navigation shells must be driven strictly by the verified `roles` list returned by the server.

---

## 4. Reconciliation of Historical Documentation Discrepancies

To prevent implementation ambiguity without modifying the six frozen governance files, the following historical discrepancies are formally reconciled:

### Discrepancy 1: Test Suite Directory Paths (`tests/` vs `backend/tests/`)
- **Historical Reference:** Certain sprint notes and task descriptions refer to `pytest backend/tests/`.
- **Authoritative Reality:** The complete, canonical 84-test backend test suite is located at repository root `tests/` (`tests/database/`, `tests/unit/`, `tests/api/`, `tests/security/`). There is no directory named `backend/tests/`.
- **Reconciliation:** All testing commands, CI workflows, and validation scripts authoritatively target `tests/`.

### Discrepancy 2: Token Exchange Endpoint Route Naming (`/session` vs `/firebase-exchange`)
- **Backend Implementation:** `backend/app/api/v1/endpoints/auth.py` registers `POST /api/v1/auth/session`.
- **Mobile Client Constant:** `mobile/lib/core/constants/api_endpoints.dart` defines `authFirebaseExchange = '$apiVersion/auth/firebase-exchange'`.
- **Master PRD:** PRD §12.1 and §14.1 refer to both `/api/v1/auth/session` and the exchange contract.
- **Reconciliation:** The backend route `POST /api/v1/auth/session` is the canonical primary endpoint. In Phase 02, the mobile constant will be updated to target `/api/v1/auth/session`, and the backend will register an alias `POST /api/v1/auth/firebase-exchange` pointing to the identical handler to ensure 100% backward and forward compatibility.

### Discrepancy 3: Role Naming Conventions (`OWNER` vs `SPACE_OWNER`, `GUARD` vs `SECURITY_GUARD`)
- **Database Enum (`backend/app/models/enums.py`):** `UserRoleEnum` uses `DRIVER`, `OWNER`, `GUARD`, `OPERATIONS`, `ADMIN`.
- **Specification Text:** PRD and task descriptions frequently use `SPACE_OWNER` and `SECURITY_GUARD`.
- **Mobile Model:** `UserRoleExtension.fromString` in `mobile/lib/core/routing/app_router.dart` already accepts both aliases (`SPACE_OWNER` $\to$ `UserRole.owner`, `SECURITY_GUARD` $\to$ `UserRole.guard`).
- **Reconciliation:** The PostgreSQL database enum and backend models maintain the canonical values `DRIVER`, `OWNER`, `GUARD`, `OPERATIONS`, `ADMIN`. Serialization schemas accept either alias and normalize to the canonical enum.

### Discrepancy 4: Client-Side vs Server-Authoritative Role Assignment
- **Current Mobile State:** `otp_view.dart` renders a role dropdown enabling user selection of any role.
- **Specification Invariant:** PRD §7 and Acceptance Gate 5 mandate that public users receive strictly the default `DRIVER` role. Privileged roles (`OPERATIONS`, `GUARD`, `OWNER`) must be assigned through administrative actions or verified property onboarding.
- **Reconciliation:** The client-side role dropdown in `otp_view.dart` is an unverified prototype artifact. In Stage 6, it will be removed. The mobile client will navigate to the role shell authorized by the server's `TokenResponse.user.roles`.

### Discrepancy 5: Strategic Roadmap Phases vs Tactical Sprint Work Packages
- **Strategic Roadmap ([phases.md](../../phases.md)):** Defines 15 strategic phases (Phase 00 through Phase 14), with Phase 02 being "Identity, Authentication, Authorization & Role-Based Access Control".
- **Sprint Tracker ([PROJECT.md](../../PROJECT.md), [IMPLEMENTATION_TASK_TRACKER.md](IMPLEMENTATION_TASK_TRACKER.md)):** Tracks 11 engineering sprint milestones (M0 through M10), distributing IAM work across M3 (mobile foundation), M5 (auth infrastructure), and M6 (security/RBAC).
- **Reconciliation:** As formalized in `PROJECT.md` § Governance Architecture Note, the strategic roadmap in `phases.md` is canonical for product scope and acceptance gates. Technical sprint milestones track execution work packages. Phase 02 deliverables map directly to completing sprint work items under M3, M5, and M6.

### Discrepancy 6: Role Switcher Widget Directory Location
- **Specification Reference:** `PROJECT.md` line 49 references `mobile/lib/app/shell/role_switcher.dart`.
- **Actual Codebase:** The folder `mobile/lib/app/` does not exist; all presentation shells are organized under `mobile/lib/features/<role>/presentation/<role>_shell.dart`.
- **Reconciliation:** The dynamic `RoleSwitcher` widget will be authored in a shared presentation directory (`mobile/lib/features/auth/presentation/widgets/role_switcher.dart`) and imported into `DriverShell` and `OwnerShell`.

---

## 5. Architectural Gap Synthesis Across Phase 02 Stages

The comprehensive gap analysis reveals the specific engineering tasks required across each stage of Phase 02:

```
+----------------------------------------------------------------------------------------------------+
|                               PHASE 02 STAGE WORKFLOW ARCHITECTURE                                 |
+----------------------------------------------------------------------------------------------------+
|  Stage 0: Discovery, Reconciliation & Gap Matrix  <-- [COMPLETED BY THIS REPORT & GAP MATRIX]      |
|  Stage 1: Identity & Account Model Hardening (Alembic 004, firebase_uid, status enum, UPSERT)     |
|  Stage 2: Authentication & Session Lifecycle (Refresh rotation, reuse detection, /logout, /me)    |
|  Stage 3: Server-Side RBAC & IDOR Shield Hardening (Dependencies on bookings, access, payments)   |
|  Stage 4: Abuse Protection, Fail-Closed Rate Limiter & Audit Logging (Security events, Redis)     |
|  Stage 5: Mobile Data & Domain IAM Scaffolding (FirebaseAuthPort, AuthRepository, AuthNotifier)    |
|  Stage 6: Mobile Presentation, 401 Interceptor & Dynamic Role Switcher (Shell routing, storage)   |
|  Stage 7: Database Migration Verification & Security Integration Tests (Downgrades, races, IDOR)  |
|  Stage 8: Mobile Widget & End-to-End Auth Tests (Session restoration, mock OTP, token refresh)    |
|  Stage 9: Documentation, Threat Modeling & Implementation Report (PHASE_02_IMPLEMENTATION_REPORT) |
|  Stage 10: CI/CD Pipeline Verification & Remote GitHub Actions Green Run                          |
+----------------------------------------------------------------------------------------------------+
```

### Stage 1: Identity & Account Model
- **Alembic Migration 004:** Add `firebase_uid` (VARCHAR(128), unique index) and `status` (`user_status_enum`: `ACTIVE`, `SUSPENDED`, `DISABLED`) to `users` table. Create `user_sessions` table with family tracking.
- **Race Condition Elimination:** Wrap user creation in PostgreSQL atomic UPSERT (`INSERT INTO users ... ON CONFLICT (phone_number) DO UPDATE`) to eliminate HTTP 500 crashes during concurrent bursts.
- **Role Assignment Security:** Ensure public token exchange provisions strictly the `DRIVER` role.

### Stage 2: Authentication & Session Lifecycle
- **Refresh Token Rotation:** Replace stateless refresh tokens with single-use rotating tokens backed by `user_sessions`.
- **Token Reuse Detection:** Invalidate the entire session family in Redis and PostgreSQL if an already-rotated refresh token is replayed.
- **Endpoint Expansion:** Implement `POST /api/v1/auth/logout` (revoking active session) and `GET /api/v1/auth/me` (returning user profile and roles).
- **Firebase Configuration:** Load `FIREBASE_CREDENTIALS_PATH` via `credentials.Certificate()` in `_init_firebase()`.

### Stage 3: Server-Side Authorization & RBAC
- **IDOR Shield Enforcement:** Inject `get_current_user` and `verify_resource_ownership` into:
  - `GET /api/v1/bookings/{reservation_id}`
  - `POST /api/v1/access/issue-tokens`
  - `POST /api/v1/payments/refund/request`
- **Role Check Enforcement:** Require `require_roles(UserRoleEnum.GUARD)` on `POST /api/v1/access/validate-scan` and derive guard ID strictly from the authenticated principal (`current_user.id`).
- **Administrative Protection:** Protect `POST /api/v1/payments/payouts/simulate` with `require_roles(UserRoleEnum.OPERATIONS, UserRoleEnum.ADMIN)`.

### Stage 4: Abuse Protection, Rate Limiting & Auditing
- **Fail-Closed Redis Policy:** Add `fail_closed: bool = True` to `SlidingWindowRateLimiter` for authentication endpoints (`/auth/session`, OTP issuance), falling back to in-memory caching or HTTP 503 instead of failing open.
- **Attach Rate Limiters:** Connect `login_rate_limiter` to `/auth/session` and `otp_rate_limiter` to 2FA endpoints.
- **Anti-Enumeration Error Normalization:** Standardize error messages so external callers cannot deduce account registration status.
- **Audit Event Emission:** Instrument `AuditService.log_event` across all authentication lifecycle events (`AUTH_SESSION_EXCHANGED`, `AUTH_LOGIN_FAILED`, `AUTH_TOKEN_REFRESHED`, `AUTH_TOKEN_REUSE_DETECTED`, `AUTH_LOGOUT`, `IDOR_VIOLATION_ATTEMPT`).

### Stages 5 & 6: Flutter Mobile Client Integration
- **Clean Auth Architecture:** Author `FirebaseAuthPort` with `MockAuthRemoteDataSource` (for local dev/test without SMS costs) and `ProductionFirebaseAuthDataSource`.
- **Secure Storage Wiring:** Wire `FlutterSecureStorageServiceImpl` into `AuthRepository` and `ApiClient`.
- **401 Refresh Interceptor:** Implement an automatic token refresh interceptor in Dio that handles 401s seamlessly.
- **Session Restoration on Boot:** Check stored tokens on startup in `main.dart` and navigate directly to the authorized role shell.
- **Dynamic Role Switcher:** Author `RoleSwitcher` widget in `mobile/lib/features/auth/presentation/widgets/role_switcher.dart` allowing dual-role users (Driver/Owner) to toggle viewports.
- **Eliminate Insecure Role Dropdown:** Remove the role selector from `otp_view.dart`.

### Stages 7 & 8: Database & Security Automated Testing
- Add migration upgrade/downgrade automated tests for migration 004.
- Add concurrency stress tests verifying atomic UPSERT under 20 concurrent threads for the same phone number.
- Add security test suites for token rotation, reuse detection, IDOR shielding, fail-closed rate limiter behavior, and audit log emission.
- Add Flutter widget tests for phone entry, OTP submission, session restoration, and role switching.

### Stages 9 & 10: Documentation & CI/CD Pipeline
- Produce Threat Model and Permission Matrix.
- Produce final `PHASE_02_IMPLEMENTATION_REPORT.md`.
- Verify remote GitHub Actions CI/CD pipeline (`.github/workflows/spec-validation.yml`) executes 100% green.

---

## 6. Conclusion

The Gadispot Phase 01 baseline is rock-solid, fully reproducible, and verified 100% green. The IAM architecture survey and gap analysis completed in this report provide an exhaustive, unambiguous blueprint for Phase 02 execution. 

Proceeding to **Stage 1 (Identity & Account Model)** with migration 004 and atomic UPSERT handling will directly address the highest-severity identity gaps while preserving the integrity of all 84 existing backend tests and 37 mobile tests.
