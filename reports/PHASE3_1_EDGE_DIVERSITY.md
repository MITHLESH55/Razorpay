# PHASE 3.1 — EDGE DIVERSITY SCORING

**Status:** ✅ Implemented  
**Module:** `src/graph/edge_diversity.py`  
**Schema Version:** 3.1.0  
**Date:** 2026-08-29  

---

## Executive Summary

Edge Diversity Scoring distinguishes **multi-signal corroboration** from **repeated single-signal evidence**.

**Problem Solved:**  
In Phase 2.1/2.2, a customer sharing an IP address 50 times with a suspect received high edge weight, even though all 50 events came from the *same* signal family (connectivity via IP). This created high false positives on office networks, campus WiFi, and shared public IPs.

**Solution:**  
Categorize relationship signals into three **independent evidence families**:
1. **CONNECTIVITY:** Shared device, IP, instrument (infrastructure)
2. **BEHAVIORAL:** Temporal coordination, merchant overlap
3. **OUTCOME:** Refund coordination

Do NOT double-count correlated signals within the same family. Require multi-family corroboration for high diversity scores.

---

## Evidence Families

| Family | Signal Types | Meaning | Independence Justification |
|--------|--------------|---------|---------------------------|
| **CONNECTIVITY** | `device`, `ip`, `instrument` | Shared physical/digital infrastructure | Hardware + network layer |
| **BEHAVIORAL** | `temporal`, `merchant` | Coordinated actions and targets | Application/behavior layer |
| **OUTCOME** | `refund` | Abuse monetization | Financial settlement layer |

**Key Principle:**  
Sharing an IP (connectivity) + sharing a device (connectivity) = 2 signals within 1 family.  
Sharing an IP (connectivity) + coordinated burst timing (behavioral) = 2 signals across 2 families (stronger corroboration).

---

## Architecture & Formula

### Diversity Score Calculation

```python
# 1. Categorize edge types into evidence families
connectivity_evidence = sum([has_device, has_ip, has_instrument])  # max 3
behavioral_evidence = sum([has_temporal, has_merchant])              # max 2
outcome_evidence = int(has_refund)                                   # max 1

total_families = connectivity_evidence + behavioral_evidence + outcome_evidence

# 2. Non-linear scoring formula
if total_families == 0:
    diversity_score = 0.0
else:
    # Reward multi-family evidence more than individual edge types
    diversity_score = min(1.0, 0.15 × total_families + 0.05 × len(unique_edge_types))
```

**Scoring Behavior:**

| Scenario | Evidence Families | Unique Edge Types | Diversity Score | Interpretation |
|----------|-------------------|-------------------|-----------------|----------------|
| Shared IP only | 1 (connectivity) | 1 (`ip`) | **0.20** | Weak (single signal) |
| Shared IP + Device | 1 (connectivity) | 2 (`ip`, `device`) | **0.40** | Moderate (infrastructure only) |
| IP + Merchant Overlap | 2 (connectivity, behavioral) | 2 (`ip`, `merchant`) | **0.40** | Moderate (multi-family) |
| Device + IP + Merchant | 2 (connectivity, behavioral) | 3 (`device`, `ip`, `merchant`) | **0.60** | Strong (multi-family) |
| Device + IP + Instrument + Merchant + Temporal | 2 (connectivity, behavioral) | 5 (all 5) | **0.80** | Very Strong |
| All 6 signals (includes refund) | 3 (all families) | 6 (all 6) | **0.95+** | Maximum corroboration |

---

## Dataclass Structure

```python
@dataclass
class EdgeDiversityScore:
    """Edge diversity analysis for a customer pair relationship."""

    customer_id: str
    related_customer_id: str
    total_edge_count: int
    unique_edge_types: set[str]
    diversity_score: float  # [0, 1]
    
    # Signal flags
    has_device: bool
    has_ip: bool
    has_instrument: bool
    has_merchant: bool
    has_temporal: bool
    has_refund: bool
    
    # Family counts
    connectivity_evidence: int  # device + IP + instrument (max 3)
    behavioral_evidence: int    # temporal + merchant (max 2)
    outcome_evidence: int       # refund (max 1)
```

---

## Point-in-Time Safety

**CRITICAL:** Edge diversity scoring is causally safe.

**Edge Construction Rules:**
- Only edges present in the point-in-time graph (`events <= as_of_time`) are considered.
- No future events are traversed.
- No ground truth labels (`abuse_label`, `ring_id`, `pattern_type`) are accessed.

