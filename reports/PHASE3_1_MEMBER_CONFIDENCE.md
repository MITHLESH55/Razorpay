# PHASE 3.1 — MEMBER CONFIDENCE MODEL

**Status:** ✅ Implemented  
**Module:** `src/graph/member_confidence.py`  
**Schema Version:** 3.1.0  
**Date:** 2026-08-29  

---

## Executive Summary

The Member Confidence Model replaces Phase 2.2's binary ring membership expansion (all members flagged = 1) with a continuous, explainable confidence score in [0, 1] that categorizes members into PRIMARY, SECONDARY, and TERTIARY tiers.

**Problem Solved:**  
Phase 2.2 flagged all 2-hop connected accounts equally, causing 75.77% FPR (21,443 false positives, ₹27.87L cost) despite 79.17% ring recall. Weak connections (shared office IP, multi-user devices) triggered blanket blocking of legitimate transactions.

**Solution:**  
Multi-signal confidence scoring that distinguishes strong direct evidence (shared device + IP + instrument + temporal coordination) from weak indirect connections (single shared campus IP).

---

## Architecture

### Confidence Formula

```python
confidence_score = (
    0.25 × phase1_risk_score +       # Individual transaction risk
    0.20 × edge_diversity_score +    # Multi-signal corroboration
    0.20 × max_edge_strength +       # Strongest connection (hubness-corrected)
    0.15 × distance_factor +         # Graph proximity (1-hop vs 2-hop)
    0.10 × temporal_relevance +      # Recent activity weight
    0.10 × evidence_strength         # Evidence quality
)

# Bounded to [0, 1]
confidence_score = max(0.0, min(1.0, confidence_raw))
```

**Weights are validation-tunable** — Phase 3.1 provides the architecture; weight optimization happens in validation experiments.

---

## Tier Assignment

| Tier | Confidence Threshold | Interpretation | Gating Strategy |
|------|---------------------|----------------|-----------------|
| **PRIMARY** | ≥ 0.65 | Strong direct + contextual evidence | Composite scoring with Phase 1 floor |
| **SECONDARY** | 0.35 – 0.65 | Strong relational but weaker direct evidence | Require both relationship + transaction risk |
| **TERTIARY** | < 0.35 | Weak/indirect connection | No blanket blocking; Phase 1 threshold only |

**Key Principle:**  
Tertiary members (e.g., shared office IP only) are NEVER blanket-blocked. They require high individual transaction risk (Phase 1 ≥ 0.35) to be flagged.

---

## Component Breakdown

### 1. Phase 1 Risk Score (Weight: 0.25)

**Source:** Frozen Phase 1 LightGBM model (`artifacts/phase1/risk_model_v1.txt`)  
**Range:** [0, 1]  
**Purpose:** Individual transaction-level risk independent of graph context  

Customers with high Phase 1 scores are more likely to be true ring members even with moderate relational evidence.

---

### 2. Edge Diversity Score (Weight: 0.20)

**Source:** `src/graph/edge_diversity.py`  
**Range:** [0, 1]  
**Purpose:** Multi-signal corroboration across independent evidence families  

**Evidence Families:**
- **Connectivity:** Device, IP, Instrument (shared infrastructure)
- **Behavioral:** Temporal coordination, Merchant overlap
- **Outcome:** Refund coordination

**Scoring:**
```python
total_families = connectivity_count + behavioral_count + outcome_count
diversity_score = min(1.0, 0.15 × total_families + 0.05 × unique_edge_types)
```

**Example:**
- 1 signal (shared IP only): diversity ≈ 0.20
- 3 signals (device + IP + merchant): diversity ≈ 0.60
- 5+ signals (device + IP + instrument + merchant + temporal): diversity ≈ 0.90+

---

### 3. Max Edge Strength (Weight: 0.20)

**Source:** `src/graph/strength.py` (hubness-corrected)  
**Range:** [0, 1]  
**Purpose:** Strength of the strongest connecting relationship  

