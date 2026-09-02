"""
RiskOrbit — Investigation Budget Selector (Phase 2.1)

Evaluates investigation workload budgets K on validation data only.
Freezes the operating budget K before any held-out evaluation.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.graph.hybrid_candidate_union import HybridCandidate

logger = logging.getLogger(__name__)


def select_investigation_budget(
    ranked_candidates: List[HybridCandidate],
    validation_df: pd.DataFrame,
    candidate_budgets: List[int] = None,
) -> Dict[str, Any]:
    """
    Evaluates investigation performance across multiple budget caps K on validation set.
    """
    if candidate_budgets is None:
        candidate_budgets = [50, 100, 250, 500, 1000]

    abuse_val = validation_df[validation_df["abuse_label"] == 1]
    all_val_rings = sorted(abuse_val["ring_id"].dropna().unique().tolist())
    total_val_rings = len(all_val_rings)

    # Map ring to customers
    ring_to_custs = {}
    for r in all_val_rings:
        ring_to_custs[r] = set(abuse_val[abuse_val["ring_id"] == r]["customer_id"].unique())

    abuse_cust_set = set(abuse_val["customer_id"].unique())

    ablation_results = []
    selected_k = candidate_budgets[0]
    best_score = -1.0

    for k in candidate_budgets:
        top_k = ranked_candidates[:k]
        top_k_cids = set(c.customer_id for c in top_k)

        # Abuse candidate precision
        true_abuse_cands = top_k_cids & abuse_cust_set
        precision = (len(true_abuse_cands) / k) if k > 0 else 0.0

        # Ring coverage
        covered_rings = 0
        a_covered, b_covered, c_covered = 0, 0, 0
        for r, custs in ring_to_custs.items():
            if len(custs & top_k_cids) >= 1:
                covered_rings += 1
                if r.startswith("RING_A"):
                    a_covered += 1
                elif r.startswith("RING_B"):
                    b_covered += 1
                elif r.startswith("RING_C"):
                    c_covered += 1

        ring_recall = (covered_rings / total_val_rings) if total_val_rings > 0 else 0.0

        res = {
            "budget_k": k,
            "investigated_candidates": len(top_k),
            "true_abuse_candidates": len(true_abuse_cands),
            "candidate_precision": round(float(precision), 4),
            "covered_rings": covered_rings,
            "total_val_rings": total_val_rings,
            "ring_recall": round(float(ring_recall), 4),
            "pattern_a_covered": a_covered,
            "pattern_b_covered": b_covered,
            "pattern_c_covered": c_covered,
        }
        ablation_results.append(res)

        # Selection heuristic: maximize ring recall while candidate precision is >= 0.5%
        # or best ring recall with lowest workload
        score = ring_recall * 10.0 + precision
        if score > best_score:
            best_score = score
            selected_k = k

    return {
        "selected_k": selected_k,
        "ablation_results": ablation_results,
    }


def save_frozen_budget_config(
    selected_k: int,
    ablation_summary: Dict[str, Any],
    output_path: Path | str = "configs/phase2_1_budget.json",
) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "2.1",
        "frozen_investigation_budget_k": selected_k,
        "selection_partition": "validation",
        "ablation_summary": ablation_summary,
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Saved frozen budget configuration to %s (K=%d)", p, selected_k)
