# GADISPOT — PHASE 2.5 INDEPENDENT SECURITY AUDIT
**Project:** Gadispot  
**Phase:** 2.5 — Identity, Authentication & Authorization Security Remediation  
**Date:** 2026-11-07  
**Auditor:** Principal Application Security Engineer & Independent System Auditor  
**Repository:** `https://github.com/officialayush5839-arch/Gadispot`  
**Inspected Git Baseline:** Commit `7e87623` on branch `main`  
**Working Tree Status:** Clean (0 uncommitted changes, 0 modified files)  
**Governing Documents:** `PRD-GSP-2026-V2.3.2-VERIFIED`, `PHASES-GSP-2026-V1.0-VERIFIED`  

---

## 1. Executive Summary

This independent security audit evaluates the IAM foundation delivered in Phase 02 against the 9 reported security findings. Source-code inspection confirmed that all nine vulnerabilities and design inconsistencies exist in the active codebase at commit `7e87623`.

None of the findings were false positives. This document establishes the exact root causes, vulnerable code paths, severity ratings, exploitability assessments, and required remediation measures.

---

## 2. Revalidation of Audit Findings

### Finding F25-01: TOTP Two-Factor Authentication Unbound & Client-Authoritative
- **Status:** `CONFIRMED`
- **Severity:** `CRITICAL`
- **Location:** `backend/app/api/v1/endpoints/auth.py:242-273`, `backend/app/core/security.py:126-150`
- **Root Cause:**
  1. `POST /2fa/setup` lacks `get_current_user` dependency; unauthenticated callers can trigger secret generation.
  2. The email in the provisioning URI is hardcoded to `"operations.user@gadispot.in"`.
  3. The secret is never stored in the database, never encrypted at rest, and never bound to any user account.
  4. `POST /2fa/verify` accepts `secret` directly in the client request body (`payload.secret`) and verifies against it. Any client can submit an arbitrary secret and valid TOTP code to pass verification.
- **Impact:** Complete bypass of 2FA. Fails to provide any security benefit while falsely claiming RFC 6238 compliance.
- **Required Remediation:** If retained, bind TOTP to authenticated user, encrypt secrets at rest using AES-GCM, require code proof before activation, and verify against persisted DB secret. If deferred, safely remove/disable endpoints and update documentation.

---

### Finding F25-02: Access-Token Revocation Bypass on Redis Failure
- **Status:** `CONFIRMED`
- **Severity:** `HIGH`
- **Location:** `backend/app/core/dependencies.py:108-109`
- **Root Cause:**
  In `get_current_user`, when verifying whether `jti` or `family_id` is revoked via Redis blocklist, an `aioredis.RedisError` exception is caught with `pass`:
  ```python
  except aioredis.RedisError:
      pass
  ```
  If Redis is down or timing out, this blocklist check is silently bypassed. A revoked access token or revoked token family continues to successfully authenticate.
- **Impact:** Revocation state is completely lost during distributed cache degradation. Stolen/revoked tokens regain validity.
- **Required Remediation:** Implement authoritative DB fallback check against `user_sessions` or fail-closed authentication error (`503 Service Unavailable` or `401 Unauthorized`) for sensitive tokens when revocation status cannot be verified.

---

### Finding F25-03: Rate Limiter Degradation, Unbounded Memory & Broad Exception Swallowing
- **Status:** `CONFIRMED`
- **Severity:** `MEDIUM`
- **Location:** `backend/app/core/rate_limiter.py:84-102`
- **Root Cause:**
  `is_rate_limited` catches broad `Exception as exc:` and triggers fallback for any runtime error (including `TypeError`, `KeyError`, etc.).
  The fallback `self._memory_cache` dictionary appends timestamps with no TTL eviction, no LRU bound, and no max size, leading to memory exhaustion under sustained load. Furthermore, process-local memory cannot enforce distributed consistency across multi-worker Gunicorn/Uvicorn deployments.