**Hubness Penalty:**
```python
penalty_IP = max(0.05, 1 / (1 + 0.35 × ln(1 + degree)))
penalty_DEVICE = max(0.10, 1 / (1 + 0.25 × ln(1 + degree)))
```

**Effect:**
- Private home device (2 users): strength ≈ 0.85
- Shared office IP (50+ users): strength ≈ 0.15
- Campus WiFi (200+ users): strength ≈ 0.08

---

### 4. Distance Factor (Weight: 0.15)

**Purpose:** Graph proximity penalty (closer = stronger evidence)  

| Distance | Factor | Interpretation |
|----------|--------|----------------|
| 0 (primary suspect) | 1.00 | Root of investigation |
| 1 (direct connection) | 1.00 | Direct shared entity |
| 2 (2-hop) | 0.70 | 30% penalty |
| 3+ | 0.40 | 60% penalty (should not occur with max_hops=2) |

---

### 5. Temporal Relevance (Weight: 0.10)

**Source:** Max edge strength (which includes recency scoring)  
**Range:** [0, 1]  
**Purpose:** Recent relationships are stronger evidence  

Relationships from 6+ months ago are discounted vs. activity within the last 30 days.

---

### 6. Evidence Strength (Weight: 0.10)

**Source:** Optional evidence records or edge diversity fallback  
**Range:** [0, 1]  
**Purpose:** Quality and grounding of supporting evidence  

When investigation agent provides grounded evidence records:
```python
evidence_strength = min(1.0, evidence_count × 0.15)
```

Fallback: uses edge_diversity_score as proxy.

---

## Point-in-Time Safety

**CRITICAL:** Member confidence computation is causally safe.

**Does NOT Access:**
- `abuse_label`
- `ring_id`
- `pattern_type`
- Future events (timestamp > `as_of_time`)

**Verified By:**
- `tests/test_phase3_1.py::test_member_confidence_no_abuse_label_access`
- Static source inspection of `src/graph/member_confidence.py`

---

## API

### Primary Function

```python
from src.graph.member_confidence import compute_member_confidence

confidence = compute_member_confidence(
    customer_id="CUST_12345",
    primary_suspect_id="CUST_PRIME",
    graph=networkx_graph,
    phase1_risk_score=0.65,
    graph_distance=1,
    as_of_time=datetime(2024, 10, 1),
    connected_entities=["DEV_001", "IP_456"],
    edge_strengths={"DEV_001": 0.85, "IP_456": 0.20},
    evidence_records=None,  # Optional
)

# Returns MemberConfidence dataclass:
# - confidence_score: float [0, 1]
# - tier: "PRIMARY" | "SECONDARY" | "TERTIARY"
# - phase1_risk: float
# - edge_diversity_score: float
# - max_edge_strength: float
# - graph_distance: int
# - confidence_components: dict (explainability)
```

### Batch Function

```python
from src.graph.member_confidence import compute_ring_member_confidences

confidences = compute_ring_member_confidences(
    primary_suspect_id="CUST_PRIME",
    member_customer_ids=["CUST_A", "CUST_B", "CUST_C"],
    graph=networkx_graph,
    phase1_scores={"CUST_A": 0.75, "CUST_B": 0.40, "CUST_C": 0.10},
    as_of_time=datetime(2024, 10, 1),
    max_hops=2,
)

# Returns: dict[customer_id, MemberConfidence]
```

---

## Examples

### Example 1: PRIMARY Tier — Strong Evidence

**Scenario:** Two customers share a private device, same IP (home network), overlapping merchants, high Phase 1 scores.

**Inputs:**
- `phase1_risk_score = 0.75`
- `edge_diversity_score = 0.65` (device + IP + merchant)
- `max_edge_strength = 0.85` (private device, 2 users)
- `distance_factor = 1.0` (direct connection)
- `temporal_relevance = 0.80` (recent activity)
- `evidence_strength = 0.60`

