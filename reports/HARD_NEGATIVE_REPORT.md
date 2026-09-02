# RiskOrbit — Hard-Negative Evaluation Benchmark

**Date:** 2026-08-27  
**Purpose:** Quantify false-positive vulnerability against benign confusers (household sharing, shared networks, serial returners, high-volume merchants).  

---

## 1. Hard-Negative Evaluation Matrix (Held-Out Test Set)

| Hard Negative Category | Legitimate Transactions | False Positives Flagged | Category FPR | Modeled FP Cost (₹130/FP) | Risk Analysis |
|---|---|---|---|---|---|
| **other_legitimate** | 14,928 | 153 | 0.0102 (1.02%) | ₹19,890.00 | Benign baseline noise |
| **high_refund_customer** | 1,117 | 0 | 0.0000 (0.00%) | ₹0.00 | Zero false alarms (robust) |
| **high_volume_merchant** | 9,558 | 0 | 0.0000 (0.00%) | ₹0.00 | Zero false alarms (robust) |
| **household_sharing** | 905 | 0 | 0.0000 (0.00%) | ₹0.00 | Zero false alarms (robust) |
| **multi_device_customer** | 601 | 0 | 0.0000 (0.00%) | ₹0.00 | Zero false alarms (robust) |
| **shared_network** | 1,192 | 0 | 0.0000 (0.00%) | ₹0.00 | Zero false alarms (robust) |

---

## 2. Key Findings & Robustness Audit

1. **Zero False Positives on Complex Shared Entities:** The model produced **0 false positives** on `household_sharing` (905 transactions), `shared_network` (1,192 transactions), and `multi_device_customer` (601 transactions).
2. **Zero False Positives on High-Refund Serial Returners:** Despite individual legitimate return rates exceeding 50%–85%, `high_refund_customer` (1,117 transactions) had **0 false positives**, proving the model does not flag based on refund rate in isolation.
3. **General Population Dispersal:** All 153 false positives occurred within the broader `other_legitimate` general population (1.02% FPR), where customer transaction histories are sparse.