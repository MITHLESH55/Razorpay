"""
RiskOrbit — Live E2E Authentication & Session Flow Verification Script

Performs rigorous HTTP verification of the RiskOrbit Authentication, Session Management,
and Role-Based Access Control (RBAC) subsystem against the live backend (default: http://127.0.0.1:8001).

Tests executed:
1. Public Endpoint Probe & Demo Identity Discovery (/ready, /api/v2/ops/auth/demo-users)
2. Passwordless Demo Persona Authentication (ANALYST, SENIOR_ANALYST, ADMIN, VIEWER)
3. Explicit Credential Authentication with Valid and Invalid Passwords
4. Authoritative Session Validation (/api/v2/ops/auth/session)
5. Anti-Tampering & Client Role Escalation Prevention
6. Hierarchical RBAC Authorization Enforcement Across Operational Endpoints
7. Session Invalidation & Token Revocation Flow (/api/v2/ops/auth/logout)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

BASE_URL = "http://127.0.0.1:8001"


def http_request(
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Execute raw HTTP request and return (status_code, parsed_json)."""
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8")
            return status_code, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        status_code = e.code
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw_error": body}
        return status_code, parsed
    except Exception as e:
        print(f"Connection failed to {url}: {e}")
        sys.exit(1)


def run_auth_verification():
    print("=" * 80)
    print("RISKORBIT -- LIVE END-TO-END AUTHENTICATION & RBAC RUNTIME VERIFICATION")
    print(f"Target Backend: {BASE_URL}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. System Probe & Demo Catalog Discovery
    # -------------------------------------------------------------------------
    print("\n[Step 1] Verifying System Probes & Demo Catalog Discovery...")
    status, ready_data = http_request("/ready")
    assert status == 200, f"Expected 200 from /ready, got {status}"
    assert ready_data.get("overall_status") == "HEALTHY"
    print("  [PASS] /ready: Component health confirmed HEALTHY")

    status, demo_users = http_request("/api/v2/ops/auth/demo-users")
    assert status == 200, f"Expected 200 from /api/v2/ops/auth/demo-users, got {status}"
    assert len(demo_users) >= 4, f"Expected >= 4 demo personas, got {len(demo_users)}"
    roles_found = {u["role"] for u in demo_users}
    print(f"  [PASS] Discovered {len(demo_users)} pre-configured demo personas with roles: {sorted(list(roles_found))}")

    # -------------------------------------------------------------------------
    # 2. Passwordless Demo Logins for All 4 Roles
    # -------------------------------------------------------------------------
    print("\n[Step 2] Testing Passwordless Demo Persona Logins...")
    role_tokens: Dict[str, str] = {}
    for demo_id in ["analyst_01", "senior_analyst_01", "admin_01", "viewer_01"]:
        status, login_res = http_request(
            "/api/v2/ops/auth/login",
            method="POST",
            data={"username_or_email": demo_id},
        )
        assert status == 200, f"Failed login for {demo_id}: {login_res}"
        token = login_res.get("token")
        assert token and token.startswith("tok_"), f"Malformed token for {demo_id}: {token}"
        role = login_res["user"]["role"]
        role_tokens[role] = token
        print(f"  [PASS] Persona '{demo_id}' -> Role: {role:15s} | Token: {token[:16]}... (Expires: {login_res['expires_at']})")

    # -------------------------------------------------------------------------
    # 3. Credential Logins (Valid & Invalid Passwords)
    # -------------------------------------------------------------------------
    print("\n[Step 3] Testing Credential Validation...")
    # Valid password
    status, cred_res = http_request(
        "/api/v2/ops/auth/login",
        method="POST",
        data={"username_or_email": "admin_01", "password": "password123"},
    )
    assert status == 200, f"Expected 200 for valid credentials, got {status}"
    assert cred_res["user"]["role"] == "ADMIN"
    print("  [PASS] Correct password ('password123') successfully validated")

    # Invalid password
    status, bad_res = http_request(
        "/api/v2/ops/auth/login",
        method="POST",
        data={"username_or_email": "admin_01", "password": "wrong_password_999"},
    )
    assert status == 401, f"Expected 401 for bad password, got {status}"
    print("  [PASS] Incorrect password correctly rejected with 401 Unauthorized")

    # -------------------------------------------------------------------------
    # 4. Authoritative Session Validation (/api/v2/ops/auth/session)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Session Validation with Bearer Tokens...")
    for role, token in role_tokens.items():
        status, sess_res = http_request(
            "/api/v2/ops/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status == 200, f"Expected 200 for session check, got {status}"
        assert sess_res.get("valid") is True
        assert sess_res["user"]["role"] == role
        print(f"  [PASS] Session validated for role '{role}': User '{sess_res['user']['name']}' ({sess_res['user']['title']})")

    # Invalid / fabricated token
    status, invalid_tok_res = http_request(
        "/api/v2/ops/auth/session",
        headers={"Authorization": "Bearer tok_fabricated_attacker_token_xyz"},
    )
    assert status == 401, f"Expected 401 for fake token, got {status}"
    print("  [PASS] Fabricated Bearer token correctly rejected with 401 Unauthorized")

    # -------------------------------------------------------------------------
    # 5. Anti-Tampering & Client Role Escalation Prevention
    # -------------------------------------------------------------------------
    print("\n[Step 5] Testing Anti-Tampering & Client Role Escalation Prevention...")
    # Attacker attempts to login as analyst_01 but sends role="ADMIN" in payload
    status, tampered_login = http_request(
        "/api/v2/ops/auth/login",
        method="POST",
        data={"username_or_email": "analyst_01", "role": "ADMIN"},
    )
    assert status == 200
    assert tampered_login["user"]["role"] == "ANALYST", (
        f"CRITICAL FAULT: Backend accepted client role override! Got {tampered_login['user']['role']}"
    )
    print("  [PASS] Server enforced authoritative role 'ANALYST' despite client requesting 'ADMIN'")

    # Attacker sends spoofed headers (X-User-Role: ADMIN) without valid token
    status, spoofed_res = http_request(
        "/api/v2/ops/controls",
        method="POST",
        headers={"X-User-Role": "ADMIN", "X-User-ID": "admin_spoofed"},
        data={"kill_switch": True},
    )
    assert status == 401, f"Expected 401 on spoofed header attempt, got {status}"
    print("  [PASS] Spoofed X-User-Role headers rejected: Bearer token is strictly required")

    # -------------------------------------------------------------------------
    # 6. Hierarchical RBAC Authorization Across Endpoints
    # -------------------------------------------------------------------------
    print("\n[Step 6] Testing Hierarchical RBAC Authorization Enforcements...")

    viewer_tok = role_tokens["VIEWER"]
    analyst_tok = role_tokens["ANALYST"]
    sr_analyst_tok = role_tokens["SENIOR_ANALYST"]
    admin_tok = role_tokens["ADMIN"]

    # Test A: Overview & Queue (All roles can read)
    status, overview_data = http_request("/api/v2/ops/overview", headers={"Authorization": f"Bearer {viewer_tok}"})
    assert status == 200, f"Expected 200 from /overview for VIEWER, got {status}"
    print(f"  [PASS] VIEWER can read /overview: Active cases = {overview_data['active_cases_total']}")

    # Test B: Governance / Controls (Only ADMIN can mutate)
    status, _ = http_request(
        "/api/v2/ops/controls",
        method="POST",
        headers={"Authorization": f"Bearer {analyst_tok}"},
        data={"kill_switch": True},
    )
    assert status == 403, f"Expected 403 for ANALYST toggling controls, got {status}"
    print("  [PASS] ANALYST denied access to system controls (403 Forbidden)")

    status, admin_ctrl_res = http_request(
        "/api/v2/ops/controls",
        method="POST",
        headers={"Authorization": f"Bearer {admin_tok}"},
        data={"shadow_mode": True, "reason": "E2E Verification"},
    )
    assert status == 200, f"Expected 200 for ADMIN toggling controls, got {status}"
    print(f"  [PASS] ADMIN allowed access to system controls: Shadow mode = {admin_ctrl_res['shadow_mode_enabled']}")

    # Reset control state
    http_request(
        "/api/v2/ops/controls",
        method="POST",
        headers={"Authorization": f"Bearer {admin_tok}"},
        data={"shadow_mode": False, "reason": "Reset"},
    )

    # Test C: Action Approval (High impact requires SENIOR_ANALYST or ADMIN)
    # CASE-RING-A-01 recommended action is high-impact BLOCK_TRANSACTION
    status, _ = http_request(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        method="POST",
        headers={"Authorization": f"Bearer {viewer_tok}"},
        data={"notes": "Viewer approval attempt"},
    )
    assert status == 403, f"Expected 403 for VIEWER approving action, got {status}"
    print("  [PASS] VIEWER denied action approval (403 Forbidden)")

    status, _ = http_request(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        method="POST",
        headers={"Authorization": f"Bearer {analyst_tok}"},
        data={"notes": "Analyst high impact approval attempt"},
    )
    assert status == 403, f"Expected 403 for ANALYST approving high-impact action, got {status}"
    print("  [PASS] Standard ANALYST denied high-impact BLOCK approval (403 Forbidden)")

    status, approve_res = http_request(
        "/api/v2/ops/cases/CASE-RING-A-01/approve",
        method="POST",
        headers={"Authorization": f"Bearer {sr_analyst_tok}"},
        data={"notes": "Senior analyst verification approval", "idempotency_key": "E2E-IDEM-001"},
    )
    assert status == 200, f"Expected 200 for SENIOR_ANALYST approving high-impact action, got {status}"
    print(f"  [PASS] SENIOR_ANALYST allowed high-impact action approval (Status: {approve_res['status']})")

    # -------------------------------------------------------------------------
    # 7. Logout & Session Invalidation
    # -------------------------------------------------------------------------
    print("\n[Step 7] Testing Logout & Session Invalidation...")
    test_logout_token = role_tokens["ANALYST"]
    status, logout_res = http_request(
        "/api/v2/ops/auth/logout",
        method="POST",
        headers={"Authorization": f"Bearer {test_logout_token}"},
    )
    assert status == 200, f"Expected 200 from logout, got {status}"
    assert logout_res.get("status") == "SUCCESS"
    print("  [PASS] Successfully called /api/v2/ops/auth/logout")

    # Verify token is now completely revoked
    status, after_logout = http_request(
        "/api/v2/ops/auth/session",
        headers={"Authorization": f"Bearer {test_logout_token}"},
    )
    assert status == 401, f"Expected 401 after logout, got {status}"
    print("  [PASS] Subsequent /session check with revoked token returns 401 Unauthorized")

    print("\n" + "=" * 80)
    print("ALL E2E AUTHENTICATION & RBAC SECURITY INVARIANTS CERTIFIED 100% OPERATIONAL")
    print("=" * 80)


if __name__ == "__main__":
    run_auth_verification()
