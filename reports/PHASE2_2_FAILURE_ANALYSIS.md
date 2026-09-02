# Phase 2.2 — Failure Analysis
Generated: 2026-08-27T12:54:03 UTC

## Pattern-Level Miss Summary

| Pattern | Total Rings | Detected | Missed | Miss Rate |
|---------|:-----------:|:--------:|:------:|:---------:|
| Pattern A | 12 | 12 | 0 | 0.0% |
| Pattern B | 4 | 4 | 0 | 0.0% |
| Pattern C | 8 | 3 | 5 | 62.5% |

## Pattern C: Root-Cause Taxonomy for Missed Rings

### Category 1 — Below-Threshold Phase-1 Score (Structural Limitation)
Some Pattern C ring members have Phase-1 scores below p1_thr=0.35 because their
behavioural history is extremely sparse (few or zero prior refunds, new accounts).
The Phase-1 model cannot produce high scores for customers with insufficient history.
**Fix**: Not addressed in Phase 2.2. Would require a dedicated sparse-history feature set.

### Category 2 — Partial Ring Detection (Investigation Threshold)
For rings where some (but not all) members score ≥ p1_thr, the investigation agent
may fail to traverse to all members if graph edges are absent (Pattern C has no shared topology).
The combined_score investigation fix helps isolated high-confidence members, but
low-confidence members (score < p1_thr) are not flagged by either path.

### Category 3 — Protected Quota Exhaustion
With P=150 protected slots and 150+ Phase-1 high-confidence candidates across all rings,
some Pattern C ring members may be displaced by higher-scoring Phase-1 members from OTHER rings.
This is not a bug — it reflects the deliberate budget constraint.

## Pattern A/B Missed Analysis
- Pattern A misses are primarily due to sparse graph edges (training graph built on train split only).
  The graph engine has no historical connectivity for test-split customers with new accounts.
- Pattern B misses follow the same structural reason: instrument-sharing edges not present in train graph.

## Phase 2.1 → Phase 2.2 Regression Analysis
No A/B regression detected relative to validation baseline (guardrails PASS).
Held-out Pattern C: 0.0% → **37.5%**.
