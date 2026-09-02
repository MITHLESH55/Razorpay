# Phase 2.2 — Reproducibility Report
Generated: 2026-08-27T12:54:03 UTC

## Frozen Configuration
`json
{
  "K": 1000,
  "P": 150,
  "p1_threshold": 0.35
}
`

## Exact Reproduction Commands
`ash
# 1. Run Phase 2.2 evaluation (validation tuning + held-out)
python scripts/evaluate_phase2_2.py

# 2. Generate all reports from summary JSON
python scripts/generate_all_phase2_2_reports.py

# 3. Run complete test suite (110 Phase 1/2.1 + 24 Phase 2.2 tests)
pytest --tb=short -q
`

## Artifacts
| Artifact | Role |
|----------|------|
| rtifacts/riskorbit-risk-v1/ | Frozen Phase 1 model (never modified) |
| data/splits/train.csv | Graph engine context (point-in-time safe) |
| data/splits/validation.csv | P quota selection (only partition used for tuning) |
| data/splits/heldout_test.csv | Final evaluation (touched exactly once) |
| configs/phase2_2_budget.json | Frozen K=1000, P=150, p1_thr=0.35 |
| 
eports/phase2_2_summary.json | Machine-readable results |

## Selection Process
| Decision | Partition Used |
|----------|---------------|
| Ranking variant (D_full_hybrid) | Validation (inherited from Phase 2.1) |
| Total budget K=1000 | Validation (inherited from Phase 2.1) |
| Protected quota P=150 | Validation (Phase 2.2) |
| Phase-1 threshold for protection | Phase 1 artifact (frozen) |
| Final held-out evaluation | Held-out (single evaluation) |

## Leakage Audit
- All candidate generation code audited for 
ing_id, buse_label, pattern_type access.
- FORBIDDEN_COLUMNS enforced in protected_pool.py via runtime guard.
- Tests 	est_protected_pool_no_ring_id_access and 	est_protected_pool_raises_on_label_in_candidates verify this.
- Validation labels used ONLY for metric computation inside evaluate_protected_pool_on_validation.

## Point-in-Time Guarantee
- Graph engine built on 	rain context only.
- s_of_time = train['timestamp'].max() for all investigation calls.
- Future events (val/test timestamps) never contribute graph edges.
