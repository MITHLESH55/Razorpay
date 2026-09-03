"""
RiskOrbit — System Integrity, Data Lineage & Forensic Verification Suite

Comprehensive test suite verifying:
- 1. test_dashboard_metrics_are_backend_derived
- 2. test_queue_cases_are_backend_derived
- 3. test_case_detail_is_backend_derived
- 4. test_case_approval_changes_backend_state
- 5. test_approval_creates_audit_event
- 6. test_approval_state_survives_refresh
- 7. test_unknown_credentials_rejected
- 8. test_wrong_password_rejected
- 9. test_role_cannot_be_escalated
- 10. test_logout_invalidates_session
- 11. test_simulation_threshold_changes_candidate_behavior
- 12. test_simulation_does_not_mutate_frozen_policy
- 13. test_psi_zero_for_matching_distribution
- 14. test_psi_positive_for_shifted_distribution
- 15. test_graph_nodes_are_case_derived
- 16. test_graph_edges_are_case_derived
- 17. test_evidence_is_source_grounded
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app_v2 import app
from src.ops.case_manager import case_manager, CaseStatus, RiskCaseRecord, CasePriority
from src.ops.drift_detector import compute_psi
from src.ops.rbac import user_repository, hash_password

client = TestClient(app)
_integrity_approval_case_id: str | None = None


def _get_auth_header(username_or_email: str = "senior_analyst_01", password: str = "RiskOrbit@Senior2026") -> dict[str, str]:
    """Helper to authenticate and generate Bearer header."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": username_or_email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {username_or_email}: {res.text}"
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test 1: Dashboard metrics are backend derived
# ---------------------------------------------------------------------------
def test_dashboard_metrics_are_backend_derived():
    """Verify overview dashboard values reflect dynamic backend calculations and authoritative artifacts."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    res = client.get("/api/v2/ops/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Check required dynamic fields
    assert "active_cases_total" in data
    assert "critical_priority_count" in data
    assert "pending_human_approvals" in data
    assert "approved_interventions" in data
    assert "pending_exposure_inr" in data
    assert "held_out_metrics" in data

    # Compare with authoritative metrics file
    metrics_path = Path("reports/RISKORBIT_FINAL_METRICS.json")
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            raw_metrics = json.load(f)
            p32 = raw_metrics.get("phase32_final_tiered", {})
            assert data["held_out_metrics"]["held_out_transactions"] == raw_metrics.get("dataset_rows", 28591)
            expected_fpr = f"{p32.get('hard_block_fpr_pct', 0.04):.2f}%"
            assert data["held_out_metrics"]["hard_block_fpr"] == expected_fpr


# ---------------------------------------------------------------------------
# Test 2: Queue cases are backend derived
# ---------------------------------------------------------------------------
def test_queue_cases_are_backend_derived():
    """Verify queue items are loaded directly from the case manager queue."""
    headers = _get_auth_header("analyst_01", "RiskOrbit@Analyst2026")
    res = client.get("/api/v2/ops/queue", headers=headers)
    assert res.status_code == 200
    queue = res.json()
    assert len(queue) > 0

    # Ensure queue items contain necessary attributes
    for item in queue:
        assert "case_id" in item
        assert "transaction_id" in item
        assert "customer_id" in item
        assert "amount_inr" in item
        assert "decision_score" in item
        assert "recommended_action" in item
        assert "status" in item
        assert "priority" in item


# ---------------------------------------------------------------------------
# Test 3: Case detail is backend derived
# ---------------------------------------------------------------------------
def test_case_detail_is_backend_derived():
    """Verify case detail returns complete dossier with case, graph, evidence, and decision trace."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    case_id = "CASE-RING-A-01"
    res = client.get(f"/api/v2/ops/cases/{case_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "case" in data
    assert data["case"]["case_id"] == case_id
    assert "graph" in data
    assert "nodes" in data["graph"]
    assert "edges" in data["graph"]
    assert "evidence_records" in data
    assert "decision_trace" in data
    assert "narrative" in data
    assert len(data["evidence_records"]) > 0


# ---------------------------------------------------------------------------
# Test 4: Case approval changes backend state
# ---------------------------------------------------------------------------
def test_case_approval_changes_backend_state():
    """Verify approving a case updates its status, reviewer, and version."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    global _integrity_approval_case_id
    pending_cases = [case for case in case_manager.list_queue(limit=500) if case.status == CaseStatus.PENDING_APPROVAL]
    assert pending_cases, "Integrity test requires a pending approval case"
    case_id = pending_cases[0].case_id
    _integrity_approval_case_id = case_id

    # Reset or get initial state
    initial_res = client.get(f"/api/v2/ops/cases/{case_id}", headers=headers)
    assert initial_res.status_code == 200
    init_case = initial_res.json()["case"]

    # Perform approval
    approve_res = client.post(
        f"/api/v2/ops/cases/{case_id}/approve",
        headers=headers,
        json={"notes": "Approved by senior analyst integrity test"},
    )
    assert approve_res.status_code == 200
    approved_case = approve_res.json()

    assert approved_case["status"] == "APPROVED"
    assert approved_case["reviewed_by"] == "senior_analyst_01"
    assert approved_case["reviewer_notes"] == "Approved by senior analyst integrity test"
    assert approved_case["version"] >= init_case["version"]


# ---------------------------------------------------------------------------
# Test 5: Approval creates audit event
# ---------------------------------------------------------------------------
def test_approval_creates_audit_event():
    """Verify approval writes an immutable audit record."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    case_id = _integrity_approval_case_id
    assert case_id is not None

    # Fetch audit log for this case
    audit_res = client.get(f"/api/v2/ops/audit?case_id={case_id}", headers=headers)
    assert audit_res.status_code == 200
    audit_events = audit_res.json()
    assert len(audit_events) > 0

    # Verify latest audit event matches action (audit_events are in chronological order from get_case_audit)
    latest_event = audit_events[-1]
    assert latest_event["case_id"] == case_id
    assert latest_event["actor_id"] == "senior_analyst_01"
    assert latest_event["event_type"] in (
        "ACTION_APPROVED",
        "ACTION_EDITED",
        "ACTION_REJECTED",
        "SIMULATION_EXECUTED",
        "FEEDBACK_RECORDED",
        "CASE_APPROVED",
    )


# ---------------------------------------------------------------------------
# Test 6: Approval state survives refresh / re-query
# ---------------------------------------------------------------------------
def test_approval_state_survives_refresh():
    """Verify state persistence across multiple queries."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    case_id = _integrity_approval_case_id
    assert case_id is not None

    # Query case detail again
    res = client.get(f"/api/v2/ops/cases/{case_id}", headers=headers)
    assert res.status_code == 200
    case_data = res.json()["case"]
    assert case_data["status"] == "APPROVED"
    assert case_data["reviewed_by"] == "senior_analyst_01"


# ---------------------------------------------------------------------------
# Test 7: Unknown credentials rejected
# ---------------------------------------------------------------------------
def test_unknown_credentials_rejected():
    """Verify non-existent username/email receives 401 unauthorized."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "unknown_user_99999", "password": "anypassword"},
    )
    assert res.status_code == 401
    assert "Invalid user ID/email or password." in res.json().get("detail", res.json().get("message", ""))


