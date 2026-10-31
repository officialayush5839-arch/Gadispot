# SmartPark Exchange — Payment Engine & Financial Ledger Specification (V2.2)

> **Document Version:** 2.2.0  
> **Date:** October 31, 2026  
> **Authors:** Principal Software Architect, Payment Systems Specialist, Financial Engineering Lead  
> **Status:** Authoritative Engineering Design (Targeted Revision V2.2)  

---

## 1. Executive Summary & Mandatory Financial Invariants

The SmartPark payment and settlement subsystem is engineered as an immutable, regulatory-compliant double-entry financial transaction engine. It decouples customer payment orchestration from physical booking confirmation and marketplace disbursements.

### Mandatory Financial Invariants
1. **Never Trust Client Callbacks:** Under zero circumstances is a booking confirmed based on a Flutter client callback or presentation sheet dismissal. Confirmation strictly requires authoritative server-to-server webhook verification with raw HMAC-SHA256 signature validation or authenticated server-to-gateway polling.
2. **Durable Database-Level Idempotency:** Webhook event deduplication is enforced at the database layer via a unique constraint on `(gateway_name, gateway_event_id)` in the `payment_webhook_events` table. Redis is an optional speed cache, never the sole deduplication authority.
3. **True Double-Entry Bookkeeping:** All monetary movements are recorded in a two-tier Journal Header (`journal_entries`) and Journal Lines (`journal_lines`) schema. Every posted journal transaction must strictly satisfy:
   $$\sum_{\text{lines}} \text{Debits} = \sum_{\text{lines}} \text{Credits} \quad \text{enforced at the database transaction level}$$
4. **Database-Level Balancing Enforcement:** A journal entry cannot transition to `POSTED` status unless the sum of its debit lines equals the sum of its credit lines and there are at least two lines. Unbalanced journals are rejected by database triggers.
5. **Append-Only Immutability:** Posted journal entries and lines are never updated or deleted. Corrections, cancellations, and refunds are executed exclusively through compensating reversing journal entries referencing `reversal_of_journal_id`.
6. **Merchant of Record & Regulatory Posture:** SmartPark acts as the Merchant of Record (MoR) for driver payments and bears full legal liability for chargebacks, customer refunds, and payment disputes. Owner payouts during pilot are scheduled batch bank transfers from the platform corporate current account under prior bank underwriting and strict KYC, **not** an unregulated proprietary "escrow".

---

## 2. Relational Double-Entry Database Architecture