- **Impact:** Programming defects disguised as infrastructure outages; memory leakage; multi-worker rate-limit circumvention.
- **Required Remediation:** Catch specific Redis exceptions (`aioredis.RedisError`, `asyncio.TimeoutError`). Implement bounded LRU/TTL cleanup for local fallback. Reconcile fail-closed policy per endpoint.

---

### Finding F25-04: Role Vocabulary Inconsistency & Wildcard ADMIN Superuser Privileges
- **Status:** `CONFIRMED`
- **Severity:** `HIGH`
- **Location:** `backend/app/core/authorization.py:19`, `backend/app/models/enums.py:6-12`
- **Root Cause:**
  `RoleChecker` unilaterally injects `UserRoleEnum.ADMIN.value` into all endpoint authorization sets:
  ```python
  self.allowed_roles.add(UserRoleEnum.ADMIN.value)
  ```
  This creates wildcard superuser privileges bypassing all scoped RBAC. Furthermore, `UserRoleEnum` defines `DRIVER`, `OWNER`, `GUARD`, `OPERATIONS`, `ADMIN`, while PRD specifies `DRIVER`, `SPACE_OWNER`, `SECURITY_GUARD`, `OPS`.
- **Impact:** Uncontrolled privilege escalation for administrative accounts; architectural drift between PRD and database schema.
- **Required Remediation:** Restrict wildcard bypass. Reconcile role vocabulary with compatibility mappings. Explicitly scope operations privileges.

---

### Finding F25-05: Access-Token Lifetime Mismatch (15 Minutes vs. 60 Minutes)
- **Status:** `CONFIRMED`
- **Severity:** `MEDIUM`
- **Location:** `backend/app/core/config.py:61`, `backend/app/services/auth_service.py:235, 414`, `backend/app/schemas/auth.py:63`
- **Root Cause:**
  `config.py` sets `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60` and `auth_service.py` hardcodes `"expires_in": 3600`. However, Phase 02 documentation (`PHASE_02_API_CONTRACTS.md`, `PHASE_02_IMPLEMENTATION_REPORT.md`) explicitly specified a 15-minute access token (900 seconds) to mitigate token theft risks.
- **Impact:** Discrepancy between architectural security claims and runtime token validity. Excessive exposure window for compromised access tokens.
- **Required Remediation:** Centralize token TTL in `Settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15` (900 seconds). Align schemas, service responses, and client refresh scheduling.

---

### Finding F25-06: Non-Atomic Refresh Token Rotation & Overbroad User-Wide Revocation
- **Status:** `CONFIRMED`
- **Severity:** `HIGH`
- **Location:** `backend/app/services/auth_service.py:287-325`
- **Root Cause:**
  1. `select(UserSession).where(UserSession.refresh_token_hash == token_hash)` executes without row-level locking (`with_for_update()`). Under concurrent requests, two requests can simultaneously consume the same token without triggering reuse detection.
  2. When reuse IS detected, lines 298-302 revoke ALL sessions for the entire user account across all devices:
     ```python
     update(UserSession).where(UserSession.user_id == session_rec.user_id)
     ```
     This violates token family isolation by terminating unrelated legitimate sessions on other devices.
- **Impact:** Race conditions during rapid network retries; denial of service across all user devices upon single token reuse.
- **Required Remediation:** Use `with_for_update()` for atomic refresh token consumption. Scope reuse revocation strictly to `family_id`.

---

### Finding F25-07: Firebase Exception Details Leaked to Client Responses
- **Status:** `CONFIRMED`
- **Severity:** `MEDIUM`
- **Location:** `backend/app/integrations/firebase.py:108-111`
- **Root Cause:**
  In `verify_firebase_id_token`:
  ```python
  except Exception as exc:
      logger.warning("Firebase Admin token verification failed: %s", exc)
      if settings.is_production:
          raise UnauthorizedException(
              detail=f"Firebase ID token verification failed: {exc!s}",
              code="FIREBASE_TOKEN_INVALID",
          )
  ```
  `{exc!s}` directly returns raw internal Firebase exceptions, SDK error traces, and project metadata to the client.
