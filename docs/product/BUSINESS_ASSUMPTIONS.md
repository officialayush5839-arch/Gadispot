# Gadispot (formerly SmartPark Exchange) — Business Assumptions, Economics & Sensitivity Analysis (V2.3)

> **Document Version:** 2.3.0  
> **Date:** October 31, 2026  
> **Authors:** Principal Product Manager, Senior Business Analyst, Finance Lead  
> **Status:** Authoritative Financial & Unit Economics Reference (Targeted Revision V2.3)  

---

## 1. Classification of Financial & Commercial Information

To maintain institutional integrity, all commercial figures in SmartPark documentation are categorized into four strict classes:

1. **[VERIFIED FACT]:** Statutory tax rates (18.0% GST on services), official gateway rates (Razorpay 2.0% MDR + 18% GST = 2.36%), and published vendor tiers (Firebase Auth 10k free tier).
2. **[PROPOSED BUSINESS POLICY]:** Working defaults selected by the product team requiring executive founder signoff before commercial launch (15.0% commission, ₹10 convenience fee).
3. **[ILLUSTRATIVE PROJECTION]:** Mathematical modeling examples used to test unit economics and software logic; not historical revenue claims.
4. **[OPEN COMMERCIAL DECISION]:** Unresolved contract negotiations, provider fee waivers, or operational SLAs documented in `OPEN_QUESTIONS.md`.

---

## 2. Business Assumption Register

| ID | Assumption Statement | Current Baseline Value | Classification | Evidence & Statutory Basis | Financial Impact | Validation Method | Decision Owner |
|---|---|---|---|---|---|---|---|
| **ASM-001** | Platform Take-Rate (Commission) | Flat 15.0% on gross parking fee | PROPOSED POLICY | Standard marketplace benchmark (Urban Company 15-20%, Airbnb 14-16%). | Primary platform revenue driver; directly dictates owner net margins. | Pilot cohort profitability review in Bengaluru. | Founders |
| **ASM-002** | Driver Platform Convenience Fee | Flat ₹10.00 per completed booking | PROPOSED POLICY | Standard Indian consumer booking fee (BookMyShow ₹15-25, Zomato ₹5-9). | Offsets telecom SMS, cloud infrastructure, and gateway overhead. | Search-to-booking drop-off A/B testing. | Product Lead |
| **ASM-003** | GST on Marketplace Facilitation Services | 18.0% Goods & Services Tax | VERIFIED FACT | Notification No. 11/2017-Central Tax (Rate); SAC 9985 (Support Services). | Mandatory statutory deduction; payable on convenience fees and platform commissions. | Written tax opinion from chartered accountant. | Indirect Tax Lead |
| **ASM-004** | GST on Residential Space Rentals | 0.0% (Exempt for unregistered individuals) | VERIFIED FACT | Rental of residential property for parking by unregistered individuals is not subject to forward-charge GST. | Space owners retain gross parking fee without forward GST withholding. | Written tax opinion from legal counsel. | Indirect Tax Lead |
| **ASM-005** | Payment Gateway MDR Rate (Razorpay) | 2.0% + 18% GST (Net: 2.36%) | VERIFIED FACT | Published standard Razorpay India merchant rate for UPI, cards, and netbanking. | Direct transactional deduction from gross collections. | Merchant Agreement signing with Razorpay. | Payment Lead |
| **ASM-006** | Razorpay Route Marketplace Fee | ~0.25% + 18% GST per transfer | OPEN DECISION | Published indicative Route fee for automated linked account transfers. | Deducted per vendor settlement transfer. | Final commercial contract execution. | Finance Lead |
| **ASM-007** | Automated Batch Bank Transfer Fee (Fallback) | ₹2.00 to ₹4.00 per IMPS transfer | VERIFIED FACT | Published RazorpayX / Cashfree Payouts pricing for direct API IMPS payouts. | Minor fixed fee per weekly owner disbursement. | Merchant agreement signing. | Payment Lead |
| **ASM-008** | Firebase Phone Auth SMS Free Tier | 10,000 verifications/month free | VERIFIED FACT | Official Google Firebase Identity Platform pricing sheet. | Zero authentication cost for initial 10,000 monthly active users. | Google Cloud Billing monitoring. | DevOps Lead |
| **ASM-009** | Firebase SMS Overage Cost in India | ~$0.015 per verification (~₹1.25/SMS) | VERIFIED FACT | Published Firebase Identity Platform telecom routing rates for India (+91). | Scales linearly with user registration volume beyond 10,000 MAU. | Monthly billing audits. | DevOps Lead |
| **ASM-010** | GPRP Alternative Space Price Subsidy | Platform subsidizes difference up to ₹100 | PROPOSED POLICY | Proposed customer recovery guarantee; absorbs excess cost of alternative bay. | Direct platform operating expense incurred upon arrival failures. | Pilot incident frequency analysis (<2% target). | Operations Lead |

---

## 3. Unit Economics Modeling Across Duration Tiers (Reconciled & Balanced)

### 3.1 Detailed Step-by-Step Accounting Breakdown (2-Hour Stay at ₹40/hr)

