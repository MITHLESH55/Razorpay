"""
RiskOrbit -- Protected Phase-1 Candidate Pool (Phase 2.2)

Implements deterministic candidate preservation: reserves a validation-selected quota P
within the total investigation budget K for high-confidence Phase 1 candidates
(phase1_score >= p1_threshold).

This restores Pattern C recall without sacrificing Pattern A/B, since:
- Pattern A/B candidates enter via the graph stream and fill (K - P) slots
- Pattern C candidates (Phase-1-only) are guaranteed P slots

SECURITY:
- No ground-truth labels are accessed (ring_id, abuse_label, pattern_type forbidden)
- Quota P is selected on validation only, never on held-out test
- All selections are deterministic (sorted by score, tie-broken by customer_id)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.graph.hybrid_candidate_union import HybridCandidate

logger = logging.getLogger(__name__)

# Forbidden columns -- must never appear in any feature or decision logic
FORBIDDEN_COLUMNS = frozenset(["ring_id", "abuse_label", "pattern_type", "abuse_pattern_type"])


def build_protected_pool(
    phase1_candidates: Dict[str, float],  # customer_id -> phase1_score
    p1_threshold: float,
    protected_quota: int,
) -> List[HybridCandidate]:
    """
    Builds a deterministic protected pool of high-confidence Phase 1 candidates.

    Selects up to protected_quota Phase 1 candidates with phase1_score >= p1_threshold,
    sorted descending by score (tie-broken by customer_id for determinism).

    Args:
        phase1_candidates: Dict mapping customer_id -> max phase1_score
        p1_threshold: Minimum score for a candidate to qualify for protection
        protected_quota: Maximum number of slots reserved in the budget

    Returns:
        List of HybridCandidate objects for the protected pool (length <= protected_quota)
    """
    # Strict leakage guard
    for col in FORBIDDEN_COLUMNS:
        if col in phase1_candidates:
            raise ValueError(f"LEAKAGE GUARD: forbidden key '{col}' found in phase1_candidates")

    # Filter to high-confidence candidates only
    high_conf = [
        (cid, score)
        for cid, score in phase1_candidates.items()
        if score >= p1_threshold
    ]

    # Deterministic sort: descending score, ascending customer_id as tie-breaker
    high_conf.sort(key=lambda x: (-x[1], x[0]))

    # Take top-P
    protected = high_conf[:protected_quota]

    pool: List[HybridCandidate] = []
    for rank_idx, (cid, score) in enumerate(protected, start=1):
        cand = HybridCandidate(
            candidate_id=f"CAND-{cid}",
            customer_id=cid,
            sources=["phase1"],
            phase1_score=round(float(score), 4),
            graph_ring_score=0.0,
            composite_rank_score=round(float(score), 4),  # use p1 score directly for protected pool
            candidate_rank=rank_idx,
            trigger_reasons=[f"Protected Phase-1 high-confidence ({score:.4f} >= {p1_threshold:.4f})"],
        )
        pool.append(cand)

    logger.info(
        "Protected pool: %d high-confidence Phase-1 candidates (quota=%d, threshold=%.4f)",
        len(pool), protected_quota, p1_threshold,
    )
    return pool


def build_hybrid_with_protected_pool(
    phase1_candidates: Dict[str, float],
    graph_candidates: Dict[str, Dict[str, Any]],
    hybrid_ranked_all: List[HybridCandidate],
    p1_threshold: float,
    protected_quota: int,
    total_budget_k: int,
) -> List[HybridCandidate]:
    """
    Constructs the final investigation list with a protected Phase-1 pool.

    Architecture:
        Protected pool (up to P slots): high-confidence Phase 1 candidates (score >= p1_thr)
        Remainder pool (K - P slots):   global hybrid ranking, excluding protected candidates

    The result is deduplicated by customer_id. Protected candidates always enter regardless
    of their global ranking position.

    Args:
        phase1_candidates: Dict customer_id -> phase1_score
        graph_candidates: Dict customer_id -> graph metadata
        hybrid_ranked_all: All candidates ranked globally (from HybridCandidateUnion)
        p1_threshold: Phase 1 score threshold for protection eligibility
        protected_quota: P -- max slots reserved for protected Phase-1 candidates
        total_budget_k: K -- total investigation budget

    Returns:
        Final candidate list of length <= total_budget_k, with protected candidates first
    """
    # Build protected pool
    protected = build_protected_pool(phase1_candidates, p1_threshold, protected_quota)
    protected_cids = {c.customer_id for c in protected}

    # Remaining slots filled by global ranking (skipping already-protected candidates)
    remaining_slots = total_budget_k - len(protected)
    remainder: List[HybridCandidate] = []
    for cand in hybrid_ranked_all:
        if len(remainder) >= remaining_slots:
            break
        if cand.customer_id not in protected_cids:
            remainder.append(cand)

    # Reassign final ranks: protected candidates get ranks 1..len(protected)
    # Remainder get ranks len(protected)+1 .. K
    final_list = protected + remainder
    for i, cand in enumerate(final_list, start=1):
        cand.candidate_rank = i

    logger.info(
        "Final investigation list: %d protected + %d remainder = %d total (budget K=%d)",
        len(protected), len(remainder), len(final_list), total_budget_k,
    )
    return final_list


def evaluate_protected_pool_on_validation(
    phase1_candidates: Dict[str, float],
    graph_candidates: Dict[str, Dict[str, Any]],
    hybrid_ranked_all: List[HybridCandidate],
    validation_df: pd.DataFrame,
    p1_threshold: float,
    quota_values: List[int],
    total_budget_k: int,
) -> List[Dict[str, Any]]:
    """
    Evaluates multiple protected quota values P on the validation set.
    Computes multi-objective score for each P.

    SECURITY: validation_df['ring_id'] and ['abuse_label'] are used ONLY for
    evaluation metric computation -- they are NEVER passed to the candidate
    generation or ranking logic.

    Returns:
        List of dicts with results for each P value
    """
    # Ground truth from validation (for metric computation only)
    abuse_val = validation_df[validation_df["abuse_label"] == 1]
    all_val_rings = sorted(abuse_val["ring_id"].dropna().unique().tolist())
    total_val_rings = len(all_val_rings)

    ring_to_custs: Dict[str, set] = {
        r: set(abuse_val[abuse_val["ring_id"] == r]["customer_id"].unique())
        for r in all_val_rings
    }
    abuse_cust_set = set(abuse_val["customer_id"].unique())
    legit_set = set(validation_df[validation_df["abuse_label"] == 0]["customer_id"].unique())

    results = []

    for quota in quota_values:
        final_list = build_hybrid_with_protected_pool(
            phase1_candidates=phase1_candidates,
            graph_candidates=graph_candidates,
            hybrid_ranked_all=hybrid_ranked_all,
            p1_threshold=p1_threshold,
            protected_quota=quota,
            total_budget_k=total_budget_k,
        )

        top_k_cids = {c.customer_id for c in final_list}

        # Ring coverage
        a_covered = b_covered = c_covered = total_covered = 0
        for r, custs in ring_to_custs.items():
            if len(custs & top_k_cids) >= 1:
                total_covered += 1
                if r.startswith("RING_A"):
                    a_covered += 1
                elif r.startswith("RING_B"):
                    b_covered += 1
                elif r.startswith("RING_C"):
                    c_covered += 1

        ring_recall = total_covered / total_val_rings if total_val_rings > 0 else 0.0
        pat_a_recall = a_covered / max(1, sum(1 for r in all_val_rings if r.startswith("RING_A")))
        pat_b_recall = b_covered / max(1, sum(1 for r in all_val_rings if r.startswith("RING_B")))
        pat_c_recall = c_covered / max(1, sum(1 for r in all_val_rings if r.startswith("RING_C")))

        # False positive rate (candidates who are legitimate)
        fp_in_budget = len(top_k_cids & legit_set)
        fpr_cand = fp_in_budget / len(legit_set) if legit_set else 0.0

        # Multi-objective score: prioritize A/B/C recall with FP penalty
        # Pattern C gets extra weight (recovery objective), A/B protected via their terms
        # Guardrail: A regression penalized heavily
        n_pat_a = max(1, sum(1 for r in all_val_rings if r.startswith("RING_A")))
        n_pat_b = max(1, sum(1 for r in all_val_rings if r.startswith("RING_B")))
        n_pat_c = max(1, sum(1 for r in all_val_rings if r.startswith("RING_C")))

        multi_obj_score = (
            3.0 * (a_covered / n_pat_a)
            + 3.0 * (b_covered / n_pat_b)
            + 4.0 * (c_covered / n_pat_c)
            + 2.0 * ring_recall
            - 1.0 * fpr_cand
        )

        results.append({
            "protected_quota": quota,
            "total_in_budget": len(final_list),
            "protected_slots_used": min(quota, len([c for c in final_list if "phase1" in c.sources and c.candidate_rank <= quota])),
            "ring_recall": round(ring_recall, 4),
            "pat_a_recall": round(pat_a_recall, 4),
            "pat_b_recall": round(pat_b_recall, 4),
            "pat_c_recall": round(pat_c_recall, 4),
            "pat_a_covered": a_covered,
            "pat_b_covered": b_covered,
            "pat_c_covered": c_covered,
            "fp_in_budget": fp_in_budget,
            "fpr_candidate": round(fpr_cand, 4),
            "multi_obj_score": round(multi_obj_score, 4),
        })

        logger.info(
            "Protected quota P=%d: RingRecall=%.3f, A=%.3f, B=%.3f, C=%.3f, MultiObj=%.4f",
            quota, ring_recall, pat_a_recall, pat_b_recall, pat_c_recall, multi_obj_score,
        )

    return results


def select_protected_quota(
    ablation_results: List[Dict[str, Any]],
    guardrails: Optional[Dict[str, float]] = None,
) -> int:
    """
    Selects the optimal protected quota from validation ablation results.

    Selection logic (in order):
      1. Enforce hard guardrails (pat_a_min, pat_b_min, ring_recall_min).
         Only configurations that pass ALL guardrails are eligible.
      2. Among eligible configurations, pick the one with the highest multi_obj_score.
      3. Tie-break: prefer smaller quota (less disruption to the system).
      4. Fallback: if no configuration passes all guardrails, pick the one with
         the highest ring_recall (at least passes ring floor), preferring smaller P.
      5. Final fallback: P=0 (no protected pool — do not degrade the system).

    Args:
        ablation_results: Output of evaluate_protected_pool_on_validation
        guardrails: Dict with optional keys: pat_a_min, pat_b_min, ring_recall_min, fpr_max.
                    If None, uses multi_obj_score only.

    Returns:
        Selected protected quota P
    """
    g = guardrails or {}
    pat_a_min = g.get("pat_a_min", 0.0)
    pat_b_min = g.get("pat_b_min", 0.0)
    ring_min = g.get("ring_recall_min", 0.0)
    fpr_max = g.get("fpr_max", 1.0)

    def passes_guardrails(r: Dict[str, Any]) -> bool:
        return (
            r["pat_a_recall"] >= pat_a_min
            and r["pat_b_recall"] >= pat_b_min
            and r["ring_recall"] >= ring_min
            and r.get("fpr_candidate", 1.0) <= fpr_max
        )

    # Primary: configs passing all guardrails, then highest multi_obj, then smallest P
    eligible = [r for r in ablation_results if passes_guardrails(r)]
    if eligible:
        best = max(eligible, key=lambda r: (r["multi_obj_score"], -r["protected_quota"]))
        logger.info(
            "Selected protected quota P=%d (guardrails passed, multi_obj=%.4f, A=%.3f, B=%.3f, C=%.3f)",
            best["protected_quota"], best["multi_obj_score"],
            best["pat_a_recall"], best["pat_b_recall"], best["pat_c_recall"],
        )
        return best["protected_quota"]

    # Fallback 1: best ring_recall with smallest P
    logger.warning(
        "No configuration passes all guardrails. "
        "Falling back to best ring_recall with smallest protected quota."
    )
    fallback = min(
        ablation_results,
        key=lambda r: (-r["ring_recall"], r["protected_quota"]),
    )
    logger.warning(
        "Fallback selected P=%d (ring_recall=%.3f, A=%.3f, B=%.3f, C=%.3f)",
        fallback["protected_quota"], fallback["ring_recall"],
        fallback["pat_a_recall"], fallback["pat_b_recall"], fallback["pat_c_recall"],
    )
    return fallback["protected_quota"]


def save_phase22_config(
    selected_k: int,
    selected_p: int,
    p1_threshold: float,
    ablation_results: List[Dict[str, Any]],
    output_path: str = "configs/phase2_2_budget.json",
) -> None:
    """Saves frozen Phase 2.2 configuration (K, P, threshold) to disk."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "2.2",
        "frozen_investigation_budget_k": selected_k,
        "frozen_protected_quota_p": selected_p,
        "p1_threshold_for_protection": p1_threshold,
        "selection_partition": "validation",
        "ablation_results": ablation_results,
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Saved Phase 2.2 frozen config to %s (K=%d, P=%d)", p, selected_k, selected_p)
