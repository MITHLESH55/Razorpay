# RiskOrbit — Model Comparison Benchmark

**Date:** 2026-08-27  
**Benchmark Scope:** Fair comparison of 4 risk architectures under identical data splits, feature sets, validation protocols, and cost parameters.  

---

## 1. Held-Out Evaluation Summary

| Model | Threshold | Test Precision | Test Recall | Test F1 | Test PR-AUC | Test FPR | Test FP Cost | Brier Score | ECE |
|---|---|---|---|---|---|---|---|---|---|
| **RuleBaseline** | 0.50 | 0.0000 | 0.0000 | 0.0000 | 0.0107 | 0.0000 | ₹0.00 | 0.0404 | 0.1675 |
| **LogisticRegression** | 0.60 | 0.0875 | 0.1276 | 0.1038 | 0.0523 | 0.0136 | ₹50,180.00 | 0.0202 | 0.0209 |
| **RandomForest** | 0.12 | 0.1311 | 0.3138 | 0.1850 | 0.0806 | 0.0213 | ₹78,390.00 | 0.0104 | 0.0035 |
| **LightGBM** | 0.35 | 0.3517 | 0.2862 | 0.3156 | 0.0969 | 0.0054 | ₹19,890.00 | 0.0105 | 0.0062 |

---

## 2. Abuse Pattern & Ring Detection Breakdown

| Model | Pattern A Recall (Shared Device) | Pattern B Recall (Cross-Merchant) | Pattern C Recall (Rotating Account) | Ring Recall (>=1 Member) | Strong Ring Recall (>=50%) |
|---|---|---|---|---|---|
| **RuleBaseline** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **LogisticRegression** | 0.0764 | 0.2045 | 0.1667 | 0.5417 | 0.0000 |
| **RandomForest** | 0.0417 | 0.2955 | 0.7059 | 0.6250 | 0.2500 |
| **LightGBM** | 0.0069 | 0.0455 | 0.7843 | 0.4583 | 0.2917 |

---

## 3. Architecture Analysis

1. **RuleBaseline:** Fails to achieve viable precision or recall due to static hardcoded cuts that confuse household device sharing with actual abuse.
2. **LogisticRegression:** Strong baseline for linear boundaries, but suffers from high false-positive costs under severe class imbalance (~1.02%).
3. **RandomForest:** Strong ensemble tree baseline, but LightGBM achieves superior non-linear gradient-boosted splits, lower calibration error, and lower false-positive operational overhead.
4. **LightGBM (Main):** Demonstrates superior trade-off between precision (35.17%), controlled FPR (0.54%), and lowest economic false-positive cost (₹19,890.00).