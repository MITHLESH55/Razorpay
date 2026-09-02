# PHASE 2.1 CANDIDATE COVERAGE ANALYSIS

## Coverage Funnel

ALL EVENTS (28,591 test transactions)
    |
    |-- Phase 1 Stream -----> 460 candidates (score >= 0.20)
    |-- Graph Stream -------> 12,488 candidates (structural ring scoring, unsupervised)
    |
    Union (Deduplicated) ---> 12,573 unique candidates
            |-- Phase 1 only: 85
            |-- Graph only:   12,113
            |-- Both:         375
                    |
                    Budget Cap (K=1000) -> Top 1000 -> Investigation

## Candidate Metrics (denominator = all 24 held-out rings)

| Metric | Value |
|--------|-------|
| Rings in Union Candidates | 24 / 24 |
| **Candidate Recall** | **100.00%** |
| Candidate Precision | 1.10% |
| True Abuse Customers in Union | 138 |
| Total Union Candidates | 12,573 |

## Source-Level Ring Coverage

| Stream | Candidates | True Abuse | Rings | Pat A | Pat B | Pat C |
|--------|-----------|------------|-------|-------|-------|-------|
| Phase 1 only | 85 | 55 | 8 | 0 | 0 | 8 |
| Graph only | 12,113 | 78 | 16 | 12 | 4 | 0 |
| Both | 375 | 5 | 3 | 1 | 2 | 0 |
| Total Hybrid | 12,573 | 138 | 24 | 12 | 4 | 8 |

## Strict Denominator Accounting

| Metric | Numerator | Denominator | Value |
|--------|-----------|-------------|-------|
| Candidate Recall | Rings with >=1 member in union | All 24 rings | 100.00% |
| Candidate Precision | True abuse in union | All union candidates | 1.10% |
| E2E Ring Recall | Rings confirmed by investigation | All 24 rings | 62.50% |
| Complete Ring Detection | Rings with 100% members confirmed | All 24 rings | 16.67% |
