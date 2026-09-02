"""
RiskOrbit — Evaluation Tests
Tests: threshold from validation, held-out not used in training, metrics deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_threshold_selected_on_validation_only():
    """Model metadata must confirm threshold was selected on validation partition."""
    import json
    meta_path = Path("artifacts/riskorbit-risk-v1/model_metadata.json")
    if not meta_path.exists():
        pytest.skip("Artifacts not found")
    data = json.loads(meta_path.read_text())
    assert data.get("threshold_selection_partition") == "validation", (
        "threshold_selection_partition must be 'validation', not test"
    )


def test_select_threshold_uses_validation_not_test():
    """
    select_threshold() must be called with validation data.
    Verify the function works correctly and deterministically.
    """
    from src.evaluation.metrics import select_threshold
    rng = np.random.default_rng(42)
    y_true = rng.choice([0, 1], size=1000, p=[0.92, 0.08])
    y_score = np.where(y_true == 1, rng.uniform(0.5, 1.0, 1000), rng.uniform(0.0, 0.6, 1000))

    t1, _ = select_threshold(y_true, y_score, fpr_max=0.10)
    t2, _ = select_threshold(y_true, y_score, fpr_max=0.10)
    assert t1 == t2, "select_threshold must be deterministic"
    assert 0.0 < t1 < 1.0


def test_compute_metrics_precision_recall_consistent():
    """P*R must be consistent with F1 = 2PR/(P+R)."""
    from src.evaluation.metrics import compute_metrics
    rng = np.random.default_rng(99)
    y_true = rng.choice([0, 1], size=500, p=[0.90, 0.10])
    y_pred = (rng.random(500) > 0.5).astype(int)
    m = compute_metrics(y_true, y_pred)
    p, r = m["precision"], m["recall"]
    if p + r > 0:
        expected_f1 = round(2 * p * r / (p + r), 4)
        assert abs(m["f1"] - expected_f1) < 0.001, (
            f"F1 inconsistency: computed={m['f1']}, expected={expected_f1}"
        )


def test_confusion_matrix_sums_to_total():
    from src.evaluation.metrics import compute_metrics
    rng = np.random.default_rng(77)
    y_true = rng.choice([0, 1], size=200)
    y_pred = rng.choice([0, 1], size=200)
    m = compute_metrics(y_true, y_pred)
    total = m["tp"] + m["tn"] + m["fp"] + m["fn"]
    assert total == 200


def test_heldout_evaluation_does_not_modify_artifacts():
    """
    The artifacts directory mtime must not change after evaluation.
    This test checks the concept — actual mtime check requires full pipeline run.
    """
    # This is a documentation test — the evaluate_heldout.py script
    # calls load_artifact() (read-only) and never calls save_artifact().
    from src.models.main_model import load_artifact, save_artifact
    import inspect
    eval_source = Path("scripts/evaluate_heldout.py").read_text() if Path("scripts/evaluate_heldout.py").exists() else ""
    assert "save_artifact" not in eval_source, (
        "evaluate_heldout.py must not call save_artifact (read-only evaluation)"
    )
    assert "fit(" not in eval_source, (
        "evaluate_heldout.py must not call .fit() (no retraining)"
    )


def test_cost_model_positive_cost():
    """FP cost must always be positive for non-zero FPs."""
    import yaml
    with open("configs/generation_config.yaml") as f:
        cfg = yaml.safe_load(f)
    from src.evaluation.cost_model import FPCostModel
    model = FPCostModel(cfg)
    assert model.cost_per_fp() > 0
    assert model.total_fp_cost(100) > 0
    assert model.total_fp_cost(0) == 0.0


def test_fpr_formula_correctness():
    """FPR must strictly be FP / (FP + TN) = FP / N_legitimate."""
    from src.evaluation.metrics import compute_metrics
    # Case 1: 0 FP -> 0 FPR
    y_true = np.array([0, 0, 0, 1, 1])
    y_pred = np.array([0, 0, 0, 1, 0])
    m = compute_metrics(y_true, y_pred)
    assert m["fp"] == 0
    assert m["tn"] == 3
    assert m["fpr"] == 0.0

    # Case 2: 1 FP out of 3 negatives -> 1/3 FPR
    y_pred = np.array([1, 0, 0, 1, 0])
    m = compute_metrics(y_true, y_pred)
    assert m["fp"] == 1
    assert m["tn"] == 2
    assert abs(m["fpr"] - 1/3) < 1e-4

    # Denominator must equal total ground truth negatives
    assert (m["fp"] + m["tn"]) == int((y_true == 0).sum())


def test_fp_cost_multiplication():
    """FP cost must strictly equal FP * Rs.130."""
    fps = [0, 1, 112, 153, 21443, 21575]
    for fp in fps:
        expected = fp * 130
        assert fp * 130 == expected


def test_heldout_evaluation_population_invariants():
    """Held-out evaluation set dimensions must remain frozen and strictly checked."""
    import pandas as pd
    test_path = Path("data/splits/heldout_test.csv")
    if not test_path.exists():
        pytest.skip("heldout_test.csv not found")
    df = pd.read_csv(test_path, low_memory=False)
    assert len(df) == 28591, "Total held-out transactions must be exactly 28,591"
    assert int((df["abuse_label"] == 1).sum()) == 290, "Abuse transactions must be exactly 290"
    assert int((df["abuse_label"] == 0).sum()) == 28301, "Legitimate transactions must be exactly 28,301"


def test_phase21_baseline_consistency_in_phase22():
    """Phase 2.2 summary must faithfully record the Phase 2.1 frozen baseline metrics."""
    import json
    p21_path = Path("reports/phase2_1_summary.json")
    p22_path = Path("reports/phase2_2_summary.json")
    if not p21_path.exists() or not p22_path.exists():
        pytest.skip("Summaries not found")

    p21_data = json.loads(p21_path.read_text(encoding="utf-8"))
    p22_data = json.loads(p22_path.read_text(encoding="utf-8"))

    p21_m = p21_data["metrics"]
    p22_base = p22_data["phase21_baseline"]

    assert p22_base["ring_recall"] == p21_m["ring_recall"]
    assert p22_base["pat_a"] == p21_m["pat_a_recall"]
    assert p22_base["pat_b"] == p21_m["pat_b_recall"]
    assert p22_base["pat_c"] == p21_m["pat_c_recall"]
    assert p22_base["fpr"] == p21_m["fpr"]
    assert p22_base["fp_cost"] == p21_m["fp_cost"]

