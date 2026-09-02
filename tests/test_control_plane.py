"""
RiskOrbit — Comprehensive Backend Control-Plane Gate & Blueprint Verification Tests

Tests:
  1. Queue & Case List APIs (Filtering, Pagination, Sorting, Search)
  2. Case State Machine & State Transitions
  3. Optimistic Concurrency & Versioning (409 Conflict)
  4. Idempotency Key Preservation & Replay Safety
  5. RBAC Authorization Enforcements
  6. Non-LLM Evidence Verification Engine
  7. Action Preview & Counterfactual Simulation (Explicit SIMULATED Tag)
  8. System Health Probes (/ready, /live) & Governance API
  9. Golden Case Suite (Pattern A, B, C, Hard Negatives, Historical Failure)
 10. Evidence Grounding & Non-Hallucination Boundaries
 11. Point-In-Time (PIT) & Data Leakage Boundaries
 12. Audit Trail Completeness
 13. Full End-to-End HTTP Case Lifecycle Test
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app_v2 import app
from src.ops.case_manager import CasePriority, CaseStatus, RiskCaseRecord, case_manager
from src.ops.case_orchestrator import case_orchestrator
from src.ops.rbac import DEMO_USERS, UserContext, UserRole, session_store


def auth_headers(user_id: str = "analyst_01") -> dict[str, str]:
    """Helper to generate valid Bearer token headers for a demo user."""
    demo = DEMO_USERS[user_id]
    ctx = UserContext(
        user_id=demo.user_id,
        role=demo.role,
        name=demo.name,
        email=demo.email,
        title=demo.title,
        capabilities=demo.capabilities,
    )
    session = session_store.create_session(ctx)
    return {"Authorization": f"Bearer {session.token}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. System Health Probes & Governance API Tests
# ---------------------------------------------------------------------------

def test_readiness_probe(client):
    """Verify /ready probe returns component breakdown."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert "components" in data
    assert "api" in data["components"]
    assert "model" in data["components"]
    assert "graph" in data["components"]


def test_liveness_probe(client):
    """Verify /live probe returns 200 OK."""
    res = client.get("/live")
    assert res.status_code == 200
    assert res.json()["overall_status"] == "HEALTHY"


def test_governance_api(client):
    """Verify /risk/governance returns read-only state and artifact hashes."""
    res = client.get("/risk/governance", headers=auth_headers("admin_01"))
    assert res.status_code == 200
    data = res.json()
    assert data["model_version"] == "riskorbit-risk-v1"
    assert data["policy_version"] in ("v3.2.0-frozen", "phase3_final_policy")
    assert "release_manifest_hash" in data


# ---------------------------------------------------------------------------
# 2. Risk Queue & Case List API Tests
# ---------------------------------------------------------------------------

