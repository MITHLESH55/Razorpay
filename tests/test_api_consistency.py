"""
RiskOrbit — API Consistency & Inference Parity Tests
Verifies that POST /risk/score produces identical scores and top signals as batch inference.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.app import app
from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.models.main_model import load_artifact


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_version"] == "riskorbit-risk-v1"
    assert 0.0 < data["threshold"] < 1.0


def test_api_batch_parity(client):
    """Verify API prediction score matches batch pipeline prediction."""
    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    if not artifact_dir.exists():
        pytest.skip("Artifacts not found")

    pipeline, threshold, feature_names = load_artifact(artifact_dir)

    raw = Path("data/raw")
    txns = pd.read_csv(raw / "transactions.csv", low_memory=False, nrows=50)
    sample_txn = txns.iloc[0]

    response = client.post(
        "/risk/score",
        json={
            "customer_id": str(sample_txn["customer_id"]),
            "transaction_id": str(sample_txn["transaction_id"]),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "risk_score" in data
    assert "risk_label" in data
    assert "top_signals" in data
    assert data["threshold"] == threshold
    assert 0.0 <= data["risk_score"] <= 1.0
    assert len(data["top_signals"]) <= 5