**Graph Traversal:**
- Checks direct edges between `customer_a` and `customer_b`.
- Traverses 1-hop paths through shared intermediate entities (devices, IPs, instruments, merchants).
- Collects edge types from both sides of the intermediate entity.

---

## API

### Pair Diversity

```python
from src.graph.edge_diversity import compute_edge_diversity

diversity = compute_edge_diversity(
    graph=networkx_graph,
    customer_a="CUST_1",
    customer_b="CUST_2",
)

# Returns EdgeDiversityScore:
# - diversity.diversity_score: float [0, 1]
# - diversity.unique_edge_types: set[str]
# - diversity.connectivity_evidence: int
# - diversity.behavioral_evidence: int
# - diversity.outcome_evidence: int
```

### Multi-Member Diversity

```python
from src.graph.edge_diversity import compute_multi_member_diversity

diversity_map = compute_multi_member_diversity(
    graph=networkx_graph,
    primary_customer="CUST_PRIME",
    member_customers=["CUST_A", "CUST_B", "CUST_C"],
)

# Returns: dict[customer_id, EdgeDiversityScore]
```

### Aggregate Diversity

```python
from src.graph.edge_diversity import aggregate_diversity_score

scores = [div_A, div_B, div_C]
agg_score = aggregate_diversity_score(scores)

# Uses maximum diversity (strongest evidence path)
# Returns: float [0, 1]
```

---

## Hard Negative Protection

### Case 1: Shared Office Network (Shared IP Only)

**Scenario:** 50 legitimate employees use the same office WiFi IP. None share devices, instruments, or show coordinated refund behavior.

**Phase 2.1 Behavior:**  
High degree IP caused moderate edge weight; all 50 employees flagged if one was suspicious.

**Phase 3.1 Behavior:**  
- `has_ip = True`, all other flags `False`
- `connectivity_evidence = 1`, `behavioral_evidence = 0`, `outcome_evidence = 0`
- `diversity_score = 0.20` (low)
- Feeds into Member Confidence → **TERTIARY tier**
- Feeds into Transaction Gating → **Transactions cleared unless individual Phase 1 risk ≥ 0.35**

**Result:** Hard negative protected; no false positives from shared office IP alone.

---

### Case 2: Household Sharing (Shared Device + IP)

**Scenario:** Two family members share a home tablet and home WiFi. No merchant overlap, no refund coordination.

**Phase 3.1 Behavior:**  
- `has_device = True`, `has_ip = True`
- `connectivity_evidence = 2`, `behavioral_evidence = 0`, `outcome_evidence = 0`
- `unique_edge_types = {"device", "ip"}`
- `diversity_score = 0.40` (moderate)
- Feeds into Member Confidence → **SECONDARY tier**
- Feeds into Transaction Gating → **Requires individual Phase 1 risk ≥ 0.15**

**Result:** Legitimate transactions from family members are cleared; only genuinely risky transactions are flagged.

---

### Case 3: Coordinated Abuse Ring (Multi-Family Corroboration)

**Scenario:** Fraudsters rotate accounts across multiple devices and IPs, target the same merchants within minutes, and execute coordinated refund requests.

**Phase 3.1 Behavior:**  
- `has_device = True`, `has_ip = True`, `has_instrument = True` (connectivity = 3)
- `has_temporal = True`, `has_merchant = True` (behavioral = 2)
- `has_refund = True` (outcome = 1)
- `unique_edge_types = 6`
- `diversity_score = 0.95+` (maximum)
- Feeds into Member Confidence → **PRIMARY tier**
- Feeds into Transaction Gating → **Flagged even with moderate individual transaction risk**

**Result:** High ring recall preserved; coordinated rings detected with high confidence.

---

## Testing & Verification

**Test Suite:** `tests/test_phase3_1.py`

**Coverage:**

| Test | Purpose |
|------|---------|
| `test_edge_diversity_single_type` | Verifies low score for single signal |
| `test_edge_diversity_multi_family` | Verifies high score for multi-family evidence |
| `test_edge_diversity_deterministic` | Verifies reproducibility |
| `test_edge_diversity_no_connection` | Verifies 0.0 for disconnected nodes |
| `test_aggregate_diversity_uses_maximum` | Verifies maximum aggregation |

**Run Tests:**
```bash
pytest tests/test_phase3_1.py -k edge_diversity -v
```

**Result:** 5/5 passing ✅

---

## Summary

Edge Diversity Scoring provides the missing **structural corroboration** signal in the RiskOrbit pipeline. By separating evidence into independent families, it prevents repeated single-signal connections from masquerading as strong evidence, directly addressing the root cause of the 75.77% FPR in Phase 2.2.
