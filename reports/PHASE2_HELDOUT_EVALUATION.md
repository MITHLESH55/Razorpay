# RiskOrbit — Phase 2 Held-Out Evaluation Report

**Model:** `riskorbit-risk-v2`  
**Operating Threshold:** 0.3200 (selected on validation only)  
**Evaluation Set:** Locked Held-Out Test  

---

## Primary Metrics

- **Precision:** 0.3812
- **Recall:** 0.2379
- **F1-Score:** 0.2930
- **PR-AUC:** 0.1140
- **FPR:** 0.0040
- **TP:** 69  |  **FP:** 112  |  **FN:** 221  |  **TN:** 28189
- **Modeled FP Cost:** ₹14,560

## Ring-Level Metrics

- Ring Recall: 0.3750
- Strong Ring Recall: 0.2500
- Complete Ring Detection: 0.1667
- Missed Rings: 15
- Avg Detected Fraction: 0.2555

## Hard-Negative Category FPR

| Category | Support | FP | FPR |
|---|---|---|---|
| high_refund_customer | 1117 | 0 | 0.0000 |
| high_volume_merchant | 9558 | 0 | 0.0000 |
| household_sharing | 905 | 0 | 0.0000 |
| multi_device_customer | 601 | 0 | 0.0000 |
| shared_network | 1192 | 0 | 0.0000 |
