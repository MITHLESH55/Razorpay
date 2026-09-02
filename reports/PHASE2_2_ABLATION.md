# Phase 2.2 — Ablation Study
Generated: 2026-08-27T12:54:03 UTC

## Validation Guardrails (P=0 baseline minus 5pp tolerance)
| Metric | Guardrail | Held-Out Result | Pass? |
|--------|:---------:|:---------------:|:-----:|
| Pattern A | ≥ 65.0% | 100.0% | ✅ |
| Pattern B | ≥ 23.6% | 100.0% | ✅ |
| Ring Recall | ≥ 35.0% | 79.2% | ✅ |
| FPR | ≤ 90.0% | 75.8% | ✅ |

## Pattern Matrix (Validation + Held-Out)

| System | Pattern A | Pattern B | Pattern C | Ring Recall | FPR (cand) | Multi-Obj |
|--------|:---------:|:---------:|:---------:|:-----------:|:----------:|:---------:|
| Phase 1 (frozen) | 91.7% | 100.0% | 0.0% | 62.5% | — | — |
| Phase 2.1 (frozen) | 91.7% | 100.0% | 0.0% | 62.5% | — | — |
| Phase 2.2 P=0 | 70.0% | 28.6% | 0.0% | 37.5% | 7.47% | 3.6324 |
| Phase 2.2 P=50 | 70.0% | 28.6% | 0.0% | 37.5% | 7.47% | 3.6324 |
| Phase 2.2 P=100 | 70.0% | 28.6% | 28.6% | 45.8% | 7.41% | 4.9425 |
| Phase 2.2 P=150 ← **SELECTED** | 70.0% | 28.6% | 28.6% | 45.8% | 7.41% | 4.9426 |
| Phase 2.2 P=200 | 60.0% | 28.6% | 100.0% | 62.5% | 7.11% | 7.8360 |
| Phase 2.2 P=300 | 60.0% | 28.6% | 100.0% | 62.5% | 7.10% | 7.8362 |
| **Phase 2.2 Final (held-out)** | **100.0%** | **100.0%** | **37.5%** | **79.2%** | **75.8%** | — |


> Note: Validation metrics use candidate-level FPR (fraction of legitimate customers in top-K).
> Held-out FPR is transaction-level from the full investigation pipeline.

## Configuration Freeze
Selected P=150 (validation-optimal, all guardrails PASS).
Config frozen to configs/phase2_2_budget.json before any held-out evaluation.
