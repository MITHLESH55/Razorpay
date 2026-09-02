# RiskOrbit — Phase 3.2: Security, Isolation & Data Leakage Audit

**Status:** Complete  
**Audit Scope:** Codebase Execution Paths, Validation Pipeline, Causal Graph Bounds  
**Held-Out Test Status:** FULLY ISOLATED & UNTOUCHED  
**Date:** 2026-08-31  

---

## 1. Executive Summary

This security and isolation audit certifies that Phase 3.2 implementation, experiments, and ablations adhere strictly to zero-leakage standards, point-in-time (PIT) causal boundaries, and non-destructive reversibility requirements.

---

## 2. Held-Out Test Set Isolation & Zero-Leakage Audit

### 2.1 File & Execution Path Inspection
Every python script and notebook in the repository was audited for references to `heldout_test.csv`:

| Path Audited | `heldout_test.csv` Referenced? | Status |
|---|---|---|
| `scripts/phase3_2_validation_experiment.py` | **No** (Integrity hash check only, no loading) | **Isolated** |
| `src/simulation/policy_engine.py` | **No** | **Isolated** |
| `src/simulation/execution.py` | **No** | **Isolated** |
| `src/simulation/human_gate.py` | **No** | **Isolated** |
| `src/simulation/verifier.py` | **No** | **Isolated** |
| `tests/test_phase3_2.py` | **No** (Isolation assertion only) | **Isolated** |
| `evaluate_phase3.py` | Not Executed / Locked | **Untouched** |

### 2.2 Dataset Separation Integrity

| Partition | Row Count | SHA256 Hash | Status |
|---|---|---|---|
| **Validation Set** (`data/splits/validation.csv`) | 28,581 | `a521d2540737028b342de89dcd576bc6599ea332543555b3e1bd9d379db14600` | Processed |
| **Held-Out Test Set** (`data/splits/heldout_test.csv`) | 28,591 | `f0fe47be1191db1bbb62ab61f1747b952926d2fd2cc2adc72c3835a173dd164c` | **LOCKED** |

- **Transaction ID Overlap:** **0 transactions** (0.00% overlap)
- **Customer ID Overlap:** Disjoint entity sets across partitions
- **Abuse Ring ID Overlap:** **0 rings** (0.00% overlap)

### 2.3 Ground-Truth Feature Stripping
During the entire Phase 3.2 simulation:
- `abuse_label` (ground truth label)
- `ring_id` (ground truth ring membership)
- `pattern_type` (ground truth abuse typology)

were stripped and completely inaccessible to the `PolicyDecisionEngine`, `SimulationEngine`, and `ExecutionEngine`.

---

## 3. Point-in-Time (PIT) Causal Graph Safety

To prevent future lookahead bias in graph edge formulation:
1. **Timestamp Bounds:** Edge creation and graph updates are strictly bounded by transaction arrival time $t_i \le T_{\text{cutoff}}$.
2. **Causal Propagation:** Risk scores and community memberships are calculated exclusively from backward-looking historical subgraphs ($t < t_i$).
3. **Verified Invariant:** Unit test `test_point_in_time_causal_graph_safety` asserts that no transaction occurring after $T_{\text{cutoff}}$ contributes to graph edge formulation or centrality metrics.

---

## 4. State Execution Reversibility & Blast-Radius Governance

### 4.1 State Machine Transition Invariants
Account and entity states follow a controlled, monotonic escalation hierarchy:
$$\text{ACTIVE} \longrightarrow \text{RESTRICTED} \longrightarrow \text{FROZEN}$$
- Direct un-escalated transitions from `ACTIVE` to `FROZEN` without high-blast-radius gate approval are blocked.
- Transactions for one customer ID cannot mutate the state of an unrelated customer ID.

### 4.2 Reversibility & Remediation API
Phase 3.2 provides complete, audited remediation mechanisms:
- `unrestrict_account(customer_id, reason)` $\to$ returns state to `ACTIVE`
- `unfreeze_account(customer_id, reason)` $\to$ returns state to `ACTIVE`
- `revert_account_state(customer_id, target_state, reason)` $\to$ audited state rollback

### 4.3 Invariant Verifier
The `OutcomeVerifier` passed 100% of assertion checks across all 28,581 validation transactions:
- **Zero negative friction or review costs**
- **Zero unauthorized state transitions**
- **Zero tertiary hard blocks without individual risk corroboration**
- **Zero un-escalated extreme-value transactions ($\ge ₹100,000$)**

---

## 5. Security & Isolation Conclusion

Phase 3.2 conforms fully to data isolation and defensive safety principles. No leakage from the held-out test partition occurred.
