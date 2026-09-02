# PHASE 3.2 — HUMAN APPROVAL GATE & AUDIT SYSTEM SPECIFICATION

**Status:** ✅ Implemented & Verified  
**Schema Version:** 3.2.0  
**Date:** 2026-08-29  

---

## Executive Summary

This report documents the architectural design, escalation protocols, and immutable audit trail guarantees of the **RiskOrbit Human Approval Gate** (`src/decision/human_gate.py`).

In high-stakes payment operations, autonomous execution of broad-blast-radius interventions (such as freezing entire account networks or blocking high-value corporate transfers) introduces non-linear commercial and legal risk. The Human Approval Gate implements strict human-in-the-loop controls to bound blast radius while maintaining operational throughput.

---

## 1. Escalation Protocols & Trigger Criteria

An automated policy evaluation is routed to the Human Approval Queue when **any** of the following conditions are met:

| Escalation Rule | Condition | Target Action / Escalation | Rationale |
|---|---|---|---|
| **E-01: Ring-Wide Freeze** | Action recommended = `FREEZE_RING` | Routes to Fraud Lead Queue | Multi-entity freeze impacts multiple legal entities |
| **E-02: Account Suspension** | Action recommended = `RESTRICT_ACCOUNT` | Routes to Senior Fraud Analyst | Suspension freezes customer balances |
| **E-03: Extreme Amount** | Transaction amount $\ge ₹100,000$ | Mandatory Human Gate | Bounds single-transaction operational error |
| **E-04: Non-Primary High-Value Block** | Transaction $\ge ₹50,000$ and tier $\neq \text{PRIMARY}$ | Escalates `BLOCK` to `MANUAL_REVIEW` | Prevents VIP / enterprise false blocks |
| **E-05: Manual Review Policy** | Action recommended = `MANUAL_REVIEW` | Enters Analyst Queue | Standard analyst queue assignment |

---

## 2. Request Lifecycle & State Machine

```
               +-------------------------------------------------+
               |              submit_request(...)                |
               +-------------------------------------------------+
                                       |
                                       v
               +-------------------------------------------------+
               |                     PENDING                     |
               +-------------------------------------------------+
                        /                  |                  \
           approve(...) /       reject(...) |      timeout(...) \
                       /                   |                     \
                      v                    v                      v
        +-------------------+    +-------------------+    +--------------------+
        |     APPROVED      |    |     REJECTED      |    |  TIMEOUT_FALLBACK  |
        | (execute action)  |    |  (apply override) |    |  (apply fallback)  |
        +-------------------+    +-------------------+    +--------------------+
```

### State Definitions

1. **`PENDING`**: Request is queued in real-time queue awaiting analyst triage.
2. **`APPROVED`**: Analyst confirms risk evidence; proposed action is executed.
3. **`REJECTED`**: Analyst determines transaction is benign; override action (typically `ALLOW` or `STEP_UP_2FA`) is applied.
4. **`TIMEOUT_FALLBACK`**: SLA expired before analyst review; system automatically applies bounded fallback (default: `DELAY_SETTLEMENT`).

---

## 3. Immutable Audit Record Schema

Every resolved request generates an append-only `ApprovalAuditRecord`:

```json
{
  "request_id": "REQ_A91B4401CF2E",
  "transaction_id": "TXN_784910284",
  "customer_id": "CUST_992144",
  "proposed_action": "RESTRICT_ACCOUNT",
  "final_action": "RESTRICT_ACCOUNT",
  "status": "APPROVED",
  "amount": 75000.0,
  "tier": "PRIMARY",
  "risk_score": 0.92,
  "escalation_reason": "High-confidence ring coordinator detected with 4 shared devices",
  "created_at": "2026-08-29T10:15:30.123456+00:00",
  "reviewer_id": "ANALYST_007",
  "reviewed_at": "2026-08-29T10:18:12.654321+00:00",
  "review_notes": "Reviewed transaction history and shared device graph; confirmed abuse ring.",
  "metadata": {
    "graph_distance": 0,
    "edge_diversity_score": 0.85
  }
}
```

---

## 4. Operational Safety Guarantees

1. **Strict Immutability**:
   - Once a request transitions out of `PENDING` into `APPROVED`, `REJECTED`, or `TIMEOUT_FALLBACK`, it cannot be re-opened or modified.
2. **Safe Fallback Degradation**:
   - In the event of an operational queue backlog, timeouts downgrade hard blocks to non-destructive `DELAY_SETTLEMENT` (holding settlement for async investigation without interrupting the user checkout experience).
3. **Complete Lineage**:
   - Every human action captures timestamp, analyst identifier, and rationale notes for regulatory compliance and internal audit review.

---

**Status:** ✅ Human Gate Architecture Verified  
**Test Suite:** `tests/test_phase3_2.py::test_human_approval_gate_*` (3/3 passing)
