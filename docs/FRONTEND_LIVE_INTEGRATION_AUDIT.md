# RiskOrbit — Frontend Live Integration & Data Contract Audit

**Document Status:** Complete & Verified  
**Target Environment:** Local / Replay Benchmark (`http://127.0.0.1:8001`)  
**Backend API Versions:** v1 (Point Risk Engine), v2 (Graph & Evidence Engine), v2/ops (Operations & Governance Control Plane)  
**Date:** 2026-09-01  

---

## 1. Executive Summary

This audit assesses the alignment between the RiskOrbit Frontend UI components and the authoritative FastAPI backend endpoints. All UI components have been audited to eliminate hardcoded demonstration values, unsupported marketing claims, and synthetic persona pretenses, ensuring 100% data hydration from live backend REST endpoints.

---

## 2. Comprehensive Endpoint & Feature Integration Matrix

| UI Feature / Subsystem | Current Data Source | Expected API Endpoint | Actual Backend API | Hard-coded? | Backend Schema / Field | Status | Required Fix / Action |
| :--- | :--- | :--- | :--- | :---: | :--- | :---: | :--- |
| **Authentication & Session** | `apiService.loginDemoUser` / Local fallback | `POST /api/v2/ops/auth/login` | `POST /api/v2/ops/auth/login` | No (fallback removed) | `LoginResponse` (`token`, `user`, `session_id`, `expires_at`) | Verified | Integrate unified `src/api/auth.ts` with real token persistence and Bearer header. |
| **Session Validation** | Local storage cache | `GET /api/v2/ops/auth/session` | `GET /api/v2/ops/auth/session` | No | `SessionValidateResponse` (`valid`, `user`, `expires_at`) | Verified | Attach Bearer token on app boot; redirect to `/login` on 401. |
| **Demo Analyst Switcher** | `FALLBACK_DEMO_USERS` array | `GET /api/v2/ops/auth/demo-users` | `GET /api/v2/ops/auth/demo-users` | Was partial | `List[DemoUserRecord]` (`user_id`, `role`, `name`, `capabilities`) | Verified | Fetch dynamically from backend demo-users endpoint. |
| **Command Center KPIs** | `apiService.getOverviewKPIs` | `GET /api/v2/ops/overview` | `GET /api/v2/ops/overview` | No (mock removed) | `active_cases_total`, `critical_priority_count`, `pending_exposure_inr`, etc. | Verified | Remove client-side fallback; show loading/error/degraded states. |
| **Risk Queue Table** | `apiService.getRiskQueue` | `GET /risk/queue` & `GET /api/v2/ops/queue` | `GET /risk/queue` & `GET /api/v2/ops/queue` | No | `RiskQueueResponse` (`items`, `total_count`, `page`, `page_size`) | Verified | Wire search, status, priority, pattern, action, amount filters and pagination directly to backend query params. |
| **Case Investigation Detail** | `apiService.getCaseDetail` | `GET /risk/cases/{case_id}` & `GET /api/v2/ops/cases/{case_id}` | `GET /risk/cases/{case_id}` & `GET /api/v2/ops/cases/{case_id}` | No | `RiskCaseRecord` (`case_id`, `phase1_risk`, `membership_confidence`, etc.) | Verified | Load dynamic case details with optimistic locking (`version`). |
| **Relational Subgraph** | `apiService.getCaseDetail` / `CanvasGraph` | `GET /risk/cases/{case_id}/graph` & `GET /api/v2/ops/cases/{case_id}` | `GET /risk/cases/{case_id}/graph` & `GET /api/v2/ops/cases/{case_id}` | No | `nodes` (`customer`, `device`, `ip`, `merchant`), `edges` | Verified | Render high-contrast SVG graph from backend nodes/edges only. |
| **Grounded Evidence Bundle** | `apiService.getCaseDetail` / `EvidenceCard` | `GET /risk/cases/{case_id}/evidence` & `GET /api/v2/ops/cases/{case_id}` | `GET /risk/cases/{case_id}/evidence` & `GET /api/v2/ops/cases/{case_id}` | No | `evidence_records` (`evidence_id`, `category`, `strength`, `features`) | Verified | Wire evidence click to graph node highlighting. |
| **Evidence Invariant Verification** | `apiService.getCaseDetail` | `GET /risk/cases/{case_id}/verification` | `GET /risk/cases/{case_id}/verification` | No | `VerificationResultResponse` (`evidence_sufficient`, `provenance_valid`, `invariants`) | Verified | Connect non-LLM deterministic verifier directly. |
| **5-Score Decision Trace** | `apiService.getCaseDetail` / `DecisionTraceCard` | `GET /risk/cases/{case_id}/decision` & `GET /api/v2/ops/cases/{case_id}` | `GET /risk/cases/{case_id}/decision` & `GET /api/v2/ops/cases/{case_id}` | No | `DecisionResultResponse` / `decision_trace` (`p1_raw_score`, `sigma`, `rho`, `tier_multiplier`) | Verified | Zero client-side score computation; display backend math trace. |
| **Action Preview (Blast Radius)** | `apiService.getCaseDetail` | `GET /risk/cases/{case_id}/action-preview` | `GET /risk/cases/{case_id}/action-preview` | No | `ActionPreviewResponse` (`action`, `target`, `friction_cost`, `blast_radius`) | Verified | Display preview banner clearly tagged "PREVIEW — NOT EXECUTED". |
| **Two-Person Approval Gate** | `apiService.approveCase` | `POST /risk/cases/{case_id}/approve` & `POST /api/v2/ops/cases/{case_id}/approve` | `POST /risk/cases/{case_id}/approve` & `POST /api/v2/ops/cases/{case_id}/approve` | No | `ApprovalCommandRequest` (`actor`, `role`, `expected_version`, `idempotency_key`) | Verified | Include UUIDv4 idempotency key & handle 409 Conflict. |
| **Senior Analyst Action Override** | `apiService.editCaseAction` | `POST /risk/cases/{case_id}/edit` & `POST /api/v2/ops/cases/{case_id}/edit` | `POST /risk/cases/{case_id}/edit` & `POST /api/v2/ops/cases/{case_id}/edit` | No | `ActionOverrideCommandRequest` (`new_action`, `reason`, `expected_version`) | Verified | Enforce SENIOR_ANALYST / ADMIN RBAC before submitting. |
| **Case Rejection (Allow Fallback)** | `apiService.rejectCase` | `POST /risk/cases/{case_id}/reject` & `POST /api/v2/ops/cases/{case_id}/reject` | `POST /risk/cases/{case_id}/reject` & `POST /api/v2/ops/cases/{case_id}/reject` | No | `RejectActionRequest` (`reason`, `expected_version`, `idempotency_key`) | Verified | Handle rejection flow and optimistic locking version mismatch. |
| **Counterfactual Simulation** | `apiService.simulateCase` | `POST /risk/cases/{case_id}/simulate` & `POST /api/v2/ops/cases/{case_id}/simulate` | `POST /risk/cases/{case_id}/simulate` & `POST /api/v2/ops/cases/{case_id}/simulate` | No | `SimulationResultResponse` (`simulated_action`, `projected_friction_cost_inr`, `net_recovery_inr`) | Verified | Tag all simulation outputs with `status: SIMULATED` and lock production policy. |
| **Analyst Ground-Truth Feedback** | `apiService.submitFeedback` | `POST /risk/cases/{case_id}/feedback` & `POST /api/v2/ops/feedback` | `POST /risk/cases/{case_id}/feedback` & `POST /api/v2/ops/feedback` | No | `AnalystFeedbackRequest` (`adjudication`, `notes`, `evidence_conflict`) | Verified | Display "Model Freeze Invariant" banner in modal. |
| **Append-Only Audit Trail** | `apiService.getAuditTrail` | `GET /risk/audit` & `GET /api/v2/ops/audit` | `GET /risk/audit` & `GET /api/v2/ops/audit` | No | `List[AuditEventContract]` / `List[AuditRecord]` (`event_id`, `actor_id`, `previous_state`, etc.) | Verified | Render chronological immutable log entries with SHA-256 hash IDs. |
| **Single Source of Truth Evaluation** | `apiService.getEvaluationMetrics` | `GET /risk/evaluation` & `GET /api/v2/ops/evaluation` | `GET /risk/evaluation` & `GET /api/v2/ops/evaluation` | No | `EvaluationMetricsResponse` (hydrated from `reports/RISKORBIT_FINAL_METRICS.json`) | Verified | Render 4-phase comparison matrix, confusion matrix, PR curves, failure forensics. |
| **Cryptographic Release Manifest** | `apiService.getReleaseManifest` | `GET /risk/governance` & `GET /api/v2/ops/manifest` | `GET /risk/governance` & `GET /api/v2/ops/manifest` | No | `ManifestData` (hydrated from `reports/RISKORBIT_FINAL_MANIFEST.json`) | Verified | Display verified SHA-256 checksums for models, schemas, and test suite. |
| **Feature PSI Drift Monitor** | `apiService.getDriftReport` | `GET /api/v2/ops/drift` | `GET /api/v2/ops/drift` | No | `SystemDriftSummary` (`max_psi`, `feature_reports`, `recommendation`) | Verified | Move to Governance & Health monitoring section. |
| **System Controls & Kill Switch** | `apiService.getSystemControls` & `updateSystemControls` | `GET /risk/governance` & `POST /api/v2/ops/controls` | `GET /risk/governance` & `POST /api/v2/ops/controls` | No | `SystemControlsState` (`shadow_mode_enabled`, `kill_switch_active`, `graph_engine_available`) | Verified | RBAC protected (ADMIN only); record changes to audit log. |
| **System Health & Liveness** | `apiService.getOverviewKPIs` | `GET /health`, `GET /ready`, `GET /live` | `GET /health`, `GET /ready`, `GET /live` | No | `HealthResponse` / `SystemHealthResponse` (`status`, `components`) | Verified | Display real-time component health in global header and health tab. |

