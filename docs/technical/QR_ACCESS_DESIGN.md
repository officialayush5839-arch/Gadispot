# Gadispot (formerly SmartPark Exchange) — QR Access & Verification Architecture (V2.3)

> **Document Version:** 2.3.0  
> **Date:** October 31, 2026  
> **Authors:** Mobile Application Architect, Application Security Engineer, Principal Software Architect  
> **Status:** Authoritative Engineering Design (Targeted Revision V2.3)  

---

## 1. Architectural Separation of the Two QR Subsystems

A fatal flaw in early parking app designs is conflating payment confirmation credentials with physical gate access credentials. SmartPark enforces complete domain and cryptographic separation between the **Payment QR** and the **Parking Access QR**.

```
+---------------------------------------------------------------------------------------------------+
|                                  TWO DISTINCT QR CODE SYSTEMS                                     |
+------------------------------------+--------------------------------------------------------------+
| 1. Dynamic Payment QR              | 2. Parking Access Credentials (Entry & Exit)                 |
+------------------------------------+--------------------------------------------------------------+
| • Domain: Financial Settlement     | • Domain: Physical Gate Access & Security                   |
| • Generation Engine: Gateway API   | • Generation Engine: SmartPark Core Cryptographic Service    |
| • Consumer: Driver UPI Application | • Consumer: Guard Mobile Application (mobile_scanner)        |
| • Payload: NPCI UPI URI string     | • Payload: Opaque CSPRNG 128-bit Token (secrets.token_hex(16))|
| • Expiry: Exactly 480 Seconds (8m) | • Expiry: Phased (Entry Window vs Exit Window)              |
| • Replay Protection: Banking Switch| • Replay Protection: Database Atomic State Burn             |
| • Endpoint: NPCI Payment Gateway   | • Endpoint: POST /api/v1/access/validate-scan                |
+------------------------------------+--------------------------------------------------------------+
```

---

## 2. Complete Credential Lifecycle: Phased Token States & Extensions

A consumed entry credential cannot be reused for exit. SmartPark establishes distinct tokens with a formal 5-state lifecycle:

```
+----------------------------------------------------------------------------------------+
|                      TOKEN STATE MACHINE (ENTRY_TOKEN & EXIT_TOKEN)                    |
+----------------------------------------------------------------------------------------+
|                                                                                        |
|         +--------------+        Scheduled Start Window Reached                         |
|         |    ISSUED    | -------------------------------------------> [ ACTIVE ]       |
|         +--------------+                                                  |            |
|                |                                                          |            |
|                | Cancellation /                                           |            |
|                | GPRP Replaced                                            |            |
|                v                                                          v            |
|         +--------------+                                      +--------------------+   |
|         |   REVOKED    |                                      |      CONSUMED      |   |
|         +--------------+                                      +--------------------+   |
|                ^                                                          ^            |
|                |                                                          |            |
|                | Window Elapsed                               Valid Scan  |            |
|                | Without Scan                                 at Gate     |            |
|                +---------------------- [ EXPIRED ] <----------------------+            |
|                                                                                        |
+----------------------------------------------------------------------------------------+
```

### 2.1 Credential Specifications and Binding Rules
Every access token is cryptographically bound to an explicit context:
$$\text{Token Context} = \{\text{reservation\_id}, \text{parking\_space\_id}, \text{property\_id}, \text{token\_type}, \text{entropy\_128bit}\}$$

1. **`ENTRY_TOKEN`:**
   - *Format:* `spx_ent_` + 32-character hexadecimal string (`secrets.token_hex(16)` = 128 bits of entropy).
   - *Validity Window:* $[t_{\text{start}} - 15\text{m}, t_{\text{start}} + 30\text{m})$.
   - *State Transitions:*
     - Transitions from `ISSUED` to `ACTIVE` at $t_{\text{start}} - 15\text{m}$.
     - Transitions to `CONSUMED` upon verified guard entry scan.
     - Transitions to `EXPIRED` if no scan occurs by $t_{\text{start}} + 30\text{m}$ (triggering `NO_SHOW`).
     - Transitions to `REVOKED` if driver cancels or booking is replaced under GPRP.
2. **`EXIT_TOKEN`:**
   - *Format:* `spx_ext_` + 32-character hexadecimal string (`secrets.token_hex(16)`).
   - *Pre-caching:* Minted upon booking confirmation and pre-cached securely in driver app local storage upon successful check-in, enabling display even if the driver's phone loses cellular connectivity in basement parking.
   - *Validity Window:* $[t_{\text{checkin}}, t_{\text{end}} + 15\text{m})$.
   - *Dynamic Session Extension:* When a driver purchases a 30m or 60m extension (`EXT-001`), the database atomically updates `valid_until = new_end_time + 15m`. The client updates the local token metadata upon receipt of confirmation.
   - *Overstay Behavior:* If exit occurs after $t_{\text{end}} + 15\text{m}$, the token is still readable by the guard scanner. The scanner identifies the overstay duration, computes the penalty, prompts payment, and transitions the token to `CONSUMED` upon clearance.

