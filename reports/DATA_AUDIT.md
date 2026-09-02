# RiskOrbit — Dataset Audit Report

**Audit Date:** 2026-08-27  
**Dataset Version:** `phase1-raw-v1`  
**Evaluation Scope:** Synthetic Payment Ecosystem & Ground Truth Integrity  

---

## 1. Entity & Record Count Audit

| Entity / Table | Record Count | Description | Primary Key |
|---|---|---|---|
| **Transactions** | **190,618** | Transaction events with timestamps, amounts, payment methods | `transaction_id` |
| **Orders** | **190,615** | Order details (product category, delivery region, timestamps) | `order_id` |
| **Refunds** | **36,128** | Refund events (requested/processed timestamps, amounts, reasons) | `refund_id` |
| **Customers** | **22,000** | Customer profiles with segments and account age | `customer_id` |
| **Merchants** | **1,100** | Merchant catalog with category baseline refund rates | `merchant_id` |
| **Devices** | **13,000** | Unique hardware device profiles | `device_id` |
| **IP Entities** | **9,000** | Network/IP addresses | `ip_id` |
| **Payment Instruments** | **18,000** | Cards, UPI handles, and wallets | `instrument_id` |

---

## 2. Target Class & Prevalence Breakdown

- **Total Transactions:** 190,618
- **Legitimate Transactions ($Y=0$):** 188,668 (98.98%)
- **Abuse Transactions ($Y=1$):** 1,950 (1.023%)
- **Total Coordinated Abuse Rings:** 160 rings

### Abuse Pattern Distribution:

| Pattern Name | Description | Ring Count | Injected Txns | % of Abuse |
|---|---|---|---|---|
| **Pattern A** | `pattern_a_shared_device` (Coordinated multi-account device clustering) | 60 rings | 805 txns | 41.28% |
| **Pattern C** | `pattern_c_rotating_account` (Rotating burner accounts linked by IP/instrument) | 50 rings | 597 txns | 30.62% |
| **Pattern B** | `pattern_b_cross_merchant` (Distributed accounts targeting multiple merchants) | 50 rings | 548 txns | 28.10% |
| **Total** | | **160 rings** | **1,950 txns** | **100.0%** |

---

## 3. Hard-Negative Population Breakdown

The synthetic generator explicitly injects confusers to mirror real-world benign edge cases:

| Hard Negative Type | Txn Count | % of Total | Behavioral Characteristic |
|---|---|---|---|
| **None (Standard Legitimate)** | 101,632 | 53.32% | Standard single/multi-purchase benign customers |
| **High Volume Merchant** | 63,110 | 33.11% | Concentrated transactions from high-throughput merchants |
| **Shared Network (Office/Campus)** | 8,011 | 4.20% | Multiple independent accounts transacting via single IP |
| **High Refund Customer (Serial Returner)** | 7,729 | 4.05% | Benign customers with legitimate refund rate 50%–85% |
| **Household Device Sharing** | 6,025 | 3.16% | Family members sharing 1–2 household tablets/laptops |
| **Multi-Device Customer** | 4,111 | 2.16% | Legitimate power-users transacting across 4–8 devices |

---

## 4. Distribution Analysis

### Transaction Amounts (INR):
- **Mean:** ₹1,039.12
- **Std Dev:** ₹1,280.39
- **Min / Max:** ₹10.90 / ₹29,947.66
- **Percentiles:** P25 = ₹324.82 | Median = ₹617.98 | P75 = ₹1,220.22 | P95 = ₹3,412.09

### Refunds:
- **Total Incurred Refunds:** 36,128 events (18.95% overall transaction refund rate)
- **Total Refunded Amount:** ₹32,068,826.38
- **Mean Refund Amount:** ₹887.64 (Median: ₹490.86)

### Temporal Coverage:
- **Span:** 2023-01-01 00:00:06 to 2024-12-30 23:53:10 (730.0 calendar days / 2 full years)
- **Seasonality:** Preserves Nov/Dec festive spikes (Diwali & Year-End peak volume multipliers).
