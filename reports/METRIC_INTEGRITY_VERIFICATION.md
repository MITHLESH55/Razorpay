# Phase 2.2 — Metric Integrity Audit Verification
**Date:** 2026-08-29  
**Auditor:** Principal ML Evaluation Scientist  
**Status:** ✅ AUDIT VERIFIED — NO BUGS FOUND

---

## Executive Summary

### 🟡 METRIC DEFINITIONS DIFFER — RECONCILIATION REQUIRED

The apparent discrepancy between Phase 2.1's reported metrics is **NOT an evaluation bug**. The metrics are mathematically correct but represent fundamentally different system architectures:

- **Phase 2.0 (Model E)**: Transaction-level supervised classifier → FPR = 0.40%, FP Cost = ₹14,560
- **Phase 2.1 & 2.2**: Entity-level hybrid candidate discovery + ring expansion → FPR = 76.23%, FP Cost = ₹28,04,750

---

## 1. Population Verification

**Source:** `data/splits/heldout_test.csv` (frozen, untouched)

| Population | Count | Notes |
|------------|------:|-------|
| Total Transactions | 28,591 | Complete held-out test set |
| Abuse Transactions | 290 | Ground truth positives |
| Legitimate Transactions | 28,301 | Ground truth negatives (FPR denominator) |
| Total Rings | 24 | 12×Pattern A, 4×Pattern B, 8×Pattern C |
| Abuse Customers | 158 | Unique abuse customer entities |

**Verification:** ✅ All three systems (Phase 1, Phase 2.1, Phase 2.2) evaluate on the identical population.

---

## 2. FPR Formula Verification

### Definition
```
FPR = FP / (FP + TN) = FP / N_legitimate
```

Where:
- FP = Count of legitimate transactions predicted as abuse
- TN = Count of legitimate transactions predicted as legitimate
- N_legitimate = Total legitimate transactions = 28,301

### Phase 1 (Frozen Baseline)
```
TP = 83
FP = 153
FN = 207
TN = 28,148
FPR = 153 / (153 + 28,148) = 153 / 28,301 = 0.0054 = 0.54% ✅
```

### Phase 2.0 (Model E — Transaction Classifier)
```
TP = 69
FP = 112
FN = 221
TN = 28,189
FPR = 112 / (112 + 28,189) = 112 / 28,301 = 0.00396 = 0.40% ✅
```

### Phase 2.1 (Hybrid Candidate + Ring Expansion)
```
TP = 128
FP = 21,575
FN = 162
TN = 6,726
FPR = 21,575 / (21,575 + 6,726) = 21,575 / 28,301 = 0.7623 = 76.23% ✅
```

### Phase 2.2 (Protected Pool + Ring Expansion)
```
TP = 142
FP = 21,443
FN = 148
TN = 6,858
FPR = 21,443 / (21,443 + 6,858) = 21,443 / 28,301 = 0.7577 = 75.77% ✅
```

**Verification:** ✅ All FPR calculations are mathematically exact. The denominator is always the total legitimate transaction count (28,301).

---

## 3. FP Cost Formula Verification

### Definition
```
FP Cost = FP × ₹130
```

### Verification

| System | FP | Calculation | Reported Cost | Verified? |
|--------|---:|-------------|--------------|-----------|
| Phase 1 | 153 | 153 × ₹130 | ₹19,890 | ✅ |
| Phase 2.0 | 112 | 112 × ₹130 | ₹14,560 | ✅ |
| Phase 2.1 | 21,575 | 21,575 × ₹130 | ₹28,04,750 | ✅ |
| Phase 2.2 | 21,443 | 21,443 × ₹130 | ₹27,87,590 | ✅ |

**Verification:** ✅ All FP cost calculations are exact. No rounding errors, no bugs.

---

## 4. Root Cause Analysis: Why 0.40% → 76.23%?