```sql
-- Chart of Accounts Master Table
CREATE TYPE account_type_enum AS ENUM (
    'ASSET',
    'LIABILITY',
    'EQUITY',
    'REVENUE',
    'EXPENSE'
);

CREATE TABLE ledger_accounts (
    account_code VARCHAR(16) PRIMARY KEY,
    account_name VARCHAR(128) NOT NULL,
    account_type account_type_enum NOT NULL,
    normal_balance VARCHAR(8) NOT NULL CHECK (normal_balance IN ('DEBIT', 'CREDIT')),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Pre-populate Standard Chart of Accounts
INSERT INTO ledger_accounts (account_code, account_name, account_type, normal_balance, description) VALUES
('1010', 'Gateway Transit Account (Aggregator In-Flight)', 'ASSET', 'DEBIT', 'Driver funds captured via UPI/cards awaiting settlement to SmartPark bank account'),
('1020', 'Operating Current Bank Account', 'ASSET', 'DEBIT', 'Primary commercial bank account holding platform reserves and commission proceeds'),
('2010', 'Owner Payable Liability', 'LIABILITY', 'CREDIT', 'Accumulated net earnings owed to parking property owners for completed parking sessions'),
('2020', 'Customer Refund Payable', 'LIABILITY', 'CREDIT', 'Pending customer refunds due to cancellations, LPRP expiry, or GPRP failures'),
('2030', 'GST Output Tax Payable (CGST/SGST/IGST)', 'LIABILITY', 'CREDIT', '18% GST collected on platform commission and driver convenience fees'),
('3010', 'Platform Commission Revenue', 'REVENUE', 'CREDIT', 'Marketplace facilitation commission earned on completed parking sessions'),
('3020', 'Driver Convenience Fee Revenue', 'REVENUE', 'CREDIT', 'Platform convenience fees billed to drivers to cover infrastructure and SMS costs'),
('4010', 'Payment Gateway MDR Expense', 'EXPENSE', 'DEBIT', 'Merchant Discount Rate and processing fees charged by Razorpay / Cashfree'),
('4020', 'GPRP Customer Recovery Subsidy Expense', 'EXPENSE', 'DEBIT', 'Platform-subsidized goodwill allowances absorbed during arrival failure rerouting');

-- Journal Headers Table
CREATE TYPE journal_status_enum AS ENUM ('DRAFT', 'POSTED', 'VOIDED');

CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_number VARCHAR(32) NOT NULL UNIQUE,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_reference VARCHAR(64) NOT NULL,
    transaction_type VARCHAR(32) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    posting_status journal_status_enum NOT NULL DEFAULT 'DRAFT',
    reversal_of_journal_id UUID REFERENCES journal_entries(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_at TIMESTAMPTZ
);

-- Journal Lines Table
CREATE TYPE entry_side_enum AS ENUM ('DEBIT', 'CREDIT');

CREATE TABLE journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE RESTRICT,
    line_number INT NOT NULL,
    account_code VARCHAR(16) NOT NULL REFERENCES ledger_accounts(account_code),
    entry_side entry_side_enum NOT NULL,
    amount_in_paise BIGINT NOT NULL CHECK (amount_in_paise > 0),
    description TEXT,
    
    CONSTRAINT uq_journal_line UNIQUE (journal_id, line_number)
);

CREATE INDEX idx_journal_lines_journal ON journal_lines(journal_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_code);
CREATE INDEX idx_journal_entries_reference ON journal_entries(transaction_reference);

-- Payment Webhook Deduplication Table (Durable Database Idempotency)
CREATE TABLE payment_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway_name VARCHAR(32) NOT NULL,
    gateway_event_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_gateway_event UNIQUE (gateway_name, gateway_event_id)
);
CREATE INDEX idx_webhook_status ON payment_webhook_events(status);

-- Transactional Outbox Table for Downstream Events
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX idx_outbox_pending ON outbox_events(status, created_at) WHERE status = 'PENDING';
```

### 2.1 Database Triggers: Enforcing Ledger Balancing and Immutability
```sql
-- Trigger 1: Enforce Debit == Credit Balance and Minimum 2 Lines
CREATE OR REPLACE FUNCTION fn_verify_journal_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_total_debits BIGINT;
    v_total_credits BIGINT;
    v_line_count INT;
BEGIN
    IF NEW.posting_status = 'POSTED' AND (OLD.posting_status IS NULL OR OLD.posting_status != 'POSTED') THEN
        SELECT 
            COALESCE(SUM(CASE WHEN entry_side = 'DEBIT' THEN amount_in_paise ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN entry_side = 'CREDIT' THEN amount_in_paise ELSE 0 END), 0),
            COUNT(*)
        INTO v_total_debits, v_total_credits, v_line_count
        FROM journal_lines
        WHERE journal_id = NEW.id;

        IF v_line_count < 2 THEN
            RAISE EXCEPTION 'Cannot post journal entry %: Must contain at least 2 lines (found %)', NEW.id, v_line_count;
        END IF;

        IF v_total_debits != v_total_credits THEN
            RAISE EXCEPTION 'Journal entry % does not balance! Total Debits: % paise, Total Credits: % paise',
                NEW.id, v_total_debits, v_total_credits;
        END IF;

        NEW.posted_at := CLOCK_TIMESTAMP();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_verify_journal_balance
BEFORE UPDATE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_verify_journal_balance();

-- Trigger 2: Prevent Modification or Deletion of Posted Journals
CREATE OR REPLACE FUNCTION fn_prevent_posted_journal_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.posting_status = 'POSTED' THEN
        RAISE EXCEPTION 'Immutable Ledger Violation: Posted journal % cannot be updated or deleted. Post a reversing entry instead.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_modification
BEFORE UPDATE OR DELETE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_journal_modification();

CREATE OR REPLACE FUNCTION fn_prevent_posted_lines_modification()
RETURNS TRIGGER AS $$
DECLARE
    v_parent_status journal_status_enum;
BEGIN
    SELECT posting_status INTO v_parent_status FROM journal_entries WHERE id = COALESCE(OLD.journal_id, NEW.journal_id);
    IF v_parent_status = 'POSTED' THEN
        RAISE EXCEPTION 'Immutable Ledger Violation: Cannot modify journal lines of already posted journal %', COALESCE(OLD.journal_id, NEW.journal_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_lines_mod
BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_posted_lines_modification();
```

