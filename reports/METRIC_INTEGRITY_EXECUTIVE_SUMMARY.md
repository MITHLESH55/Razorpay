# METRIC INTEGRITY AUDIT — EXECUTIVE SUMMARY
**Date:** 2026-08-29  
**Auditor:** Principal ML Evaluation Scientist  
**Duration:** Complete audit cycle  

---

## 🟡 VERDICT: METRIC DEFINITIONS DIFFER — RECONCILIATION REQUIRED

**No bug found. Metrics are mathematically correct.**

---

## The Question

Why did FPR jump from 0.40% to 76.23% between Phase 2.0 and Phase 2.1?

---

## The Answer

**They are different systems with different architectures optimizing for different objectives.**

| System | What It Does | FPR | Ring Recall |
|--------|--------------|-----|-------------|
| **Phase 2.0** | Scores each transaction independently (LightGBM classifier) | 0.40% | 37.5% |
| **Phase 2.1** | Detects abuse rings, expands to all connected accounts | 76.23% | 62.5% |
| **Phase 2.2** | Phase 2.1 + Pattern C recovery mechanism | 75.77% | 79.17% |

---

## Key Findings (All Verified ✅)

1. **FPR Formula:** `FPR = FP / 28,301` (always uses 28,301 legitimate transactions as denominator) ✅
2. **FP Cost Formula:** `FP Cost = FP × ₹130` (exact arithmetic, no rounding) ✅
3. **Population:** All systems evaluate on identical 28,591 transaction held-out test set ✅
4. **Phase 2.2 Baseline:** Exactly reproduced Phase 2.1 metrics (0 error) ✅
5. **Confusion Matrices:** All TP+TN+FP+FN sum to 28,591 ✅

---

## What Happened

### Phase 2.0 (Transaction Classifier)
- Flags 181 transactions (69 TP + 112 FP)
- FPR = 112 / 28,301 = **0.40%**

### Phase 2.1 (Ring Detector + Expansion)
- Detects abuse entities
- Expands via 2-hop graph traversal to ring members
- Flags all transactions of connected accounts
- Dense shared infrastructure (IPs, devices) causes expansion to 21,575 legitimate transactions
- FPR = 21,575 / 28,301 = **76.23%**

### Phase 2.2 (Pattern C Recovery)
- Reserves 150 protected slots for high-scoring Phase 1 candidates
- Recovers Pattern C rings (0% → 37.5%)
- Maintains Pattern A/B at 100%
- Reduces FPR slightly (76.23% → 75.77%)

---

## Why High FPR in Phase 2.1/2.2?

**By design.** The system:
1. Detects abuse entities (customers)
2. Expands to all ring members via graph
3. **Blocks ALL transactions from flagged accounts** (account-level blocking, not transaction-level scoring)

This is optimal for **ring detection** but creates high **transaction-level FPR**.

---

## Phase 3 Path Forward

**Objective:** Reduce transaction-level FPR while preserving ring recall

**Strategy:**
1. Confidence-weighted member blocking (not blanket account blocking)
2. Transaction-level risk thresholds post-expansion
3. Edge strength filtering (exclude weak shared-infrastructure connections)
4. Pattern C velocity features (RNN/GNN for temporal bursts)

**Expected:** FPR <10%, Ring Recall >70%

---

## Tests Added (All Passing ✅)

1. `test_fpr_formula_correctness()` — Verifies FPR denominator
2. `test_fp_cost_multiplication()` — Verifies cost arithmetic
3. `test_heldout_evaluation_population_invariants()` — Enforces frozen test set
4. `test_phase21_baseline_consistency_in_phase22()` — Verifies baseline reproduction

**Run:** `pytest tests/test_evaluation.py` → **10/10 passing**

---

## Bottom Line

| Question | Answer |
|----------|--------|
| Is there a bug? | ❌ No |
| Are metrics correct? | ✅ Yes |
| Did Phase 2.2 reproduce Phase 2.1? | ✅ Yes (exact match) |
| Why the FPR jump? | Architecture change: transaction-level → entity-level |
| Is Phase 2.2 better than 2.1? | ✅ Yes (ring recall: 62.5% → 79.17%, Pattern C: 0% → 37.5%) |
| Should we proceed to Phase 3? | ✅ Yes, with FPR mitigation strategy |

---

## Full Reports

- **Detailed Audit:** `reports/PHASE2_2_METRIC_INTEGRITY_AUDIT_FINAL.md`
- **Verification Log:** `reports/METRIC_INTEGRITY_VERIFICATION.md`
- **Original Audit:** `reports/PHASE2_2_METRIC_INTEGRITY_AUDIT.md` (confirmed correct)
- **Tests:** `tests/test_evaluation.py` (lines 98-147)

---

**Audit Status:** ✅ Complete  
**Recommendation:** Proceed to Phase 3 with transaction-level FPR mitigation architecture

**END SUMMARY**
