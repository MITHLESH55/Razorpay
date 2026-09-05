"""
RiskOrbit — Governance Controls State Transition & Integrity Tests
"""
import pytest
from fastapi.testclient import TestClient
from src.api.app_v2 import app
from src.ops.system_state import SystemHealthStatus, system_state


@pytest.fixture(autouse=True)
def reset_system_state():
    """Ensure system state is reset before each test."""
    system_state.update_controls(
        shadow_mode=False,
        kill_switch=False,
        graph_available=True,
        actor_id="test_reset",
        actor_role="ADMIN",
        reason="Test fixture reset",
    )
    system_state.set_model_ready(True)
    yield
    system_state.update_controls(
        shadow_mode=False,
        kill_switch=False,
        graph_available=True,
        actor_id="test_reset",
        actor_role="ADMIN",
        reason="Test fixture cleanup",
    )
    system_state.set_model_ready(True)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def get_auth_header(client: TestClient, role: str) -> dict[str, str]:
    login_resp = client.post("/api/v2/ops/auth/evaluation-login", json={"role": role})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_transition_1_default_healthy_startup(client):
    """TEST 1: Verify fresh default startup state is HEALTHY."""
    headers = get_auth_header(client, "ANALYST")
    res = client.get("/api/v2/ops/controls", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["health_status"] == SystemHealthStatus.HEALTHY.value
    assert data["kill_switch_active"] is False
    assert data["graph_engine_available"] is True


def test_transition_2_admin_activates_kill_switch(client):
    """TEST 2: ADMIN deliberately activates kill switch."""
    headers = get_auth_header(client, "ADMIN")
    res = client.post(
        "/api/v2/ops/controls",
        headers=headers,
        json={"kill_switch": True, "reason": "Deliberate test drill"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kill_switch_active"] is True
    assert data["health_status"] == SystemHealthStatus.SAFE_MODE.value


def test_transition_3_admin_deactivates_kill_switch(client):
    """TEST 3: ADMIN deactivates kill switch to restore normal state."""
    headers = get_auth_header(client, "ADMIN")
    # Activate first
    client.post(
        "/api/v2/ops/controls",
        headers=headers,
        json={"kill_switch": True, "reason": "Activate"},
    )
    # Deactivate
    res = client.post(
        "/api/v2/ops/controls",
        headers=headers,
        json={"kill_switch": False, "reason": "Deactivate"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kill_switch_active"] is False
    assert data["health_status"] == SystemHealthStatus.HEALTHY.value
    assert data["graph_engine_available"] is True


def test_transition_4_analyst_cannot_toggle_kill_switch(client):
    """TEST 4: ANALYST attempts to toggle kill switch (403 Forbidden)."""
    headers = get_auth_header(client, "ANALYST")
    res = client.post(
        "/api/v2/ops/controls",
        headers=headers,
        json={"kill_switch": True},
    )
    assert res.status_code == 403


def test_transition_5_viewer_cannot_toggle_kill_switch(client):
    """TEST 5: VIEWER attempts to toggle kill switch (403 Forbidden)."""
    headers = get_auth_header(client, "VIEWER")
    res = client.post(
        "/api/v2/ops/controls",
        headers=headers,
        json={"kill_switch": True},
    )
    assert res.status_code == 403


def test_transition_6_fresh_instance_default(client):
    """TEST 6: Fresh instance follows deterministic healthy default."""
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["overall_status"] == "HEALTHY"
    assert ready_data["components"]["graph"]["status"] == "HEALTHY"
