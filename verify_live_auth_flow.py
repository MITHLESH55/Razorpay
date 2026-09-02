"""
RiskOrbit — Live Authentication & End-to-End Route Flow Verification Script

Validates:
1. Demo Persona Logins:
   - Sarah Chen (analyst_01 -> ANALYST)
   - Marcus Vance (senior_analyst_01 -> SENIOR_ANALYST)
   - Elena Rostova (admin_01 -> ADMIN)
   - Audit & Compliance (viewer_01 -> VIEWER)
2. Token verification via GET /api/v2/ops/auth/session
3. Session invalidation via POST /api/v2/ops/auth/logout
4. Role tampering defense
5. Operational data access with valid tokens
6. Google OAuth environment configuration detection
7. Invalid credential handling (401)
8. Unauthenticated access protection
"""
import sys
from fastapi.testclient import TestClient
from src.api.app_v2 import app

client = TestClient(app)

def run_all_verifications():
    print("=" * 70)
    print("RISKORBIT LIVE AUTHENTICATION & ROUTE FLOW VERIFICATION")
    print("=" * 70)

    # 1. Test Demo Users Endpoint
    print("\n[1/7] Testing Demo Users Endpoint...")
    res = client.get("/api/v2/ops/auth/demo-users")
    assert res.status_code == 200, f"Failed: {res.status_code}"
    demo_users = res.json()
    print(f" -> Found {len(demo_users)} pre-configured demo personas:")
    for u in demo_users:
        print(f"    - {u['name']} ({u['user_id']}) -> Role: {u['role']}")

    # 2. Test All 4 Demo Persona Real Authentication
    print("\n[2/7] Testing Real Backend Authentication for 4 Personas...")
    personas = [
        ("analyst_01", "ANALYST", "Sarah Chen"),
        ("senior_analyst_01", "SENIOR_ANALYST", "Marcus Vance"),
        ("admin_01", "ADMIN", "Elena Rostova"),
        ("viewer_01", "VIEWER", "Audit & Compliance Officer"),
    ]

    tokens = {}
    for uid, expected_role, name in personas:
        # Step A: POST /api/v2/ops/auth/login
        login_res = client.post("/api/v2/ops/auth/login", json={"username_or_email": uid})
        assert login_res.status_code == 200, f"Login failed for {uid}: {login_res.text}"
        login_data = login_res.json()
        token = login_data["token"]
        assert login_data["user"]["role"] == expected_role
        tokens[uid] = token

        # Step B: Authoritative GET /api/v2/ops/auth/session check
        sess_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {token}"})
        assert sess_res.status_code == 200, f"Session check failed for {uid}: {sess_res.text}"
        sess_data = sess_res.json()
        assert sess_data["valid"] is True
        assert sess_data["user"]["role"] == expected_role
        assert sess_data["user"]["name"] == name
        print(f" -> Verified: {name} ({uid}) authenticated via backend, server-authoritative role: {expected_role}")

    # 3. Test Protected Operational Overview Access
    print("\n[3/7] Testing Authenticated Access to Protected Operational Overview...")
    sarah_token = tokens["analyst_01"]
    overview_res = client.get("/api/v2/ops/overview", headers={"Authorization": f"Bearer {sarah_token}"})
    assert overview_res.status_code == 200
    overview = overview_res.json()
    print(f" -> Operational Overview retrieved successfully:")
    print(f"    - Active Cases Total: {overview['active_cases_total']}")
    print(f"    - Critical Priority: {overview['critical_priority_count']}")
    print(f"    - Pending Approvals: {overview['pending_human_approvals']}")
    print(f"    - System Health: {overview['system_health']}")

    # 4. Test Role Tamper Defense
    print("\n[4/7] Testing Role Tamper Defense (Client attempts privilege escalation)...")
    tamper_res = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "analyst_01", "role": "ADMIN"},
    )
    assert tamper_res.status_code == 200
    assert tamper_res.json()["user"]["role"] == "ANALYST", "Security flaw: role was tampered!"
    tamper_token = tamper_res.json()["token"]
    tamper_sess = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {tamper_token}"})
    assert tamper_sess.json()["user"]["role"] == "ANALYST"
    print(" -> Defense Verified: Client-supplied role='ADMIN' ignored; server enforced ANALYST.")

    # 5. Test Logout & Session Invalidation
    print("\n[5/7] Testing Session Termination & Invalidation Lifecycle...")
    marcus_token = tokens["senior_analyst_01"]
    logout_res = client.post("/api/v2/ops/auth/logout", headers={"Authorization": f"Bearer {marcus_token}"})
    assert logout_res.status_code == 200
    print(" -> Session successfully logged out on server.")

    # Re-verify token is dead
    dead_sess_res = client.get("/api/v2/ops/auth/session", headers={"Authorization": f"Bearer {marcus_token}"})
    assert dead_sess_res.status_code == 401, f"Expected 401, got {dead_sess_res.status_code}"
    print(" -> Invalidation Verified: Post-logout session query rejected with 401 Unauthorized.")

    # 6. Test Google OAuth Configuration Probe
    print("\n[6/7] Testing Google OAuth Configuration Probe...")
    google_res = client.get("/api/v2/ops/auth/google/config")
    assert google_res.status_code == 200
    gdata = google_res.json()
    print(f" -> Google OAuth Configured: {gdata['configured']}")
    print(f" -> Message: '{gdata['message']}'")

    # 7. Test Negative Security: Invalid Credentials & Unauthenticated Endpoints
    print("\n[7/7] Testing Negative Security Handling...")
    invalid_login = client.post(
        "/api/v2/ops/auth/login",
        json={"username_or_email": "fake_user_999", "password": "wrongpassword"},
    )
    assert invalid_login.status_code == 401
    print(" -> Invalid credentials rejected with 401 Unauthorized.")

    unauth_sess = client.get("/api/v2/ops/auth/session")
    assert unauth_sess.status_code == 401
    print(" -> Missing token request to /session rejected with 401 Unauthorized.")

    print("\n" + "=" * 70)
    print("ALL 7 END-TO-END FLOW CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_verifications()