---

## 3. Online Authoritative Gate Validation Workflow

### 3.1 Entry Scan Workflow
1. Driver presents Entry QR (`SCR-104`).
2. Guard scans QR using Flutter camera engine (`SCR-301`).
3. Guard app calls `POST /api/v1/access/validate-scan` with payload `{ "token": "spx_ent_...", "gate_id": "...", "guard_id": "..." }`.
4. Backend executes in an atomic transaction:
   - Queries `access_credentials` matching `opaque_token` where `token_type = 'ENTRY'`.
   - Checks:
     - Token status must be `ACTIVE` or `ISSUED` (within valid window).
     - Current server timestamp must fall within $[t_{\text{start}} - 15\text{m}, t_{\text{start}} + 30\text{m})$.
     - Property ID of reservation must match guard's assigned property.
   - Atomically updates:
     - `access_credentials.status = 'CONSUMED'`, `consumed_at = NOW()`, `consumed_by_guard_id = guard_id`.
     - `space_reservations.status = 'ACTIVE_SESSION'`, `updated_at = NOW()`.
     - Inserts record into `access_scan_logs`.
   - Commits transaction.
5. Guard app flashes **BOLD GREEN** with bay number, vehicle plate, and scheduled exit time.
6. Driver app transitions to Active Parking Session screen with live timer and pre-cached Exit QR pass.

---

## 4. Deep Basement Outage: Controlled Manual Exception Protocol

### 4.1 Reality of Underground Mobile Dead Zones
In Indian commercial buildings and basement parking complexes (B1/B2/B3), 4G/5G mobile signals frequently drop to zero. A cached offline schedule on a guard's phone **cannot authoritatively verify booking validity** because the booking may have been cancelled, refunded under LPRP, or revoked while the guard was offline.

### 4.2 The Controlled Manual Exception Protocol
SmartPark establishes that offline admission is **never treated as an equivalent verified QR scan**. Instead, it is treated as an **Audited Controlled Manual Exception** (`MANUAL_OVERRIDE_PENDING_RECONCILIATION`):

```
[Guard Scanner Detects Network Timeout (>3s)]
                       |
                       v
     [Guard App Enters Offline Exception Mode]
                       |
       1. Guard enters vehicle registration plate manually.
       2. Guard app matches plate against locally encrypted shift cache (read-only reference).
       3. Guard takes photo proof of vehicle registration plate at gate.
       4. Guard captures Driver Phone Number last 4 digits.
       5. Guard selects Reason: "DEEP_BASEMENT_OUTAGE".
                       |
                       v
 [Guard Taps "ADMIT ON CONDITIONAL MANUAL EXCEPTION"]
                       |
 • Guard app flashes AMBER WARNING: "CONDITIONAL ADMISSION - PENDING RECONCILIATION".
 • Action is cryptographically signed and queued in local encrypted SQLite queue.
                       |
                       v
 [Device Reconnects to 4G/Wi-Fi Surface Network]
                       |
 • App flushes signed audit queue: POST /api/v1/access/reconcile-offline-admissions.
                       |
          +------------+------------+
          |                         |
          v                         v
   [RECONCILED CLEANLY]      [CONFLICT DETECTED]
   (Booking was valid;       (Booking was cancelled, refunded,
   session recorded)          or plate duplicate)
                                    |
                                    v
                             [Security Incident Created]
                             - Property manager alerted
                             - Penalty fee assessed to driver account
```

### 4.3 Security, Privacy & Data Retention Controls for Offline Storage
1. **Local Storage Encryption:** Guard offline records and cached shift schedules are stored in an encrypted SQLite database using **SQLCipher (AES-256)**. The encryption key is derived from the guard's authenticated session JWT and is never stored on disk.
2. **Device Authentication & Guard Scoping:** The guard device must authenticate every 12 hours via online OTP. Shift caches are strictly scoped to the guard's assigned property and active 8-hour shift.
3. **Automated Photo Proof Purge Rule:** Gate photos captured during manual exceptions are uploaded to a private AWS S3 bucket. An automated S3 lifecycle expiration policy **permanently deletes vehicle gate photos within 7 days of successful backend reconciliation**, retaining only the cryptographic event hash for permanent audit.
4. **Tamper-Evident Event Chaining:** Every local offline admission record includes a SHA-256 hash incorporating the previous entry's hash, timestamp, vehicle plate, and guard ID, preventing local database tampering.
5. **Conflict Resolution:** If a reconciled booking reveals that the driver parked after cancelling or receiving an LPRP refund, SmartPark automatically bills the driver's default payment method or flags the account with an outstanding penalty balance.
