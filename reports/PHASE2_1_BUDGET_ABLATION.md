# PHASE 2.1 BUDGET ABLATION

**Frozen K = 1000** (selected on validation set, saved to configs/phase2_1_budget.json)

## Held-Out Budget Ablation Table

| Budget K | Investigated | Ring Recall | Pat A | Pat B | Pat C | Cand Prec | Est FP Cost |
|----------|-------------|-------------|-------|-------|-------|-----------|------------|
| 50 | 50 | 4.17% | 0 | 1 | 0 | 2.00% | Rs.6,370 |
| 100 | 100 | 12.50% | 1 | 2 | 0 | 3.00% | Rs.12,610 |
| 250 | 250 | 12.50% | 1 | 2 | 0 | 1.20% | Rs.32,110 |
| 500 | 500 | 16.67% | 2 | 2 | 0 | 0.80% | Rs.64,480 |
| 1,000 | 1,000 | 25.00% | 2 | 4 | 0 | 0.80% | Rs.128,960 |

> FP Cost = (investigated - true abuse in budget) x Rs.130 analyst cost per false lead.

## Budget Selection Rationale

K=1000 was chosen because:
1. Ring recall plateaus around K=1000 in validation (diminishing gains beyond).
2. K=1000 fits within analyst capacity for batch investigation.
3. The 250->500->1000 range shows meaningful ring recall gain from graph candidates.