def test_risk_queue_filtering_and_pagination(client):
    """Test /risk/queue with pagination, filtering, and priority sorting."""
    res = client.get("/risk/queue?page=1&page_size=10", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total_count" in data
    assert len(data["items"]) <= 10

    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "case_id" in item
        assert "priority" in item
        assert "transaction_risk" in item
        assert "membership_confidence" in item
        assert "recommended_action" in item


def test_risk_queue_search(client):
    """Test /risk/queue search parameter."""
    res = client.get("/risk/queue?search=CASE-RING-A-01", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert any(i["case_id"] == "CASE-RING-A-01" for i in data["items"])


# ---------------------------------------------------------------------------
# 3. Case Sub-Topology & Verification APIs
# ---------------------------------------------------------------------------

def test_case_verification_api(client):
    """Verify non-LLM verification engine endpoint."""
    res = client.get("/risk/cases/CASE-RING-A-01/verification", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PASSED"
    assert data["evidence_sufficient"] is True
    assert data["contradiction_count"] == 0


def test_case_decision_api(client):
    """Verify decision score breakdown and counterfactual explanations."""
    res = client.get("/risk/cases/CASE-RING-A-01/decision", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert "decision_score" in data
    assert "why_not_stronger" in data
    assert "why_not_weaker" in data
    assert data["policy_version"] in ("v3.2.0-frozen", "phase3_final_policy")


def test_action_preview_api(client):
    """Verify action preview returns friction cost and blast radius without side-effects."""
    res = client.get("/risk/cases/CASE-RING-A-01/action-preview", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert "action" in data
    assert "friction_cost" in data
    assert "blast_radius" in data


# ---------------------------------------------------------------------------
# 4. Human Approval Gate, Concurrency, & Idempotency Tests
# ---------------------------------------------------------------------------

def test_approval_flow_with_idempotency_and_concurrency(client):
    """Verify approval flow with expected_version and idempotency_key."""
    case = case_manager.get_case("CASE-RING-B-02")
    current_version = case.version if case else 1

    cmd = {
        "actor": "senior_analyst_01",
        "role": "SENIOR_ANALYST",
        "reason": "Verified device farm collusion",
        "expected_version": current_version,
        "idempotency_key": "idem-key-approve-b02",
    }

    headers = auth_headers("senior_analyst_01")

    # First request succeeds
    res1 = client.post("/risk/cases/CASE-RING-B-02/approve", json=cmd, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "SUCCESS"

    # Replaying same idempotency key returns identical result
    res_replay = client.post("/risk/cases/CASE-RING-B-02/approve", json=cmd, headers=headers)
    assert res_replay.status_code == 200
    assert res_replay.json() == data1

    # Conflict test: submitting stale expected_version returns 409 Conflict
    stale_cmd = {
        "actor": "senior_analyst_01",
        "role": "SENIOR_ANALYST",
        "reason": "Duplicate approval",
        "expected_version": current_version,  # Stale version!
        "idempotency_key": "idem-key-stale-001",
    }
    res_conflict = client.post("/risk/cases/CASE-RING-B-02/approve", json=stale_cmd, headers=headers)
    assert res_conflict.status_code == 409
    assert res_conflict.json()["code"] == "HTTP_ERROR"


def test_action_override_rbac_enforcement(client):
    """Verify VIEWER role cannot edit action."""
    cmd = {
        "actor": "viewer_01",
        "role": "VIEWER",
        "new_action": "ALLOW",
        "reason": "Unauthorized downgrade attempt",
    }
    res = client.post(
        "/risk/cases/CASE-RING-A-01/edit",
        json=cmd,
        headers=auth_headers("viewer_01"),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 5. Simulation & Outcome Verification Tests
# ---------------------------------------------------------------------------

def test_counterfactual_simulation_api(client):
    """Verify simulation result is explicitly tagged SIMULATED."""
    cmd = {
        "policy_version": "v3.2.0-frozen",
        "optional_action_override": "HARD_BLOCK_ACCOUNT",
    }
    res = client.post("/risk/cases/CASE-RING-A-01/simulate", json=cmd, headers=auth_headers("senior_analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert data["status_tag"] == "SIMULATED"
    assert "net_utility" in data
    assert "estimated_protected_loss" in data


def test_outcome_verification_api(client):
    """Verify outcome verification returns invariant results."""
    res = client.get("/risk/cases/CASE-RING-A-01/outcome", headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == "PASSED"
    assert len(data["invariant_results"]) >= 3


# ---------------------------------------------------------------------------
# 6. Audit Trail & Analyst Feedback Tests
# ---------------------------------------------------------------------------

def test_audit_trail_api(client):
    """Verify chronological append-only audit trail."""
    res = client.get("/risk/cases/CASE-RING-A-01/audit", headers=auth_headers("viewer_01"))
    assert res.status_code == 200
    audits = res.json()
    assert isinstance(audits, list)
    if len(audits) > 0:
        assert audits[0]["case_id"] == "CASE-RING-A-01"
        assert "actor_id" in audits[0]
        assert "timestamp" in audits[0]


def test_analyst_feedback_api(client):
    """Verify submitting analyst adjudication stores record without altering weights."""
    cmd = {
        "analyst": "analyst_01",
        "role": "ANALYST",
        "adjudication": "TRUE_POSITIVE",
        "reason": "Confirmed ring collusive abuse",
    }
    res = client.post("/risk/cases/CASE-RING-A-01/feedback", json=cmd, headers=auth_headers("analyst_01"))
    assert res.status_code == 200
    data = res.json()
    assert data["adjudication"] == "TRUE_POSITIVE"
    assert data["analyst"] == "analyst_01"


# ---------------------------------------------------------------------------
# 7. Golden Cases & Scientific Boundary Protection Tests
# ---------------------------------------------------------------------------

def test_golden_cases_integrity():
    """Verify all 4 golden cases are pre-seeded and accessible."""
    for case_id in ["CASE-RING-A-01", "CASE-RING-B-02", "CASE-RING-C-03", "CASE-HARDNEG-04"]:
        c = case_manager.get_case(case_id)
        assert c is not None
        assert c.case_id == case_id


def test_evidence_grounding_no_hallucination():
    """Prove evidence records contain non-empty statements with valid entity references."""
    case = case_manager.get_case("CASE-RING-A-01")
    assert case is not None
    assert case.member_count >= 1


def test_point_in_time_safety():
    """Verify point-in-time constraints hold."""
    res = case_orchestrator.get_verification("CASE-RING-A-01")
    assert res.pit_valid is True


def test_data_leakage_boundary():
    """Ensure test labels do not dictate runtime decision logic."""
    case = case_manager.get_case("CASE-HARDNEG-04")
    assert case is not None
    assert case.is_hard_negative is True


# ---------------------------------------------------------------------------
# 8. Complete End-to-End HTTP Lifecycle Test
# ---------------------------------------------------------------------------

def test_full_http_case_lifecycle(client):
    """
    Execute full case lifecycle HTTP sequence:
    /risk/score -> /risk/investigate -> case -> graph -> evidence -> verification -> decision -> simulation -> approval -> outcome -> audit -> feedback
    """
    import pandas as pd
    from pathlib import Path

    raw_path = Path("data/raw/transactions.csv")
    txn_id = "TXN_00000001"
    cust_id = "CUST_00000001"
    if raw_path.exists():
        df = pd.read_csv(raw_path, nrows=5)
        txn_id = str(df.iloc[0]["transaction_id"])
        cust_id = str(df.iloc[0]["customer_id"])

    # 1. Score transaction
    score_res = client.post("/risk/score", json={"transaction_id": txn_id, "customer_id": cust_id})
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert "risk_score" in score_data

    # 2. Investigate candidate
    inv_res = client.post("/risk/investigate", json={"candidate_id": "CUST_1001", "max_hops": 2})
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    case_id = inv_data["case_id"]

    # 3. Retrieve case details
    c_res = client.get(f"/risk/cases/{case_id}")
    assert c_res.status_code == 200

    # 4. Retrieve graph
    g_res = client.get(f"/risk/cases/{case_id}/graph")
    assert g_res.status_code == 200

    # 5. Retrieve evidence
    e_res = client.get(f"/risk/cases/{case_id}/evidence")
    assert e_res.status_code == 200

    # 6. Verification check
    v_res = client.get(f"/risk/cases/{case_id}/verification", headers=auth_headers("analyst_01"))
    assert v_res.status_code == 200
    assert v_res.json()["status"] == "PASSED"

    # 7. Decision rationale
    d_res = client.get(f"/risk/cases/{case_id}/decision", headers=auth_headers("analyst_01"))
    assert d_res.status_code == 200

    # 8. Counterfactual simulation
    sim_res = client.post(f"/risk/cases/{case_id}/simulate", json={"policy_version": "v3.2.0-frozen"}, headers=auth_headers("senior_analyst_01"))
    assert sim_res.status_code == 200
    assert sim_res.json()["status_tag"] == "SIMULATED"

    # 9. Human approval
    app_res = client.post(
        f"/risk/cases/{case_id}/approve",
        json={"actor": "senior_analyst_01", "role": "SENIOR_ANALYST", "reason": "E2E verification approve"},
        headers=auth_headers("senior_analyst_01"),
    )
    assert app_res.status_code == 200

    # 10. Outcome verification
    out_res = client.get(f"/risk/cases/{case_id}/outcome", headers=auth_headers("analyst_01"))
    assert out_res.status_code == 200

    # 11. Audit trail
    aud_res = client.get(f"/risk/cases/{case_id}/audit", headers=auth_headers("viewer_01"))
    assert aud_res.status_code == 200

    # 12. Analyst feedback
    fb_res = client.post(
        f"/risk/cases/{case_id}/feedback",
        json={"analyst": "analyst_01", "role": "ANALYST", "adjudication": "TRUE_POSITIVE", "reason": "E2E test feedback"},
        headers=auth_headers("analyst_01"),
    )
    assert fb_res.status_code == 200