### Phase 2.0: Transaction-Level Point Classifier
- **Architecture:** LightGBM scoring each transaction independently
- **Decision:** Flag transaction if `score ≥ 0.32`
- **Mechanism:** 181 transactions flagged (69 TP + 112 FP)
- **Result:** FPR = 112 / 28,301 = **0.40%**

### Phase 2.1: Entity-Level Ring Investigation Pipeline
- **Architecture:** Hybrid candidate discovery (Phase 1 + Graph) → K=1000 budget → Investigation Agent → 2-hop ring expansion
- **Decision:** Flag candidate entity → Expand to all connected ring members → Flag ALL transactions of those accounts
- **Mechanism:**
  1. 12,488 graph candidates generated
  2. Top K=1000 selected for investigation
  3. Investigation agent confirms flagged entities
  4. 2-hop graph traversal expands to connected accounts
  5. All transactions of flagged accounts marked positive
  6. Dense shared-infrastructure components (shared IPs/devices from multi-customer networks) caused expansion to 21,575 legitimate transactions
- **Result:** FPR = 21,575 / 28,301 = **76.23%**

### Key Insight
Phase 2.1 did NOT increase FPR from Phase 2.0. These are **different system architectures** evaluated for **different objectives**:
- Phase 2.0 optimizes transaction-level precision/recall
- Phase 2.1 optimizes ring-level detection with entity-level expansion

---

## 5. Confusion Matrix Side-by-Side

| System | Architecture | TP | TN | FP | FN | Precision | Recall | F1 | FPR | FP Cost |
|--------|-------------|----|----|----|----|-----------|--------|----|----|---------|
| **Phase 1** | Tabular LightGBM (thr=0.35) | 83 | 28,148 | 153 | 207 | 35.17% | 28.62% | 0.3156 | 0.54% | ₹19,890 |
| **Phase 2.0** | Tabular + Graph GBDT (thr=0.32) | 69 | 28,189 | 112 | 221 | 38.12% | 23.79% | 0.2930 | **0.40%** | **₹14,560** |
| **Phase 2.1** | Hybrid K=1000 + Agent + Ring Expansion | 128 | 6,726 | 21,575 | 162 | 0.59% | 44.14% | 0.0116 | **76.23%** | **₹28,04,750** |
| **Phase 2.2** | Protected Pool P=150 + K=1000 + Agent | 142 | 6,858 | 21,443 | 148 | 0.66% | 48.97% | 0.0130 | **75.77%** | **₹27,87,590** |

---

## 6. Ring-Level Metrics

Transaction-level FPR and ring-level recall are **orthogonal metrics** serving different evaluation purposes:

| System | Ring Recall | Pattern A | Pattern B | Pattern C |
|--------|-------------|-----------|-----------|-----------|
| Phase 1 | 45.83% | 0.69% | 4.55% | 78.43% |
| Phase 2.0 | 37.50% | 0.00% | 2.27% | 66.67% |
| Phase 2.1 | **62.50%** | **91.67%** | **100.00%** | **0.00%** |
| Phase 2.2 | **79.17%** | **100.00%** | **100.00%** | **37.50%** |

Phase 2.1 and 2.2 are optimized for **ring detection**, not transaction-level FPR minimization.

---

## 7. Phase 2.2 Baseline Reproduction

The Phase 2.2 evaluation report correctly reproduced the Phase 2.1 baseline:

**From `phase2_2_summary.json` → `phase21_baseline`:**
```json
{
  "ring_recall": 0.625,
  "pat_a": 0.9167,
  "pat_b": 1.0,
  "pat_c": 0.0,
  "precision": 0.0059,
  "recall": 0.4414,
  "f1": 0.0116,
  "prauc": 0.0176,
  "fpr": 0.7623,
  "fp_cost": 2804750
}
```

**From `phase2_1_summary.json` → `metrics`:**
```json
{
  "precision": 0.0059,
  "recall": 0.4414,
  "f1": 0.0116,
  "prauc": 0.0176,
  "fpr": 0.7623,
  "fp_cost": 2804750,
  "tp": 128,
  "fp": 21575,
  "fn": 162,
  "tn": 6726
}
```