**Confidence Calculation:**
```
0.25×0.75 + 0.20×0.65 + 0.20×0.85 + 0.15×1.0 + 0.10×0.80 + 0.10×0.60
= 0.1875 + 0.13 + 0.17 + 0.15 + 0.08 + 0.06
= 0.7775
```

**Result:**  
- **Confidence:** 0.78  
- **Tier:** PRIMARY  
- **Interpretation:** Strong direct evidence; high confidence ring member  

---

### Example 2: TERTIARY Tier — Weak Shared IP Only

**Scenario:** Two customers share a campus IP (200+ users), no other connections, low Phase 1 scores.

**Inputs:**
- `phase1_risk_score = 0.10`
- `edge_diversity_score = 0.15` (single signal: IP only)
- `max_edge_strength = 0.08` (campus IP, 200+ users, heavy hubness penalty)
- `distance_factor = 0.70` (2-hop connection)
- `temporal_relevance = 0.10`
- `evidence_strength = 0.15`

**Confidence Calculation:**
```
0.25×0.10 + 0.20×0.15 + 0.20×0.08 + 0.15×0.70 + 0.10×0.10 + 0.10×0.15
= 0.025 + 0.03 + 0.016 + 0.105 + 0.01 + 0.015
= 0.201
```

**Result:**  
- **Confidence:** 0.20  
- **Tier:** TERTIARY  
- **Interpretation:** Weak indirect connection; hard negative protection active  

**Gating Decision:** This customer's transactions will NOT be blanket-blocked. Each transaction requires individual Phase 1 risk ≥ 0.35 to be flagged.

---

### Example 3: SECONDARY Tier — Moderate Evidence

**Scenario:** Shared device (multi-user), weak IP connection, moderate Phase 1 score.

**Inputs:**
- `phase1_risk_score = 0.45`
- `edge_diversity_score = 0.35` (device + IP, weak overlap)
- `max_edge_strength = 0.50` (multi-user device, moderate hubness)
- `distance_factor = 1.0`
- `temporal_relevance = 0.50`
- `evidence_strength = 0.35`

**Confidence Calculation:**
```
0.25×0.45 + 0.20×0.35 + 0.20×0.50 + 0.15×1.0 + 0.10×0.50 + 0.10×0.35
= 0.1125 + 0.07 + 0.10 + 0.15 + 0.05 + 0.035
= 0.5175
```

**Result:**  
- **Confidence:** 0.52  
- **Tier:** SECONDARY  
- **Interpretation:** Moderate relational evidence  

**Gating Decision:** Requires BOTH composite score ≥ 0.35 AND Phase 1 ≥ 0.15 to flag transactions.

---

## Determinism & Reproducibility

**Guaranteed Properties:**
1. **Deterministic:** Same inputs → same confidence score (no randomness, no timestamps in formula)
2. **Bounded:** Output always in [0, 1]
3. **Monotonic Components:** Higher input signals → higher confidence
4. **Explainable:** Component breakdown available in `confidence_components` dict

**Test Coverage:**
- `test_member_confidence_deterministic()` — Verifies identical outputs for repeated calls
- `test_member_confidence_bounded()` — Verifies [0, 1] range with extreme inputs
- `test_member_confidence_distance_penalty()` — Verifies distance monotonicity

---

## Validation Tuning

**Parameters Open for Validation Tuning:**

| Parameter | Phase 3.1 Default | Tuning Range | Purpose |
|-----------|-------------------|--------------|---------|
| `w_phase1` | 0.25 | [0.20, 0.40] | Weight for transaction risk |
| `w_diversity` | 0.20 | [0.15, 0.30] | Weight for multi-signal corroboration |
| `w_strength` | 0.20 | [0.15, 0.30] | Weight for edge strength |
| `w_distance` | 0.15 | [0.10, 0.20] | Weight for graph proximity |
| `w_temporal` | 0.10 | [0.05, 0.15] | Weight for recency |
| `w_evidence` | 0.10 | [0.05, 0.15] | Weight for evidence quality |
| `PRIMARY_THRESHOLD` | 0.65 | [0.60, 0.75] | Tier threshold |
| `SECONDARY_THRESHOLD` | 0.35 | [0.30, 0.45] | Tier threshold |

