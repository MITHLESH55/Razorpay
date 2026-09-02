# RiskOrbit — Frontend ↔ Backend Contract Audit Matrix

**Specification Source**: OpenAPI 3.1.0 (`http://127.0.0.1:8001/openapi.json`)  
**Backend Application**: `src.api.app_v2:app`  
**Base URL**: `http://127.0.0.1:8001`  
**Audit Date**: 2026-09-01  
**Status**: Authoritative & Verified Live

---

## Namespace 1: Authentication & Session Management (`/api/v2/ops/auth/*`)

| Endpoint | Method | Authentication | Request Schema | Response Schema | Frontend Consumer | Status |
|---|---|---|---|---|---|---|
| `/api/v2/ops/auth/login` | `POST` | Public | `LoginRequest` (`username_or_email`, `password`, `role`, `remember_me`) | `LoginResponse` (`token`, `token_type`, `session_id`, `user`, `expires_at`) | `AuthContext.login()`, `LoginModal.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/auth/session` | `GET` | Bearer Token | None (Header: `Authorization: Bearer <tok>`) | `SessionValidateResponse` (`valid`, `session_id`, `user`, `expires_at`) | `AuthContext` initialization & auto-refresh | **VERIFIED (200 OK / 401)** |
| `/api/v2/ops/auth/logout` | `POST` | Bearer Token | None (Header: `Authorization: Bearer <tok>`) | `LogoutResponse` (`status`, `message`) | `Navbar.tsx` (Sign Out), `AuthContext.logout()` | **VERIFIED (200 OK)** |
| `/api/v2/ops/auth/demo-users` | `GET` | Public | None | `List[DemoUserRecord]` (`user_id`, `role`, `name`, `email`, `title`, `department`, `capabilities`) | `LoginModal.tsx`, `Navbar.tsx` (Demo Role Switcher) | **VERIFIED (200 OK)** |

---

## Namespace 2: Operations Console (`/api/v2/ops/*`)

