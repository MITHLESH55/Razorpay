"""
RiskOrbit — Model Tests
Tests: artifact loads, predictions valid, scores in [0,1], schema correct.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

ARTIFACT_DIR = Path("artifacts/riskorbit-risk-v1")


@pytest.fixture(scope="session")
def artifact():
    if not ARTIFACT_DIR.exists():
        pytest.skip("Artifacts not found — run train_models.py first")
    from src.models.main_model import load_artifact
    return load_artifact(ARTIFACT_DIR)


def test_artifact_loads(artifact):
    pipeline, threshold, feature_names = artifact
    assert pipeline is not None
    assert 0 < threshold < 1
    assert len(feature_names) > 0


def test_threshold_in_valid_range(artifact):
    _, threshold, _ = artifact
    assert 0.0 < threshold < 1.0


def test_threshold_json_exists():
    if not ARTIFACT_DIR.exists():
        pytest.skip()
    t_path = ARTIFACT_DIR / "threshold.json"
    assert t_path.exists(), "threshold.json missing"
    data = json.loads(t_path.read_text())
    assert "threshold" in data
    assert "model_version" in data


def test_feature_schema_json_exists():
    if not ARTIFACT_DIR.exists():
        pytest.skip()
    schema_path = ARTIFACT_DIR / "feature_schema.json"
    assert schema_path.exists()
    data = json.loads(schema_path.read_text())
    assert "feature_names" in data
    assert len(data["feature_names"]) > 0


def test_model_metadata_json_exists():
    if not ARTIFACT_DIR.exists():
        pytest.skip()
    meta_path = ARTIFACT_DIR / "model_metadata.json"
    assert meta_path.exists()
    data = json.loads(meta_path.read_text())
    assert "model_version" in data
    assert "threshold" in data
    assert "threshold_selection_partition" in data
    assert data["threshold_selection_partition"] == "validation"


def test_predictions_valid_range(artifact):
    """Scores must be in [0, 1]."""
    pipeline, threshold, feature_names = artifact
    import pandas as pd
    # Create a zero-feature row
    X = pd.DataFrame([[0.0] * len(feature_names)], columns=feature_names)
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(X)
    proba = pipeline.named_steps["lgbm"].predict_proba(X_imp)
    assert proba.shape[1] == 2
    assert 0.0 <= proba[0][1] <= 1.0


def test_rule_baseline_predictions_binary():
    from src.models.rule_baseline import RuleBaseline
    import pandas as pd
    from src.features.pipeline import FEATURE_COLUMNS
    rule = RuleBaseline()
    X = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)], columns=FEATURE_COLUMNS)
    preds = rule.predict_from_features(X)
    assert set(preds).issubset({0, 1})


def test_score_response_schema():
    """ScoreResponse must produce valid risk_label values."""
    from src.api.schema import ScoreResponse
    for score, threshold, expected_label in [
        (0.9, 0.7, "high"),
        (0.4, 0.7, "low"),
        (0.5, 0.7, "medium"),  # ~60% of threshold
    ]:
        resp = ScoreResponse.from_score(
            transaction_id="TXN_TEST",
            customer_id="CUS_TEST",
            risk_score=score,
            threshold=threshold,
            model_version="riskorbit-risk-v1",
            top_signals=[],
        )
        assert resp.risk_label in {"low", "medium", "high"}
        assert 0.0 <= resp.risk_score <= 1.0
        assert resp.model_version == "riskorbit-risk-v1"
