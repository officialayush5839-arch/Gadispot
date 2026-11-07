# Gadispot — Dual-Mode Demo Payment Architecture

**Specification Reference:** PRD-GSP-2026-V2.3.2-VERIFIED  
**Audience:** IIT Kanpur TIC Hackathon Jury, Evaluators & Core Engineers  
**Classification:** Core Financial Architecture  

---

## 1. Executive Summary

Gadispot requires a zero-cost, fully reproducible end-to-end payment demonstration architecture capable of executing realistic checkout workflows without requiring paid payment aggregator accounts, commercial merchant banking setups, real UPI bank transfers, or monetary outflows.

To fulfill this requirement with absolute architectural integrity, Gadispot implements a **Dual-Mode Payment Architecture**:

```
                                      +------------------------------------+
                                      |       Checkout Intent Request      |
                                      +------------------------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |       PaymentGatewayFactory        |
                                      +------------------------------------+
                                                        |
                                +-----------------------+-----------------------+
                                |                                               |
                                v                                               v
                  +---------------------------+                   +---------------------------+
                  |  MODE A: DemoPayment      |                   |  MODE B: YoupiPayment     |
                  |  (Default, Zero-Cost)     |                   |  (Isolated, Opt-In)       |
                  +---------------------------+                   +---------------------------+
                                |                                               |
                  +-------------+-------------+                   +-------------+-------------+
                  | Deterministic Simulation  |                   | External Observer Tracker |
                  | SUCCESS / FAILURE / TIMEOUT|                   | Strict Observer Boundary  |
                  +---------------------------+                   +---------------------------+
                                |                                               |
                                v                                               v
                  +---------------------------+                   +---------------------------+
                  | Confirms SpaceReservation |                   | DOES NOT Confirm Booking  |
                  | Mints Access QR Passes    |                   | Marks Reconciliation Flag |
                  | Posts Balanced Ledger     |                   | Awaits Bank Settlement   |
                  +---------------------------+                   +---------------------------+
```

---

## 2. Core Operational Modes

### Mode A: Demo Simulated Payment (Default)

- **Provider Identifier:** `demo`
- **Default Status:** Active by default in non-production environments (`DEMO_PAYMENTS_ENABLED=True`, `PAYMENT_MODE=demo`).
- **Zero Financial Liability:** No external merchant credentials or bank accounts are required.
- **Deterministic Outcomes:**
  - `SUCCESS`: Confirms `SpaceReservation`, mints 128-bit CSPRNG entry and exit access credentials (`spx_ent_...`, `spx_ext_...`), and posts balanced 5-line double-entry General Ledger journal.
  - `FAILURE`: Marks `Payment.status = FAILED`, retains reservation hold (or triggers expiry), preserves diagnostic failure reason.
  - `CANCEL`: Marks `Payment.status = CANCELLED`.
  - `TIMEOUT`: Marks `Payment.status = EXPIRED` and invalidates reservation hold upon expiration.
- **Fail-Closed Protection:** Strictly blocked if `ENVIRONMENT=production`.

### Mode B: YOUPI-PG Experimental Adapter (Isolated & Opt-In)

- **Provider Identifier:** `youpi`
- **Default Status:** Strictly disabled by default (`YOUPI_ENABLED=False`).
- **Zero Third-Party Code Vendoring:** No unlicensed or commercial private packages are incorporated or vendored. All interactions occur across a clean REST/HMAC integration port.
- **Observer Constraint:** Notifications derived from app/SMS observers are treated strictly as unverified telemetry (`OBSERVED_SUCCESS`) and **never** directly transition a reservation to `CONFIRMED`.

---

## 3. General Ledger Accounting Invariants

Every successful demo payment posts an immutable, balanced 5-line journal entry adhering to the PRD V2.3.2 financial breakdown:

$$\text{Driver Inflow} = \text{Owner Entitlement} + \text{Platform Commission} + \text{Driver Convenience Fee} + \text{GST Output Liability}$$

| Line | Account Code | Account Name | Normal Balance | Entry Side | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `1010` | Gateway Transit Asset | DEBIT | **DEBIT** | Total monetary inflow collected from driver |
| **2** | `2010` | Owner Payable Liability | CREDIT | **CREDIT** | Host net earnings entitlement |
| **3** | `3010` | Platform Commission Revenue | CREDIT | **CREDIT** | 15% platform take-rate |
| **4** | `3020` | Driver Convenience Fee Revenue | CREDIT | **CREDIT** | Fixed ₹10.00 convenience fee |
| **5** | `2030` | GST Output Tax Liability | CREDIT | **CREDIT** | 18% GST (CGST + SGST) on convenience & commission |

### Database Trigger Enforcement

PostgreSQL trigger `trg_verify_journal_balance` executes prior to updating a journal entry to `POSTED`. It enforces:
1. `line_count >= 2`.
2. $\sum \text{Debits} = \sum \text{Credits}$.
3. Zero modification or deletion of lines once posted (`trg_prevent_posted_modification` and `trg_prevent_posted_lines_mod`).

---

## 4. Owner Payout Simulation

Host earnings accumulated in Account `2010` (Owner Payable Liability) can be disbursed in simulation batches:

1. **Balance Discovery:** Queries net outstanding balance:
   $$\text{Net Payable} = \sum \text{Credits}_{2010} - \sum \text{Debits}_{2010}$$
2. **Balanced Disbursement Journal:**
   - **DEBIT** Account `2010` (Reduces Owner Payable Liability)
   - **CREDIT** Account `1020` (Disburses Operating Bank Account funds)
3. **Double-Pay Defense:** Once the payout journal is posted, subsequent queries immediately calculate $\text{Net Payable} = 0$, preventing double payout executions.
