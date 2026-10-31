# SmartPark Exchange — Security Threat Model & Privacy Impact Review

> **Document Version:** 2.2.0  
> **Date:** 2026-10-31  
> **Authors:** Application Security Engineer, Privacy & Data Protection Specialist, Principal Software Architect  
> **Compliance Baseline:** Digital Personal Data Protection Act (DPDPA) 2023 / OWASP Top 10 API / STRIDE  
> **Status:** Approved Engineering Baseline (V2.2 Harmonized)  

---

## 1. Executive Summary & Security Perimeter

SmartPark Exchange bridges the digital domain (mobile apps, cloud APIs, payment aggregators) with the physical domain (real-world vehicle gates, private residential driveways, security guards). This cyber-physical boundary introduces unique security threats: physical vehicle unauthorized parking, QR code replay and screenshot sharing, fraudulent property listings, and payment webhook spoofing.

This review presents a comprehensive **STRIDE Threat Model**, vulnerability remediation blueprints, and a **DPDPA 2023 Privacy Impact Assessment**.

---

## 2. STRIDE Threat Model & Vulnerability Analysis

```
+---------------------------------------------------------------------------------------------------+
|                                STRIDE SECURITY THREAT MATRIX                                      |
+----+----------------------+---------------------------------+-------------------------------------+
| ID | Threat Category      | Attack Vector                   | Core Architectural Mitigation       |
+----+----------------------+---------------------------------+-------------------------------------+
| S  | **Spoofing**         | Webhook Signature Forgery       | Raw HMAC-SHA256 signature check     |
|    |                      | SMS OTP Interception            | Play Integrity + Firebase Auth SDK  |
|    |                      | QR Screen Forgery               | Opaque 128-bit high-entropy token   |
+----+----------------------+---------------------------------+-------------------------------------+
| T  | **Tampering**        | Checkout Price Manipulation     | Authoritative backend pricing math  |
|    |                      | Booking Time Interval Overlap   | PostgreSQL GiST exclusion constraint|
|    |                      | Legal Document Upload Tampering | S3 direct-upload virus & MIME check |
+----+----------------------+---------------------------------+-------------------------------------+
| R  | **Repudiation**      | Driver denies parking session   | Immutable access_scans entry record |
|    |                      | Guard denies gate admission     | Guard-authenticated scan audit log  |
|    |                      | Altered financial payouts       | Append-only double-entry ledger     |
+----+----------------------+---------------------------------+-------------------------------------+
| I  | **Information Leak** | IDOR on booking receipts        | Scoped token claims + DB WHERE user |
|    |                      | PII exposed in QR payload       | Zero PII in QR; opaque token only   |
|    |                      | Private property deeds exposed  | S3 private bucket + presigned URLs  |
+----+----------------------+---------------------------------+-------------------------------------+
| D  | **Denial of Service**| Concurrent slot lockup (Hoard)  | 480s hold TTL + max 2 active holds  |
|    |                      | SMS OTP exhaustion attack       | 3 req/15m phone limit + 60s cooldown|
|    |                      | Search API geographic flooding  | CloudFront WAF rate limits (100/min)|
+----+----------------------+---------------------------------+-------------------------------------+
| E  | **Elevation of Priv**| Driver calls Guard/Ops APIs     | Scoped RBAC middleware inspection   |
|    |                      | Guard accesses payout ledger    | Strict role-restricted API schemas  |
+----+----------------------+---------------------------------+-------------------------------------+
```

---

## 3. Deep-Dive Vulnerability & Mitigation Catalog

### 3.1 Threat SEC-001: Webhook Forgery & Payment Spoofing
- **Threat Actor:** Malicious driver / External attacker.
- **Attack Scenario:** Attacker sends an HTTP `POST` to `/api/v1/webhooks/razorpay` containing a fabricated `payment.captured` payload for their own unpaid reservation, attempting to force booking confirmation.
- **Impact:** Critical (Financial fraud; unauthorized slot allocation without payment).
- **Likelihood:** High.
- **Risk Rating:** **CRITICAL (P0)**.
- **Architectural Mitigation:**
  1. The webhook endpoint retrieves the raw request body bytes (`request.body()`) directly before any JSON parsing.
  2. The server computes the HMAC-SHA256 signature using the secret `RAZORPAY_WEBHOOK_SECRET` stored in AWS Secrets Manager.
  3. Uses `hmac.compare_digest()` to prevent timing attacks.
  4. Mismatched signatures immediately abort with HTTP 400 Bad Request; booking remains unconfirmed.
- **Detection & Recovery:** Failed signature attempts log source IP to `security_alerts`; SecOps receives automated alert if >3 failures occur in 5 minutes.

### 3.2 Threat SEC-002: Insecure Direct Object References (IDOR)
- **Threat Actor:** Authenticated driver or rogue user.
- **Attack Scenario:** Attacker calls `GET /api/v1/bookings/{booking_id}` replacing `{booking_id}` with another customer's UUID, attempting to inspect parking schedules, receipts, or vehicle license plates.
- **Impact:** High (Privacy violation; regulatory penalty under DPDPA).
- **Likelihood:** High.
- **Risk Rating:** **HIGH (P0)**.
- **Architectural Mitigation:**
  1. Endpoints derive user identity strictly from validated JWT claims (`current_user.id = token.sub`).
  2. Database queries explicitly bind:
     `SELECT * FROM space_reservations WHERE id = :bid AND driver_id = :current_user_id`.
  3. If the booking does not belong to the caller, the API returns HTTP 404 Not Found (preventing entity existence enumeration).
- **Detection:** Automated audit log flags repeated 404 errors across distinct IDs as potential enumeration scanning.

