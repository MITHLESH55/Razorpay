# RiskOrbit — Frontend Blueprint Traceability Matrix

This document tracks implementation status for every major Blueprint requirement defined in the RiskOrbit specifications.

---

## Blueprint Traceability Matrix

| Blueprint Section | Requirement | Frontend Page | Backend Endpoint | Test Case | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Overview** | Live KPIs, Open Cases, Active Rings, Intervention Rate, Hard-Block FPR, FP Cost, Modeled Net Protection, Compact Benchmark Snapshot | `src/views/OverviewView.tsx` | `GET /api/v2/ops/overview`, `GET /risk/evaluation` | `frontend/tests/overview.test.ts` | **CONFORMANT / READY** |
| **Risk Queue** | Search, filter (priority, status, pattern, amount, score), deterministic triage ordering | `src/views/RiskQueueView.tsx` | `GET /api/v2/ops/queue`, `GET /risk/queue` | `frontend/tests/queue.test.ts` | **CONFORMANT / READY** |
| **Ring Explorer** | Subgraph topology visualization, 2-hop ring expansion, entity clustering (devices, IPs, merchants) | `src/components/CanvasGraph.tsx`, `src/views/CaseDetailView.tsx` | `GET /risk/cases/{case_id}/graph`, `GET /api/v2/ops/cases/{case_id}` | `frontend/tests/graph.test.ts` | **CONFORMANT / READY** |
| **Case Page** | Flagship investigation dossier: Case Hero, Narrative, Evidence Inspector, 3-Tier Decision Decomposition | `src/views/CaseDetailView.tsx` | `GET /api/v2/ops/cases/{case_id}` | `frontend/tests/case.test.ts` | **CONFORMANT / READY** |
| **Simulation** | Counterfactual Policy Simulation: offline threshold exploration (tau, auto-block, friction penalty) without model mutation | `src/views/SimulationView.tsx` | `POST /risk/cases/{case_id}/simulate`, `POST /api/v2/ops/simulation` | `frontend/tests/simulation.test.ts` | **CONFORMANT / READY** |
| **Decision Gate** | Bounded Human Decision Gate: Approve, Edit Action, Reject with optimistic concurrency (`expected_version`, 409 Conflict) & Idempotency Key | `src/components/ApprovalGateModal.tsx`, `src/views/CaseDetailView.tsx` | `POST /api/v2/ops/cases/{case_id}/approve`, `/edit`, `/reject` | `frontend/tests/approval.test.ts` | **CONFORMANT / READY** |
| **Audit Trail** | Immutable Append-Only Audit Trail tracking actor, role, event type, timestamps, previous/new state | `src/views/AuditView.tsx`, `src/components/AuditTimeline.tsx` | `GET /risk/audit`, `GET /api/v2/ops/cases/{case_id}/audit` | `frontend/tests/audit.test.ts` | **CONFORMANT / READY** |
| **Evaluation** | Single Source of Truth canonical benchmarks: PR-AUC, Confusion Matrix, 100% Ring Recall (24/24), Hard-Block FPR <= 0.05% | `src/views/EvaluationView.tsx` | `GET /api/v2/ops/evaluation`, `GET /risk/evaluation` | `frontend/tests/evaluation.test.ts` | **CONFORMANT / READY** |
| **Failure Analysis** | "WHAT BROKE" historical evolution narrative (Pattern C velocity loss, blanket expansion false positives, binary gating cost) | `src/views/EvaluationView.tsx` (Failures Tab) | `GET /api/v2/ops/evaluation` (`historical_failures`) | `frontend/tests/evaluation.test.ts` | **CONFORMANT / READY** |
| **Stable Demo** | Deterministic Golden Replay workflow across all 9 Lifecycle Stages for Pattern A, B, C and Hard Negatives | `src/App.tsx`, `src/components/Navbar.tsx` | Seeded Backend Cases & Replay Fixtures | `frontend/tests/demo.test.ts` | **CONFORMANT / READY** |
| **Reproducibility** | Cryptographic Manifest & Release Checksums: SHA-256 verification of models, policies, test splits, and evaluation report | `src/views/EvaluationView.tsx` (Manifest Tab) | `GET /api/v2/ops/manifest`, `GET /risk/governance` | `frontend/tests/manifest.test.ts` | **CONFORMANT / READY** |
| **Controls & Health** | Operational health & emergency controls: Shadow Mode, Kill Switch, Safe Mode, Graph Fallback, Readiness probes | `src/views/GovernanceView.tsx`, `src/components/Navbar.tsx` | `GET /ready`, `GET /live`, `GET/POST /api/v2/ops/controls` | `frontend/tests/governance.test.ts` | **CONFORMANT / READY** |
| **Drift Monitoring** | Population Stability Index (PSI) tracking, feature drift detection, and early warning thresholds | `src/views/DriftView.tsx` | `GET /api/v2/ops/drift` | `frontend/tests/drift.test.ts` | **CONFORMANT / READY** |
| **Authentication & RBAC** | Real token-based authentication (`POST /api/v2/ops/auth/login`), demo role switcher, permission hierarchy enforcement | `src/views/LoginView.tsx`, `src/components/Navbar.tsx` | `POST /api/v2/ops/auth/login`, `GET /api/v2/ops/auth/session` | `frontend/tests/auth.test.ts` | **CONFORMANT / READY** |
