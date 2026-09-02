# RiskOrbit — Frontend/Backend Integration Contract

## 1. Architecture Overview
All frontend data queries and mutations route through the centralized TypeScript API client (`src/api/client.ts`) and the singleton service (`src/services/api.ts`).

- Base API URL: Defaults to empty string in development (proxied by Vite to `http://127.0.0.1:8001`) or configured via `VITE_API_URL`.
- Authentication: Standard `Authorization: Bearer <token>` header injected automatically.
- Request Tracing: Standard `X-Request-ID` header generated via `crypto.randomUUID()` on each invocation.

---

## 2. API Route Specifications

### 2.1 Authentication & Session
- `POST /api/v2/ops/auth/login`
  - Request: `{ username_or_email: string, password?: string, role?: string, remember_me?: boolean }`
  - Response: `{ token: string, token_type: "Bearer", session_id: string, user: UserContext, expires_at: number }`
- `GET /api/v2/ops/auth/session`
  - Headers: `Authorization: Bearer <token>`
  - Response: `{ valid: boolean, session_id: string, user: UserContext, expires_at: number }`
- `POST /api/v2/ops/auth/logout`
  - Headers: `Authorization: Bearer <token>`
  - Response: `{ status: "SUCCESS", message: "Logged out successfully" }`
- `GET /api/v2/ops/auth/demo-users`
  - Response: `DemoUserRecord[]`

### 2.2 Operational Console & Queue
- `GET /api/v2/ops/overview`
  - Response: `OverviewKPIs` (Active cases, pending approvals, critical count, ring recall, hard-block FPR)
- `GET /api/v2/ops/queue`
  - Query Params: `search`, `priority`, `status`, `pattern`, `limit`, `offset`
  - Response: `RiskCaseRecord[]`
- `GET /api/v2/ops/cases/{case_id}`
  - Response: `CaseDetailResponse` (Full case record, graph nodes/edges, grounded evidence records, decision breakdown)
- `POST /api/v2/ops/cases/{case_id}/approve`
  - Request: `{ notes?: string, idempotency_key?: string, expected_version?: number }`
  - Response: `RiskCaseRecord` (Status updated to `APPROVED` or `PENDING_EXECUTION`)
- `POST /api/v2/ops/cases/{case_id}/edit`
  - Request: `{ new_action: string, reason: string, idempotency_key?: string, expected_version?: number }`
  - Response: `RiskCaseRecord` (Recommended action updated)
- `POST /api/v2/ops/cases/{case_id}/reject`
  - Request: `{ reason: string, idempotency_key?: string, expected_version?: number }`
  - Response: `RiskCaseRecord` (Status updated to `DISMISSED`)

### 2.3 Evaluation, Governance & Observability
- `GET /api/v2/ops/evaluation`
  - Response: `EvaluationMetricsResponse` (Canonical held-out metrics from `reports/RISKORBIT_FINAL_METRICS.json`)
- `GET /api/v2/ops/manifest`
  - Response: `ManifestData` (Frozen hashes for model, policy, features, splits)
- `GET /api/v2/ops/drift`
  - Response: `SystemDriftSummary` (PSI scores, feature drift alerts, latency p50/p95)
- `GET /api/v2/ops/controls`
  - Response: `SystemControlsState` (Health status, shadow mode, kill switch, active versions)
- `POST /api/v2/ops/controls`
  - Request: `{ shadow_mode?: boolean, kill_switch?: boolean, graph_available?: boolean, reason?: string }`
  - Response: `SystemControlsState`
- `GET /api/v2/ops/audit`
  - Query Params: `case_id`, `limit`
  - Response: `AuditRecord[]` (Append-only audit trail)

---

## 3. Error Handling Contract

All non-2xx responses from the backend follow the structured `ApiError` schema:
```json
{
  "code": "HTTP_ERROR",
  "message": "Human-readable explanation",
  "request_id": "req_8f12a9...",
  "case_id": "CASE-RING-A-01",
  "retryable": false
}
```

The frontend catches this in `apiRequest` and raises a typed `ApiError` containing status code, error code, and request correlation ID.
