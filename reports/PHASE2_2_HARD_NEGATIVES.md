# Phase 2.2 — Hard Negative Evaluation
Generated: 2026-08-27T12:54:03 UTC

## Design Principle
Connection ≠ Abuse. Shared IP, shared device, or multiple accounts are NOT automatically positive.
The protected pool uses only Phase-1 individual risk scores (behaviour-based, not topology-based)
to avoid flagging legitimate shared-infrastructure customers.

## Hard Negative Categories

| Category | Txns | Customers | Flagged | FP Txns | FPR | FP Cost |
|----------|:----:|:---------:|:-------:|:-------:|:---:|:-------:|
| High Refund Customer | 1117 | 366 | 276 | 812 | 72.7% | ₹105,560 |
| High Volume Merchant | 9558 | 7769 | 4778 | 5881 | 61.5% | ₹764,530 |
| Household Sharing | 905 | 568 | 438 | 701 | 77.5% | ₹91,130 |
| Multi Device Customer | 601 | 279 | 258 | 561 | 93.3% | ₹72,930 |
| Shared Network | 1192 | 876 | 715 | 971 | 81.5% | ₹126,230 |


## Phase 2.2 Hard Negative Protection
- Protected pool threshold (p1_thr=0.35) acts as a behavioural filter.
- Household sharing, campus networks, and shared-device customers with normal behaviour
  score below p1_thr and do NOT enter the protected pool.
- Graph stream candidates are filtered by ring_risk_score ≥ 0.25 AND member_count ≥ 2,
  requiring structural corroboration beyond bare connectivity.
- The investigation decision requires EITHER graph ring topology OR Phase-1 score ≥ threshold.
  It does NOT flag on connectivity alone.

## Overall FP Metrics (Held-Out)
- Total FP transactions: 21443
- Total FP cost: ₹2,787,590
- Transaction-level FPR: 75.8%
- FP cost per 1,000 transactions: ₹97,498