### 3.3 Threat SEC-003: QR Code Replay & Screenshot Sharing
- **Threat Actor:** Colluding drivers / Fraudulent customers.
- **Attack Scenario:** Driver A reserves a bay, takes a screenshot of the Access QR code, sends the screenshot to Driver B, and both vehicles attempt entry.
- **Impact:** High (Physical space conflict; guard dispute; double-parking).
- **Likelihood:** High.
- **Risk Rating:** **HIGH (P0)**.
- **Architectural Mitigation:**
  1. Access tokens are single-use credentials (`access_credentials.status = 'ISSUED'`).
  2. When scanned, the token is atomically updated to `status = 'CONSUMED'` within the same database transaction that creates the active session.
  3. Subsequent presentation of the same QR displays an immediate **BOLD RED** alert on the guard app: "ACCESS REJECTED: QR code already consumed at [Timestamp]."
- **Detection:** Scan attempts on `CONSUMED` tokens generate an audit record in `access_scans` with result `REPLAY_REJECTED`.

### 3.4 Threat SEC-004: Speculative Slot Hoarding (Denial of Inventory)
- **Threat Actor:** Competitor parking operator or malicious bot.
- **Attack Scenario:** Attacker scripts automated hold requests across all parking bays in a commercial district, holding all inventory in `ACTIVE_HOLD` to block legitimate drivers.
- **Impact:** High (Revenue loss; marketplace failure).
- **Likelihood:** Medium.
- **Risk Rating:** **MEDIUM (P0)**.
- **Architectural Mitigation:**
  1. Maximum **2 concurrent active holds** permitted per verified phone number.
  2. Per-user hold creation rate limit: Max 5 hold creations per 30 minutes.
  3. Holds have a strict, non-renewable lifespan of **480 seconds (8 minutes)** enforced by PostgreSQL timestamp checks and the two-tier hold expiration engine (lazy query + scheduled sweeper).
  4. IP-level rate limiting on `/bookings/hold` (max 10 req/min per IP via WAF).

### 3.5 Threat SEC-005: Property Document Tampering & Fraudulent Listings
- **Threat Actor:** Unauthorized tenant or trespasser.
- **Attack Scenario:** Attacker uploads a fake electricity bill or forged society NOC to list a parking bay they do not own, collecting passive rental income.
- **Impact:** Critical (Trespassing liability; police intervention; brand destruction).
- **Likelihood:** Medium.
- **Risk Rating:** **CRITICAL (P0)**.
- **Architectural Mitigation:**
  1. Spaces are strictly locked in `UNVERIFIED` status upon creation; completely excluded from search results.
  2. Uploaded documents are stored in an encrypted private S3 bucket accessible only via 15-minute presigned URLs generated for authorized operations staff.
  3. Mandatory manual human audit of ownership evidence (Tax receipt or Society NOC matching owner name) before property status transitions to `APPROVED`.
  4. Owner bank account name verified via Penny-Drop API prior to any payout.

---

## 4. Digital Personal Data Protection Act (DPDPA 2023) Assessment

As an Indian digital marketplace handling personal geolocation, phone numbers, and vehicle registration plates, SmartPark complies with the core principles of the **Digital Personal Data Protection Act, 2023**.

```
+---------------------------------------------------------------------------------------------------+
|                                  DPDPA 2023 COMPLIANCE MATRIX                                     |
+------------------------------+------------------------------------+-------------------------------+
| Statutory Principle          | Operational Implementation         | Technical Control             |
+------------------------------+------------------------------------+-------------------------------+
| **1. Notice & Consent**      | Unambiguous consent checkbox during| Consent record stored with    |
| (Section 5 & 6)              | phone registration with clear      | timestamp, IP, and policy     |
|                              | purpose specification.             | version ID in users table.    |
+------------------------------+------------------------------------+-------------------------------+
| **2. Purpose Limitation**    | Personal data collected strictly   | PII never sold or shared with |
| (Section 7)                  | for gate verification and billing. | external advertising brokers. |
+------------------------------+------------------------------------+-------------------------------+
| **3. Data Minimization**     | Zero collection of Aadhaar numbers,| Only phone number, name, and  |
| (Section 8)                  | driving licenses, or bank passwords| vehicle plate collected.      |
+------------------------------+------------------------------------+-------------------------------+
| **4. Storage Limitation**    | Completed GPS tracks purged after   | Automated pg_cron job purges   |
| (Section 8)                  | 180 days; offline basement vehicle  | search coordinates >180 days;  |
|                              | photos purged after 7 days.         | S3 Lifecycle purges gate photos|
+------------------------------+------------------------------------+-------------------------------+
| **5. Data Security**         | All personal data encrypted at     | AWS KMS AES-256 for storage;  |
| (Section 8)                  | rest and in transit.               | TLS 1.3 for all API endpoints.|
+------------------------------+------------------------------------+-------------------------------+
| **6. Right to Erasure**      | Drivers can request account closure| Soft-delete with 30-day purge |
| (Section 12)                 | and data deletion via Profile.     | (financial audit ledger kept).|
+------------------------------+------------------------------------+-------------------------------+
| **7. Grievance Redressal**   | Resident Grievance Officer details | Published in mobile settings  |
| (Section 13)                 | published in app (48h SLA).        | with direct email and address.|
+------------------------------+------------------------------------+-------------------------------+
```

### 4.1 Designated Grievance Officer Information
In accordance with Rule 3(2) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 and DPDPA 2023:
- **Designation:** Resident Grievance Officer, SmartPark Technologies Private Limited.
- **Physical Address:** SmartPark Operations HQ, 5th Block, Koramangala, Bengaluru, Karnataka 560095.
- **Direct Redressal Email:** `grievance@smartpark.in`.
- **Response SLA:** Grievance acknowledgment within 48 hours; final resolution within 30 days.
