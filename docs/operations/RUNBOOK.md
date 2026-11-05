# Gadispot Operational Runbooks & Operations Manual

> **Document Baseline:** `PRD-GSP-2026-V2.3.2`  
> **Classification:** Platform Operations / L1–L2 Engineering & Guard Ops  
> **Last Updated:** 2026-11-05  

---

## 1. Property Listing Verification & Authorization Runbook

### Objective
Audit submitted property deed documents, society NOCs, and electricity bills within the 24-hour SLA to grant listing activation (`APPROVED`).

### SLA & Authority
- **SLA:** 24 hours from submission.
- **Role Authority:** `OPERATIONS` or `ADMIN`.

### Operational Workflow
1. **Access Authorization Queue:**
   - Navigate to `GET /api/v1/admin/authorizations/pending`.
   - Inspect property metadata: title, address, pincode, GPS coordinates, property type (`RESIDENTIAL_DRIVEWAY`, `APARTMENT_SOCIETY`, `COMMERCIAL_BUILDING`, `OPEN_PLOT`).
2. **Document Inspection:**
   - Access deed / tax receipt via 15-minute presigned S3 URLs (`GET /api/v1/admin/documents/{doc_id}/presigned-url`).
   - Confirm ownership name matches host bank account KYC.
   - For societies, verify RWA/Society Secretary NOC stamp and expiry date.
3. **Decision Dispatch:**
   - **Approve:** `POST /api/v1/admin/authorizations/{id}/approve` -> transitions status to `APPROVED`, sends SMS to host, marks spaces `is_active = TRUE`.
   - **Reject:** `POST /api/v1/admin/authorizations/{id}/reject` with `reason_code` (`ILLEGIBLE_DOCUMENT`, `NAME_MISMATCH`, `INVALID_NOC`) -> notifies host to resubmit.

---

## 2. Guaranteed Parking Recovery Protocol (GPRP) Incident Runbook

### Objective
Resolve driver bay obstruction incidents (e.g. bay occupied by unauthorized vehicle upon arrival) within 180 seconds.

### Incident Invariant
- Never strand a driver who paid for guaranteed parking.
- Absorb up to ₹100 tariff difference as platform operating expense (Account 4020).

### Operational Procedure
1. **Incident Trigger:**
   - Driver presses "Bay Occupied / Issue at Gate" in mobile app within 15 minutes of reservation start time.
   - API records `status = ARRIVAL_FAILED` on active reservation.
2. **Automated Bay Reroute Search:**
   - Backend queries PostGIS within a 500-meter radius (`ST_DWithin`) for immediate compatible spaces.
   - If suitable alternative bay is found:
     - Reserve alternative space with a 180-second driver acceptance window.
     - Reissue access pass (`spx_ent_...`) without additional charge.
     - Post compensating subsidy in ledger (Account 4020: GPRP Recovery Subsidy Expense).
3. **Fallback Refund (When Zero Alternative Bays Exist):**
   - If no alternative space is available within 500m:
     - Immediately invoke `RefundService.initiate_refund(db, reservation_id, reason="GPRP_UNFULFILLABLE_NO_BAYS")`.
     - Platform issues 100% full refund to original payment source (UPI/Card).
     - Send transactional SMS and push apology voucher.

---

## 3. Subterranean Gate Manual Fallback & Photo Audit Reconciliation

### Objective
Reconcile guard admissions performed offline in subterranean cellular dead zones with zero duplicate entries.

### Guard Offline Protocol
1. **Offline Admission:**
   - Guard mobile client scans QR or inputs vehicle plate.
   - Guard captures offline vehicle proof photo.
   - Client stores record locally with HMAC-SHA256 device signature and timestamp.
2. **Batch Sync Upon Connectivity:**
   - When guard tablet re-establishes Wi-Fi/cellular connection:
     - Photos upload to private S3 bucket (`gadispot-gate-photos`).
     - Metadata posts to `POST /api/v1/access/offline-sync`.
3. **DPDPA Automated 7-Day Purge:**
   - Background worker (`PhotoPurgeWorker`) runs daily at 02:00 UTC.
   - Permanently deletes S3 photo binaries older than 7 days.
   - Leaves SHA-256 audit hash intact in `offline_manual_admissions.photo_s3_key = 'PURGED:DPDPA_7DAY:<hash>'`.

---

## 4. Weekly Batch Host Payout Execution & Discrepancy Reconciliation

### Objective
Disburse host accumulated earnings every Tuesday for balances $\ge ₹500$ under Merchant of Record (MoR) status.

### Ledger & Payout Workflow
1. **Balance Threshold Sweep:**
   - Run batch query against Account 2010 (Owner Payable Liability) at Tuesday 04:00 IST:
     ```sql
     SELECT owner_id, SUM(credit_paise - debit_paise) AS net_payable
     FROM v_owner_balances
     WHERE net_payable >= 50000 -- >= Rs 500.00
     GROUP BY owner_id;
     ```
2. **Payout Order Generation:**
   - Dispatch transfer orders via primary provider (Cashfree / RazorpayX Payouts).
   - Require Operations 2FA TOTP code for batches $> ₹1,00,000$.
3. **Double-Entry Settlement:**
   - Upon receipt of bank transfer webhook (`transfer.processed`):
     - Debit Account 2010 (Owner Payable Liability).
     - Credit Account 1020 (Operating Current Bank Account).
     - Record bank UTR in `payout_records`.

---

## 5. Security & Incident Response Runbook

### Key Incident Scenarios
| Incident | Detection Signal | Immediate Mitigation | Post-Incident Action |
|---|---|---|---|
| **Brute Force OTP / Login** | Rate limiter returns 429 spike | IP sliding window throttles to 3 req / 15m automatically | Inspect Redis blocklist, block malicious subnet via CloudFront WAF |
| **Suspected IDOR Attack** | 403 `IDOR_ACCESS_DENIED` log alert | User session revoked via Redis blocklist | Audit user query history in `audit_events` |
| **Double Webhook Delivery** | Repeated gateway webhook POST | Database unique constraint on `(gateway_name, gateway_event_id)` drops duplicate | Verify HTTP 200 returned with zero duplicate ledger lines |
| **Subterranean Photo Tampering** | Photo hash mismatch on sync | Admission marked `FLAGGED_FRAUD` | Guard supervisor notified for physical deed inspection |
