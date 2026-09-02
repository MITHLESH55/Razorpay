# PHASE 2.1 HYBRID ABLATION STUDY

## Variant A - Phase 1 Only (Frozen Baseline)

| Metric | Value |
|--------|-------|
| Precision | 35.17% |
| Recall | 28.62% |
| F1 | 31.56% |
| Ring Recall | 45.83% |
| Complete Ring | 12.50% |
| Pattern A | 0.69% |
| Pattern B | 4.55% |
| Pattern C | 78.43% |
| FP Cost | Rs.19,890 |

## Variant B - Graph Only (Unsupervised Candidate Coverage)

| Metric | Value |
|--------|-------|
| Total Candidates | 12,488 |
| Candidate Precision | 0.66% |
| Rings Covered | 16/24 |
| Pattern A | 100.00% |
| Pattern B | 100.00% |
| Pattern C | 0.00% |

## Variant C - Union Candidates (Phase 1 + Graph, no budget)

| Stream | Candidates | Rings |
|--------|-----------|-------|
| Phase 1 only | 85 | 8 |
| Graph only | 12,113 | 16 |
| Both | 375 | 3 |
| **Total** | **12,573** | **24** |

## Variant E - Full Phase 2.1 (Hybrid + Ranking + Investigation) [PRIMARY]

| Metric | Value |
|--------|-------|
| Precision | **0.59%** |
| Recall | **44.14%** |
| F1 | **1.16%** |
| PR-AUC | **0.0176** |
| FPR | **76.23%** |
| FP Cost | **Rs.2,804,750** |
| Ring Recall (E2E) | **62.50%** |
| Strong Ring Recall | **58.33%** |
| Complete Ring | **16.67%** |
| Pattern A | **91.67%** |
| Pattern B | **100.00%** |
| Pattern C | **0.00%** |

## Summary Table

| Variant | Ring Recall | Pat A | Pat B | Pat C | FP Cost |
|---------|------------|-------|-------|-------|---------|
| A: Phase 1 Only | 45.83% | 0.69% | 4.55% | 78.43% | Rs.19,890 |
| B: Graph Only (cand) | 66.67% | 100.00% | 100.00% | 0.00% | - |
| E: Full Hybrid P2.1 | **62.50%** | **91.67%** | **100.00%** | **0.00%** | **Rs.2,804,750** |
