# RiskOrbit — Final Authentication & Role-Based Access Control (RBAC) Verification

**Date:** 2026-09-02  
**Status:** 100% PASS / ENFORCED  
**Security Standard:** Zero-Trust Bearer Token Authorization / Cryptographic Secrets  
**Authoritative Backend:** `src/api/auth.py` & `src/api/routes_auth.py`  

---

## 1. Authentication Architecture & Token Mechanics

RiskOrbit implements zero-trust authorization across all operational endpoints:

1. **Token Generation:** 192-bit cryptographically secure hex tokens generated via Python `secrets.token_hex(24)`.
2. **Transmission:** Tokens are transmitted in the HTTP `Authorization` header as `Bearer <token>`.
3. **Storage:** Client maintains the active token in memory and local session storage, attaching it to all outbound API calls via `frontend/src/api/client.ts`.
4. **Validation:** FastAPI dependency `get_current_user` validates session tokens against the in-memory token store with TTL enforcement (default 8 hours). Missing or invalid tokens result in HTTP 401 Unauthorized.

---

## 2. Role Hierarchy & Action Permission Matrix

The system enforces a strict 4-tier role hierarchy:

$$\text{VIEWER} < \text{ANALYST} < \text{SENIOR\_ANALYST} < \text{ADMIN}$$

| Action / Capability | VIEWER | ANALYST | SENIOR_ANALYST | ADMIN | Backend Enforcer |
| :--- | :---: | :---: | :---: | :---: | :--- |
| View Dashboard & Metrics | ✅ | ✅ | ✅ | ✅ | `require_role(VIEWER)` |
| View Investigation Queue | ✅ | ✅ | ✅ | ✅ | `require_role(VIEWER)` |
| Inspect Graph Subgraphs & SHAP | ✅ | ✅ | ✅ | ✅ | `require_role(VIEWER)` |
| Run Counterfactual Simulations | ✅ | ✅ | ✅ | ✅ | `require_role(VIEWER)` |
| Approve Recommended Action | ❌ (403) | ✅ | ✅ | ✅ | `require_role(ANALYST)` |
| Dismiss / Reject Risk Case | ❌ (403) | ✅ | ✅ | ✅ | `require_role(ANALYST)` |
| Submit Ground Truth Feedback | ❌ (403) | ✅ | ✅ | ✅ | `require_role(ANALYST)` |
| Override Case Action (Edit) | ❌ (403) | ❌ (403) | ✅ | ✅ | `require_role(SENIOR_ANALYST)` |
| Toggle System Kill Switches | ❌ (403) | ❌ (403) | ❌ (403) | ✅ | `require_role(ADMIN)` |
| Toggle Safe Mode / Graph Bypass | ❌ (403) | ❌ (403) | ❌ (403) | ✅ | `require_role(ADMIN)` |
| Toggle Shadow Pipeline | ❌ (403) | ❌ (403) | ❌ (403) | ✅ | `require_role(ADMIN)` |

---

## 3. Demo Personas & Fast Switching

To facilitate seamless demonstration and security auditing without manual credential management, RiskOrbit provides 4 certified personas:

- `viewer_01` (Role: `VIEWER`, Display: *Auditor / Observer*)
- `analyst_01` (Role: `ANALYST`, Display: *Fraud Analyst*)
- `senior_analyst_01` (Role: `SENIOR_ANALYST`, Display: *Lead Investigator*)
- `admin_01` (Role: `ADMIN`, Display: *System Operations Admin*)

Selecting a persona generates an authentic Bearer session token and reloads the authenticated context across the application shell.

---

## 4. Concurrency & Replay Attack Protection

- **Optimistic Version Locking:** State mutations require `expected_version`. If a concurrent analyst modified the record, the server returns HTTP 409 Conflict with the current record state.
- **Idempotency Keys:** Action endpoints accept client-generated UUID idempotency keys to prevent duplicate lifecycle transitions under network retries.
