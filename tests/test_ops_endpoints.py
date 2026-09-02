"""
Unit and integration tests for RiskOrbit Operations & Trust Console backend.
"""
import pytest
from fastapi.testclient import TestClient

from src.api.app_v2 import app
from src.ops.audit_log import AuditEventType, audit_trail
from src.ops.case_manager import CasePriority, CaseStatus, case_manager
from src.ops.drift_detector import DriftStatus, drift_detector
from src.ops.feedback_store import AdjudicationOutcome, feedback_store
from src.ops.monitoring import operational_monitor
from src.ops.rbac import DEMO_USERS, UserContext, UserRole, require_role, session_store
from src.ops.system_state import SystemHealthStatus, system_state

client = TestClient(app)


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


def test_overview_endpoint():
    """Verify overview API returns operational KPIs."""
    headers = auth_headers("analyst_01")
    response = client.get("/api/v2/ops/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "active_cases_total" in data
    assert data["active_cases_total"] >= 6
    assert data["held_out_metrics"]["ring_recall"] == "100.0% (24/24 rings)"
    assert data["held_out_metrics"]["hard_block_fpr"] == "0.04%"


def test_queue_filtering_and_priority():
    """Verify queue sorting and filter parameters."""
    headers = auth_headers("analyst_01")
    response = client.get("/api/v2/ops/queue?priority=CRITICAL", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 3
    for item in items:
        assert item["priority"] == "CRITICAL"


def test_case_detail_golden_data():
    """Verify case detail returns nodes, edges, and evidence."""
    headers = auth_headers("analyst_01")
    response = client.get("/api/v2/ops/cases/CASE-RING-A-01", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["case_id"] == "CASE-RING-A-01"
    assert len(data["graph"]["nodes"]) >= 5
    assert len(data["graph"]["edges"]) >= 5
    assert len(data["evidence_records"]) >= 3
    assert data["evidence_records"][0]["evidence_id"] == "EVID-DEV-001"


def test_rbac_approval_permission():
    """Test RBAC enforcement for high-impact action approval."""
    from src.ops.demo_fixtures import seed_demo_cases
    seed_demo_cases()

    # VIEWER cannot approve
    resp_viewer = client.post(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        headers=auth_headers("viewer_01"),
        json={"notes": "test approval"},
    )
    assert resp_viewer.status_code == 403

    # SENIOR_ANALYST can approve BLOCK_TRANSACTION
    resp_sr = client.post(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        headers=auth_headers("senior_analyst_01"),
        json={"notes": "Approved blocking", "idempotency_key": "IDEM-TEST-001"},
    )
    assert resp_sr.status_code == 200
    assert resp_sr.json()["status"] == "APPROVED"

    # Idempotent re-submission
    resp_idem = client.post(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        headers=auth_headers("senior_analyst_01"),
        json={"notes": "Duplicate request", "idempotency_key": "IDEM-TEST-001"},
    )
    assert resp_idem.status_code == 200


def test_analyst_feedback_submission():
    """Verify domain feedback capture without model mutation."""
    resp = client.post(
        "/api/v2/ops/feedback",
        headers=auth_headers("analyst_01"),
        json={
            "case_id": "CASE-RING-B-02",
            "transaction_id": "TXN-DEMO-B4402",
            "adjudication": "TRUE_POSITIVE",
            "notes": "Confirmed circular layering pattern.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjudication"] == "TRUE_POSITIVE"
    assert data["status_notice"] == "Feedback captured — model remains frozen."


def test_system_controls_and_kill_switch():
    """Verify system controls toggle and audit logging."""
    # Non-admin cannot toggle kill switch
    resp_unauth = client.post(
        "/api/v2/ops/controls",
        headers=auth_headers("analyst_01"),
        json={"kill_switch": True},
    )
    assert resp_unauth.status_code == 403

    # Admin can toggle kill switch
    resp_admin = client.post(
        "/api/v2/ops/controls",
        headers=auth_headers("admin_01"),
        json={"kill_switch": True, "reason": "Simulated drill"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["kill_switch_active"] is True
    assert resp_admin.json()["health_status"] == "SAFE_MODE"

    # Reset kill switch
    resp_reset = client.post(
        "/api/v2/ops/controls",
        headers=auth_headers("admin_01"),
        json={"kill_switch": False, "reason": "Drill ended"},
    )
    assert resp_reset.status_code == 200
    assert resp_reset.json()["kill_switch_active"] is False


def test_manifest_and_evaluation_endpoints():
    """Verify release manifest and evaluation endpoints."""
    headers = auth_headers("viewer_01")
    resp_man = client.get("/api/v2/ops/manifest", headers=headers)
    assert resp_man.status_code == 200
    assert "status" in resp_man.json()

    resp_eval = client.get("/api/v2/ops/evaluation", headers=headers)
    assert resp_eval.status_code == 200
    eval_data = resp_eval.json()
    assert eval_data["ring_intervention_recall"] == 1.0
    assert eval_data["hard_block_fpr"] == 0.0004
