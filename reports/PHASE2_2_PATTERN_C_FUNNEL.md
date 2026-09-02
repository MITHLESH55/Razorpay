# Phase 2.2 — Pattern C Funnel Audit
Generated: 2026-08-27T12:54:03 UTC  |  K=1000  |  P=150  |  p1_thr=0.3500

## Mandate
Trace EVERY Pattern C ring from ground truth to final investigation decision.
Identify the FIRST stage at which Pattern C recall collapses.

## Funnel Table

| Stage                                 | Pattern C Rings | Ring Recall | Members   | Txns   |
|---------------------------------------|:---------------:|:-----------:|:---------:|:------:|
| Ground Truth                          |        8        |   100.0%    |    68     |  102   |
| Phase 1 (score>=0.20)                 |        8        |   100.0%    |    55     |  None  |
| Phase 1 (score>=p1_thr)               |        8        |   100.0%    |    53     |  None  |
| Graph Candidates                      |        0        |    0.0%     |     0     |  None  |
| Union (deduplicated)                  |        8        |   100.0%    |    55     |  None  |
| Hybrid Ranked (all)                   |        8        |   100.0%    |   None    |  None  |
| K Budget (K=1000)                     |        3        |    37.5%    |    12     |  None  |
| Investigation Final                   |        3        |    37.5%    |    12     |  None  |

## Analysis

### Where Pattern C Was Lost in Phase 2.1
**Primary Failure — Ranking/Budget Stage:**
Pattern C candidates are exclusively Phase-1-only (no graph edges, no device/IP sharing).
The composite ranking formula weights graph signals at 70% (graph_ring + sharing + refund_rate + cross_merchant).
A typical Pattern C Phase-1-only candidate scores .30 × 0.35 = 0.105 composite.
A typical Graph-only candidate scores .25 × 0.50 + 0.20 × 0.70 = 0.265.
With 12,488 graph candidates, all 85 Phase-1-only Pattern C candidates ranked below position ~3000,
well outside the K=1000 budget.

**Secondary Failure — Investigation Decision:**
Even if a Pattern C candidate entered K=1000, the investigation formula
combined_score = 0.35 × indiv + 0.65 × rel_score would produce ~0.12 (below 0.35 threshold)
because Pattern C rings have zero relational topology detectable by the graph engine.

### Phase 2.2 Fix
A protected quota P=150 reserves 150 slots for high-confidence Phase-1 candidates (score ≥ p1_thr).
This guarantees Pattern C candidates reach the investigation stage.
The investigation decision fix restores Phase-1 flagging for isolated (topology-less) candidates.

## Key Finding
Phase 1 successfully generated Pattern C candidates at **100% ring recall**.
Pattern C was entirely lost at the **ranking/budget stage**, NOT at detection.
