# Phase 2.2 — Budget & Quota Analysis
Generated: 2026-08-27T12:54:03 UTC

## Frozen Configuration
- **Total investigation budget K**: 1000
- **Protected Phase-1 quota P**: 150
- **Remaining slots (K-P)**: 850 (filled by global hybrid ranking)
- **Phase 1 threshold for protection**: 0.3500
- **Selection partition**: validation (held-out never touched during selection)

## Protected Quota Ablation (Validation)

| Quota P | Budget Used | Ring Recall | Pat A | Pat B | Pat C | Multi-Obj Score |
|---------|:-----------:|:-----------:|:-----:|:-----:|:-----:|:---------------:|
| P=0  | 1000 | 37.5% | 70.0% | 28.6% | 0.0% | 3.6324 |
| P=50  | 1000 | 37.5% | 70.0% | 28.6% | 0.0% | 3.6324 |
| P=100  | 1000 | 45.8% | 70.0% | 28.6% | 28.6% | 4.9425 |
| P=150 ← selected | 1000 | 45.8% | 70.0% | 28.6% | 28.6% | 4.9426 |
| P=200  | 1000 | 62.5% | 60.0% | 28.6% | 100.0% | 7.8360 |
| P=300  | 1000 | 62.5% | 60.0% | 28.6% | 100.0% | 7.8362 |


## How P Was Selected
1. P=0 result establishes the validation baseline (A=70.0%, B=28.6%, C=0.0%).
2. Guardrails: A≥baseline−5pp, B≥baseline−5pp, Ring Recall≥35%.
3. Among configurations that pass ALL guardrails, select maximum multi-objective score.
4. Tie-break: prefer smaller P (less disruption to A/B).
5. Selected P=150 on validation. Config frozen. Held-out evaluated once.

## Held-Out Result (K=1000, P=150)
- Ring Recall: **79.2%**
- Pattern C: **37.5%**
- FP Cost: **₹2,787,590**
- Investigation workload: **1000 candidates** (bounded, unchanged from Phase 2.1)
