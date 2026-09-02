# PHASE 3.1 — TRANSACTION GATING DESIGN

**Status:** ✅ Implemented  
**Module:** `src/decision/transaction_gate.py`  
**Schema Version:** 3.1.0  
**Date:** 2026-08-29  

---

## Executive Summary

Transaction Gating is the core architectural mechanism in Phase 3.1 designed to decouple **ring membership detection** from **transaction-level blocking**.

**Core Principle:**  
A customer being identified as a ring member does **NOT** automatically mean every subsequent transaction from that account must be blocked.

Instead, the gate evaluates three questions simultaneously:
1. **Transaction Risk:** How risky is this specific transaction? (Phase 1 score)
2. **Relationship Strength:** How confident are we in the customer's ring membership? (Member confidence)
3. **Connecting Evidence:** How strong and diverse is the graph evidence? (Edge strength & diversity)

---

## Architecture & Scoring Formula

### Composite Decision Score

For transactions associated with a ring-connected customer:

```python
decision_score = (
    w_phase1 × phase1_score +
    w_member_conf × member_confidence_score +
    w_edge_strength × max_edge_strength +
    w_diversity × edge_diversity_score
)
```

**Default Weights (Validation-Tunable):**

| Component | Weight | Default | Description |
|-----------|--------|---------|-------------|
| `weight_phase1` | $w_{\text{p1}}$ | **0.40** | Individual transaction LightGBM risk score |
| `weight_member_conf` | $w_{\text{conf}}$ | **0.30** | Member confidence tier score |
| `weight_edge_strength` | $w_{\text{strength}}$ | **0.15** | Hubness-corrected max edge strength |
| `weight_diversity` | $w_{\text{div}}$ | **0.15** | Multi-signal edge diversity score |

*Weights must sum to 1.0.*

---

## Tier-Specific Gating Rules

| Tier | Gating Rule | Gating Rationale |
|------|-------------|------------------|
| **ISOLATED** (No ring context) | $\text{phase1} \ge 0.35$ | Standard transaction-level classifier decision |
| **PRIMARY** ($\text{conf} \ge 0.65$) | $\text{score} \ge 0.35$ **OR** ($\text{phase1} \ge 0.20 \land \text{conf} \ge 0.70$) | Primary suspects flagged on lower transaction threshold |
| **SECONDARY** ($0.35 \le \text{conf} < 0.65$) | $\text{score} \ge 0.35 \land \text{phase1} \ge 0.15$ | Requires both relationship corroboration AND non-zero transaction risk |
| **TERTIARY** ($\text{conf} < 0.35$) | $\text{phase1} \ge 0.35 \land \text{score} \ge 0.35$ | Weak connection; NEVER blanket-blocked; Phase 1 threshold enforced |

---

## Dataclass Structure

```python
@dataclass
class TransactionDecision:
    """Structured per-transaction decision assessment."""

    transaction_id: str
    customer_id: str
    decision_score: float        # [0, 1] Composite transaction decision score
    is_flagged: bool             # Whether transaction meets gating threshold
    confidence: float            # Overall confidence in decision
    tier: DecisionTier           # "PRIMARY" | "SECONDARY" | "TERTIARY" | "ISOLATED"

    # Component breakdown for explainability
    phase1_risk: float
    member_confidence: float
    max_edge_strength: float
    edge_diversity_score: float
    evidence_strength: float
    graph_distance: int

    # Explainability & Audit trail
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    component_scores: dict[str, float] = field(default_factory=dict)
    schema_version: str = "3.1.0"
```

---

## Comparison: Phase 2.2 vs. Phase 3.1 Decision Flow

```
Phase 2.2 (Account Blanket Blocking):
Candidate Discovery → 2-Hop Graph Expansion → Flag ALL transactions of connected accounts
                                               ↓
                                   [FPR = 75.77%, 21,443 FPs]

Phase 3.1 (Transaction-Level Gating):
Candidate Discovery → Confidence Scoring (PRIMARY / SECONDARY / TERTIARY)
                            ↓
             Transaction-Level Evaluation:
             ┌────────────────────────────────────────────────────────┐
             │ Score = 0.40(p1) + 0.30(conf) + 0.15(edge) + 0.15(div)  │
             └────────────────────────────────────────────────────────┘
                            ↓
             Tier-Specific Threshold Check:
             - PRIMARY: Flagged on composite or p1 >= 0.20
             - SECONDARY: Requires p1 >= 0.15 (clears benign txns)
             - TERTIARY: Requires p1 >= 0.35 (protects hard negatives)
             - ISOLATED: Uses standard p1 >= 0.35
                            ↓
             [Significantly Reduced FPR, Preserved Ring Recall]
```

---

## Explainability & Audit Trail

Every `TransactionDecision` generates human-readable and structured explainability metadata:

```json
{
  "transaction_id": "TXN_987654",
  "customer_id": "CUST_54321",
  "decision_score": 0.4850,
  "is_flagged": true,
  "tier": "SECONDARY",
  "phase1_risk": 0.3200,
  "member_confidence": 0.6200,
  "max_edge_strength": 0.7000,
  "edge_diversity_score": 0.5500,
  "graph_distance": 1,
  "reason": "SECONDARY ring member flagged with corroborating risk (composite=0.4850, p1=0.3200)",
  "component_scores": {
    "phase1_contribution": 0.1280,
    "member_conf_contribution": 0.1860,
    "edge_strength_contribution": 0.1050,
    "diversity_contribution": 0.0825
  },
  "schema_version": "3.1.0"
}
```

---

## Anti-Leakage & Safety Verification

1. **No Ground Truth Access:** The `TransactionGate` class source code contains zero references to `abuse_label`, `ring_id`, `pattern_type`, or `abuse_pattern_type`.
2. **Point-in-Time Causality:** Inputs to `evaluate_transaction` depend strictly on features and graphs computed with $t \le T_{\text{decision}}$.
3. **Weight Sum Invariant:** Initializer asserts $| \sum w_i - 1.0 | < 10^{-4}$, raising `ValueError` on malformed weight configurations.
4. **Deterministic Evaluation:** Identical inputs produce identical floating-point scores and boolean flags.

---

## Testing & Verification

**Test Suite:** `tests/test_phase3_1.py`

**Coverage:**

| Test | Purpose |
|------|---------|
| `test_transaction_gate_isolated_high_risk` | Verifies isolated high-risk transaction flagged |
| `test_transaction_gate_isolated_low_risk` | Verifies isolated low-risk transaction cleared |
| `test_transaction_gate_primary_member_high_risk` | Verifies primary member high-risk transaction flagged |
| `test_transaction_gate_secondary_member_low_risk` | Verifies secondary member benign transaction cleared |
| `test_transaction_gate_tertiary_member_cleared` | Verifies tertiary member cleared without blanket block |
| `test_transaction_gate_deterministic` | Verifies reproducibility |
| `test_transaction_gate_decision_score_bounded` | Verifies [0, 1] output range |
| `test_transaction_gate_weights_sum_to_one` | Enforces weight normalization invariant |
| `test_transaction_gate_hard_negative_shared_ip_only` | Verifies office network hard negative resilience |
| `test_transaction_gate_no_ground_truth_access` | **LEAKAGE GUARD:** Static verification of zero ground truth access |

**Run Tests:**
```bash
pytest tests/test_phase3_1.py -k transaction_gate -v
```

**Result:** 10/10 passing ✅
