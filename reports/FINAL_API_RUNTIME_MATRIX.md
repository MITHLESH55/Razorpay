# RiskOrbit — Final API Runtime & Contract Matrix

**Date:** 2026-09-02  
**Status:** 100% VERIFIED  
**Framework:** FastAPI 0.115 / Pydantic V2 / Uvicorn  
**Authoritative Router:** `src/api/routes_ops.py` & `src/api/routes_auth.py`  

---

## 1. RESTful Ops API Specification & Contract Matrix

| HTTP Method | Route Endpoint | Purpose / Description | Minimum Role Required | Request Body / Query Params | Response Type | Status Codes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v2/ops/overview` | KPI summary statistics, queue counts, net utility, FPR | `VIEWER` | None | `DashboardMetrics` | 200, 401 |
| `GET` | `/api/v2/ops/queue` | Prioritized risk case review queue with multi-signal scores | `VIEWER` | `page`, `page_size`, `status_filter`, `sort_by` | `PaginatedQueueResponse` | 200, 401 |
| `GET` | `/api/v2/ops/cases/{case_id}` | Case investigation detail, topological subgraph, SHAP, trace | `VIEWER` | Path: `case_id` | `RiskCaseDetail` | 200, 401, 404 |
| `POST` | `/api/v2/ops/cases/{case_id}/approve` | Approve recommended policy intervention action | `ANALYST` | `actor`, `role`, `reason`, `expected_version`, `idempotency_key` | `RiskCaseRecord` | 200, 400, 401, 403, 404, 409 |
| `POST` | `/api/v2/ops/cases/{case_id}/edit` | Override case action (escalation / downgrade) | `SENIOR_ANALYST` | `actor`, `role`, `new_action`, `reason`, `expected_version`, `idempotency_key` | `RiskCaseRecord` | 200, 400, 401, 403, 404, 409 |
| `POST` | `/api/v2/ops/cases/{case_id}/reject` | Dismiss risk case as false positive / benign | `ANALYST` | `actor`, `role`, `reason`, `expected_version`, `idempotency_key` | `RiskCaseRecord` | 200, 400, 401, 403, 404, 409 |
| `POST` | `/api/v2/ops/cases/{case_id}/simulate` | Execute sandbox counterfactual simulation on case | `VIEWER` | `simulated_action`, `override_policy_parameters` | `SimulationResult` | 200, 401, 404 |
| `POST` | `/api/v2/ops/feedback` | Submit analyst feedback & adjudication labels | `ANALYST` | `case_id`, `transaction_id`, `adjudication`, `notes`, `evidence_conflict_notes` | `FeedbackRecord` | 200, 401, 403 |
| `GET` | `/api/v2/ops/audit` | Query immutable JSONL audit ledger records | `VIEWER` | `case_id`, `limit` | `List[AuditRecord]` | 200, 401 |
| `GET` | `/api/v2/ops/drift` | Get current feature Population Stability Index (PSI) | `VIEWER` | None | `SystemDriftSummary` | 200, 401 |
| `POST` | `/api/v2/ops/drift/recalculate` | Trigger fresh PSI calculation against sliding window | `VIEWER` | None | `SystemDriftSummary` | 200, 401 |
| `GET` | `/api/v2/ops/controls` | Get operational state, kill switches, safe mode | `VIEWER` | None | `SystemControlsState` | 200, 401 |
| `POST` | `/api/v2/ops/controls` | Update operational controls & circuit breakers | `ADMIN` | `shadow_mode`, `kill_switch`, `graph_available`, `reason` | `SystemControlsState` | 200, 401, 403 |
| `GET` | `/api/v2/ops/manifest` | Retrieve cryptographic SHA-256 release signatures | `VIEWER` | None | `ManifestData` | 200, 401 |
| `GET` | `/api/v2/ops/evaluation` | Canonical benchmark metrics from `RISKORBIT_FINAL_METRICS.json` | `VIEWER` | None | `EvaluationMetricsResponse` | 200, 401 |

---

## 2. Authentication & Session Endpoints

| HTTP Method | Route Endpoint | Purpose / Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v2/ops/auth/login` | Authenticate username/password or generate demo persona session | None |
| `GET` | `/api/v2/ops/auth/session` | Validate session token & return active role permissions | `Bearer <token>` |
| `POST` | `/api/v2/ops/auth/logout` | Invalidate active session token | `Bearer <token>` |
| `GET` | `/api/v2/ops/auth/demo-users` | Retrieve preconfigured demo personas (`viewer`, `analyst`, `senior_analyst`, `admin`) | None |

---

## 3. Runtime Verification Status

All 19 routes return deterministic, strongly typed JSON payloads validated by Pydantic models. Unit and integration tests in `tests/test_ops_endpoints.py`, `tests/test_control_plane.py`, `tests/test_auth_api.py`, and `tests/test_app_v2_routes.py` verify 100% route availability and status code conformance.
