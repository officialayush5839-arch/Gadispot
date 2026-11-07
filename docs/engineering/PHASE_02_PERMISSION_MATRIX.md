# GADISPOT — PHASE 02 ROLE & PERMISSION MATRIX (RBAC SPECIFICATION)
**Document Reference:** `RBAC-GSP-2026-P02-V1.0`  
**Governing Baseline:** `PRD-GSP-2026-V2.3.2-VERIFIED`  
**Phase:** 02 — Identity, Authentication, Authorization & RBAC  
**Status:** APPROVED & TESTED  
**Date:** November 2026

---

## 1. Executive Summary

This document specifies the authoritative Role-Based Access Control (RBAC) model, granular permission mappings, resource scopes, and authorization boundaries for Gadispot Phase 02.

The Gadispot platform recognizes four standard product roles:
1. **`DRIVER`**: Urban motorists discovering parking, managing vehicles, creating reservations, and presenting access QR credentials.
2. **`SPACE_OWNER`**: Property owners listing private parking slots, defining schedules, and monitoring space occupancy and payouts.
3. **`SECURITY_GUARD`**: On-premise gate personnel scanning access QR codes, performing offline/online access verification, and logging manual admissions.
4. **`OPERATIONS` (Ops)**: Platform administrative staff handling dispute resolutions, manual financial adjustments, property verification, and audit logs.

All authorization enforcement is strictly executed on the server side (`FastAPI` dependency injection and service layers). Client-side UI controls only adjust navigation and presentation and are never treated as security boundaries.

---

## 2. Granular Permission Definitions

| Permission Code | Category | Description |
|---|---|---|
| `profile:read` | Identity | Read own profile, assigned roles, and account status |
| `profile:update` | Identity | Modify own profile attributes (name, email) |
| `vehicle:create` | Vehicles | Register and link vehicles to personal account |
| `vehicle:read_own` | Vehicles | View personal registered vehicles |
| `booking:create` | Bookings | Initiate parking hold and complete space reservations |
| `booking:read_own` | Bookings | View details and status of own bookings |
| `booking:cancel_own` | Bookings | Cancel active bookings within permissible cancellation windows |
| `space:create` | Inventory | Register new parking space listings |
| `space:read_own` | Inventory | View occupancy, status, and earnings of owned spaces |
| `space:update_own` | Inventory | Update schedules, pricing, and availability of owned spaces |
| `gate:scan_qr` | Admissions | Scan and cryptographically verify driver parking access QR tokens |
| `gate:manual_admission` | Admissions | Record offline manual entry with timestamp and vehicle number |
| `ops:view_all_users` | Administration | Inspect platform user profiles and account statuses |
| `ops:suspend_user` | Administration | Suspend or deactivate abusive user accounts |
| `ops:view_audit_logs` | Security | Inspect tamper-evident audit logs and security telemetry |
| `ops:post_journal` | Financials | Post double-entry financial adjustments with dual approval |

---

## 3. Comprehensive Role-Permission Mapping Matrix

