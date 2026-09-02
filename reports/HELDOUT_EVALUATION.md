# RiskOrbit — Held-Out Evaluation Report

> **IMPORTANT:** This report was generated using ONLY the locked model and frozen
> threshold. No retraining or threshold adjustment occurred after this evaluation.

---

## Primary Metrics (Held-Out Test Set)

| Metric | Value |
|--------|------:|
| Precision | **0.3517** |
| Recall | **0.2862** |
| F1 | **0.3156** |
| PR-AUC | **0.0969** |
| FPR | 0.0054 |
| Accuracy (informational only) | 0.9874 |

## Calibration & Reliability

- **Brier Score:** 0.0105
- **Expected Calibration Error (ECE):** 0.0062
- **Max Calibration Error (MCE):** 0.7317

## Confusion Matrix

| | Predicted Negative | Predicted Positive |
|---|------------------:|------------------:|
| **Actual Negative** | TN=28,148 | FP=153 |
| **Actual Positive** | FN=207 | TP=83 |

## Ring-Level Detection Metrics

- **Total Abuse Rings in Holdout:** 24
- **Rings Detected (>= 1 Member):** 11 (45.83% Ring Recall)
- **Strong Ring Detection (>= 50% Members):** 29.17%
- **Complete Ring Detection (100% Members):** 12.50%
- **Rings Completely Missed:** 13 (54.17%)
- **Average Detected Fraction per Ring:** 29.41%

## Support

- Abuse cases: 290
- Legitimate cases: 28,301
- Operating threshold: **0.3500**

## False-Positive Cost (Synthetic Estimate)

> DISCLAIMER: All cost figures are synthetic estimates. Not real Razorpay data.

- False positives: 153
- Cost per FP: ₹130.00
- **Total FP cost: ₹19,890.00**

## Abuse Pattern Breakdown

| pattern                    |   precision |   recall |     f1 |    fpr |   support_positive |
|:---------------------------|------------:|---------:|-------:|-------:|-------------------:|
| legitimate                 |           0 |   0      | 0      | 0.0054 |                  0 |
| pattern_a_shared_device    |           1 |   0.0069 | 0.0138 | 0      |                144 |
| pattern_b_cross_merchant   |           1 |   0.0455 | 0.087  | 0      |                 44 |
| pattern_c_rotating_account |           1 |   0.7843 | 0.8791 | 0      |                102 |

## Hard-Negative Breakdown

| hard_negative_type    |   n_legitimate_rows |   n_incorrectly_flagged |   false_positive_rate |
|:----------------------|--------------------:|------------------------:|----------------------:|
| other_legitimate      |               14928 |                     153 |                0.0102 |
| high_refund_customer  |                1117 |                       0 |                0      |
| high_volume_merchant  |                9558 |                       0 |                0      |
| household_sharing     |                 905 |                       0 |                0      |
| multi_device_customer |                 601 |                       0 |                0      |
| shared_network        |                1192 |                       0 |                0      |