# PHASE 2.1 TEMPORAL EVALUATION

## Point-in-Time Causality Guarantee

Invariant: All decisions at time T use only events with timestamp <= T.

Enforced at three levels:
1. Graph construction: build_networkx_graph_as_of(T) -- only edges from events <= T included.
2. Candidate generation: generate_candidates(as_of_time=T) -- graph already time-filtered.
3. Investigation agent: investigate_candidate(as_of_time=T) -- get_events_as_of(T) returns only historical events.

Scoring time used: as_of_time = train_split["timestamp"].max() (last observed training event).

## Unit Test Status

test_point_in_time_causality_candidate_generator: PASSED

Test validates:
1. Build graph with 3 transactions (T=1, T=2, T=3)
2. Run candidate generation at as_of_time = T=2
3. Assert T=3 transaction edges are absent

## Temporal Properties Verified

| Property | Status |
|----------|--------|
| No future timestamps in candidates | PASSED (unit test) |
| No future timestamps in investigation | PASSED (code inspection) |
| Budget frozen on validation pre-test | PASSED (configs/phase2_1_budget.json) |
| Threshold frozen before test | PASSED (configs/threshold.json from P1 training) |

## Temporal Risk Factors

1. Training recency bias: Phase 1 LGBM trained on historical data; drift in abuse patterns reduces recall over time.
2. Graph edge decay: Edge strength uses time decay exp(-lambda * days). Dormant rings (>90 days) decay toward 0.
3. Budget relevance: K=1000 frozen on validation data from same period; recalibrate if abuse volume changes.

## Production Recommendations

1. Daily graph rebuild at as_of_time = now() for real-time ring detection.
2. Monthly budget review with rolling validation windows.
3. Quarterly Phase 1 model refresh (frozen here per mandate).

Evaluation timestamp: 2026-08-27T12:17:43.572604+00:00