---

## 3. Financial Calculation Sequence & Unit Economics (Standard Worked Example)

### 3.1 Transparent Formula Specifications (2-Hour Booking at ₹40/hr)
1. **Driver Inflow:**
   - Gross Parking Base ($P_{\text{base}}$): $2 \times ₹40.00 = ₹80.00$ (8,000 paise).
   - Driver Convenience Fee ($F_{\text{conv}}$): ₹10.00 (1,000 paise).
   - GST on Convenience Fee ($T_{\text{conv}}$ @ 18%): ₹1.80 (180 paise).
   - **Total Driver Paid via UPI:** **₹91.80 (9,180 paise)**.
2. **Platform Commission Invoice to Host:**
   - Platform Commission ($P_{\text{comm}}$ @ 15% on ₹80.00): ₹12.00 (1,200 paise).
   - GST on Commission ($T_{\text{comm}}$ @ 18% on ₹12.00): ₹2.16 (216 paise).
   - Total Platform Facilitation Charge to Host: ₹14.16 (1,416 paise).
3. **Net Property Owner Entitlement (Credit Account 2010):**
   - Gross Parking Base (₹80.00) - Total Commission & Tax (₹14.16) = **₹65.84 (6,584 paise)**.
4. **Payment Gateway Processing:**
   - Gateway MDR ($G_{\text{mdr}}$ @ 2.0% + 18% GST on MDR = 2.36% on ₹91.80): ₹2.17 (217 paise).
   - Absorbed by platform as an operating expense (Account 4010).
5. **GST Output Tax Liability (Credit Account 2030):**
   - GST on Convenience Fee (₹1.80) + GST on Commission (₹2.16) = **₹3.96 (396 paise)**.
6. **Platform Net Operating Margin (P&L):**
   - Platform Revenues (Commission ₹12.00 + Convenience Fee ₹10.00): ₹22.00.
   - Less Operating Expense (Gateway MDR): -₹2.17.
   - **Net Platform Operating Contribution:** **₹19.83 (1,983 paise)** (21.6% Net Take-Rate).
7. **Mathematical Cash Flow Reconciliation:**
   $$\text{Total Inflow (₹91.80)} = \text{Owner (₹65.84)} + \text{Platform Margin (₹19.83)} + \text{GST (₹3.96)} + \text{MDR (₹2.17)} = ₹91.80 \quad \text{[EXACT]}$$

---

## 4. Balanced Journal Entry Templates for All 12 Financial Events

Every financial transaction in SmartPark is posted via an explicit balancing journal template where $\sum \text{Debits} = \sum \text{Credits}$.

### Template 1: Driver Payment Captured (`JRN-BK`)
*Trigger:* Payment gateway webhook `payment.captured` verified.
```
Journal: JRN-BK-{reservation_id} | Type: BOOKING_CONFIRMATION | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     1010          Gateway Transit Account (Asset)  DEBIT            9,180       91.80
2     2010          Owner Payable Liability          CREDIT           6,584       65.84
3     3010          Platform Commission Revenue      CREDIT           1,200       12.00
4     3020          Driver Convenience Fee Revenue   CREDIT           1,000       10.00
5     2030          GST Output Tax Payable           CREDIT             396        3.96
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 2: Gateway Bank Settlement & MDR Deduction (`JRN-MDR`)
*Trigger:* Payment gateway net settlement arrives in corporate bank account.
```
Journal: JRN-MDR-{settlement_id} | Type: GATEWAY_SETTLEMENT | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     1020          Operating Current Bank Account   DEBIT            8,963       89.63
2     4010          Payment Gateway MDR Expense      DEBIT              217        2.17
3     1010          Gateway Transit Account (Asset)  CREDIT           9,180       91.80
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 3: Weekly Owner Batch Payout Disbursement (`JRN-PO`)
*Trigger:* Batch IMPS transfer worker executes payout to owner's verified bank account.
```
Journal: JRN-PO-{payout_id} | Type: OWNER_DISBURSEMENT | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2010          Owner Payable Liability          DEBIT            6,584       65.84
2     1020          Operating Current Bank Account   CREDIT           6,584       65.84
Total Debits: 6,584 paise (₹65.84) | Total Credits: 6,584 paise (₹65.84) [BALANCED]
```

