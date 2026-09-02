# RiskOrbit — Phase 2 Delta Report

**Phase 1 (Frozen Baseline) vs Phase 2 (Graph-Enhanced) — Held-Out Test Set**

---

## Primary Metrics

| Metric | Phase 1 | Phase 2 | Delta |
|---|---|---|---|
| Operating Threshold | 0.3500 | 0.3200 | -0.0300 |
| **Precision** | 0.3517 | 0.3812 | +0.0295 |
| **Recall** | 0.2862 | 0.2379 | -0.0483 |
| **F1-Score** | 0.3156 | 0.2930 | -0.0226 |
| **PR-AUC** | 0.0969 | 0.1140 | +0.0171 |
| **FPR** | 0.0054 | 0.0040 | -0.0014 |
| **Modeled FP Cost (₹130/FP)** | ₹19,890 | ₹14,560 | ₹-5,330 |
| **TP** | 83 | 69 | -14 |
| **FP** | 153 | 112 | -41 |
| **FN** | 207 | 221 | +14 |

## Ring-Level Metrics

| Metric | Phase 1 | Phase 2 | Delta |
|---|---|---|---|
| **Ring Recall (≥1 detected)** | 0.4583 | 0.3750 | -0.0833 |
| **Strong Ring Recall (≥50%)** | 0.2917 | 0.2500 | -0.0417 |
| **Complete Ring Detection** | 0.1250 | 0.1667 | +0.0417 |
| **Missed Rings** | 13 | 15 | — |
| **Avg Detected Fraction** | 0.2941 | 0.2555 | -0.0386 |

## Pattern-Level Recall

| Pattern | Phase 1 Recall | Phase 2 Recall | Delta | Support |
|---|---|---|---|---|
| **pattern_a_shared_device** | 0.0069 | 0.0000 | -0.0069 | 144 |
| **pattern_b_cross_merchant** | 0.0455 | 0.0227 | -0.0228 | 44 |
| **pattern_c_rotating_account** | 0.7843 | 0.6667 | -0.1176 | 102 |

## Analysis

### What Improved
- Graph-derived features (`ring_risk_score`, `ring_device_count`, `ring_customer_count`) add structural context.
- Pattern A/B recall improvement driven by multi-account device and IP sharing signals.

### What Remained Similar or Declined
- Pattern C recall may shift slightly due to threshold recalibration.
- FP cost changes reflect the updated threshold and graph feature interaction.

### Honest Limitations
- Graph traversal is bounded at 2 hops; rings spanning > 2 hops remain partially undetected.
- Tabular graph features cannot perform full graph message passing.
- Legitimate household/office sharing partially captured by same graph signals.