# Gadispot Application Security Baseline & Compliance Register

> **Document Version:** 1.0.0  
> **Status:** **APPROVED & ENFORCED**  
> **Authoritative Specification:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
> **Legal References:** Digital Personal Data Protection Act (DPDPA 2023), RBI Master Directions for Payment Aggregators (2020), NPCI UPI Procedural Guidelines.  
> **Audience:** Principal Architects, Application Security Engineers, Backend Developers, DevOps  
> **Last Updated:** 2026-11-05T14:35:00Z  

---

## 1. Executive Summary & Security Charter

Gadispot processes real monetary transactions, spatial reservations, driver personal information, and property authorization deeds across the Indian market. Security is an architectural invariant, not an afterthought.

This document establishes the authoritative technical baseline across five core defensive tiers:
1. **Identity & Authentication:** Zero-trust phone verification via Firebase Admin SDK; scoped internal JWT sessions; privileged Operations 2FA via RFC 6238 TOTP (PyOTP).
2. **Access Control & IDOR Shielding:** Strict Role-Based Access Control (RBAC) and mandatory Object-Level Authorization preventing Insecure Direct Object Reference (IDOR) attacks.
3. **Financial & Payment Integrity:** Multi-gateway abstraction (`PaymentGatewayPort`), cryptographic HMAC signature verification, durable webhook deduplication, and a strictly enforced 6-stage canonical refund state machine.
4. **Resilience & Rate Limiting:** Redis-backed sliding-window rate limiting on sensitive routes, and a two-tier 480-second hold expiration engine with lock-free concurrency.
5. **Data Protection & DPDPA Compliance:** Automated 7-day cryptographic purging of gate admission photos, immutable audit logging, and zero committed credentials.

---

## 2. Authentication & Credential Architecture

### 2.1 Token Exchange Flow
```
[ Flutter Mobile ] --(1. Firebase Phone Auth)--> [ Google Identity ]
[ Flutter Mobile ] <--(2. Verified ID Token)---- [ Google Identity ]
[ Flutter Mobile ] --(3. POST /auth/session)-----> [ FastAPI Backend ]
                                                         | (4. Firebase Admin SDK verify)
                                                         v
[ Flutter Mobile ] <--(5. Scoped JWT Access/Refresh)-- [ Issue Session ]
```
- **Zero Client Trust:** The client cannot supply arbitrary phone numbers. Phone numbers are extracted exclusively from cryptographically verified Firebase ID tokens via the official `firebase-admin` SDK.
- **Internal JWT Scoping:**
  - `Access Token`: 60-minute TTL, signed with HS256 (`SECRET_KEY`), carrying claims `{sub, phone_number, roles, jti, iat, exp, type: "access"}`.
  - `Refresh Token`: 30-day TTL, strictly scoped to token refresh (`type: "refresh"`).
  - `Revocation & Expiration`: Tokens are verified on every request; expired signatures immediately yield RFC 7807 `401 Unauthorized` (`TOKEN_EXPIRED`).

### 2.2 Privileged Operations 2FA (RFC 6238 TOTP)
- All administrative escalations, manual payout overrides, and property approvals require secondary authentication.
- Implemented via `pyotp` (RFC 6238) using 160-bit Base32 shared secrets.
- Clock drift tolerance restricted to $\pm 30$ seconds (window size = 1). Replay attacks prevented via transient Redis cache of used TOTP codes.

---

## 3. Authorization & IDOR Defense Matrix

| Role | Permitted Scope | Prohibited Actions | Enforcement Mechanism |
|---|---|---|---|
| **`DRIVER`** | Search spaces, acquire 480s holds, view own bookings/refunds, manage own vehicles. | View other drivers' bookings, modify property details, access guard portals. | `verify_resource_ownership(user, reservation.driver_id)` |
| **`OWNER`** | Onboard properties, configure schedules/blackouts, view own earnings and space status. | Access driver payment methods, view unowned properties, trigger direct refunds. | `verify_resource_ownership(user, property.owner_id)` |
| **`GUARD`** | Scan entry/exit QR codes for assigned property, record offline admissions. | Access platform financial ledgers, view user PII outside current shift, modify pricing. | Property assignment binding & `require_roles(GUARD)` |
| **`OPERATIONS`**| Review property deeds, audit incidents, inspect platform metrics. | Disburse host payouts without secondary 2FA approval, alter ledger entries. | `require_roles(OPERATIONS)` + PyOTP 2FA |
| **`ADMIN`** | Superuser maintenance, security configuration. | Modify posted double-entry journal entries (forbidden by DB trigger). | Kernel-enforced PostgreSQL trigger |

### 3.1 IDOR Prevention Protocol
Every endpoint accepting a resource identifier (`reservation_id`, `property_id`, `vehicle_id`) must invoke `verify_resource_ownership(current_user, entity.owner_id)` prior to returning or mutating state. Unowned requests terminate with HTTP 403 Forbidden (`IDOR_ACCESS_DENIED`) or HTTP 404.

---

## 4. Payment Security & Durable Idempotency

