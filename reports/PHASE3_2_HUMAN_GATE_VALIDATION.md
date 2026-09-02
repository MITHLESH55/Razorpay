# RiskOrbit — Phase 3.2: Human Approval Gate Validation Report

**Status:** Complete  
**Evaluation Scope:** Validation Dataset & Execution Simulation Tests  
**Date:** 2026-08-31  

---

## 1. Executive Summary

Phase 3.2 introduces a formal **Human Approval Gate** (`src/simulation/human_gate.py`) to govern high-blast-radius, high-value, and structurally risky policy actions before state mutations are committed. 

This report validates that:
1. Proposed destructive actions transition cleanly into a deterministic approval lifecycle (`PENDING` $\to$ `APPROVED` / `REJECTED` / `TIMED_OUT`).
2. High-blast-radius actions (such as ring freezes or accounts with $\ge 5$ sub-entities) and high-value actions ($\ge ₹100,000$) unconditionally mandate human authorization.
3. **Rejected actions never execute** and fall back to safe override actions (e.g., `ALLOW` or `STEP_UP_2FA`).
4. Full cryptographic audit trails and reviewer metadata are immutably logged.

---

## 2. Human Gate Lifecycle Architecture

```
Policy Decision Engine
         │
         ▼
[High-Blast / High-Value Trigger]
         │
         ▼
 ┌───────────────┐
 │ Request State │  ──────── (Action Held in Escrow)
 │    PENDING    │
 └───────┬───────┘
         │
         ├───────────────────────────────┐
         ▼                               ▼
 ┌───────────────┐               ┌───────────────┐
 │ Analyst Event │               │ Analyst Event │
 │   "APPROVE"   │               │   "REJECT"    │
 └───────┬───────┘               └───────┬───────┘
         │                               │
         ▼                               ▼
 ┌───────────────┐               ┌───────────────┐
 │  Final State  │               │  Final State  │
 │   APPROVED    │               │   REJECTED    │
 └───────┬───────┘               └───────┬───────┘
         │                               │
         ▼                               ▼
 Executed Action =               Executed Action =
 Proposed Action                 Safe Override Action
 (e.g., RESTRICT_ACCOUNT)        (e.g., ALLOW / STEP_UP_2FA)
```

---

## 3. Empirical Test Demonstrations

### 3.1 Scenario 1: Proposed Action $\to$ PENDING $\to$ APPROVE
- **Transaction ID:** `TXN_APP_001`
- **Customer ID:** `CUST_APP_001`
- **Amount:** ₹125,000.00
- **Proposed Action:** `BLOCK_TRANSACTION`
- **Escalation Reason:** High-value transaction ($\ge ₹100,000$)
- **Lifecycle Transition:**
  1. Submitted to Queue: `Status: PENDING` (`request_id: REQ_001`)
  2. Analyst Reviewer: `ANALYST_01` logs review notes and issues `approve()`
  3. Result: `Status: APPROVED`, `Final Action: BLOCK_TRANSACTION`
- **Execution:** The state machine commits the transaction block and records audit ID.

### 3.2 Scenario 2: Proposed Action $\to$ PENDING $\to$ REJECT (Guaranteed Non-Execution)
- **Transaction ID:** `TXN_REJ_002`
- **Customer ID:** `CUST_REJ_002`
- **Amount:** ₹65,000.00
- **Proposed Action:** `RESTRICT_ACCOUNT`
- **Escalation Reason:** Ring-level association requiring manual confirmation
- **Lifecycle Transition:**
  1. Submitted to Queue: `Status: PENDING` (`request_id: REQ_002`)
  2. Analyst Reviewer: `SENIOR_ANALYST_04` inspects context, identifies legitimate merchant batch, and calls `reject(override_action=ActionType.ALLOW)`
  3. Result: `Status: REJECTED`, `Proposed Action: RESTRICT_ACCOUNT`, `Final Action: ALLOW`
- **Execution Verification:** The target customer account remains in `EntityState.ACTIVE`. The proposed `RESTRICT_ACCOUNT` action is strictly prevented from executing.

### 3.3 Scenario 3: High-Blast-Radius Gate Enforcement
- **Action:** `FREEZE_RING` across 14 linked accounts
- **Blast Radius Metric:** 14 accounts, aggregate 30-day volume ₹4.2M
- **Enforcement Rule:** All `FREEZE_RING` actions require 2-person rule or Senior Risk Lead authorization.
- **Verification:** Automatically intercepted and placed into `PENDING` queue. Direct automated execution is rejected by the simulator policy.

---

## 4. Timeout and Fallback Mechanics

When queue SLAs expire without analyst action:
- Default timeout: 300 seconds (configurable per action tier).
- **Fallback Action:** Configured to fail-safe (`ALLOW` with post-settlement audit or `STEP_UP_2FA` challenge).
- Under no circumstances does a timed-out request auto-promote to a hard block or destructive ring freeze.

---

## 5. Audit & Compliance Verification

| Invariant / Property | Test Status | Evidence |
|---|---|---|
| Request immutability | **Passed** | SHA256 hashed request records |
| Reviewer attribution | **Passed** | Mandatory `reviewer_id` and timestamp |
| Rejection non-execution | **Passed** | Unit test `test_rejected_actions_do_not_execute` |
| Blast-radius interception | **Passed** | Unit test `test_high_blast_radius_requires_approval` |
