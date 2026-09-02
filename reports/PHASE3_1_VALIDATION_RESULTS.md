# PHASE 3.1 — VALIDATION RESULTS & WEIGHT ABLATION

**Status:** ✅ Completed  
**Dataset:** Validation Split (`data/splits/validation.csv`, 28,591 transactions)  
**Schema Version:** 3.1.0  
**Date:** 2026-08-29  

---

## Executive Summary

This report documents the validation-only performance experiments and weight ablation studies for the Phase 3.1 Transaction Gating architecture.

**Crucial Compliance:**
- **Zero test set access:** All evaluations in this report were performed strictly on `data/splits/validation.csv`.
- **Frozen baselines respected:** Phase 1 LightGBM artifact and Phase 2.1/2.2 graph definitions were unmodified.
- **Controlled comparison:** Phase 3.1 transaction gating is evaluated directly against the Phase 2.2 blanket expansion baseline on identical validation data.

---

## Benchmark Comparison (Validation Set)

| Architecture | Gating Policy | Validation FPR (%) | Validation FP Count | FP Cost (₹130/FP) | Validation Ring Recall (%) | Pattern A Recall | Pattern B Recall | Pattern C Recall |
|---|---|---|---|---|---|---|---|---|
| **Phase 2.0 (Model E)** | Transaction-Only LightGBM | **0.42%** | 118 | ₹15,340 | **41.67%** | 50.00% | 50.00% | 25.00% |
| **Phase 2.1 Baseline** | 2-Hop Blanket Expansion | **76.10%** | 21,536 | ₹27,99,680 | **62.50%** | 100.00% | 100.00% | 0.00% |
| **Phase 2.2 Baseline (P=150)** | Protected Pool + Expansion | **75.64%** | 21,407 | ₹27,82,910 | **79.17%** | 100.00% | 100.00% | 37.50% |
| **Phase 3.1 (Baseline Weights)** | Confidence-Weighted Gating | **2.85%** | **807** | **₹1,04,910** | **75.00%** | **100.00%** | **100.00%** | **25.00%** |
| **Phase 3.1 (Tuned Weights)** | Balanced Multi-Signal Gating | **3.94%** | **1,115** | **₹1,44,950** | **79.17%** | **100.00%** | **100.00%** | **37.50%** |

---

## Key Performance Insights

1. **Massive False Positive Reduction:**  
   Validation FPR dropped from **75.64%** in Phase 2.2 to **3.94%** in Phase 3.1 Tuned Gating — a **94.8% reduction in false positive transaction volume** (saving ~₹26.38L in simulated operational review costs).
2. **Preserved High Ring Recall:**  
   The Phase 3.1 Tuned Gating configuration achieves **79.17% overall ring recall** (matching Phase 2.2), maintaining **100% detection for Pattern A and Pattern B rings**.
3. **Decoupled Decisioning:**  
   By requiring secondary/tertiary ring members to exhibit non-trivial individual risk ($p1 \ge 0.15$ or $p1 \ge 0.35$), legitimate transactions conducted on shared devices/IPs by benign users are cleared instead of blocked.

---

## Weight Ablation Study

Four distinct weight configurations were evaluated across the validation partition:

| Config ID | $w_{\text{p1}}$ | $w_{\text{conf}}$ | $w_{\text{strength}}$ | $w_{\text{div}}$ | Val FPR (%) | Val FP Count | Ring Recall (%) | Strong Ring Recall (%) |
|---|---|---|---|---|---|---|---|---|
| **Config 1: Equal Distribution** | 0.40 | 0.30 | 0.15 | 0.15 | 2.85% | 807 | 75.00% | 66.67% |
| **Config 2: Phase 1 Dominant** | 0.60 | 0.20 | 0.10 | 0.10 | 1.15% | 325 | 62.50% | 50.00% |
| **Config 3: Confidence Dominant** | 0.30 | 0.40 | 0.15 | 0.15 | 6.82% | 1,930 | 79.17% | 75.00% |
| **Config 4: Balanced Diversity (Selected)** | **0.35** | **0.30** | **0.15** | **0.20** | **3.94%** | **1,115** | **79.17%** | **70.83%** |

### Analysis:
- **Config 2 (Phase 1 Dominant):** Extremely low FPR (1.15%), but sacrifices ring recall on weak-transaction rings (drops to 62.50%).
- **Config 3 (Confidence Dominant):** Maximizes ring recall (79.17%), but admits higher FPR (6.82%) due to over-relying on graph proximity.
- **Config 4 (Selected Champion):** Increases edge diversity weight $w_{\text{div}} = 0.20$, enforcing multi-signal corroboration. Matches peak ring recall (79.17%) while holding FPR under 4.0%.

---

## Tier Distribution Across Validation Transactions

| Tier | Total Transactions Evaluated | Flagged Count | Cleared Count | Flag Rate (%) |
|---|---|---|---|---|
| **PRIMARY** | 312 | 294 | 18 | 94.23% |
| **SECONDARY** | 1,480 | 642 | 838 | 43.38% |
| **TERTIARY** | 3,120 | 215 | 2,905 | 6.89% |
| **ISOLATED** | 23,679 | 254 | 23,425 | 1.07% |
| **Total** | **28,591** | **1,405** | **27,186** | **4.91%** |

**Crucial Takeaway:**  
In Phase 2.2, all 4,912 transactions in PRIMARY, SECONDARY, and TERTIARY tiers were blocked (100%). In Phase 3.1, **TERTIARY transactions are cleared 93.11% of the time**, dramatically reducing false positives on peripheral accounts.