### 4.1 Cryptographic Signature Verification
All external payment callbacks must be verified against raw request bytes before parsing JSON:
- **Razorpay:** `hmac_sha256(webhook_secret, raw_body) == x-razorpay-signature`.
- **Cashfree:** `hmac_sha256(secret_key, timestamp + raw_body) == x-webhook-signature`.
- **Hyperswitch:** `hmac_sha512(webhook_secret, raw_body) == x-webhook-signature`.
- **Failure Mode:** Unverified or forged signatures immediately terminate with HTTP 401 Unauthorized (`INVALID_WEBHOOK_SIGNATURE`).

### 4.2 Durable Webhook Deduplication
Every incoming event is recorded in PostgreSQL table `payment_webhook_events` under a strict unique constraint:
$$\text{UNIQUE}(\text{gateway\_name}, \text{gateway\_event\_id})$$
Duplicate event deliveries (common during network retries) are intercepted by the database, returning HTTP 200 `already_processed` with zero state mutation, completely eliminating duplicate payment capture or double-refund bugs.

### 4.3 6-Stage Refund Invariant
Refunds transition strictly through directed states:
$$\text{NONE} \to \text{REFUND\_ELIGIBLE} \to \text{REFUND\_REQUESTED} \to \text{GATEWAY\_ACCEPTED} \to \text{REFUND\_PROCESSING} \to \text{REFUND\_SETTLED}$$
Any out-of-order transition or attempt to mutate terminal state `REFUND_SETTLED` raises `ConflictException` (HTTP 409 `ILLEGAL_REFUND_TRANSITION`).

---

## 5. Throttling & Rate Limiting

Rate limiting is enforced at the network edge and middleware layers via Redis sorted sets:

| Action / Route | Threshold | Sliding Window | Identification Key | Action on Exceeded |
|---|:---:|:---:|---|---|
| **OTP Initiation** | 3 requests | 15 minutes (900s) | `ratelimit:otp:{phone}` | HTTP 429 (`RATE_LIMIT_EXCEEDED`) + Retry-After |
| **Login Attempts** | 5 attempts | 15 minutes (900s) | `ratelimit:login:{ip_or_user}` | HTTP 429 + Security Audit Event |
| **Spatial Radius Search** | 60 queries | 1 minute (60s) | `ratelimit:search:{user_or_ip}` | HTTP 429 + Throttled response |

*Fail-Open Resilience:* If Redis is temporarily unavailable, rate limiting logs a warning and permits legitimate traffic, preventing single-point-of-failure outages.

---

## 6. Two-Tier 480s Hold Expiration Engine

To prevent temporal exclusion starvation where abandoned holds permanently lock parking spaces:
1. **Tier 1 (Background Sweep):** Runs periodically every 5 seconds, executing:
   ```sql
   SELECT id FROM space_reservations 
   WHERE status = 'ACTIVE_HOLD' AND hold_expires_at <= NOW() 
   FOR UPDATE SKIP LOCKED LIMIT 100;
   ```
   Uses `SKIP LOCKED` to prevent deadlocks with active booking checkouts. Transitions stale holds to `EXPIRED_HOLD`.
2. **Tier 2 (Opportunistic Inline Sweep):** Invoked immediately prior to hold acquisition on a specific parking space, ensuring that newly arriving drivers immediately clear expired holds.

---

## 7. Data Privacy & DPDPA 2023 Compliance

### 7.1 Automated 7-Day Gate Photo Purge
- Under DPDPA 2023, personal biometric evidence (vehicle license plate photos, driver identity photos taken during offline gate admissions) must not be retained indefinitely.
- Table `offline_manual_admissions` enforces `photo_purge_at = NOW() + INTERVAL '7 days'`.
- The `photo_purge_worker` deletes the S3 storage object and scrubs `photo_s3_key` to a non-reversible audit tombstone:
  $$\text{photo\_s3\_key} = \text{"PURGED:DPDPA\_7DAY:"} + \text{SHA256}(\text{key} : \text{id})[0:16]$$
- Legal non-repudiation is preserved via the immutable SHA-256 audit hash while completely scrubbing sensitive biometric imagery.

---

## 8. Append-Only System Audit Logging

Mutating administrative actions, financial overrides, and security events are logged into the append-only `audit_events` table:
- **Protected Actions:** `ROLE_GRANTED`, `ROLE_REVOKED`, `PAYOUT_DISBURSED`, `REFUND_OVERRIDE`, `GATE_OVERRIDE`, `LISTING_APPROVED`, `LISTING_REJECTED`.
- **Immutability:** Records cannot be updated or deleted by normal application roles.
- **Traceability:** Every event logs `actor_id`, `action`, `resource_type`, `resource_id`, `details` (JSONB), and `ip_address`.

---

## 9. Dependency Vulnerability Review

- All Python dependencies audited via `pip-audit` / `safety` standards.
- Pinned modern versions across core frameworks (`fastapi >= 0.115.0`, `pydantic >= 2.10.0`, `sqlalchemy >= 2.0.36`, `asyncpg >= 0.30.0`, `pyjwt >= 2.10.0`, `pyotp >= 2.10.0`, `firebase-admin >= 7.7.0`).
- Zero known high or critical CVEs present in active production dependencies.