### Template 4: GST Output Tax Remittance (`JRN-TAX`)
*Trigger:* Monthly GST return filing and payment to government portal.
```
Journal: JRN-TAX-{month} | Type: TAX_REMITTANCE | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2030          GST Output Tax Payable           DEBIT              396        3.96
2     1020          Operating Current Bank Account   CREDIT             396        3.96
Total Debits: 396 paise (₹3.96) | Total Credits: 396 paise (₹3.96) [BALANCED]
```

### Template 5: 100% Driver Cancellation Refund (>2 Hours Before Start) (`JRN-CAN-100`)
*Trigger:* Driver cancels booking per policy `POL-CAN-01`. Full reversal of original booking.
```
Journal: JRN-CAN100-{refund_id} | Type: CANCELLATION_REFUND | Status: POSTED (Reversal of JRN-BK)
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2010          Owner Payable Liability (Rev)    DEBIT            6,584       65.84
2     3010          Platform Commission (Rev)        DEBIT            1,200       12.00
3     3020          Driver Convenience Fee (Rev)     DEBIT            1,000       10.00
4     2030          GST Output Tax Payable (Rev)     DEBIT              396        3.96
5     1010          Gateway Transit Account (Asset)  CREDIT           9,180       91.80
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 6: 50% Driver Cancellation Refund (30m to 2 Hours Before Start) (`JRN-CAN-50`)
*Trigger:* Driver cancels booking per policy `POL-CAN-02`. 50% refunded to driver, 50% retained.
```
Journal: JRN-CAN50-{refund_id} | Type: CANCELLATION_PARTIAL | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2010          Owner Payable Liability (50%)    DEBIT            3,292       32.92
2     3010          Platform Commission (50%)        DEBIT              600        6.00
3     3020          Driver Convenience Fee (50%)     DEBIT              500        5.00
4     2030          GST Output Tax Payable (50%)     DEBIT              198        1.98
5     1010          Gateway Transit Account (Asset)  CREDIT           4,590       45.90
Total Debits: 4,590 paise (₹45.90) | Total Credits: 4,590 paise (₹45.90) [BALANCED]
```

### Template 7: Late Payment Resolution Auto-Refund (LPRP Slot Claimed) (`JRN-LPRP`)
*Trigger:* Late webhook arrives after hold expiry and slot was claimed by competing driver.
```
Journal: JRN-LPRP-{refund_id} | Type: LPRP_UNFULFILLABLE_REFUND | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2010          Owner Payable Liability (Rev)    DEBIT            6,584       65.84
2     3010          Platform Commission (Rev)        DEBIT            1,200       12.00
3     3020          Driver Convenience Fee (Rev)     DEBIT            1,000       10.00
4     2030          GST Output Tax Payable (Rev)     DEBIT              396        3.96
5     1010          Gateway Transit Account (Asset)  CREDIT           9,180       91.80
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 8: Failed Gateway Refund Earmarking (`JRN-FLR`)
*Trigger:* Gateway reports refund failed (e.g. driver closed bank account); transferred to customer payable.
```
Journal: JRN-FLR-{refund_id} | Type: FAILED_REFUND_HOLD | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     1010          Gateway Transit Account (Asset)  DEBIT            9,180       91.80
2     2020          Customer Refund Payable          CREDIT           9,180       91.80
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 9: Bank Chargeback or Dispute Reversal (`JRN-CHG`)
*Trigger:* Acquirer debit advice for customer chargeback dispute.
```
Journal: JRN-CHG-{dispute_id} | Type: CHARGEBACK_REVERSAL | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     2010          Owner Payable (Debit Deficit)    DEBIT            6,584       65.84
2     3010          Platform Commission Revenue (Rev)DEBIT            1,200       12.00
3     3020          Driver Convenience Fee (Rev)     DEBIT            1,000       10.00
4     2030          GST Output Tax (Rev)             DEBIT              396        3.96
5     1020          Operating Current Bank Account   CREDIT           9,180       91.80
Total Debits: 9,180 paise (₹91.80) | Total Credits: 9,180 paise (₹91.80) [BALANCED]
```

### Template 10: GPRP Alternative Space Platform Subsidy (`JRN-SUB`)
*Trigger:* Platform subsidizes price difference up to ₹100 when rerouting driver to higher-priced space.
```
Journal: JRN-SUB-{incident_id} | Type: GPRP_SUBSIDY | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     4020          GPRP Customer Recovery Expense   DEBIT            3,000       30.00
2     2010          Owner Payable (Alternative Host) CREDIT           3,000       30.00
Total Debits: 3,000 paise (₹30.00) | Total Credits: 3,000 paise (₹30.00) [BALANCED]
```

### Template 11: Overstay Penalty Billing Settlement (`JRN-OST`)
*Trigger:* Driver charged 1.5× hourly penalty upon delayed exit (>15m departure grace). E.g. ₹60 penalty.
```
Journal: JRN-OST-{session_id} | Type: OVERSTAY_PENALTY | Status: POSTED
Line  Account Code  Account Name                     Side    Amount (Paise)  Amount (₹)
1     1010          Gateway Transit Account (Asset)  DEBIT            6,000       60.00
2     2010          Owner Payable (50% Compensation) CREDIT           3,000       30.00
3     3010          Platform Commission Revenue      CREDIT           2,085       20.85
4     2030          GST Output Tax Payable           CREDIT             915        9.15
Total Debits: 6,000 paise (₹60.00) | Total Credits: 6,000 paise (₹60.00) [BALANCED]
```

### Template 12: Stale Hold Expiration / Cleanup (`JRN-EXP`)
*Trigger:* 480-second hold expires without payment capture.
```
Note: Hold expiration releases inventory constraints in PostgreSQL. 
Because no customer funds were debited, zero monetary ledger journal is required.
```

---

## 5. Payout Compliance, Direct Transfers & Regulatory Assessment

### 5.1 Regulatory Reality: Direct Bank Transfers vs Marketplace Escrows
- **Correction of Previous Claims:** Using RazorpayX or Cashfree Payouts for direct bank transfers from a corporate current account **does not automatically constitute an approved marketplace escrow model**.
- **RBI Stance:** Under RBI guidelines for Payment Aggregators (DPSS.CO.PD.No.1810/02.14.008/2019-20), an e-commerce marketplace collecting customer funds and disbursing them to third-party sellers must route settlements through an RBI-authorized Payment Aggregator Escrow/Nodal account.
- **Merchant of Record (MoR):** SmartPark is the Merchant of Record for driver collections. As MoR, SmartPark bears full legal liability for refunds, customer disputes, and bank chargebacks.

### 5.2 Pilot Phase Payout Strategy (Founder Decision Q5)
1. **Dual Application:** SmartPark will apply simultaneously for marketplace onboarding with both **Razorpay** (Razorpay Route) and **Cashfree** (Cashfree Marketplace).
2. **Phase 1 Pilot Strategy (Controlled Settlement):**
   - If automated marketplace nodal routing is not approved by Day 1 of the Bengaluru pilot due to turnover thresholds, owner settlements will be disbursed via **scheduled batch bank transfers** from SmartPark's current account following strict internal KYC and fulfillment validation.
   - Every owner must complete:
     - PAN verification via Protean/NSDL API.
     - Bank account verification (Penny Drop API confirming account holder name matches KYC name).
     - GSTIN declaration (Unregistered individual, Composition scheme, or Regular registered taxpayer).
3. **Chargeback & Deficit Protection:** If a driver initiates a bank chargeback after owner funds have been disbursed, the owner's ledger balance (`2010`) enters a debit deficit, which is automatically deducted from future parking session earnings.
