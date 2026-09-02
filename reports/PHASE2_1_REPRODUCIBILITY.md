# PHASE 2.1 REPRODUCIBILITY

## Evaluation Metadata

| Field | Value |
|-------|-------|
| Evaluation timestamp | 2026-08-27T12:17:43.572604+00:00 |
| Git commit | N/A |
| Python version | 3.12.6 |
| Frozen budget K | 1000 |
| Budget config | configs/phase2_1_budget.json |
| Summary JSON | reports/phase2_1_summary.json |

## Exact Reproduction Commands

```bash
# Step 1: Verify all 110 tests pass
pytest

# Step 2: Run end-to-end Phase 2.1 evaluation
python scripts/evaluate_phase2_1.py

# Step 3: Generate all 9 reports
python scripts/generate_all_phase2_1_reports.py
```

## Data Splits

| Split | Purpose | Transactions |
|-------|---------|-------------|
| Train | Phase 1 training + graph context | ~57,180 |
| Validation | Budget K selection (frozen pre-test) | ~11,437 |
| Held-Out Test | Single untouched final evaluation | 28,591 |

## Frozen Artifacts

| Artifact | Path | Role |
|---------|------|------|
| Phase 1 LGBM | artifacts/riskorbit-risk-v1/model.pkl | Transaction scorer |
| Phase 1 threshold | configs/threshold.json | Candidacy cutoff |
| Phase 2 v2 GBDT | artifacts/riskorbit-risk-v2/model.pkl | Baseline (preserved) |
| Phase 2.1 budget | configs/phase2_1_budget.json | Frozen K |
| Phase 2.1 summary | reports/phase2_1_summary.json | Evaluation output |

## Key Package Versions

```
fastapi==0.115.0
lightgbm==4.7.0
networkx==3.5
numpy==1.26.4
pandas==2.2.3
pytest==8.3.3
pytest-cov==5.0.0
scikit-learn==1.6.1
shap==0.49.1
```

## Determinism Guarantee

| Source | Seed | Enforced |
|--------|------|---------|
| Phase 1 LGBM | random_state=42 | Frozen artifact |
| CandidateGenerator | Deterministic (no RNG) | Code design |
| HybridCandidateUnion | Deterministic composite score | Code design |
| Investigation agent | Deterministic NetworkX traversal | Code design |
| Data split | Fixed split_type column | Data design |

All pipeline components are fully deterministic given same input data and frozen artifacts.
Re-running evaluate_phase2_1.py on the same machine produces bit-identical results.
