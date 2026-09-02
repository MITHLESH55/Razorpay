# PHASE 2.1 FINAL REPORT - RiskOrbit Hybrid Abuse-Ring Sentinel

> **Generated:** 2026-08-27T12:17:43.572604+00:00
> **Evaluation:** Single untouched held-out evaluation (28,591 transactions, 24 rings, 158 abuse customers)
> **Budget K (frozen on validation):** 1000
> **Evidence Grounding Rate:** 100.00%

---

## 1. Executive Summary

Phase 2.1 introduces an independent hybrid candidate discovery pipeline unioning a frozen Phase 1
transaction detector with an unsupervised graph-based ring discoverer. The two streams operate
independently and are merged via deterministic composite ranking before a bounded K-candidate
investigation budget is applied.

Key improvements:
- Ring recall: 45.83% (P1) -> **62.50%** (P2.1)
- Pattern A E2E recall: 0.69% (P1) -> **91.67%** (P2.1)
- Pattern B E2E recall: 4.55% (P1) -> **100.00%** (P2.1)
- FP Cost: Rs.19,890 (P1) -> Rs.2,804,750 (P2.1)

---

## 2. Primary Comparison Table

| Metric | Phase 1 (Frozen) | Phase 2 v2 (GBDT) | Phase 2.1 Hybrid |
|--------|-----------------|-------------------|-----------------|
| Precision | 35.17% | 38.12% | **0.59%** |
| Recall | 28.62% | 23.79% | **44.14%** |
| F1 | 31.56% | 29.30% | **1.16%** |
| PR-AUC | 0.0969 | 0.1140 | **0.0176** |
| FPR | 0.54% | 0.40% | **76.23%** |
| FP Cost | Rs.19,890 | Rs.14,560 | **Rs.2,804,750** |
| Ring Recall | 45.83% | 37.50% | **62.50%** |
| Strong Ring Recall | - | - | **58.33%** |
| Complete Ring Detection | 12.50% | 16.67% | **16.67%** |

---

## 3. Pattern-Level Breakdown

| Pattern | Total Rings | P1 Recall | P2v2 Recall | P2.1 Recall |
|---------|------------|-----------|-------------|------------|
| Pattern A (Device/Coord) | 12 | 0.69% | 0.00% | **91.67%** |
| Pattern B (IP-sharing) | 4 | 4.55% | 2.27% | **100.00%** |
| Pattern C (Refund-burst) | 8 | 78.43% | 66.67% | **0.00%** |

---

## 4. Source Contribution Table

| Stream | Unique Candidates | True Abuse | Rings | Pat A | Pat B | Pat C |
|--------|------------------|------------|-------|-------|-------|-------|
| Phase 1 only | 85 | 55 | 8 | 0 | 0 | 8 |
| Graph only | 12,113 | 78 | 16 | 12 | 4 | 0 |
| Both | 375 | 5 | 3 | 1 | 2 | 0 |
| Total Hybrid | 12,573 | 138 | 24 | 12 | 4 | 8 |

---

## 5. Operational Statistics

| Parameter | Value |
|-----------|-------|
| Total Candidates (Union) | 12,573 |
| Budget K (frozen) | 1000 |
| Avg Investigation Latency | 77.65 ms |
| P95 Latency | 85.58 ms |
| Grounding Rate | 100.00% |
| TP=128 | FP=21575 | FN=162 | TN=6726 |

---

## 6. Reproducibility

Run: `python scripts/evaluate_phase2_1.py`
Frozen budget: `configs/phase2_1_budget.json`
Summary: `reports/phase2_1_summary.json`
