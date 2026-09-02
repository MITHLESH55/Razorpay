# Phase 2.2 — Candidate Source Analysis
Generated: 2026-08-27T12:54:03 UTC

## Source Contribution (Held-Out Test)

| Source | Unique Candidates | True Abuse | Rings | Pat A | Pat B | Pat C |
|--------|:-----------------:|:----------:|:-----:|:-----:|:-----:|:-----:|
| Phase 1 only | 85 | 55 | 8 | 0 | 0 | 8 |
| Graph only | 12113 | 78 | 16 | 12 | 4 | 0 |
| Both | 375 | 5 | 3 | 1 | 2 | 0 |
| Total Hybrid | 12573 | 138 | 24 | 12 | 4 | 8 |
| Final Budget (protected) | 1000 | 19 | 8 | 2 | 3 | 3 |


## Key Observations
- **Phase 1 only** candidates carry 100% of Pattern C rings — exclusively behavioural/tabular signal.
- **Graph only** candidates carry all Pattern A and B rings — structural/relational topology.
- **Both** (Phase 1 + Graph) represents overlap; customers flagged by both streams.
- The **protected pool (P=150)** guarantees Phase-1-only candidates enter the investigation budget.

## Attribution Integrity
- No source uses ground-truth labels (ring_id, abuse_label, pattern_type) during candidate generation.
- Source attribution is deterministic and reproducible.
- Phase 1 stream and graph stream remain fully independent candidate sources.
