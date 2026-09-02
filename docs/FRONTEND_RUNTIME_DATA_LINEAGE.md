# RiskOrbit — Frontend Runtime Data Lineage & Truth Mapping

## 1. Single Source of Truth
The RiskOrbit frontend operates strictly on live backend data streams. There are **zero** hardcoded mock fallbacks or fabricated demo numbers in production execution.

---

## 2. Component-to-Backend Lineage Map

```
┌───────────────────────────────┬──────────────────────────────────┬──────────────────────────────────────┐
│ UI Component / View           │ Backend API Endpoint             │ Authoritative Data Origin            │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ LoginView & Role Switcher     │ GET /api/v2/ops/auth/demo-users  │ src/ops/rbac.py (DEMO_USERS)         │
│                               │ POST /api/v2/ops/auth/login      │ src/ops/rbac.py (SessionStore)       │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Navigation & Header Badge     │ GET /api/v2/ops/overview         │ src/ops/case_manager.py              │
│                               │ GET /api/v2/ops/controls         │ src/ops/system_state.py              │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Overview Command Center       │ GET /api/v2/ops/overview         │ reports/RISKORBIT_FINAL_METRICS.json │
│                               │ GET /api/v2/ops/queue            │ src/ops/case_manager.py              │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Risk Queue Workstation        │ GET /api/v2/ops/queue            │ src/ops/case_manager.py              │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Case Detail & Graph Canvas    │ GET /api/v2/ops/cases/{id}       │ src/ops/case_orchestrator.py         │
│                               │ GET /api/v2/ops/audit            │ src/ops/audit_log.py                 │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Approval & Action Override    │ POST /api/v2/ops/cases/{id}/appr │ src/ops/case_manager.py (State Mach) │
│                               │ POST /api/v2/ops/cases/{id}/edit │ src/ops/audit_log.py (Audit Trail)   │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Feedback & Adjudication Modal │ POST /api/v2/ops/feedback        │ src/ops/feedback_store.py            │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Policy Simulation Workbench   │ POST /risk/cases/{id}/simulate   │ src/policy/policy_engine.py          │
│                               │ GET /api/v2/ops/queue            │ src/ops/case_manager.py              │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Governance & Kill Switch View │ GET /api/v2/ops/controls         │ src/ops/system_state.py              │
│                               │ POST /api/v2/ops/controls        │ src/ops/system_state.py              │
│                               │ GET /api/v2/ops/manifest         │ reports/RISKORBIT_FINAL_MANIFEST.jso │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Evaluation Matrix & Release   │ GET /api/v2/ops/evaluation       │ reports/RISKORBIT_FINAL_METRICS.json │
│                               │ GET /api/v2/ops/manifest         │ reports/RISKORBIT_FINAL_MANIFEST.jso │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Observability & Drift View    │ GET /api/v2/ops/drift            │ src/ops/drift_detector.py            │
│                               │ GET /ready, GET /live            │ src/ops/monitoring.py                │
└───────────────────────────────┴──────────────────────────────────┴──────────────────────────────────────┘
```

---

## 3. Grounded Evidence Invariants
Every evidence card displayed in `CaseDetailView` contains:
- `evidence_id` (e.g. `EVID-DEV-001`)
- `category` (`DEVICE_COLLUSION`, `VELOCITY_ANOMALY`, `IP_ROTATION`, etc.)
- `statement` (deterministic, grounded summary)
- `observed_value` vs `baseline_value`
- `entity_ids` (exact nodes in graph)
- `confidence_score` $\in [0.0, 1.0]$

Evidence cards are computed purely deterministically by `PaymentGraphEngine` and `InvestigationAgent`. No generative LLM is in the runtime path for evidence scoring or decision computation.