- **Impact:** Information leakage aiding attacker reconnaissance.
- **Required Remediation:** Return static, sanitized RFC 7807 error detail (`"The provided authentication token is invalid or expired."`) while logging full error details internally.

---

### Finding F25-08: Flutter Interceptor Missing `/auth/exchange` Exclusion & Concurrent 401 Race
- **Status:** `CONFIRMED`
- **Severity:** `MEDIUM`
- **Location:** `mobile/lib/core/network/api_client.dart:76-82`
- **Root Cause:**
  1. `isAuthEndpoint` excludes `/auth/firebase-exchange` but not `/auth/exchange`, risking infinite recursion if the exchange route rejects credentials with 401.
  2. `if (response?.statusCode == 401 && !isAuthEndpoint && !_isRefreshing)` does not queue subsequent requests arriving while `_isRefreshing == true`. They immediately fail with 401 instead of waiting for token renewal.
- **Impact:** User UI jank, dropped parallel requests during token expiration, and potential refresh loops.
- **Required Remediation:** Add all auth and exchange endpoints to exclusion list. Implement request queueing during active refresh.

---

### Finding F25-09: Unsafe Firebase Identity Linking & Account Takeover Risk
- **Status:** `CONFIRMED`
- **Severity:** `CRITICAL`
- **Location:** `backend/app/services/auth_service.py:118-125, 158-161`
- **Root Cause:**
  `create_user_session` queries users with `or_(User.phone_number == phone_number, User.firebase_uid == firebase_uid)`.
  If a phone matches an existing account but has a different `firebase_uid`, lines 158-159 silently overwrite the user's `firebase_uid`:
  ```python
  if firebase_uid and user.firebase_uid != firebase_uid:
      user.firebase_uid = firebase_uid
  ```
  An attacker authenticating with a recycled phone number or malicious Firebase identity can overwrite the legitimate owner's UID and take over the account.
- **Impact:** Account takeover and identity corruption.
- **Required Remediation:** Enforce strict identity verification. If phone matches but UID conflicts (or vice versa), reject with a secure conflict error. Never overwrite linked identities without explicit re-verification.

---

## 3. Finding Summary Table

| ID | Finding | Status | Severity | Primary File Affected |
|:---|:---|:---:|:---:|:---|
| **F25-01** | TOTP 2FA Unbound & Client-Authoritative | CONFIRMED | CRITICAL | `backend/app/api/v1/endpoints/auth.py` |
| **F25-02** | Access Token Revocation Bypass on Redis Down | CONFIRMED | HIGH | `backend/app/core/dependencies.py` |
| **F25-03** | Rate Limiter Unbounded Memory & Catch-All | CONFIRMED | MEDIUM | `backend/app/core/rate_limiter.py` |
| **F25-04** | Role Inconsistency & Wildcard ADMIN Grant | CONFIRMED | HIGH | `backend/app/core/authorization.py` |
| **F25-05** | Access Token Lifetime Inconsistency (15m vs 60m) | CONFIRMED | MEDIUM | `backend/app/core/config.py` |
| **F25-06** | Non-Atomic Refresh & Overbroad Revocation | CONFIRMED | HIGH | `backend/app/services/auth_service.py` |
| **F25-07** | Firebase Exception Detail Leakage | CONFIRMED | MEDIUM | `backend/app/integrations/firebase.py` |
| **F25-08** | Flutter Interceptor Exclusions & 401 Queueing | CONFIRMED | MEDIUM | `mobile/lib/core/network/api_client.dart` |
| **F25-09** | Unsafe Identity Linking & Account Takeover | CONFIRMED | CRITICAL | `backend/app/services/auth_service.py` |
