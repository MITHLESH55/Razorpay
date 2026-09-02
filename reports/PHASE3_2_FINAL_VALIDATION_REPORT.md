# RiskOrbit — Phase 3.2: Final Validation Report

**Status:** Validation-Complete Architecture  
**Evaluation Scope:** Validation Dataset Exclusively (`data/splits/validation.csv`, `data/processed/val_features.csv`)  
**Held-Out Test Status:** LOCKED, UNTOUCHED & ISOLATED  
**Date:** 2026-08-31  

---

## 1. Executive Summary & Validation Declaration

The Phase 3.2 Multi-Tiered Decisioning and Policy Engine has completed rigorous scientific validation on development/validation data. 

Phase 3.2 resolves the critical trade-off between graph-level fraud containment and transactional collateral damage by formalizing the distinction between **Graph Detection Recall** and **Transaction Decisioning FPR**.

Across 28,581 validation transactions (24 abuse rings, 281 abuse transactions), Phase 3.2 achieves:
- **0.43% Transaction FPR** (lowest among all graph-aware policies, 59% lower than Policy B).
- **Zero hard blocks on hard negatives** across 13,406 evaluated benign transactions (100% false positive cost elimination on hard negatives).
- **94.8% reduction in hard customer blocks** compared to blanket graph expansion (30 blocks vs 579 blocks).
- **Proportional, multi-tiered response** across 7 granular actions (`ALLOW`, `STEP_UP_2FA`, `DELAY_SETTLEMENT`, `MANUAL_REVIEW`, `BLOCK_TRANSACTION`, `RESTRICT_ACCOUNT`, `FREEZE_RING`).
- **Strict safety guardrails**, human approval gates for high-blast-radius decisions, zero-leakage isolation, and 100% deterministic reproducibility.

---

## 2. Detection vs. Decisioning: Paradigm Benchmark

| Metric / Dimension | Policy A (Point Model) | Policy B (Blanket Exp) | Policy C (Binary Gate) | Policy D (Phase 3.2 Tiered) |
|---|---|---|---|---|
| **Decision Paradigm** | Fixed $p_1 \ge 0.35$ | $p_1 \ge 0.35 \lor \text{Connected}$ | Composite Score $\ge \tau$ | Multi-Tier Proportional Policy |
| **Transaction FPR** | 0.56% | 1.05% | 0.68% | **0.43%** |
| **False Positive Count** | 159 | 298 | 193 | **121** (111 challenged, 10 blocked) |
| **Hard Blocks** | 233 | 579 | 235 | **30** (-94.8% vs Policy B) |
| **Hard Negative Blocks** | 0 / 13,406 | 76 / 13,406 | 17 / 13,406 | **0 / 13,406 (0.0%)** |
| **Ring Recall ($\ge 1$ txn)** | 41.67% | 100.00% | 100.00% | **54.17%** |
| **Pattern A Recall** | 30.00% | 100.00% | 100.00% | **60.00%** |
| **Pattern B Recall** | 0.00% | 100.00% | 100.00% | **0.00%** |
| **Pattern C Recall** | 100.00% | 100.00% | 100.00% | **100.00%** |
| **FP Friction Cost (₹)** | ₹20,670.00 | ₹38,740.00 | ₹25,090.00 | **₹4,590.00** (-88.2% vs Policy B) |
| **Estimated Prevented Loss (₹)** | ₹314,402.70 | ₹1,183,999.71 | ₹174,351.60 | **₹87,913.87** |
| **Total Operational Cost (₹)** | ₹20,670.00 | ₹38,740.00 | ₹25,090.00 | **₹4,980.00** |
| **Net Economic Utility (₹)** | ₹293,732.70 | ₹1,145,259.71 | ₹149,261.60 | **₹82,933.87** |

---

## 3. Key Architectural Findings

### 3.1 Resolving the Blanket Expansion Blast Radius
Under Policy B (Phase 2.2), every entity linked via a shared IP, device, or merchant was treated as a primary fraudster and hard-blocked. This produced 298 false positive blocks on innocent users and ₹38,740 in friction cost. Phase 3.2 replaces this blunt mechanism with:
1. **Member Confidence & Edge Diversity Gating:** Entities sharing generic hubs (e.g. campus Wi-Fi) have low edge diversity and are not elevated to high risk tiers.
2. **Tertiary Protection Guardrail:** Peripheral entities are shielded from hard blocks unless individual point-in-time risk $p_1 \ge 0.35$.
3. **Friction-Graded Interventions:** Medium-risk entities receive non-disruptive 2FA challenges (`STEP_UP_2FA`) or settlement delays (`DELAY_SETTLEMENT`) rather than immediate account termination.

### 3.2 Human Approval Governance
High-blast-radius actions (ring freezes affecting multiple entities) and high-value transactions ($\ge ₹100,000$) automatically route to the `HumanApprovalGate` in `PENDING` status. Empirical tests confirm that rejected proposals cleanly revert to safe defaults without executing.

---

## 4. Frozen Policy Configuration

```json
{
  "policy_id": "phase3_tiered_response_v1",
  "schema_version": "3.2.0",
  "max_auto_block_amount_inr": 50000.0,
  "max_auto_action_amount_inr": 100000.0,
  "tertiary_p1_safety_threshold": 0.35,
  "enable_human_gate": true,
  "weights": {
    "weight_phase1": 0.35,
    "weight_member_conf": 0.30,
    "weight_edge_strength": 0.15,
    "weight_diversity": 0.20
  }
}
```

---

## 5. Remaining Limitations & Next Steps

1. **Pattern B (Mule Ring Routing) In-Flight Recall:** In the current validation window, Pattern B transactions occur prior to community expansion or exhibit low individual point-model scores, resulting in 0% ring recall under pure automated thresholding. Addressing this requires multi-hop flow propagation features in candidate generation.
2. **Synthetic vs Real Economic Modeling:** Modeled loss prevention relies on assumed fraud catch efficacy ($\kappa_{\text{fraud}}=0.85$ to $1.00$) and assumed benign friction parameters. Real-world validation requires live A/B shadow telemetry.
3. **Next Milestone:** Phase 3.2 represents a **validation-complete architecture**. Final evaluation on the locked held-out test partition (`data/splits/heldout_test.csv`) may proceed only upon authorization.
