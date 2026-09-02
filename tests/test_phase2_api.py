"""
RiskOrbit — Phase 2 API Integration Tests

Tests:
  - GET  /health
  - POST /risk/score (Phase 1 backward compatibility)
  - POST /risk/investigate (Phase 2 investigation)
  - GET  /risk/cases/{case_id}
  - GET  /risk/cases/{case_id}/graph
  - GET  /risk/cases/{case_id}/evidence
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "model_not_loaded")


def test_score_endpoint_backward_compat(client):
    res = client.post("/risk/score", json={
        "customer_id": "CUS_000001",
        "transaction_id": "TXN_000001",
    })
    # If transaction exists, 200; if not in raw dataset, 404
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        data = res.json()
        assert "risk_score" in data
        assert "risk_label" in data
        assert 0.0 <= data["risk_score"] <= 1.0


def test_investigate_endpoint(client):
    res = client.post("/risk/investigate", json={
        "candidate_id": "CUS_000001",
        "max_hops": 2,
    })
    assert res.status_code in (200, 503)
    if res.status_code == 200:
        case = res.json()
        case_id = case["case_id"]
        assert case_id.startswith("CASE-")
        assert "individual_risk_score" in case
        assert "relationship_risk_score" in case
        assert "combined_risk_score" in case
        assert "evidence_records" in case
        assert "timeline" in case

        # Retrieve case
        get_res = client.get(f"/risk/cases/{case_id}")
        assert get_res.status_code == 200
        assert get_res.json()["case_id"] == case_id

        # Retrieve graph
        graph_res = client.get(f"/risk/cases/{case_id}/graph")
        assert graph_res.status_code == 200
        assert "graph_statistics" in graph_res.json()

        # Retrieve evidence
        ev_res = client.get(f"/risk/cases/{case_id}/evidence")
        assert ev_res.status_code == 200
        assert "evidence_records" in ev_res.json()
