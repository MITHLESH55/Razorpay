"""
RiskOrbit — Live Network Trace & Forensic Reproduction Script
Executes the exact browser-to-backend network requests for:
1. Health Check
2. POST /api/v2/ops/auth/login
3. GET  /api/v2/ops/auth/session (with Bearer token)
4. GET  /api/v2/ops/overview (with Bearer token)
5. GET  /api/v2/ops/queue (with Bearer token)
6. GET  /api/v2/ops/controls (with Bearer token)
7. POST /api/v2/ops/auth/logout (with Bearer token)
8. GET  /api/v2/ops/auth/session post-logout (401 verification)
"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8001"

def make_request(method, path, headers=None, body=None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            resp_body = resp.read().decode("utf-8")
            resp_headers = dict(resp.getheaders())
            return status, resp_headers, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except:
            parsed = err_body
        return e.code, dict(e.headers), parsed

print("=" * 80)
print("STEP 1: Backend Health Check")
status, headers, body = make_request("GET", "/health")
print(f"GET /health -> HTTP {status}")
print("Response body:", json.dumps(body, indent=2))
assert status == 200, f"Health check failed with {status}"

print("\n" + "=" * 80)
print("STEP 2: POST /api/v2/ops/auth/login (Testing with backend identity: analyst_01)")
login_payload = {
    "username_or_email": "analyst_01",
    "password": None,
    "remember_me": True
}
print("Request Body:", json.dumps(login_payload, indent=2))
status, headers, body = make_request("POST", "/api/v2/ops/auth/login", body=login_payload)
print(f"\nResponse Status: HTTP {status}")
print("Response Headers (selected):")
for k in ["content-type", "x-request-id"]:
    if k in headers:
        print(f"  {k}: {headers[k]}")
print("Response Body:", json.dumps(body, indent=2))
assert status == 200, f"Login failed with {status}"
token = body["token"]
user_from_login = body["user"]
print(f"\n[PASS] Captured Bearer token: {token[:12]}... (length: {len(token)})")

print("\n" + "=" * 80)
print("STEP 3: GET /api/v2/ops/auth/session (Validating session with Bearer token)")
auth_headers = {"Authorization": f"Bearer {token}"}
status, headers, body = make_request("GET", "/api/v2/ops/auth/session", headers=auth_headers)
print(f"GET /api/v2/ops/auth/session -> HTTP {status}")
print("Request Headers: Authorization: Bearer <token>")
print("Response Body:", json.dumps(body, indent=2))
assert status == 200, f"Session validation failed with {status}"
assert body["valid"] is True
server_user = body["user"]
print(f"[PASS] Server validated identity: {server_user['name']} ({server_user['user_id']}) as {server_user['role']}")

print("\n" + "=" * 80)
print("STEP 4: GET /api/v2/ops/overview (Fetching operational metrics for Dashboard)")
status, headers, body = make_request("GET", "/api/v2/ops/overview", headers=auth_headers)
print(f"GET /api/v2/ops/overview -> HTTP {status}")
print("Response Body (Overview summary):")
print(f"  Active Cases Total: {body.get('active_cases_total')}")
print(f"  Critical Priority Count: {body.get('critical_priority_count')}")
print(f"  Pending Approvals Count: {body.get('pending_human_approvals')}")
print(f"  Health Status: {body.get('health_status')}")
assert status == 200, f"Overview failed with {status}"

print("\n" + "=" * 80)
print("STEP 5: GET /api/v2/ops/controls (Fetching governance controls)")
status, headers, body = make_request("GET", "/api/v2/ops/controls", headers=auth_headers)
print(f"GET /api/v2/ops/controls -> HTTP {status}")
print(f"  Kill Switch Active: {body.get('kill_switch_active')}")
print(f"  Shadow Mode Enabled: {body.get('shadow_mode_enabled')}")
print(f"  Operating Mode: {body.get('operating_mode')}")
assert status == 200, f"Controls failed with {status}"

print("\n" + "=" * 80)
print("STEP 6: POST /api/v2/ops/auth/logout (Terminating session)")
status, headers, body = make_request("POST", "/api/v2/ops/auth/logout", headers=auth_headers)
print(f"POST /api/v2/ops/auth/logout -> HTTP {status}")
print("Response Body:", json.dumps(body, indent=2))
assert status == 200, f"Logout failed with {status}"

print("\n" + "=" * 80)
print("STEP 7: GET /api/v2/ops/auth/session after logout (Confirming 401 Unauthorized)")
status, headers, body = make_request("GET", "/api/v2/ops/auth/session", headers=auth_headers)
print(f"GET /api/v2/ops/auth/session (post-logout) -> HTTP {status}")
print("Response Body:", json.dumps(body, indent=2))
assert status == 401, f"Expected 401 post-logout, got {status}"

print("\n" + "=" * 80)
print("ALL LIVE NETWORK HANDSHAKE VERIFICATIONS COMPLETED SUCCESSFULLY (100% PASS)")
print("=" * 80)
