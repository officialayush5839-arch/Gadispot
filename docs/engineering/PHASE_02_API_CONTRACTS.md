# GADISPOT — PHASE 02 API CONTRACTS SPECIFICATION
**Document Reference:** `API-GSP-2026-P02-V1.0`  
**Governing Baseline:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
**Phase:** 02 — Identity, Authentication, Authorization & RBAC  
**Content-Type:** `application/json`  
**Error Format:** RFC 7807 `application/problem+json`  
**Date:** November 2026

---

## 1. Overview

This document specifies the complete API contracts for all authentication, session management, identity lifecycle, and role switching endpoints implemented under Phase 02.

---

## 2. Authentication Endpoints

### 2.1 Exchange Firebase Token for Application Session
- **Path:** `POST /api/v1/auth/session` (Alias: `POST /api/v1/auth/exchange`)
- **Authentication:** None (Public / Client App with verified Firebase token)
- **Rate Limit Policy:** `5 requests / 900s` per IP (Fail-closed)
- **Audit Event:** `AUTH_SESSION_CREATED` on success; `AUTH_SESSION_REJECTED` on failure.

#### Request Schema:
```json
{
  "id_token": "string (Firebase-issued ID token)"
}
```

#### Success Response (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "phone_number": "+919876543210",
    "full_name": "Ayush Sharma",
    "roles": ["DRIVER"]
  }
}
```

#### Error Responses (RFC 7807):
- **401 Unauthorized (`FIREBASE_TOKEN_INVALID`):**
```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Firebase ID token is invalid, expired, or malformed.",
  "code": "FIREBASE_TOKEN_INVALID"
}
```
- **429 Too Many Requests (`RATE_LIMIT_EXCEEDED`):**
```json
{
  "type": "about:blank",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit of 5 requests per 900s exceeded.",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after_seconds": 320
}
```

---

### 2.2 Refresh Session Access Token
- **Path:** `POST /api/v1/auth/refresh`
- **Authentication:** Refresh Token (provided in body or `Authorization: Bearer <token>` or `X-Refresh-Token` header)
- **Rate Limit Policy:** `10 requests / 60s` per IP (Fail-closed)
- **Audit Event:** `AUTH_TOKEN_ROTATED` on success; `AUTH_TOKEN_REPLAY_DETECTED` on family compromise.

#### Request Schema:
```json
{
  "refresh_token": "string (Single-use refresh token)"
}
```

#### Success Response (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "phone_number": "+919876543210",
    "full_name": "Ayush Sharma",
    "roles": ["DRIVER"]
  }
}
```

#### Error Responses (RFC 7807):
- **401 Unauthorized (`INVALID_REFRESH_TOKEN` / `REFRESH_TOKEN_REVOKED`):**
```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "The provided refresh token is revoked or already consumed.",
  "code": "REFRESH_TOKEN_REVOKED"
}
```

---

### 2.3 Terminate Session (Logout)
- **Path:** `POST /api/v1/auth/logout`
- **Authentication:** Authenticated Bearer Access Token + Active Refresh Token
- **Rate Limit Policy:** Standard API
- **Audit Event:** `AUTH_SESSION_REVOKED`

#### Request Schema:
```json
{
  "refresh_token": "string (optional if supplied via X-Refresh-Token header)"
}
```

#### Success Response (200 OK):
```json
{
  "status": "success",
  "message": "Session terminated and credentials revoked successfully."
}
```

---

### 2.4 Retrieve Current Authenticated Principal Profile
- **Path:** `GET /api/v1/auth/me`
- **Authentication:** `Authorization: Bearer <access_token>`
- **Rate Limit Policy:** Standard API
- **Audit Event:** None (read-only query)

#### Success Response (200 OK):
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "phone_number": "+919876543210",
  "full_name": "Ayush Sharma",
  "email": "ayush@example.com",
  "roles": ["DRIVER", "SPACE_OWNER"],
  "status": "ACTIVE",
  "is_active": true,
  "permissions": [
    "profile:read",
    "profile:update",
    "vehicle:create",
    "vehicle:read_own",
    "booking:create",
    "booking:read_own",
    "booking:cancel_own",
    "space:create",
    "space:read_own",
    "space:update_own"
  ],
  "firebase_uid": "firebase-uid-abcdef12345"
}
```

#### Error Responses (RFC 7807):
- **403 Forbidden (`ACCOUNT_SUSPENDED` / `ACCOUNT_DEACTIVATED`):**
```json
{
  "type": "about:blank",
  "title": "Forbidden",
  "status": 403,
  "detail": "Account is suspended. Contact operations support.",
  "code": "ACCOUNT_SUSPENDED"
}
```

---

### 2.5 Switch Active Viewport Role
- **Path:** `POST /api/v1/auth/switch-role`
- **Authentication:** `Authorization: Bearer <access_token>`
- **Rate Limit Policy:** Standard API
- **Audit Event:** `AUTH_ROLE_SWITCHED` on success; `AUTH_ROLE_SWITCH_PROHIBITED` on escalation attempt.

#### Request Schema:
```json
{
  "target_role": "SPACE_OWNER"
}
```

#### Success Response (200 OK):
```json
{
  "status": "success",
  "active_role": "SPACE_OWNER",
  "message": "Active viewport successfully switched to SPACE_OWNER"
}
```

#### Error Response (403 Forbidden):
```json
{
  "type": "about:blank",
  "title": "Forbidden",
  "status": 403,
  "detail": "User does not possess role 'OPERATIONS' or role switch is disallowed.",
  "code": "ROLE_SWITCH_PROHIBITED"
}
```

---

### 2.6 Operations 2FA TOTP Provisioning & Verification
- **Setup Path:** `POST /api/v1/auth/2fa/setup`
- **Verify Path:** `POST /api/v1/auth/2fa/verify`
- **Authentication:** Operations role
- **Rate Limit Policy:** `3 attempts per 5-minute window` on verify (Fail-closed)

#### Setup Response (200 OK):
```json
{
  "secret": "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
  "provisioning_uri": "otpauth://totp/Gadispot%20Operations:operations.user@gadispot.in?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=Gadispot%20Operations",
  "qr_code_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```

#### Verify Request:
```json
{
  "secret": "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
  "code": "123456"
}
```

#### Verify Response (200 OK):
```json
{
  "valid": true,
  "message": "Verification successful"
}
```