| Resource & Operation | HTTP Method & Route Pattern | DRIVER | SPACE_OWNER | SECURITY_GUARD | OPERATIONS | Authorization Level |
|---|---|---|---|---|---|---|
| **Auth / Identity** | | | | | | |
| Exchange Token | `POST /api/v1/auth/session` | ALLOW | ALLOW | ALLOW | ALLOW | Public / Pre-auth |
| Refresh Token | `POST /api/v1/auth/refresh` | ALLOW | ALLOW | ALLOW | ALLOW | Authenticated Refresh |
| Logout Session | `POST /api/v1/auth/logout` | ALLOW | ALLOW | ALLOW | ALLOW | Authenticated User |
| Read Own Profile | `GET /api/v1/auth/me` | ALLOW | ALLOW | ALLOW | ALLOW | `profile:read` (Own Principal) |
| Switch Viewport Role | `POST /api/v1/auth/switch-role` | ALLOW* | ALLOW* | DENY | DENY | Dual-Role Only (Driver/Owner) |
| Setup 2FA (RFC 6238) | `POST /api/v1/auth/2fa/setup` | DENY | DENY | ALLOW | ALLOW | Privileged 2FA Policy |
| Verify 2FA | `POST /api/v1/auth/2fa/verify` | DENY | DENY | ALLOW | ALLOW | Privileged 2FA Policy |
| **Bookings & Vehicles** | | | | | | |
| Create Booking Hold | `POST /api/v1/bookings` | ALLOW | DENY | DENY | DENY | `booking:create` |
| View Own Booking | `GET /api/v1/bookings/{id}` | SCOPED | DENY | DENY | ALLOW | `booking:read_own` + Ownership Check |
| View Other's Booking | `GET /api/v1/bookings/{id}` | DENY | DENY | DENY | ALLOW | Explicit Cross-Tenant IDOR Shield |
| Register Vehicle | `POST /api/v1/vehicles` | ALLOW | DENY | DENY | DENY | `vehicle:create` |
| **Parking Spaces** | | | | | | |
| Create Space Listing | `POST /api/v1/spaces` | DENY | ALLOW | DENY | DENY | `space:create` |
| View Own Space | `GET /api/v1/spaces/{id}` | DENY | SCOPED | DENY | ALLOW | `space:read_own` + Ownership Check |
| View Other's Space | `GET /api/v1/spaces/{id}` | DENY | DENY | DENY | ALLOW | Explicit Cross-Tenant IDOR Shield |
| Update Space Schedule | `PATCH /api/v1/spaces/{id}/schedule` | DENY | SCOPED | DENY | ALLOW | `space:update_own` + Ownership Check |
| **Gate Admissions** | | | | | | |
| Scan Access QR | `POST /api/v1/access/scan` | DENY | DENY | ALLOW | ALLOW | `gate:scan_qr` |
| Record Offline Entry | `POST /api/v1/access/offline-entry` | DENY | DENY | ALLOW | ALLOW | `gate:manual_admission` |
| **Operations & Security**| | | | | | |
| View All Users | `GET /api/v1/admin/users` | DENY | DENY | DENY | ALLOW | `ops:view_all_users` |
| Suspend User Account | `POST /api/v1/admin/users/{id}/suspend`| DENY | DENY | DENY | ALLOW | `ops:suspend_user` |
| View Audit Logs | `GET /api/v1/admin/audit-logs` | DENY | DENY | DENY | ALLOW | `ops:view_audit_logs` |
| Post Journal Entry | `POST /api/v1/admin/ledgers/journals` | DENY | DENY | DENY | ALLOW | `ops:post_journal` (MFA Enforced) |

*\* Note on `switch-role`: Multi-role switching is strictly permitted only between `DRIVER` and `SPACE_OWNER` viewports for verified users possessing both roles in `user_roles`. Requests to switch to `SECURITY_GUARD` or `OPERATIONS` are blocked with HTTP 403 `ROLE_SWITCH_PROHIBITED`.*

---

## 4. Architectural Enforcement Mechanics

### 4.1 Dependency-Based Enforcement
FastAPI dependencies in `app.core.dependencies` and `app.core.authorization`:
- `get_current_user`: Resolves caller JWT, checks Redis blocklist, checks `is_active=True`, checks `status=AccountStatus.ACTIVE`.
- `require_roles(roles: list[UserRoleEnum])`: Validates user possesses one of the authorized roles.
- `require_permissions(perms: list[str])`: Validates active role satisfies the required permission set.
- `verify_resource_ownership(resource_owner_id: UUID, current_user: User)`: Validates IDOR protection.

### 4.2 Account Status Lifecycle Gates
Account status is an immutable enum (`ACTIVE`, `DISABLED`, `SUSPENDED`).
- `ACTIVE`: Full access granted according to assigned roles.
- `DISABLED`: Account self-deactivated or pending verification. Blocked with HTTP 403 `ACCOUNT_DEACTIVATED`.
- `SUSPENDED`: Account administratively suspended due to fraud or policy violation. Blocked with HTTP 403 `ACCOUNT_SUSPENDED`.

---

## 5. Verification Test Traceability

| Requirement | Test Identifier | Verification Status |
|---|---|---|
| Role verification & RBAC | `tests/api/test_security_rbac.py::test_rbac_and_idor_ownership_checks` | PASSED |
| Self-escalation prevention | `tests/security/test_phase02_iam_hardening.py::test_multi_role_switching_and_escalation_defense` | PASSED |
| Cross-tenant IDOR shielding | `tests/security/test_phase02_iam_hardening.py::test_booking_idor_shielding` | PASSED |
| Account status enforcement | `tests/test_identity_lifecycle.py::test_get_current_user_dependency_status_enforcement` | PASSED |
| RFC 7807 problem details | `tests/test_identity_lifecycle.py::test_api_account_status_rfc7807_responses` | PASSED |
