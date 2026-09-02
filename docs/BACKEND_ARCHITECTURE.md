# RiskOrbit — Backend Architecture & Control-Plane Blueprint

**System Version:** `v3.2.0-frozen`  
**Status:** Certified Control-Plane Gate  
**Compliance Standard:** 100% Traceable to Original Specification  

---

## 1. System Overview

RiskOrbit is an enterprise-grade graph-native fraud detection, ring discovery, and automated decision control plane designed for high-throughput payment networks (e.g., Razorpay/UPI/Cards).

The system operates across three tightly integrated, strictly frozen scientific phases:
1. **Phase 1: LightGBM Point-in-Time Risk Scoring** (`threshold = 0.35`)
2. **Phase 2: PaymentGraphEngine & Graph-Native Ring Discovery** (DFS/BFS cycle detection, 32-node emulator farms, circular UPI layering)
3. **Phase 3: Policy Engine, Human Approval Gate & Counterfactual Control Plane** (3-tier policy rules, optimistic version locking, non-LLM evidence grounding, counterfactual simulation, audit trail)

---

## 2. Core Architectural Components

```
+-----------------------------------------------------------------------------------+
|                                 FASTAPI CONTROL PLANE                             |
|                           (src/api/app_v2.py & routes_control_plane.py)           |
+-------------------+-----------------------------------+---------------------------+
                    |                                   |
                    v                                   v
+---------------------------------------+   +---------------------------------------+
|        UNIFIED CASE ORCHESTRATOR      |   |            SYSTEM GOVERNANCE          |
|      (src/ops/case_orchestrator.py)   |   |        (src/ops/system_state.py)      |
+-------------------+-------------------+   +---------------------------------------+
                    |
    +---------------+---------------+-----------------------+-----------------------+
    |               |               |                       |                       |
    v               v               v                       v                       v
+-------+       +-------+       +-------+               +-------+               +-------+
|  P1   |       |  P2   |       |  P3   |               | Audit |               | Feedback
| Model |       | Graph |       | Policy|               | Trail |               | Store |
+-------+       +-------+       +-------+               +-------+               +-------+
```

### Component Details
1. **`src/ops/case_orchestrator.py` (`CaseOrchestrator`):**
   - Central coordinator linking investigation, verification, policy evaluation, simulation, approval state transitions, and audit logging.
2. **`src/ops/case_manager.py` (`CaseManager`):**
   - Thread-safe in-memory case state store (`_lock`) enforcing state machine transitions, priority queue ordering (`CRITICAL` > `HIGH` > `MEDIUM` > `LOW`), version increments, optimistic version checks (`expected_version` -> `409 Conflict`), and idempotency key mapping (`_idempotency_map`).
3. **`src/decision/policy_engine.py` (`PolicyEngine`):**
   - Evaluates `TransactionDecision` objects against tier rules (`PRIMARY`, `SECONDARY`, `ISOLATED`) and bounds interventions (`ALLOW`, `STEP_UP_2FA`, `DELAY_SETTLEMENT`, `MANUAL_REVIEW`, `BLOCK_TRANSACTION`, `RESTRICT_ACCOUNT`, `FREEZE_RING`).
4. **`src/investigation/investigation_agent.py` (`InvestigationAgent`):**
   - Autonomous multi-hop graph investigator extracting topological subgraphs, shared devices/IPs, and constructing grounded evidence records.
5. **`src/ops/audit_log.py` (`AuditTrail`):**
   - Chronological, append-only, tamper-evident audit logger recording state transitions, model versions, policy versions, and user actors.
6. **`src/ops/rbac.py` (`UserContext`, `UserRole`):**
   - Role-Based Access Control enforcing role permissions (`VIEWER`, `ANALYST`, `SENIOR_ANALYST`, `ADMIN`).

---

## 3. Data Integrity & Safety Invariants

1. **Scientific Core Freeze:**
   - Model weights, LightGBM features, decision threshold `0.35`, Held-Out evaluation dataset, held-out recall (100.0% / 24 rings), and false positive rate (0.04%) are **100% frozen**.
2. **Optimistic Locking:**
   - State mutations require `expected_version`. If current version != `expected_version`, API responds with `409 Conflict`.
3. **Idempotency Replay:**
   - Commands accept `idempotency_key`. Replayed requests return cached result without mutating version or side-effects.
4. **Non-LLM Grounded Evidence:**
   - Verification checks require valid SHA-256 evidence artifact hashes and non-empty statements. No LLM hallucination is permitted.
5. **Non-Monetary Simulation Guarantee:**
   - Counterfactual policy simulations return `status_tag: "SIMULATED"` and never mutate actual transactional monetary balances.

---

## 4. Verification & Testing Strategy

- **Automated Tests:** 213 unit, integration, and E2E HTTP lifecycle tests in `tests/`.
- **Golden Benchmark:** Pre-seeded golden cases (`CASE-RING-A-01`, `CASE-RING-B-02`, `CASE-RING-C-03`, `CASE-HARDNEG-04`).
- **Interactive Walkthrough:** Executable demo script `scripts/run_demo.py`.