```
1. CUSTOMER INFLOW (COLLECTED VIA UPI)
   Gross Parking Base (2.0 hrs @ ₹40.00/hr):   ₹80.00
   Driver Convenience Fee:                     ₹10.00
   GST on Convenience Fee (18.0% on ₹10.00):    ₹1.80
   -------------------------------------------------
   TOTAL DEBITED FROM DRIVER VIA UPI:          ₹91.80  (9,180 paise)

2. GATEWAY PROCESSING DEDUCTION
   Payment Gateway MDR (2.36% on ₹91.80):       ₹2.17  (217 paise - absorbed by platform)
   Net Cash Inflow to SmartPark Current Bank:  ₹89.63  (8,963 paise)

3. HOST CHARGES & NET ENTITLEMENT
   Gross Parking Base:                         ₹80.00
   Less: Platform Facilitation Commission (15%):-₹12.00
   Less: GST on Platform Commission (18%):      -₹2.16
   -------------------------------------------------
   NET OWNER ENTITLEMENT (CREDIT ACCOUNT 2010): ₹65.84  (6,584 paise)

4. TAX LIABILITIES (REMITTED TO GOVERNMENT)
   GST on Convenience Fee (collected from driver): ₹1.80
   GST on Platform Commission (collected from host):₹2.16
   -------------------------------------------------
   TOTAL GST OUTPUT TAX LIABILITY (ACCOUNT 2030):   ₹3.96  (396 paise)

5. NET PLATFORM OPERATING P&L
   Gross Operating Revenues (Commission + Conv Fee):₹22.00  (₹12.00 + ₹10.00)
   Less: Gateway Processing Expense (Account 4010): -₹2.17
   -------------------------------------------------
   NET PLATFORM OPERATING CONTRIBUTION:            ₹19.83  (1,983 paise - 21.6% Net Take-Rate)

6. MATHEMATICAL CASH FLOW RECONCILIATION INVARIANT
   Driver Inflow:                              ₹91.80
   = Net Owner Entitlement:                    ₹65.84
   + Net Platform Contribution:                ₹19.83
   + GST Output Tax Remitted:                   ₹3.96
   + Gateway Retained MDR:                      ₹2.17
   -------------------------------------------------
   TOTAL ALLOCATED FUNDS:                      ₹91.80  [EXACT - ZERO DISCREPANCY]
```

### 3.2 Model Comparison Table Across Durations

| Financial Component | 1-Hour Quick Stop (₹40/hr) | 2-Hour Standard Stay (₹40/hr) | 4-Hour Half-Day Work (₹40/hr) | 8-Hour Full-Day Office (₹35/hr) |
|---|---|---|---|---|
| **Gross Parking Base Fee** | ₹40.00 | ₹80.00 | ₹160.00 | ₹280.00 |
| **Driver Convenience Fee** | ₹10.00 | ₹10.00 | ₹10.00 | ₹10.00 |
| **GST on Convenience Fee (18%)** | ₹1.80 | ₹1.80 | ₹1.80 | ₹1.80 |
| **TOTAL DRIVER DEBITED (UPI)** | **₹51.80** | **₹91.80** | **₹171.80** | **₹291.80** |
| *Allocations:* | | | | |
| Gateway Processing MDR (2.36%) | ₹1.22 | ₹2.17 | ₹4.05 | ₹6.89 |
| Platform Commission (15%) | ₹6.00 | ₹12.00 | ₹24.00 | ₹42.00 |
| GST on Commission (18%) | ₹1.08 | ₹2.16 | ₹4.32 | ₹7.56 |
| Total GST Output Tax (Govt) | ₹2.88 | ₹3.96 | ₹6.12 | ₹9.36 |
| **NET OWNER ENTITLEMENT** | **₹32.92** (82.3%) | **₹65.84** (82.3%) | **₹131.68** (82.3%) | **₹230.44** (82.3%) |
| **NET PLATFORM OPERATING MARGIN** | **₹14.78** (28.5%) | **₹19.83** (21.6%) | **₹29.95** (17.4%) | **₹45.11** (15.5%) |

---

## 4. Sensitivity Analysis

### 4.1 Platform Commission Sensitivity (At ₹80 Base Booking)

| Commission Rate Scenario | Gross Commission | Net Owner Payout | Net Platform Margin | Owner Acceptance Viability | Platform Margin Viability |
|---|---|---|---|---|---|
| **10.0% Commission** | ₹8.00 | ₹70.56 (88.2%) | ₹15.83 (17.2%) | Very High (Strong owner acquisition) | Moderate (Higher volume needed) |
| **15.0% Commission (Baseline)**| **₹12.00** | **₹65.84 (82.3%)**| **₹19.83 (21.6%)**| **Optimal Balance** | **Healthy Sustainable Take-Rate** |
| **20.0% Commission** | ₹16.00 | ₹61.12 (76.4%) | ₹23.83 (26.0%) | Moderate (Risk of owner churn) | High Gross Margins |

---

## 5. Telecom & Infrastructure Scaling Cost Projections

| Monthly Verified Users (MAU) | Monthly OTP Verifications | Firebase SMS Cost (USD) | Firebase SMS Cost (INR) | Cloud Hosting (AWS Mumbai) | Total Tech Opex / Month |
|---|---|---|---|---|---|
| **1,000 (Alpha)** | 2,500 | $0.00 (Within 10k free tier) | ₹0.00 | ₹4,500 (ECS + RDS Dev) | ₹4,500 |
| **5,000 (Beta)** | 10,000 | $0.00 (Within 10k free tier) | ₹0.00 | ₹8,000 (RDS Multi-AZ) | ₹8,000 |
| **25,000 (Pilot Scale)** | 45,000 | $525.00 (35k overage @ $0.015) | ₹44,100 | ₹22,000 (Production cluster) | ₹66,100 |
| **100,000 (Growth)** | 180,000 | $2,550.00 (170k overage) | ₹2,14,200 | ₹55,000 (Auto-scaled) | ₹2,69,200 |

*Cost Optimization Strategy:* At >25,000 MAU, SmartPark will evaluate migrating SMS OTP delivery from Firebase to an enterprise Indian DLT-registered SMS provider (e.g., MSG91, Tanla, or Gupshup) where domestic transactional SMS rates range from **₹0.18 to ₹0.25 per SMS** (a 75% cost reduction compared to Firebase international SMS rates).
