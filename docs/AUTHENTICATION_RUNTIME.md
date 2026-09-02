# RiskOrbit — Authentication & Session Management Architecture

## 1. Overview
The RiskOrbit Operations & Trust Console implements an enterprise-grade, zero-trust authentication architecture designed specifically for high-stakes fraud and risk operations.

All frontend components communicate with the FastAPI backend over HTTP using cryptographically secure Bearer session tokens (`tok_...`). Client identity, authorization privileges, and role boundaries are authoritatively verified on the server side on every request.

---

## 2. Authentication Lifecycle

```
[ Frontend: LoginView ]
        │
        │ 1. POST /api/v2/ops/auth/login
        │    { username_or_email, password? }
        ▼
[ Backend: SessionStore & RBAC Engine ]
        │
        │ 2. Validates identity & credentials against authoritative DEMO_USERS / IdP
        │ 3. Generates high-entropy Bearer token (tok_...) & Session ID (sess_...)
        │ 4. Records session in thread-safe SessionStore with expiration timestamp (86,400s)
        ▼
[ Response: 200 OK ]
        │  { token, session_id, user: { user_id, role, name, capabilities }, expires_at }
        ▼
[ Frontend: AuthContext & apiService ]
        │
        │ 5. Stores token in localStorage / sessionStorage
        │ 6. Sets in-memory userContext
        │ 7. Periodically validates session: GET /api/v2/ops/auth/session
        │ 8. Injects "Authorization: Bearer <tok>" & "X-Request-ID" into all subsequent requests
        ▼
[ Protected Operations Endpoints ]
        │  (/api/v2/ops/overview, /api/v2/ops/queue, /risk/cases/{id}/approve, etc.)
        │
        │ 9. Dependency get_current_user extracts token, validates against SessionStore
        │ 10. Dependency require_role(min_role) validates role tier against ROLE_HIERARCHY
```

---

## 3. Core Security Invariants

1. **Strict Server-Side Authorization:**
   - Client headers such as `X-User-Role` or `X-User-ID` are **never** trusted for authorization.
   - All role checks derive solely from the validated Bearer session in `session_store`.

2. **No Client-Side Privilege Escalation:**
   - Supplying `role: "ADMIN"` during login for an analyst account (`analyst_01`) is rejected/ignored by the backend. The issued session token strictly reflects the user's provisioned role (`ANALYST`).

3. **Explicit Token Revocation:**
   - Calling `POST /api/v2/ops/auth/logout` deletes the active token from `session_store`. Subsequent calls with the same token immediately return `401 Unauthorized`.

4. **Transparent Request Correlation:**
   - Every outgoing frontend request includes an `X-Request-ID` header (e.g. `req_e4b17c...`), which is captured by the backend audit logging engine (`audit_trail`) and returned in response headers for end-to-end tracing.

5. **CORS & Multi-Port Compliance:**
   - Backend `CORSMiddleware` explicitly permits ports `3000`, `3001`, and `5173` across `localhost` and `127.0.0.1` while preserving `allow_credentials=False` for standard Bearer authentication.

---

## 4. API Endpoints

| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v2/ops/auth/demo-users` | Public | Discovers available enterprise demo analyst personas |
| `POST` | `/api/v2/ops/auth/login` | Public | Authenticates analyst credentials and issues session token |
| `GET` | `/api/v2/ops/auth/session` | Authenticated | Validates session token and returns active UserContext |
| `POST` | `/api/v2/ops/auth/logout` | Authenticated | Revokes session token and destroys active session |

---

## 5. Session Validation & Reconnection
On page load, `AuthContext` checks for an existing saved token in browser storage. It issues a `GET /api/v2/ops/auth/session` request:
- If valid: User session is re-established seamlessly without requiring re-login.
- If expired/invalid: Token is cleared, state transitions to `EXPIRED` or `UNAUTHENTICATED`, and the analyst is returned to `LoginView` with a clear session notice.