**Validation Objective:**  
Maximize ring recall while minimizing FPR on validation set. Grid search or Bayesian optimization over weight space.

**Constraints:**
- Weights must sum to 1.0
- PRIMARY_THRESHOLD > SECONDARY_THRESHOLD
- No held-out test set access during tuning

---

## Integration with Transaction Gating

Member confidence feeds directly into `src/decision/transaction_gate.py`:

```python
gate = TransactionGate()
decision = gate.evaluate_transaction(
    transaction_id="TXN_001",
    customer_id="CUST_12345",
    phase1_score=0.40,
    member_confidence=confidence,  # MemberConfidence object
)

# Decision combines:
# - phase1_score (transaction risk)
# - member_confidence.confidence_score (ring membership strength)
# - member_confidence.max_edge_strength (relationship quality)
# - member_confidence.edge_diversity_score (multi-signal corroboration)
```

See `reports/PHASE3_1_GATING_DESIGN.md` for full gating logic.

---

## Limitations & Future Work

### Current Limitations

1. **Static Weights:** Formula uses fixed weights; validation experiments will optimize these.
2. **Linear Combination:** Simple weighted sum; non-linear interactions (e.g., high diversity + low strength) not modeled.
3. **No Temporal Decay Tuning:** Recency penalty is fixed in edge strength; not separately tunable.
4. **Evidence Records Optional:** When investigation agent doesn't provide evidence, falls back to diversity proxy.

### Phase 3.2+ Enhancements

1. **Learned Confidence Model:** Replace hand-crafted formula with gradient-boosted meta-model trained on validation member → ground-truth outcomes.
2. **Adversarial Robustness:** Add penalty for patterns matching known hard negatives (household sharing, office networks).
3. **Time-Decay Curves:** Separately tunable temporal decay for different relationship types (device vs. IP vs. merchant).
4. **Cross-Ring Confidence:** Penalty for customers connected to multiple distinct rings (potential false positive).

---

## Testing

**Test Suite:** `tests/test_phase3_1.py`

**Coverage:**

| Test | Purpose |
|------|---------|
| `test_member_confidence_high_risk_close_distance` | Verifies high confidence for strong evidence |
| `test_member_confidence_low_risk_weak_edges` | Verifies low confidence for weak evidence |
| `test_member_confidence_bounded` | Verifies [0, 1] range |
| `test_member_confidence_deterministic` | Verifies repeatability |
| `test_member_confidence_distance_penalty` | Verifies distance monotonicity |
| `test_filter_members_by_tier` | Verifies tier filtering logic |
| `test_member_confidence_no_abuse_label_access` | **LEAKAGE GUARD:** Verifies no ground-truth access |

**Run Tests:**
```bash
pytest tests/test_phase3_1.py -k member_confidence -v
```

**Result:** 11/11 passing ✅

---

## References

- **Implementation:** `src/graph/member_confidence.py`
- **Edge Diversity:** `reports/PHASE3_1_EDGE_DIVERSITY.md`
- **Transaction Gating:** `reports/PHASE3_1_GATING_DESIGN.md`
- **Phase 2.2 Baseline:** `reports/PHASE2_2_EVALUATION_SUMMARY.md`
- **Metric Audit:** `reports/METRIC_INTEGRITY_EXECUTIVE_SUMMARY.md`

---

**Status:** ✅ Implemented, Tested, Ready for Validation Experiments  
**Next Step:** Run validation weight ablation study (`scripts/phase3_1_validation_experiment.py`)
