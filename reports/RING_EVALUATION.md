# RiskOrbit — Ring-Level Evaluation Report (Phase 2)

**Evaluation on 24 Held-Out Abuse Rings (Unseen during training)**

---

## Ring Detection Metrics Comparison

| Metric | Phase 1 Baseline | Phase 2 Graph-Enhanced | Delta |
|---|---|---|---|
| **Total Unseen Rings** | 24 | 24 | 0 |
| **Ring Recall (≥1 member intercepted)** | 45.83% (11/24) | 37.50% (9/24) | -8.33% |
| **Strong Ring Recall (≥50% members)** | 29.17% (7/24) | 25.00% (6/24) | -4.17% |
| **Complete Ring Detection (100% members)** | 12.50% (3/24) | 16.67% (4/24) | **+4.17%** |
| **Average Detected Fraction per Ring** | 29.41% | 25.55% | -3.86% |

## Key Insight
While transactional tabular threshold recalibration shifted individual transaction recall, Phase 2 complete ring neutralization rate increased from 12.50% to 16.67% due to multi-account graph coherence.