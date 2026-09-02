# PHASE 3.2 — COUNTERFACTUAL INTERVENTION SIMULATION REPORT

**Status:** ✅ Verified  
**Schema Version:** 3.2.0  
**Date:** 2026-08-29  

---

## Executive Summary

This report defines the mathematical models, simulation dynamics, and business impact formulas used by the **RiskOrbit Counterfactual Intervention Simulator** (`src/simulation/counterfactual_simulator.py`).

The simulator evaluates alternative intervention strategies across identical transaction streams to measure:
1. **Gross Abuse Losses Prevented (₹)**
2. **False Positive Friction Costs on Benign Users (₹)**
3. **Operational Analyst Review Costs (₹)**
4. **Net Economic Utility (₹)**
5. **Ring Containment Velocity & Blast-Radius Exposure**

---

## 1. Policy Comparison Framework

| Dimension | Policy A (Point Model Only) | Policy B (Phase 2.2 Blanket) | Policy C (Phase 3.1 Binary Gate) | Policy D (Phase 3.2 Tiered Response) |
|---|---|---|---|---|
| **Intervention Suite** | Single (`BLOCK`) | Single (`BLOCK`) | Single (`BLOCK`) | Multi (`ALLOW`, `2FA`, `DELAY`, `REVIEW`, `BLOCK`, `RESTRICT`, `FREEZE`) |
| **Graph Awareness** | None ($p1$ only) | Unweighted 2-Hop | Confidence-Weighted | Multi-signal Tiered Routing |
| **Secondary/Tertiary Handling** | Ignored unless high $p1$ | 100% Blanket Block | Gated on individual $p1$ | Proportional Challenge (`2FA` / `DELAY`) |
| **Human Escalation Gate** | None | None | None | Mandatory for high-blast-radius / high-value |
| **Friction on Shared IPs** | Very Low | Severe (~75% FPR) | Low (~3.9% FPR) | Minimal (proportional `2FA` / `DELAY` ₹15-30) |

---

## 2. Mathematical Modeling & Cost Functions

### Formal Utility Equation

For a set of transactions $T = \{t_1, t_2, \dots, t_N\}$, let:
- $y_i \in \{0, 1\}$ be the true ground-truth label ($1 = \text{Abuse}, 0 = \text{Benign}$).
- $A_i \in \mathbb{R}^+$ be the transaction amount in INR.
- $a_i \in \mathcal{A}$ be the intervention action selected by policy $\pi(t_i)$.

Each action $a \in \mathcal{A}$ is characterized by:
- $b(a) \in [0, 1]$: **Fraud Block Efficacy** (probability that fraudulent transaction loss is prevented).
- $s(a) \in [0, 1]$: **Legit Success Rate** (probability that benign user completes transaction despite intervention).
- $f(a) \in \mathbb{R}^+$: **Friction Cost** in INR incurred on benign users encountering the intervention.
- $r(a) \in \mathbb{R}^+$: **Analyst Review Cost** in INR incurred for manual inspection queues.

### Component Formulations

#### 1. Gross Abuse Losses Prevented
$$\text{Losses Prevented}(\pi) = \sum_{i: y_i = 1} b(a_i) \cdot A_i$$

#### 2. Uncaught Abuse Loss (Leakage)
$$\text{Uncaught Loss}(\pi) = \sum_{i: y_i = 1} (1 - b(a_i)) \cdot A_i$$

#### 3. Total Benign Friction Cost
$$\text{Benign Friction}(\pi) = \sum_{i: y_i = 0} f(a_i)$$

#### 4. Total Operational Review Cost
$$\text{Review Cost}(\pi) = \sum_{i} r(a_i)$$

#### 5. Net Economic Utility
$$\text{Net Utility}(\pi) = \text{Losses Prevented}(\pi) - \text{Benign Friction}(\pi) - \text{Review Cost}(\pi)$$

---

## 3. Parametric Calibration Table

| Action $a$ | $b(a)$ (Fraud Block) | $s(a)$ (Legit Pass) | $f(a)$ (Friction INR) | $r(a)$ (Review INR) | Target Population |
|---|---|---|---|---|---|
| **ALLOW** | 0.00 | 1.00 | ₹0.00 | ₹0.00 | Clear benign & low-risk accounts |
| **STEP_UP_2FA** | 0.85 | 0.96 | ₹15.00 | ₹0.00 | Secondary tier, moderate risk ($p1 \in [0.15, 0.35]$) |
| **DELAY_SETTLEMENT** | 0.90 | 1.00 | ₹30.00 | ₹0.00 | High-risk secondary, moderate tertiary |
| **MANUAL_REVIEW** | 0.98 | 0.98 | ₹20.00 | ₹130.00 | High-value borderline cases (₹50K–₹100K) |
| **BLOCK_TRANSACTION** | 1.00 | 0.00 | ₹130.00 | ₹0.00 | Primary ring members, high $p1$ ($> 0.35$) |
| **RESTRICT_ACCOUNT** | 1.00 | 0.00 | ₹350.00 | ₹130.00 | Confirmed ring coordinator accounts |
| **FREEZE_RING** | 1.00 | 0.00 | ₹1,000.00 | ₹500.00 | Large coordinated abuse syndicates (5+ members) |

---

## 4. Policy Dynamics & Invariant Guarantees

1. **Monotonicity of Net Utility**:
   - As false positives are shifted from `BLOCK_TRANSACTION` (₹130 friction) to `STEP_UP_2FA` (₹15 friction) or `DELAY_SETTLEMENT` (₹30 friction), Benign Friction decreases sharply while preserving >85% fraud prevention efficacy.
2. **Blast Radius Bounding**:
   - `RESTRICT_ACCOUNT` and `FREEZE_RING` are gated by `HumanApprovalGate`, bounding the risk of automated mass false bans.
3. **Point-in-Time & Zero Leakage**:
   - Ground truth labels are referenced **strictly** in post-decision evaluation metrics computation (`_compute_simulation_metrics`), with zero visibility to `PolicyEngine` or `TransactionGate`.

---

## 5. Verification & Mathematical Proofs

All financial accounting identities are verified by automated tests in `tests/test_phase3_2.py`:
- `test_counterfactual_simulator_math`: Verifies exact closure of conservation of funds:
  $$\text{Gross Prevented} + \text{Uncaught Loss} \equiv \text{Total Abuse Volume}$$
- `test_counterfactual_simulator_policy_comparison`: Verifies that Policy D yields strictly lower false friction cost than Policy B blanket expansion.

---

**Status:** ✅ Simulation Model Verified  
**Ready for:** Validation Counterfactual Evaluation (Phase 3.3)
