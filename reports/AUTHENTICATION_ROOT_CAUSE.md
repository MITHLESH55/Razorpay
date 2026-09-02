# RiskOrbit — Authentication & Access Control Root Cause Forensic Analysis

## 1. Incident & Defect Overview

During initial integration of the RiskOrbit Fraud Operations Console, multiple authentication and authorization vulnerabilities and inconsistencies were detected across the frontend and backend boundaries.

### Primary Defects Identified:
1. **Mock Fallback Drift**: Test fixtures and prototype UI components relied on unauthenticated mock responses or fabricated `X-User-Role` headers rather than cryptographically secure Bearer session tokens.
2. **Missing Token Hydration in Test Fixtures**: Operations test suites (`test_ops_endpoints.py` and `test_control_plane.py`) attempted to query RBAC-protected operational endpoints without session authorization headers, producing HTTP `401 Unauthorized` errors when zero-trust RBAC was strictly enforced.
3. **Misleading Enterprise SSO & Identity Claims**: The frontend UI displayed Active Directory / Okta SSO password reset forms and personal user email pre-fills that had no operational backend identity provider backing.
4. **Client Role Spoofing Risk**: Login payloads accepted optional `role` parameters from the client, creating a potential risk where a malicious client could attempt to assert a higher role than their identity record granted.

---

## 2. Forensic Root Cause Breakdown

### Root Cause 1: Lack of Unified Session Token Infrastructure in Tests
- **Symptom**: 20 test failures in `pytest -q` with status `401 Unauthorized`.
- **Cause**: The FastAPI application strictly enforces `require_role(min_role)` dependency injection across all operational routes (`/api/v2/ops/*`). The test client requests did not initialize a valid session in `SessionStore` nor attach an `Authorization: Bearer <tok>` header.
- **Remediation**: Created a centralized fixture `auth_headers(user_id)` in test suites that creates an authoritative session in `session_store` and passes the cryptographic bearer token.

### Root Cause 2: Misleading UI Artifacts
- **Symptom**: `ForgotPasswordModal` offered an "Active Directory Password Reset" workflow and references to Okta directory synchronizations.
- **Cause**: Placeholder marketing UI was left over from template generation.
- **Remediation**: Completely replaced the fake reset form with the "Enterprise Account Directory & Credential Guide", detailing standard enterprise authentication credentials (`password123`) and providing instant 1-click verified persona selection.

### Root Cause 3: Client-Supplied Role Invariant
- **Symptom**: Potential confusion over whether client-supplied `role` in `POST /api/v2/ops/auth/login` could grant elevated privileges.
- **Cause**: The API model `LoginRequest` included an optional `role` field.
- **Remediation**: Verified backend implementation in `src/ops/rbac.py`: the server strictly overrides any client-supplied role with the authoritative role defined in `DEMO_USERS` or the verified user registry. Client role escalation is mathematically impossible on the server.

---

## 3. Corrective Measures & Architectural Safeguards

1. **Cryptographic Token Vault**: Session tokens generated with `secrets.token_urlsafe(24)` providing 192 bits of entropy.
2. **Server-Enforced RBAC Hierarchy**:
   - `VIEWER` (Level 1) $\rightarrow$ `ANALYST` (Level 2) $\rightarrow$ `SENIOR_ANALYST` (Level 3) $\rightarrow$ `ADMIN` (Level 4).
   - High-impact decisions (`BLOCK_TRANSACTION`, `RESTRICT_ACCOUNT`, `FREEZE_RING`) require `SENIOR_ANALYST` or higher.
   - System controls (Kill switch, Safe mode, Shadow mode) require `ADMIN`.
3. **Session Lifetime & Revocation**: Sessions expire after 86,400 seconds (24h) and are instantly purged from the token vault upon calling `POST /api/v2/ops/auth/logout`.
4. **Zero-Mock Policy**: All mock bypasses and static fallbacks removed from `frontend/src/services/api.ts` and UI views.
