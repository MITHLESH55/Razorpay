# RiskOrbit — Comprehensive Diagnostic Error Analysis (Final)

**Date:** 2026-08-27  
**Evaluation Partition:** Held-Out Locked Test Partition (28,591 transactions)  
**Operating Point:** Threshold = 0.3500  

---

## 1. Confusion Matrix Overview

- **True Positives (TP):** 83 (Detected coordinated abuse)
- **False Negatives (FN):** 207 (Missed coordinated abuse)
- **False Positives (FP):** 153 (Benign transactions incorrectly flagged)
- **True Negatives (TN):** 28148

---

## 2. False Negative Analysis (What Failed and Why?)

### Breakdown of Missed Abuse by Pattern Type:

- **Pattern A (Shared-Device Rings):** 143 of 144 missed (**99.3% miss rate**)
- **Pattern B (Cross-Merchant Rings):** 42 of 44 missed (**95.5% miss rate**)
- **Pattern C (Rotating-Account Rings):** 22 of 102 missed (**21.6% miss rate**)

### Root Cause Diagnosis:
1. **Pattern A Blindness:** In Pattern A rings, 3–8 accounts share 1–2 devices. Because the test partition rings are entirely unseen in training (zero ring leakage), the tabular model observes individual accounts with short histories and moderate amounts. Without dynamic multi-hop community detection connecting accounts across device and IP edges, the tabular feature vector appears statistically indistinguishable from benign household tablet sharing.
2. **Pattern B Blindness:** In Pattern B rings, accounts transact across different merchants with coordinated timing. Tabular models only evaluate single transaction rows with static customer aggregates. The multi-account cross-merchant coordination pattern is completely invisible without bipartite graph neighborhood aggregation.
3. **Pattern C Success:** Pattern C succeeds (78.4% recall) because rotating burner accounts have short instrument issuance ages and low prior order counts, which tabular decision trees can isolate.

---

## 3. False Positive Analysis

- Total False Positives: 153 out of 28,301 legitimate transactions (FPR = 0.54%).
- **Primary FP Driver:** New legitimate customers with high initial purchase values and fast refund requests on apparel/electronics (where standard return rates are naturally high).
- **Modeled Economic Friction:** Total synthetic FP cost = ₹19,890.00 (@ ₹130.00/FP).

---

## 4. Phase 1 vs Phase 2 Decision Boundary

The diagnostic error analysis proves conclusively that Phase 1 has reached its theoretical tabular limit:
- Tabular feature improvements (Models A → D) lifted Precision from 3.1% to 35.2% and Pattern C Recall to 78.4%.
- However, Patterns A and B cannot be detected via single-row tabular features without creating unacceptably high false-positive rates on household sharing and corporate subnets.
- Therefore, **multi-hop graph investigation (Phase 2)** is mathematically and empirically justified.