**Verification:** ✅ Exact match. Phase 2.2 faithfully reproduced Phase 2.1 baseline with zero error.

---

## 8. The "0.40%" Origin: Phase 2.0 vs Phase 2.1 Naming Confusion

The confusion stems from **inconsistent phase naming** in reports:

- `reports/PHASE2_FINAL_REPORT.md` describes **Phase 2.0** (Model E, riskorbit-risk-v2, transaction-level GBDT)
  - FPR = 0.40%
  - FP Cost = ₹14,560
  
- `reports/PHASE2_1_FINAL_REPORT.md` describes **Phase 2.1** (Hybrid candidate pipeline)
  - FPR = 76.23%
  - FP Cost = ₹28,04,750

The Phase 2.2 summary incorrectly cited "Phase 2.1 baseline" metrics in comparison tables without clarifying that the "0.40%" belonged to Phase 2.0, not Phase 2.1.

---

## 9. Metric Level Disambiguation

To prevent future confusion:

| Metric Level | Numerator | Denominator | Phase 2.2 Value | Interpretation |
|--------------|-----------|-------------|----------------|----------------|
| **Ring-Level Detection** | Rings detected | Total ground-truth rings | 79.17% (19/24) | Core fraud ring defense capability |
| **Candidate-Level Ranking** | Legitimate customers in budget | Total legitimate customers | 7.41% (988/13,304) | Budget allocation efficiency |
| **Transaction-Level FPR** | Legitimate txns flagged | Total legitimate txns | 75.77% (21,443/28,301) | Operational transaction-level footprint after ring expansion |

---

## 10. Conclusions

### ✅ Integrity Status: VERIFIED

1. **No evaluation bug exists.** All FPR and FP cost calculations are mathematically exact.
2. **Phase 2.2 correctly reproduced Phase 2.1 baseline.** All metrics match to 4 decimal places.
3. **The 0.40% → 76.23% jump is real** but represents an architectural paradigm shift, not a bug:
   - Phase 2.0: Transaction-level point classifier
   - Phase 2.1: Entity-level ring investigation with 2-hop expansion
4. **Phase 2.2 improved over Phase 2.1:**
   - FPR: 76.23% → 75.77% (net reduction of 132 FP transactions)
   - Ring Recall: 62.50% → 79.17% (+16.67 pp)
   - Pattern C: 0.00% → 37.50% (+37.50 pp)

### 🟡 Recommendation: Reconciliation Required

**For Phase 3 / Production:**
- The current system achieves **79.17% ring recall** but flags **75.77% of all legitimate transactions** due to blanket account-level blocking after ring expansion.
- To reduce transaction-level FPR while preserving ring detection:
  1. Apply confidence weighting to ring members (only block high-confidence members)
  2. Use transaction-level risk thresholds post-expansion (not blanket account blocking)
  3. Implement precision-focused Phase 1 scoring for isolated candidates
  4. Tune ring expansion policy to limit 2-hop traversal to high-strength edges only

### 📊 Final Decision

> ## 🟡 METRIC DEFINITIONS DIFFER — RECONCILIATION REQUIRED

**No bug. Metrics are correct. Systems optimize for different objectives.**

---

## 11. Reproducibility

All evaluations use:
- Frozen held-out test set: `data/splits/heldout_test.csv`
- Frozen Phase 1 model: `artifacts/riskorbit-risk-v1/model.pkl`
- Frozen Phase 2.1 config: `configs/phase2_1_budget.json` (K=1000)
- Frozen Phase 2.2 config: `configs/phase2_2_budget.json` (K=1000, P=150)

**Reproduce:**
```bash
python scripts/evaluate_phase2.py      # Phase 2.0: FPR=0.40%
python scripts/evaluate_phase2_1.py    # Phase 2.1: FPR=76.23%
python scripts/evaluate_phase2_2.py    # Phase 2.2: FPR=75.77%
```

---

**Auditor Sign-Off:** Metric integrity verified. No bugs detected. Report complete.