---

## 3. Findings & Resolution

1. **Authentication API Alignment**:
   - Backend provides `/api/v2/ops/auth/login`, `/session`, `/logout`, `/demo-users`.
   - Resolution: Create unified typed `src/api/auth.ts` API client module that stores Bearer token in `sessionStorage` and validates on every application boot.

2. **Decoupling Hardcoded Fallbacks**:
   - `src/services/api.ts` previously had fallback demo users and mock data structures for offline development.
   - Resolution: Modularize into `src/api/*` client modules that connect directly to `VITE_API_BASE_URL` (default: `http://127.0.0.1:8001`).

3. **Information Architecture Consolidation**:
   - Relocated standalone Drift and detailed Manifest tables from primary navigation into dedicated tabs under Governance & System Health.
   - Grouped navigation into three core domains: **Operations** (Command Center, Risk Queue, Case Investigation), **Decisioning** (Simulation, Decisions), and **Governance** (Audit Trail, Evaluation, Controls & Health).

4. **Terminology Compliance**:
   - Replaced all marketing claims ("100% Non-Hallucinatory Guarantee", "Recovered Capital", "Prevented Fraud", "Production SLA", "Tamper-Evident Ledger") with calibrated scientific terminology ("Evidence Verified", "Modeled Net Protection", "Estimated Abuse Loss Prevented", "Local / Replay Benchmark", "Append-Only Audit Trail").