| Endpoint | Method | Authentication | Request Schema | Response Schema | Frontend Consumer | Status |
|---|---|---|---|---|---|---|
| `/api/v2/ops/overview` | `GET` | Bearer Token (ANALYST+) | None | `OperationalOverviewSummary` (`active_cases_total`, `pending_approval_count`, `critical_high_count`, `total_exposure_inr`, `held_out_metrics`, `recent_activity`, `system_status`) | `OverviewView.tsx` (Command Center) | **VERIFIED (200 OK)** |
| `/api/v2/ops/queue` | `GET` | Bearer Token (ANALYST+) | Query params (`status`, `pattern`, `min_priority`, `limit`) | `List[RiskCaseRecord]` | `QueueView.tsx` (Risk Queue) | **VERIFIED (200 OK)** |
| `/api/v2/ops/cases/{case_id}` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `CaseDetailPayload` (`case`, `graph`, `evidence_records`, `decision_trace`, `narrative`, `pattern_name`) | `CaseView.tsx` (Case Investigation) | **VERIFIED (200 OK)** |
| `/api/v2/ops/cases/{case_id}/approve` | `POST` | Bearer Token (ANALYST+) | `ApproveActionRequest` (`actor_notes`, `idempotency_key`, `expected_version`) | `RiskCaseRecord` | `CaseView.tsx` (Approval Gate modal) | **VERIFIED (200 OK / 409)** |
| `/api/v2/ops/cases/{case_id}/edit` | `POST` | Bearer Token (SENIOR_ANALYST+) | `EditActionRequest` (`new_action`, `reason`, `idempotency_key`, `expected_version`) | `RiskCaseRecord` | `CaseView.tsx` (Action Override modal) | **VERIFIED (200 OK / 403 / 409)** |
| `/api/v2/ops/cases/{case_id}/reject` | `POST` | Bearer Token (ANALYST+) | `RejectActionRequest` (`reason`, `idempotency_key`, `expected_version`) | `RiskCaseRecord` | `CaseView.tsx` (Action Dismiss modal) | **VERIFIED (200 OK / 409)** |
| `/api/v2/ops/cases/{case_id}/simulate` | `POST` | Bearer Token (ANALYST+) | `SimulateActionRequest` (`target_action`, `candidate_policy_version`) | `SimulationResultPayload` (`case_id`, `simulated_action`, `executed_status`, `projected_friction_cost_inr`, `prevented_loss_inr`, `net_recovery_inr`, `simulation_timestamp`) | `SimulationView.tsx`, `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/feedback` | `POST` | Bearer Token (ANALYST+) | `SubmitFeedbackRequest` (`case_id`, `transaction_id`, `adjudication`, `notes`, `suggested_policy_tuning`) | `FeedbackRecord` | `CaseView.tsx` (Adjudication & Tuning modal) | **VERIFIED (200 OK)** |
| `/api/v2/ops/feedback` | `GET` | Bearer Token (VIEWER+) | Query param (`limit`) | `List[FeedbackRecord]` | `AuditView.tsx` (Feedback tab) | **VERIFIED (200 OK)** |
| `/api/v2/ops/audit` | `GET` | Bearer Token (VIEWER+) | Query params (`case_id`, `limit`) | `List[AuditRecord]` (`audit_id`, `case_id`, `timestamp`, `actor_id`, `actor_role`, `event_type`, `details`, `request_id`) | `AuditView.tsx`, `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/monitoring` | `GET` | Bearer Token (ANALYST+) | None | `OperationalMetricsSummary` (`p95_latency_ms`, `error_rate_pct`, `throughput_tps`, `action_distribution`) | `ControlsView.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/drift` | `GET` | Bearer Token (VIEWER+) | None | `SystemDriftSummary` (`overall_status`, `max_psi`, `evaluated_features_count`, `feature_reports`, `recommendation`) | `DriftView.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/controls` | `GET` | Bearer Token (VIEWER+) | None | `SystemControlsState` (`health_status`, `shadow_mode_enabled`, `kill_switch_active`, `safe_mode_degraded`, `active_model_version`, `active_policy_version`) | `Navbar.tsx`, `ControlsView.tsx` | **VERIFIED (200 OK)** |
| `/api/v2/ops/controls` | `POST` | Bearer Token (ADMIN) | `UpdateControlsRequest` (`shadow_mode_enabled`, `kill_switch_active`, `safe_mode_degraded`, `reason`) | `SystemControlsState` | `ControlsView.tsx` (Emergency System Controls) | **VERIFIED (200 OK / 403)** |
| `/api/v2/ops/manifest` | `GET` | Bearer Token (VIEWER+) | None | `HeldOutManifest` (`manifest_version`, `heldout_test_sha256`, `model_sha256`, `policy_sha256`, `final_heldout_metrics_summary`) | `EvaluationView.tsx` (Artifacts & Hashes) | **VERIFIED (200 OK)** |
| `/api/v2/ops/evaluation` | `GET` | Bearer Token (VIEWER+) | None | `HeldOutMetricsSummary` (`ring_intervention_recall`, `hard_block_fpr_pct`, `intervention_fpr_pct`, `precision`, `recall`, `f1`, `pr_auc`, `pattern_recalls`) | `EvaluationView.tsx` (Held-Out Benchmark) | **VERIFIED (200 OK)** |

---

## Namespace 3: Risk Control Plane & Case Pipeline (`/risk/*`)

