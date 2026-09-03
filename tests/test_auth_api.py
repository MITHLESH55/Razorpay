"""
RiskOrbit — Authentication & Session Management Unit & Integration Tests

Verifies:
- Login with demo user credentials
- Login with custom credentials
- Session token retrieval and validation
- Session logout and invalidation
- Demo users list retrieval
- Role-based permissions matching user roles
- Role tampering defense (client cannot declare elevated role)
- Protected route security (401 without valid session token)
- Operational overview data access with authenticated session
"""
from fastapi.testclient import TestClient
from uuid import uuid4
from src.api.app_v2 import app

client = TestClient(app)


def test_list_demo_users():
    """Verify demo users catalog is available for fast login switching."""
    response = client.get("/api/v2/ops/auth/demo-users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    roles = {u["role"] for u in data}
    assert "ANALYST" in roles
    assert "SENIOR_ANALYST" in roles
    assert "ADMIN" in roles
    assert "VIEWER" in roles


def test_login_demo_user_success():
    """Verify login with demo user credentials."""
    response = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "senior_analyst_01", "password": "RiskOrbit@Senior2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["user_id"] == "senior_analyst_01"
    assert data["user"]["role"] == "SENIOR_ANALYST"
    assert len(data["user"]["capabilities"]) > 0

    token = data["token"]

    # Verify session validation with Bearer token
    sess_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert sess_res.status_code == 200
    sess_data = sess_res.json()
    assert sess_data["valid"] is True
    assert sess_data["user"]["user_id"] == "senior_analyst_01"


def test_login_and_logout_flow():
    """Verify full login -> session check -> logout -> session invalidation cycle."""
    login_res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "RiskOrbit@Analyst2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    # Session is valid
    val_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # Logout
    logout_res = client.post("/api/v2/ops/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "SUCCESS"

    # Subsequent session check with invalidated token must fail with 401
    expired_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert expired_res.status_code == 401


def test_google_oauth_config():
    """Verify Google OAuth configuration probe returns environment readiness."""
    res = client.get("/api/v2/ops/auth/google/config")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "message" in data


def test_all_four_demo_personas():
    """Verify each of the 4 demo personas can authenticate and receive the authoritative role."""
    personas = [
        ("analyst_01", "RiskOrbit@Analyst2026", "ANALYST"),
        ("senior_analyst_01", "RiskOrbit@Senior2026", "SENIOR_ANALYST"),
        ("admin_01", "RiskOrbit@Admin2026", "ADMIN"),
        ("viewer_01", "RiskOrbit@Viewer2026", "VIEWER"),
    ]
    for uid, password, expected_role in personas:
        res = client.post(
            "/api/v2/ops/auth/login",
            json={"username_or_email": uid, "password": password},
        )
        assert res.status_code == 200
        token = res.json()["token"]
        assert res.json()["user"]["role"] == expected_role

        # Verify session endpoint confirms the server role
        sess_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
        assert sess_res.status_code == 200
        assert sess_res.json()["user"]["role"] == expected_role


def test_role_tamper_defense():
    """Verify that specifying role='ADMIN' for analyst_01 cannot elevate privileges."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={
            "username_or_email": "analyst_01",
            "password": "RiskOrbit@Analyst2026",
            "role": "ADMIN",
        },
    )
    assert res.status_code == 200
    # Server must return ANALYST, not ADMIN
    assert res.json()["user"]["role"] == "ANALYST"
    token = res.json()["token"]

    sess_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert sess_res.status_code == 200
    assert sess_res.json()["user"]["role"] == "ANALYST"


def test_invalid_credentials_returns_401():
    """Verify invalid user identifier and password return the same 401 error."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "nonexistent_user", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid user ID/email or password."

    wrong_password = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "wrongpassword"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["message"] == res.json()["message"]


def test_empty_password_is_rejected():
    """Verify known users cannot authenticate with an empty password."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "   "},
    )
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid user ID/email or password."


def test_unauthenticated_request_to_session_returns_401():
    """Verify unauthenticated request without token to session endpoint is rejected."""
    res = client.get("/api/v2/ops/auth/session")
    assert res.status_code == 401


def test_authenticated_overview_access_flow():
    """Verify login -> session token -> accessing overview endpoint succeeds."""
    login_res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "password": "RiskOrbit@Analyst2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    # Request overview with valid bearer token
    overview_res = client.get("/api/v2/ops/overview", headers={"Authorization": f"Bearer {token}"})
    assert overview_res.status_code == 200
    overview_data = overview_res.json()
    assert "active_cases_total" in overview_data
    assert "critical_priority_count" in overview_data
    assert "pending_human_approvals" in overview_data


def _login(identifier: str, password: str) -> tuple[str, dict]:
    response = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": identifier, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["token"], payload


def test_admin_provisions_user_with_username_and_email_login():
    username = f"rahul_{uuid4().hex[:8]}"
    email = f"{username}@company.example"
    admin_token, _ = _login("admin_01", "RiskOrbit@Admin2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_response = client.post(
        "/api/v2/ops/auth/users",
        headers=headers,
        json={
            "username": username,
            "email": email,
            "password": "NewUser@2026",
            "role": "ANALYST",
            "name": "Rahul Kumar",
        },
    )
    assert create_response.status_code == 201
    assert "password_hash" not in create_response.json()

    _, username_login = _login(username, "NewUser@2026")
    assert username_login["user"]["role"] == "ANALYST"
    _, email_login = _login(email, "NewUser@2026")
    assert email_login["user"]["user_id"] == username

    wrong = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": username, "password": "wrong-password"},
    )
    assert wrong.status_code == 401

    disable_response = client.patch(
        f"/api/v2/ops/auth/users/{username}",
        headers=headers,
        json={"status": "DISABLED"},
    )
    assert disable_response.status_code == 200
    disabled_login = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": username, "password": "NewUser@2026"},
    )
    assert disabled_login.status_code == 401


def test_non_admin_cannot_manage_users():
    for identifier, password in [
        ("analyst_01", "RiskOrbit@Analyst2026"),
        ("viewer_01", "RiskOrbit@Viewer2026"),
    ]:
        token, _ = _login(identifier, password)
        response = client.get(
            "/api/v2/ops/auth/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
