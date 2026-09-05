"""
RiskOrbit — Hackathon Evaluation Auth Test Suite

Verifies the complete evaluation-ready authentication contract:

AUTH-001  Anonymous request to protected endpoint → 401
AUTH-002  Analyst evaluation login → 200 + real session
AUTH-003  Senior Analyst evaluation login → 200 + real session
AUTH-004  Admin evaluation login → 200 + real session
AUTH-005  Viewer evaluation login → 200 + real session
AUTH-006  Invalid credentials → 401
AUTH-007  Expired / invalid token → 401
AUTH-008  Logout invalidates session → 401 afterward
AUTH-009  Analyst attempting Admin-only operation → 403
AUTH-010  Viewer attempting mutation → 403
AUTH-011  Forged client role cannot escalate privileges
AUTH-012  Forged actor cannot change audit identity
AUTH-013  Fresh browser with no cookies can login (no-cookie test)
AUTH-014  Evaluation login creates real backend session
AUTH-015  Evaluation-login button does not bypass authentication
AUTH-016  Frontend role manipulation does not change backend authorization
AUTH-017  All four evaluation identities can authenticate from clean state

Mandatory named tests from the spec:
  test_evaluation_users_seeded
  test_evaluation_user_login
  test_each_evaluation_role
  test_session_created
  test_invalid_evaluation_password_rejected
  test_role_spoofing_blocked
  test_actor_spoofing_blocked
  test_admin_only_operation
  test_viewer_mutation_denied
  test_logout_invalidates_session
  test_seed_idempotency
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app_v2 import app
from src.ops.rbac import user_repository, UserRole, DEFAULT_EVALUATION_PASSWORDS

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EVAL_CREDENTIALS = {
    "ANALYST":        ("analyst_01",        DEFAULT_EVALUATION_PASSWORDS["analyst_01"]),
    "SENIOR_ANALYST": ("senior_analyst_01",  DEFAULT_EVALUATION_PASSWORDS["senior_analyst_01"]),
    "ADMIN":          ("admin_01",           DEFAULT_EVALUATION_PASSWORDS["admin_01"]),
    "VIEWER":         ("viewer_01",          DEFAULT_EVALUATION_PASSWORDS["viewer_01"]),
}


def _login(user_id: str, password: str) -> tuple[str, dict]:
    """Login via normal /login endpoint and return (token, payload)."""
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": user_id, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {user_id}: {res.text}"
    payload = res.json()
    return payload["token"], payload


def _evaluation_login(role: str) -> tuple[str, dict]:
    """Login via the dedicated /evaluation-login endpoint."""
    res = client.post(
        "/api/v2/ops/auth/evaluation-login",
        json={"role": role, "remember_me": True},
    )
    assert res.status_code == 200, f"Evaluation login failed for {role}: {res.text}"
    payload = res.json()
    return payload["token"], payload


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# test_evaluation_users_seeded
# ---------------------------------------------------------------------------

def test_evaluation_users_seeded():
    """All four evaluation identities must exist in the database as ACTIVE."""
    required = {
        "analyst_01":        "ANALYST",
        "senior_analyst_01": "SENIOR_ANALYST",
        "admin_01":          "ADMIN",
        "viewer_01":         "VIEWER",
    }
    for user_id, expected_role in required.items():
        row = user_repository.find_by_id(user_id)
        assert row is not None, f"Evaluation user '{user_id}' is missing from DB"
        assert row["status"] == "ACTIVE", f"'{user_id}' is not ACTIVE (status={row['status']})"
        assert row["role"] == expected_role, f"'{user_id}' role={row['role']}, expected {expected_role}"
        assert int(row["evaluation_only"]) == 1, f"'{user_id}' is not marked evaluation_only"


# ---------------------------------------------------------------------------
# test_seed_idempotency
# ---------------------------------------------------------------------------

def test_seed_idempotency():
    """Running _seed() twice must not create duplicate users or raise errors."""
    import sqlite3
    with user_repository._connect() as conn:
        user_repository._seed(conn)  # second seed call
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE user_id IN (?,?,?,?)",
            ("analyst_01", "senior_analyst_01", "admin_01", "viewer_01"),
        ).fetchone()[0]
    assert count == 4, f"Expected exactly 4 evaluation users, found {count}"


# ---------------------------------------------------------------------------
# test_evaluation_user_login  (via normal /login endpoint)
# ---------------------------------------------------------------------------

def test_evaluation_user_login():
    """Evaluation users must authenticate through the normal login endpoint."""
    uid, pw = EVAL_CREDENTIALS["ANALYST"]
    token, payload = _login(uid, pw)
    assert "token" in payload
    assert payload["token_type"] == "Bearer"
    assert payload["user"]["user_id"] == uid
    assert payload["user"]["role"] == "ANALYST"
    assert len(token) > 10


# ---------------------------------------------------------------------------
# test_each_evaluation_role  (AUTH-017)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ["ANALYST", "SENIOR_ANALYST", "ADMIN", "VIEWER"])
def test_each_evaluation_role(role: str):
    """Each of the four evaluation roles must authenticate and produce the correct server-side role."""
    uid, pw = EVAL_CREDENTIALS[role]
    token, payload = _login(uid, pw)

    # 1. Login response carries correct role
    assert payload["user"]["role"] == role

    # 2. Session endpoint independently confirms the server-side role
    sess = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert sess.status_code == 200
    sess_data = sess.json()
    assert sess_data["valid"] is True
    assert sess_data["user"]["role"] == role
    assert sess_data["user"]["user_id"] == uid


# ---------------------------------------------------------------------------
# test_session_created  (AUTH-014)
# ---------------------------------------------------------------------------

def test_session_created():
    """Evaluation login must produce a real backend session, not a frontend-only state."""
    # Use the dedicated evaluation-login endpoint
    token, payload = _evaluation_login("ANALYST")

    assert payload["session_id"].startswith("sess_")
    assert payload["expires_at"] > 0

    # Session must be retrievable from the backend
    sess = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert sess.status_code == 200
    body = sess.json()
    assert body["valid"] is True
    assert body["session_id"] == payload["session_id"]
    assert body["user"]["role"] == "ANALYST"


# ---------------------------------------------------------------------------
# test_invalid_evaluation_password_rejected  (AUTH-006)
# ---------------------------------------------------------------------------

def test_invalid_evaluation_password_rejected():
    """Wrong password for an evaluation user must return 401, not succeed."""
    uid, _ = EVAL_CREDENTIALS["ANALYST"]

    # The OLD wrong password that was hardcoded in the frontend before the fix
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": uid, "password": "Analyst@2026"},
    )
    assert res.status_code == 401, "Wrong password must be rejected"

    # Completely random password
    res2 = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": uid, "password": "totally_wrong_password!"},
    )
    assert res2.status_code == 401


# ---------------------------------------------------------------------------
# test_role_spoofing_blocked  (AUTH-011 / AUTH-016)
# ---------------------------------------------------------------------------

def test_role_spoofing_blocked():
    """Client cannot escalate privileges by supplying role=ADMIN in the request body."""
    # Attempt login as analyst_01 but with role=ADMIN in payload
    res = client.post(
        "/api/v2/ops/auth/login",
        json={
            "username_or_email": "analyst_01",
            "password": DEFAULT_EVALUATION_PASSWORDS["analyst_01"],
            "role": "ADMIN",          # extra unsupported field, must be ignored
        },
    )
    assert res.status_code == 200
    payload = res.json()
    # Server must return ANALYST, never ADMIN
    assert payload["user"]["role"] == "ANALYST", (
        f"Role spoofing succeeded! Server returned {payload['user']['role']}"
    )

    # Confirm the session endpoint also reports ANALYST
    token = payload["token"]
    sess = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert sess.status_code == 200
    assert sess.json()["user"]["role"] == "ANALYST"


# ---------------------------------------------------------------------------
# test_actor_spoofing_blocked  (AUTH-012)
# ---------------------------------------------------------------------------

def test_actor_spoofing_blocked():
    """Client cannot override actor identity via arbitrary request headers."""
    uid, pw = EVAL_CREDENTIALS["ANALYST"]
    token, _ = _login(uid, pw)

    # Attempt to claim to be admin_01 via a spoofed header
    spoofed_headers = {
        "Authorization": f"Bearer {token}",
        "X-Actor-Id": "admin_01",
        "X-User-Role": "ADMIN",
        "X-Analyst-Role": "ADMIN",
    }
    sess = client.get("/api/v2/ops/auth/session", headers=spoofed_headers)
    assert sess.status_code == 200
    data = sess.json()
    # Backend must still resolve ANALYST identity from the token, not the header
    assert data["user"]["user_id"] == uid
    assert data["user"]["role"] == "ANALYST"


# ---------------------------------------------------------------------------
# test_admin_only_operation  (AUTH-009)
# ---------------------------------------------------------------------------

def test_admin_only_operation():
    """ADMIN can access admin-only user management; ANALYST and VIEWER cannot."""
    admin_token, _ = _login(*EVAL_CREDENTIALS["ADMIN"])
    analyst_token, _ = _login(*EVAL_CREDENTIALS["ANALYST"])
    viewer_token, _ = _login(*EVAL_CREDENTIALS["VIEWER"])

    # ADMIN: list users → 200
    admin_res = client.get(
        "/api/v2/ops/auth/users",
        headers=_auth_header(admin_token),
    )
    assert admin_res.status_code == 200

    # ANALYST: list users → 403
    analyst_res = client.get(
        "/api/v2/ops/auth/users",
        headers=_auth_header(analyst_token),
    )
    assert analyst_res.status_code == 403, (
        f"Analyst should be denied user management, got {analyst_res.status_code}"
    )

    # VIEWER: list users → 403
    viewer_res = client.get(
        "/api/v2/ops/auth/users",
        headers=_auth_header(viewer_token),
    )
    assert viewer_res.status_code == 403, (
        f"Viewer should be denied user management, got {viewer_res.status_code}"
    )


# ---------------------------------------------------------------------------
# test_viewer_mutation_denied  (AUTH-010)
# ---------------------------------------------------------------------------

def test_viewer_mutation_denied():
    """VIEWER cannot perform mutations (system control POST requires ADMIN)."""
    viewer_token, _ = _login(*EVAL_CREDENTIALS["VIEWER"])
    analyst_token, _ = _login(*EVAL_CREDENTIALS["ANALYST"])

    # POST /api/v2/ops/controls requires ADMIN
    # VIEWER → 403
    viewer_res = client.post(
        "/api/v2/ops/controls",
        headers=_auth_header(viewer_token),
        json={"shadow_mode": False},
    )
    assert viewer_res.status_code == 403, (
        f"VIEWER must be denied system controls, got {viewer_res.status_code}"
    )

    # ANALYST → also 403 (admin-only)
    analyst_res = client.post(
        "/api/v2/ops/controls",
        headers=_auth_header(analyst_token),
        json={"shadow_mode": False},
    )
    assert analyst_res.status_code == 403


# ---------------------------------------------------------------------------
# test_logout_invalidates_session  (AUTH-008)
# ---------------------------------------------------------------------------

def test_logout_invalidates_session():
    """After logout, the same token must be rejected with 401."""
    uid, pw = EVAL_CREDENTIALS["ANALYST"]
    token, _ = _login(uid, pw)

    # Session is valid before logout
    pre = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert pre.status_code == 200
    assert pre.json()["valid"] is True

    # Logout
    logout_res = client.post("/api/v2/ops/auth/logout", headers=_auth_header(token))
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "SUCCESS"

    # Same token must now be rejected
    post = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert post.status_code == 401, (
        f"Invalidated token must return 401, got {post.status_code}"
    )


# ---------------------------------------------------------------------------
# AUTH-001 — Anonymous request to protected endpoint
# ---------------------------------------------------------------------------

def test_anonymous_protected_request_returns_401():
    """Protected endpoints must reject requests with no Authorization header."""
    for url in [
        "/api/v2/ops/auth/session",
        "/api/v2/ops/overview",
        "/api/v2/ops/auth/users",
    ]:
        res = client.get(url)
        assert res.status_code == 401, f"Expected 401 for anonymous {url}, got {res.status_code}"


# ---------------------------------------------------------------------------
# AUTH-007 — Invalid token returns 401
# ---------------------------------------------------------------------------

def test_invalid_token_returns_401():
    """Fabricated or expired tokens must be rejected."""
    fake_headers = {"Authorization": "Bearer tok_this_is_a_completely_fake_token_abc123"}
    res = client.get("/api/v2/ops/auth/session", headers=fake_headers)
    assert res.status_code == 401

    malformed_headers = {"Authorization": "Bearer "}
    res2 = client.get("/api/v2/ops/auth/session", headers=malformed_headers)
    assert res2.status_code == 401


# ---------------------------------------------------------------------------
# AUTH-013 — Fresh-browser login (no cookies, no stored state)
# ---------------------------------------------------------------------------

def test_fresh_browser_no_cookies_can_login():
    """Authentication must work purely from Bearer token — no cookie dependency."""
    # TestClient starts with no cookies; this directly verifies token-only auth.
    uid, pw = EVAL_CREDENTIALS["ADMIN"]
    res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": uid, "password": pw},
        # Explicitly no cookies, no extra headers
    )
    assert res.status_code == 200
    token = res.json()["token"]
    assert token.startswith("tok_")

    sess = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
    assert sess.status_code == 200
    assert sess.json()["user"]["role"] == "ADMIN"


# ---------------------------------------------------------------------------
# AUTH-015 — Evaluation-login endpoint is a real auth call
# ---------------------------------------------------------------------------

def test_evaluation_login_is_real_backend_auth():
    """POST /evaluation-login must produce a session verifiable at /auth/session."""
    for role in ("ANALYST", "SENIOR_ANALYST", "ADMIN", "VIEWER"):
        token, payload = _evaluation_login(role)
        assert payload["user"]["role"] == role

        # Token must be verifiable by the session endpoint
        sess = client.get("/api/v2/ops/auth/session", headers=_auth_header(token))
        assert sess.status_code == 200
        assert sess.json()["user"]["role"] == role

        # Logout to keep the session store clean between iterations
        client.post("/api/v2/ops/auth/logout", headers=_auth_header(token))


# ---------------------------------------------------------------------------
# Demo-users endpoint — must not expose secrets
# ---------------------------------------------------------------------------

def test_demo_users_endpoint_safe_metadata_only():
    """GET /auth/demo-users must expose only safe fields — never passwords or hashes."""
    res = client.get("/api/v2/ops/auth/demo-users")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    for user in data:
        assert "password" not in user, "Plaintext password must never be exposed"
        assert "password_hash" not in user, "Password hash must never be exposed"
        assert user.get("evaluation_only") is True
        assert "role" in user
        assert "user_id" in user
        assert "capabilities" in user

    roles = {u["role"] for u in data}
    assert roles >= {"ANALYST", "SENIOR_ANALYST", "ADMIN", "VIEWER"}


# ---------------------------------------------------------------------------
# Senior Analyst — high-impact approval denied for plain Analyst
# ---------------------------------------------------------------------------

def test_senior_analyst_can_login_analyst_cannot_reach_senior_only_if_any():
    """Senior Analyst has a higher privilege level than Analyst."""
    analyst_token, analyst_payload = _login(*EVAL_CREDENTIALS["ANALYST"])
    senior_token, senior_payload = _login(*EVAL_CREDENTIALS["SENIOR_ANALYST"])

    assert analyst_payload["user"]["role"] == "ANALYST"
    assert senior_payload["user"]["role"] == "SENIOR_ANALYST"

    # Both should be able to read the overview
    for token in (analyst_token, senior_token):
        res = client.get("/api/v2/ops/overview", headers=_auth_header(token))
        assert res.status_code == 200

    # Neither Analyst nor Senior Analyst can reach Admin user management
    for token in (analyst_token, senior_token):
        res = client.get("/api/v2/ops/auth/users", headers=_auth_header(token))
        assert res.status_code == 403
