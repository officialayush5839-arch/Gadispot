# GADISPOT — PHASE 2.5 SECURITY DECISION RECORDS (SDR)
**Project:** Gadispot  
**Phase:** 2.5 — IAM Security Remediation  
**Date:** 2026-11-07  
**Status:** ACCEPTED & IMPLEMENTED (CHECKPOINT 7)  

---

## Decision SDR-25-01: TOTP Two-Factor Authentication Policy
- **Problem:** Existing `/2fa/setup` and `/2fa/verify` endpoints generate unbound secrets and verify client-supplied secrets with zero persistence, zero encryption, and zero user authentication.
- **Alternatives:**
  - *Option A (Retain & Harden):* Add `totp_secret_encrypted`, `totp_enabled`, `totp_verified_at` columns to `users`. Bind `/2fa/setup` to authenticated principal (`Depends(get_current_user)`). Encrypt secret with AES-GCM (using `TOTP_ENCRYPTION_KEY` in environment). Require user to prove possession with valid 6-digit code before enabling. Verify against persisted secret.
  - *Option B (Defer & Disable):* Defer TOTP until an enterprise operations admin panel is introduced in later phases. Disable `/2fa/setup` and `/2fa/verify` endpoints, mark them deprecated/disabled, and document deferral.
- **Recommendation:** **Option A (Retain & Harden)**. Hardening TOTP ensures Operations and Administrative staff have an authentic, account-bound second factor compliant with RFC 6238 without deferring security debt.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-02: Access Token Lifetime & Expiration Policy
- **Problem:** Architectural reports specify a 15-minute access token (900 seconds), but `config.py` configured 60 minutes and responses hardcoded 3600 seconds.
- **Alternatives:**
  - *Option A:* Keep 60 minutes (lower load on refresh endpoint, higher exposure window).
  - *Option B:* Enforce 15 minutes (900 seconds) centrally across `Settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15`, JWT `exp`, response payloads, and Flutter interceptors.
- **Recommendation:** **Option B (Enforce 15 Minutes / 900 Seconds)**. Aligns runtime behavior with governing architecture and security standards, minimizing exposure duration of stolen access tokens.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-03: Refresh Token Reuse & Revocation Scope
- **Problem:** Currently, when refresh token reuse is detected, all sessions for the entire user are revoked across all user devices. Furthermore, rotation lookup lacks row-level locking.
- **Alternatives:**
  - *Option A (User-Wide Nuking):* Continue revoking all sessions for the user across every device.
  - *Option B (Family-Scoped Revocation):* Scope revocation strictly to the affected `family_id`. Add `with_for_update()` to `select(UserSession)` to ensure atomic single-use rotation. If a token from family F is reused, only sessions with `family_id == F` are revoked; active sessions on other devices in different families remain intact.
- **Recommendation:** **Option B (Family-Scoped Revocation + Atomic Row Locking)**. Conforms to OAuth 2.0 Security Best Current Practice (BCP) for Refresh Token Rotation without causing unnecessary cross-device Denial of Service.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-04: Redis Failure Policy for Revocation Checks
- **Problem:** `get_current_user` catches `aioredis.RedisError` and silently continues authentication (`pass`), rendering token blocklists and family revocation useless if Redis is down.
- **Alternatives:**
  - *Option A (Blind Fail-Open):* Continue silently passing when Redis fails.
  - *Option B (Authoritative DB Fallback):* When Redis is unreachable, execute an authoritative database query against `user_sessions` verifying that `family_id` is active (`is_revoked is False`). If the DB confirms revocation or DB query fails, reject the request with 401 Unauthorized.
- **Recommendation:** **Option B (Authoritative Database Fallback)**. Ensures security properties hold even during complete Redis degradation. Revoked sessions cannot authenticate.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-05: Rate Limiter Error Handling & Degraded Memory Fallback
- **Problem:** `rate_limiter.py` catches broad `Exception`, disguising runtime errors as Redis outages. Its fallback in-memory dictionary grows without bounds.
- **Alternatives:**
  - *Option A:* Unbounded in-memory dictionary.
  - *Option B:* Catch only `aioredis.RedisError` and `asyncio.TimeoutError`. Bound in-memory fallback with a sliding TTL eviction window and max key cap (e.g. 5,000 keys) to prevent memory exhaustion. Ensure authentication endpoints fail closed.
- **Recommendation:** **Option B (Specific Exception Handling + Bounded Cache)**. Prevents silent error swallowing and memory leaks while enforcing strict abuse protection.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-06: Canonical Role Vocabulary & Elimination of Wildcard ADMIN
- **Problem:** `RoleChecker` unilaterally adds `ADMIN` to every endpoint's allowed roles, creating uncontrolled privilege escalation. Role vocabulary mixes `OWNER`/`GUARD` with `SPACE_OWNER`/`SECURITY_GUARD`.
- **Alternatives:**
  - *Option A:* Retain wildcard `ADMIN` inject on all routes.
  - *Option B:* Remove automatic `ADMIN` injection. Require routes to declare explicit role sets (e.g. `require_roles(UserRoleEnum.OPERATIONS, UserRoleEnum.ADMIN)`). Standardize mapping between database enums (`OWNER`, `GUARD`, `OPERATIONS`) and canonical API roles (`SPACE_OWNER`, `SECURITY_GUARD`, `OPS`).
- **Recommendation:** **Option B (Explicit Role Sets + No Wildcard Bypass)**. Enforces strict principle of least privilege.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-07: Firebase Identity Linking & Account Takeover Defense
- **Problem:** `create_user_session` matches users by `phone_number OR firebase_uid` and silently overwrites `user.firebase_uid` if the phone number matches an existing user.
- **Alternatives:**
  - *Option A (Silent Overwrite):* Retain existing lookup and overwrite behavior.
  - *Option B (Fail-Closed Conflict Detection):*
    - If user exists with matching `firebase_uid` and matching `phone_number`: Authenticate successfully.
    - If user exists with matching `firebase_uid` but different `phone_number`: Return 409 Conflict (`IDENTITY_CONFLICT`).
    - If user exists with matching `phone_number` but different `firebase_uid`: Return 409 Conflict (`PHONE_ALREADY_LINKED`) unless explicit multi-factor account recovery is completed.
    - If user does not exist: Create new account atomically.
- **Recommendation:** **Option B (Fail-Closed Conflict Detection)**. Eliminates account takeover vulnerabilities and prevents identity corruption.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-08: Firebase Error Sanitization
- **Problem:** `verify_firebase_id_token` in `backend/app/integrations/firebase.py` includes raw exception string `{exc!s}` in client response in production.
- **Recommendation:** Return standard RFC 7807 problem details with generic message `"The provided authentication token is invalid or could not be verified."` while logging detailed exception stack traces to server logs.
- **Status:** **ACCEPTED & IMPLEMENTED**

---

## Decision SDR-25-09: Flutter Interceptor Exclusions & 401 Queueing
- **Problem:** Flutter `RefreshTokenInterceptor` does not exclude `/auth/exchange`, and drops concurrent 401 requests while a refresh is in flight.
- **Recommendation:** Exclude all auth endpoints (`/auth/session`, `/auth/exchange`, `/auth/refresh`, `/auth/logout`, `/2fa/*`). Implement a FIFO request queue while `_isRefreshing == true`, retrying all queued requests once the refresh completes.
- **Status:** **ACCEPTED & IMPLEMENTED**