| Endpoint | Method | Authentication | Request Schema | Response Schema | Frontend Consumer | Status |
|---|---|---|---|---|---|---|
| `/risk/governance` | `GET` | Bearer Token (ANALYST+) | None | `GovernanceStateResponse` (`model_version`, `policy_version`, `heldout_hash`, `frozen_timestamp`) | `Navbar.tsx`, `ControlsView.tsx` | **VERIFIED (200 OK)** |
| `/risk/queue` | `GET` | Bearer Token (ANALYST+) | Query params (`pattern`, `priority`, `page`, `page_size`) | `QueueResponse` (`items`, `total_count`, `page`, `page_size`) | `QueueView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases` | `GET` | Bearer Token (ANALYST+) | None | `List[RiskCaseRecord]` | `QueueView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `CaseDetailResponse` | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/graph` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `GraphResponse` (`nodes`, `edges`, `ring_topology`) | `CaseView.tsx` (Graph Visualizer) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/evidence` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `EvidenceResponse` (`evidence_items`, `summary_score`) | `CaseView.tsx` (Evidence Ledger) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/verification` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `VerificationResponse` (`verification_status`, `checks`, `confidence_interval`) | `CaseView.tsx` (Verification Badge) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/decision` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `DecisionTraceResponse` (`point_risk_p1`, `evidence_strength`, `recommended_action`, `policy_rules_fired`) | `CaseView.tsx` (Decision Trace Card) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/action-preview` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `ActionPreviewResponse` (`action`, `target_entity`, `friction_cost`, `blast_radius_users`, `approval_required`) | `CaseView.tsx` (Action Preview Card) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/approve` | `POST` | Bearer Token (ANALYST+) | `ApproveRequest` (`actor`, `role`, `reason`, `idempotency_key`) | `CaseActionResponse` | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/reject` | `POST` | Bearer Token (ANALYST+) | `RejectRequest` (`actor`, `role`, `reason`, `idempotency_key`) | `CaseActionResponse` | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/edit` | `POST` | Bearer Token (SENIOR_ANALYST+) | `EditRequest` (`actor`, `role`, `new_action`, `reason`) | `CaseActionResponse` | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/simulate` | `POST` | Bearer Token (ANALYST+) | `SimulateRequest` (`policy_version`, `candidate_thresholds`) | `SimulationResponse` | `SimulationView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/outcome` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `OutcomeResponse` (`prevented_loss_inr`, `customer_impact`, `actual_chargeback_status`) | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/audit` | `GET` | Bearer Token (ANALYST+) | Path: `case_id` | `List[AuditRecord]` | `CaseView.tsx` (Case Timeline) | **VERIFIED (200 OK)** |
| `/risk/audit` | `GET` | Bearer Token (VIEWER+) | Query param (`limit`) | `List[AuditRecord]` | `AuditView.tsx` (Global Audit Ledger) | **VERIFIED (200 OK)** |
| `/risk/cases/{case_id}/feedback` | `POST` | Bearer Token (ANALYST+) | `FeedbackRequest` (`analyst`, `role`, `adjudication`, `reason`) | `FeedbackResponse` | `CaseView.tsx` | **VERIFIED (200 OK)** |
| `/risk/evaluation` | `GET` | Public / VIEWER+ | None | `HeldOutMetricsSummary` | `EvaluationView.tsx` | **VERIFIED (200 OK)** |
| `/risk/score` | `POST` | Public / Internal | `ScoreRequest` (`transaction`) | `ScoreResponse` (`p1`, `risk_tier`, `action`) | `ScoringEngine` | **VERIFIED (200 OK)** |
| `/risk/investigate` | `POST` | Public / Internal | `InvestigateRequest` (`transaction_id`) | `InvestigationResponse` | `InvestigationPipeline` | **VERIFIED (200 OK)** |

---

## Namespace 4: Health & Liveness Probes

| Endpoint | Method | Authentication | Response Schema | Frontend Consumer | Status |
|---|---|---|---|---|---|
| `/health` | `GET` | Public | `{"status": "ok", "timestamp": str}` | Preflight connectivity check | **VERIFIED (200 OK)** |
| `/ready` | `GET` | Public | `SystemHealthResponse` (`overall_status`, `components`) | `Navbar.tsx`, `ControlsView.tsx` | **VERIFIED (200 OK)** |
| `/live` | `GET` | Public | `SystemHealthResponse` (`overall_status`, `uptime_seconds`) | Server liveness heartbeat | **VERIFIED (200 OK)** |

---

## Invariant Conformance & Constraints
1. All mutating operations enforce optimistic concurrency via `expected_version` with `409 Conflict` error mapping.
2. All mutating operations support deduplication via `idempotency_key`.
3. All requests inject `X-Request-ID` and support CORS preflight for `http://localhost:5173` and `http://127.0.0.1:5173`.
4. Role-based capabilities are server-authoritative (`VIEWER`, `ANALYST`, `SENIOR_ANALYST`, `ADMIN`).