# ---------------------------------------------------------------------------
# Test 8: Wrong password rejected
# ---------------------------------------------------------------------------
def test_wrong_password_rejected():
    """Verify known user with wrong password receives 401 unauthorized."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    assert "Invalid user ID/email or password." in res.json().get("detail", res.json().get("message", ""))


# ---------------------------------------------------------------------------
# Test 9: Role cannot be escalated from client
# ---------------------------------------------------------------------------
def test_role_cannot_be_escalated():
    """Verify client-supplied role cannot escalate privileges."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "RiskOrbit@Analyst2026", "role": "ADMIN"},
    )
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["role"] == "ANALYST"  # Must remain authoritative server-side role


# ---------------------------------------------------------------------------
# Test 10: Logout invalidates session
# ---------------------------------------------------------------------------
def test_logout_invalidates_session():
    """Verify token is invalidated upon logout and subsequent calls return 401."""
    # Login
    login_res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "viewer_01", "password": "RiskOrbit@Viewer2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session active
    sess_res = client.get("/api/v2/ops/auth/session", headers=headers)
    assert sess_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v2/ops/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Session check must now fail
    invalid_res = client.get("/api/v2/ops/auth/session", headers=headers)
    assert invalid_res.status_code == 401


# ---------------------------------------------------------------------------
# Test 11: Simulation threshold changes candidate behavior
# ---------------------------------------------------------------------------
def test_simulation_threshold_changes_candidate_behavior():
    """Verify modifying simulation parameters evaluates different counterfactual outcomes."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    case_id = "CASE-RING-B-02"

    # Simulate with step up 2FA
    res1 = client.post(
        f"/api/v2/ops/cases/{case_id}/simulate",
        headers=headers,
        json={"case_id": case_id, "simulated_action": "STEP_UP_2FA"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["simulated_action"] == "STEP_UP_2FA"
    assert data1["projected_friction_cost_inr"] == 25.0

    # Simulate with freeze ring
    res2 = client.post(
        f"/api/v2/ops/cases/{case_id}/simulate",
        headers=headers,
        json={"case_id": case_id, "simulated_action": "FREEZE_RING"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["simulated_action"] == "FREEZE_RING"
    assert data2["projected_friction_cost_inr"] > data1["projected_friction_cost_inr"]


# ---------------------------------------------------------------------------
# Test 12: Simulation does not mutate frozen policy
# ---------------------------------------------------------------------------
def test_simulation_does_not_mutate_frozen_policy():
    """Verify running simulations does not change production policy version or controls."""
    headers = _get_auth_header("senior_analyst_01", "RiskOrbit@Senior2026")
    controls_res = client.get("/api/v2/ops/controls", headers=headers)
    assert controls_res.status_code == 200
    initial_controls = controls_res.json()

    # Run simulation
    client.post(
        "/api/v2/ops/cases/CASE-RING-B-02/simulate",
        headers=headers,
        json={"case_id": "CASE-RING-B-02", "simulated_action": "FREEZE_RING"},
    )

    # Check controls remained unaltered
    controls_after = client.get("/api/v2/ops/controls", headers=headers).json()
    assert controls_after["policy_version"] == initial_controls["policy_version"]
    assert controls_after["model_version"] == initial_controls["model_version"]
    assert controls_after["kill_switch_active"] == initial_controls["kill_switch_active"]


# ---------------------------------------------------------------------------
# Test 13: PSI is zero for matching distribution
# ---------------------------------------------------------------------------
def test_psi_zero_for_matching_distribution():
    """Verify Population Stability Index is ~0.0 for identical baseline and current distributions."""
    sample = [100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0] * 10
    psi_score, _ = compute_psi(sample, sample)
    assert psi_score < 0.05  # Highly stable


# ---------------------------------------------------------------------------
# Test 14: PSI is positive for shifted distribution
# ---------------------------------------------------------------------------
def test_psi_positive_for_shifted_distribution():
    """Verify Population Stability Index detects distribution shifts."""
    baseline = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0] * 10
    shifted = [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0] * 10
    psi_score, _ = compute_psi(baseline, shifted)
    assert psi_score >= 0.25  # Significant drift detected


# ---------------------------------------------------------------------------
# Test 15: Graph nodes are case derived
# ---------------------------------------------------------------------------
def test_graph_nodes_are_case_derived():
    """Verify graph nodes accurately represent entities associated with the case."""
    headers = _get_auth_header("analyst_01", "RiskOrbit@Analyst2026")
    res = client.get("/api/v2/ops/cases/CASE-RING-A-01", headers=headers)
    assert res.status_code == 200
    nodes = res.json()["graph"]["nodes"]
    assert len(nodes) >= 3

    node_types = {n["type"] for n in nodes}
    assert "customer" in node_types or "device" in node_types or "ip" in node_types or "merchant" in node_types


# ---------------------------------------------------------------------------
# Test 16: Graph edges are case derived
# ---------------------------------------------------------------------------
def test_graph_edges_are_case_derived():
    """Verify graph edges accurately link entities in the case subtopology."""
    headers = _get_auth_header("analyst_01", "RiskOrbit@Analyst2026")
    res = client.get("/api/v2/ops/cases/CASE-RING-A-01", headers=headers)
    assert res.status_code == 200
    edges = res.json()["graph"]["edges"]
    nodes = res.json()["graph"]["nodes"]
    node_ids = {n["id"] for n in nodes}

    assert len(edges) > 0
    for edge in edges:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


# ---------------------------------------------------------------------------
# Test 17: Evidence is source grounded
# ---------------------------------------------------------------------------
def test_evidence_is_source_grounded():
    """Verify evidence items are corroborated with cryptographic SHA-256 hashes and categories."""
    headers = _get_auth_header("analyst_01", "RiskOrbit@Analyst2026")
    res = client.get("/api/v2/ops/cases/CASE-RING-A-01", headers=headers)
    assert res.status_code == 200
    evidence = res.json()["evidence_records"]

    assert len(evidence) > 0
    for ev in evidence:
        assert "evidence_id" in ev
        assert "category" in ev
        assert "title" in ev
        assert "strength" in ev
        assert "hash_sha256" in ev
        assert len(ev["hash_sha256"]) == 64  # Valid SHA-256 length
        assert ev["verified"] is True
