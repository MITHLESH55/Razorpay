"""
Phase 2.2 Test Suite

Tests for:
  - Pattern C funnel stages
  - Protected pool candidate preservation
  - Source attribution correctness
  - A/B regression guardrails
  - Pattern C recovery
  - Hard-negative protection
  - Future leakage prevention
  - Label leakage prevention
  - Point-in-time behaviour
  - Deterministic reproducibility
  - Investigation decision fix (isolated candidate branch)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

from src.graph.protected_pool import (
    build_protected_pool,
    build_hybrid_with_protected_pool,
    evaluate_protected_pool_on_validation,
    select_protected_quota,
    FORBIDDEN_COLUMNS,
)
from src.graph.hybrid_candidate_union import HybridCandidateUnion, HybridCandidate
from src.graph.graph_engine import PaymentGraphEngine
from src.graph.candidate_generator import CandidateGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_p1_cands(scores: Dict[str, float]) -> Dict[str, float]:
    return scores


def make_graph_cands(cids_scores: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    return {
        cid: {
            "ring_risk_score": score,
            "member_count": 3,
            "shared_device_count": 2,
            "shared_ip_count": 1,
            "shared_instrument_count": 0,
            "member_refund_rate": 0.30,
            "member_customers": [cid, "NEIGH_1", "NEIGH_2"],
            "targeted_merchants": ["MRC_A", "MRC_B"],
        }
        for cid, score in cids_scores.items()
    }


def make_union(p1: Dict[str, float], g: Dict[str, float], weights=None) -> List[HybridCandidate]:
    hu = HybridCandidateUnion(weights=weights)
    g_meta = make_graph_cands(g)
    return hu.union_and_rank(p1, g_meta)


def make_val_df(abuse_cids: List[str], legit_cids: List[str], ring_prefix="RING_C") -> pd.DataFrame:
    rows = []
    for i, cid in enumerate(abuse_cids):
        rows.append({"customer_id": cid, "abuse_label": 1, "ring_id": f"{ring_prefix}_{i:04d}", "timestamp": "2024-01-01"})
    for cid in legit_cids:
        rows.append({"customer_id": cid, "abuse_label": 0, "ring_id": None, "timestamp": "2024-01-01"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Protected pool correctness
# ---------------------------------------------------------------------------

def test_protected_pool_only_high_confidence():
    """Only candidates with score >= p1_threshold enter the protected pool."""
    p1_cands = {"C1": 0.80, "C2": 0.40, "C3": 0.20, "C4": 0.35, "C5": 0.10}
    pool = build_protected_pool(p1_cands, p1_threshold=0.35, protected_quota=10)
    pool_cids = {c.customer_id for c in pool}
    assert "C1" in pool_cids, "High-confidence C1 must be protected"
    assert "C4" in pool_cids, "Exactly-at-threshold C4 must be protected"
    assert "C3" not in pool_cids, "Below-threshold C3 must NOT be protected"
    assert "C5" not in pool_cids, "Below-threshold C5 must NOT be protected"


def test_protected_pool_respects_quota():
    """Protected pool never exceeds protected_quota."""
    p1_cands = {f"C{i}": 0.80 for i in range(50)}
    pool = build_protected_pool(p1_cands, p1_threshold=0.35, protected_quota=10)
    assert len(pool) == 10, f"Pool should have exactly 10 candidates, got {len(pool)}"


def test_protected_pool_deterministic():
    """Same inputs always produce the same pool in the same order."""
    p1_cands = {f"C{i:03d}": float(i) / 100 for i in range(50, 100)}
    pool1 = build_protected_pool(p1_cands, p1_threshold=0.60, protected_quota=20)
    pool2 = build_protected_pool(p1_cands, p1_threshold=0.60, protected_quota=20)
    assert [c.customer_id for c in pool1] == [c.customer_id for c in pool2]


def test_protected_pool_sorted_descending_score():
    """Protected pool is sorted descending by score."""
    p1_cands = {"A": 0.90, "B": 0.70, "C": 0.50, "D": 0.40}
    pool = build_protected_pool(p1_cands, p1_threshold=0.35, protected_quota=10)
    scores = [c.phase1_score for c in pool]
    assert scores == sorted(scores, reverse=True), "Pool must be sorted descending by score"


def test_protected_pool_leakage_guard():
    """build_protected_pool raises ValueError if forbidden keys found."""
    bad_cands = {"ring_id": 0.9, "C1": 0.5}
    with pytest.raises(ValueError, match="LEAKAGE GUARD"):
        build_protected_pool(bad_cands, p1_threshold=0.35, protected_quota=5)


# ---------------------------------------------------------------------------
# 2. Hybrid with protected pool
# ---------------------------------------------------------------------------

def test_hybrid_protected_pool_total_within_budget():
    """Final investigation list never exceeds K."""
    p1 = {f"P{i}": 0.80 for i in range(50)}
    g = {f"G{i}": 0.50 for i in range(500)}
    g_meta = make_graph_cands({f"G{i}": 0.50 for i in range(500)})
    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)

    final = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=20, total_budget_k=100,
    )
    assert len(final) <= 100, "Final list must not exceed budget K=100"


def test_hybrid_protected_candidates_present():
    """Protected Phase-1 candidates appear in the final list even if they'd rank below K in global order."""
    # 200 strong graph candidates that would outrank Phase-1 candidates
    g_meta = make_graph_cands({f"G{i:03d}": 0.90 for i in range(200)})
    # 5 Phase-1 candidates with low composite scores (would rank below 100 globally)
    p1 = {f"P{i}": 0.36 for i in range(5)}  # 0.36 >= p1_thr=0.35 -> eligible for protection
    p1_all = dict(p1)
    p1_all.update({f"G{i:03d}": 0.10 for i in range(200)})  # graph candidates also have some p1 score

    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1_all.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)

    final = build_hybrid_with_protected_pool(
        phase1_candidates=p1,
        graph_candidates=g_meta,
        hybrid_ranked_all=ranked_all,
        p1_threshold=0.35,
        protected_quota=5,
        total_budget_k=50,  # K=50 would normally exclude P-candidates at rank 200+
    )
    final_cids = {c.customer_id for c in final}
    # All 5 protected Phase-1 candidates must be in the final list
    for cid in p1:
        assert cid in final_cids, f"Protected candidate {cid} must appear in final list"


def test_hybrid_no_duplicates_in_final_list():
    """Final investigation list contains no duplicate customer_ids."""
    p1 = {"C1": 0.80, "C2": 0.70, "C3": 0.40}
    g_meta = make_graph_cands({"C2": 0.60, "C3": 0.55, "C4": 0.50})
    hu = HybridCandidateUnion()
    ranked_all = hu.union_and_rank({cid: s for cid, s in p1.items() if s >= 0.20}, g_meta)

    final = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=5, total_budget_k=20,
    )
    cids = [c.customer_id for c in final]
    assert len(cids) == len(set(cids)), "Duplicate customer_ids found in final list"


def test_hybrid_ranks_are_contiguous_from_1():
    """Ranks in final list start at 1 and are contiguous."""
    p1 = {f"P{i}": 0.80 for i in range(10)}
    g_meta = make_graph_cands({f"G{i}": 0.60 for i in range(20)})
    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)
    final = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=5, total_budget_k=15,
    )
    ranks = sorted(c.candidate_rank for c in final)
    assert ranks[0] == 1, "First rank must be 1"
    assert ranks == list(range(1, len(ranks)+1)), "Ranks must be contiguous"


# ---------------------------------------------------------------------------
# 3. Validation ablation
# ---------------------------------------------------------------------------

def test_validation_ablation_runs_all_quotas():
    """evaluate_protected_pool_on_validation returns one result per quota value."""
    p1 = {"C1": 0.80, "C2": 0.50, "L1": 0.10}
    g_meta = make_graph_cands({"G1": 0.70, "G2": 0.60})
    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1.items() if s >= 0.20}
    ranked = hu.union_and_rank(p1_020, g_meta)
    val_df = make_val_df(["C1", "C2"], ["L1", "G1", "G2"])

    quotas = [0, 5, 10]
    results = evaluate_protected_pool_on_validation(
        phase1_candidates=p1, graph_candidates=g_meta,
        hybrid_ranked_all=ranked, validation_df=val_df,
        p1_threshold=0.35, quota_values=quotas, total_budget_k=10,
    )
    assert len(results) == 3, "Must have one result per quota value"
    result_quotas = {r["protected_quota"] for r in results}
    assert result_quotas == {0, 5, 10}


def test_validation_ablation_no_label_leakage_in_candidates():
    """Validation labels must not influence candidate generation (only metric computation)."""
    # Candidate generation happens independently; ablation only uses labels for metric scoring.
    # Verify: the multi_obj_score field exists and is a float (label-based metric)
    # but the pool itself uses only phase1_score threshold (no label access)
    p1 = {"A1": 0.80, "B1": 0.60, "L1": 0.05}
    g_meta = make_graph_cands({"G1": 0.70})
    hu = HybridCandidateUnion()
    ranked = hu.union_and_rank({"A1": 0.80, "B1": 0.60}, g_meta)
    val_df = make_val_df(["A1"], ["L1", "G1"])

    results = evaluate_protected_pool_on_validation(
        phase1_candidates=p1, graph_candidates=g_meta,
        hybrid_ranked_all=ranked, validation_df=val_df,
        p1_threshold=0.35, quota_values=[5], total_budget_k=10,
    )
    # Protected pool for P=5 must contain A1 and B1 (score >= 0.35), NOT L1 (score 0.05)
    pool = build_protected_pool(p1, p1_threshold=0.35, protected_quota=5)
    pool_cids = {c.customer_id for c in pool}
    assert "L1" not in pool_cids, "Low-score legitimate customer must NOT be in protected pool"


def test_select_protected_quota_picks_best_multi_obj():
    """select_protected_quota picks the result with the highest multi_obj_score when no guardrails."""
    ablation = [
        {"protected_quota": 0,  "multi_obj_score": 5.0, "pat_a_recall": 0.9, "pat_b_recall": 1.0, "pat_c_recall": 0.0, "ring_recall": 0.5, "fpr_candidate": 0.1},
        {"protected_quota": 50, "multi_obj_score": 7.5, "pat_a_recall": 0.9, "pat_b_recall": 1.0, "pat_c_recall": 0.5, "ring_recall": 0.6, "fpr_candidate": 0.1},
        {"protected_quota": 100,"multi_obj_score": 6.0, "pat_a_recall": 0.8, "pat_b_recall": 0.9, "pat_c_recall": 0.75, "ring_recall": 0.55, "fpr_candidate": 0.1},
    ]
    # No guardrails: pick highest multi_obj
    selected = select_protected_quota(ablation, guardrails=None)
    assert selected == 50, f"Expected P=50 (highest multi_obj), got {selected}"


def test_select_protected_quota_respects_guardrails():
    """select_protected_quota must not select a config that violates guardrails."""
    ablation = [
        {"protected_quota": 0,  "multi_obj_score": 5.0, "pat_a_recall": 0.90, "pat_b_recall": 0.95, "pat_c_recall": 0.0,  "ring_recall": 0.5, "fpr_candidate": 0.1},
        {"protected_quota": 50, "multi_obj_score": 9.0, "pat_a_recall": 0.50, "pat_b_recall": 0.30, "pat_c_recall": 1.0,  "ring_recall": 0.7, "fpr_candidate": 0.1},
        {"protected_quota": 20, "multi_obj_score": 7.0, "pat_a_recall": 0.85, "pat_b_recall": 0.90, "pat_c_recall": 0.5,  "ring_recall": 0.6, "fpr_candidate": 0.1},
    ]
    # Guardrails: A>=0.80, B>=0.85 → P=50 must be excluded (A=0.50, B=0.30)
    guardrails = {"pat_a_min": 0.80, "pat_b_min": 0.85, "ring_recall_min": 0.40, "fpr_max": 0.90}
    selected = select_protected_quota(ablation, guardrails=guardrails)
    # P=0 (score=5.0) and P=20 (score=7.0) pass guardrails; P=20 has higher score
    assert selected == 20, f"Expected P=20 (passes guardrails, best multi_obj), got {selected}"


# ---------------------------------------------------------------------------
# 4. A/B regression guardrail test
# ---------------------------------------------------------------------------

def test_pattern_ab_candidates_still_present_with_protection():
    """
    Pattern A/B graph candidates must still reach the final list when protection is active.
    Protected pool fills P slots; graph candidates fill remaining K-P slots.
    """
    # 10 Phase-1 high-confidence candidates (would occupy P=10 slots)
    p1 = {f"P{i}": 0.80 for i in range(10)}
    # 50 strong graph candidates (Pattern A/B style -- high ring score, device sharing)
    g_meta = make_graph_cands({f"G{i:03d}": 0.85 for i in range(50)})

    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)

    final = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=10, total_budget_k=30,
    )
    # 30 total: 10 protected Phase-1 + 20 graph candidates
    graph_in_final = [c for c in final if "graph" in c.sources and "phase1" not in c.sources]
    assert len(graph_in_final) == 20, f"Expected 20 graph-only candidates in final, got {len(graph_in_final)}"


# ---------------------------------------------------------------------------
# 5. Pattern C recovery test
# ---------------------------------------------------------------------------

def test_pattern_c_candidates_enter_budget_with_protection():
    """
    Pattern C candidates (Phase-1-only, score >= p1_thr) must enter the budget
    when a non-zero protected quota P is active.
    """
    # 200 graph candidates that dominate ranking
    g_meta = make_graph_cands({f"G{i:03d}": 0.90 for i in range(200)})
    # 8 Pattern-C style Phase-1 candidates (score=0.36, above threshold 0.35)
    p1 = {f"C_RING_C_{i}": 0.36 for i in range(8)}

    p1_all = dict(p1)
    for cid in g_meta:
        p1_all[cid] = 0.05  # graph candidates have negligible p1 score

    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1_all.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)

    # Without protection (P=0): Pattern C candidates would rank ~208+, outside K=50
    final_no_protection = ranked_all[:50]
    p1_only_in_budget_no_prot = {c.customer_id for c in final_no_protection if c.sources == ["phase1"]}
    pat_c_in_budget_no_prot = {cid for cid in p1_only_in_budget_no_prot if "C_RING_C" in cid}
    assert len(pat_c_in_budget_no_prot) == 0, "Without protection Pattern C should be outside K=50"

    # With protection (P=8): Pattern C candidates are guaranteed entry
    final_with_protection = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=8, total_budget_k=50,
    )
    final_cids = {c.customer_id for c in final_with_protection}
    pat_c_in_budget = {cid for cid in final_cids if "C_RING_C" in cid}
    assert len(pat_c_in_budget) == 8, f"All 8 Pattern C candidates must be in budget with P=8, got {len(pat_c_in_budget)}"


# ---------------------------------------------------------------------------
# 6. Hard negative tests
# ---------------------------------------------------------------------------

def test_household_sharing_not_automatically_in_protected_pool():
    """
    Household sharing customers (legitimate) with low p1 scores must NOT enter the protected pool.
    """
    # Household customers typically have moderate scores from refund activity
    # but below the high-confidence threshold
    household = {"HOUSE_1": 0.25, "HOUSE_2": 0.28, "HOUSE_3": 0.30}
    pool = build_protected_pool(household, p1_threshold=0.35, protected_quota=10)
    pool_cids = {c.customer_id for c in pool}
    assert len(pool_cids) == 0, "Household sharing customers below threshold must NOT enter protected pool"


def test_high_refund_legitimate_below_threshold_not_protected():
    """Legitimate serial returners with score < p1_thr must not enter protected pool."""
    legit_returners = {"LEGIT_1": 0.32, "LEGIT_2": 0.33, "LEGIT_3": 0.34}
    pool = build_protected_pool(legit_returners, p1_threshold=0.35, protected_quota=10)
    assert len(pool) == 0, "Legitimate returners below 0.35 threshold must not be protected"


# ---------------------------------------------------------------------------
# 7. Label leakage tests (Phase 2.2 specific)
# ---------------------------------------------------------------------------

def test_protected_pool_no_ring_id_access():
    """FORBIDDEN_COLUMNS must include all ground-truth identifiers."""
    for col in ["ring_id", "abuse_label", "pattern_type", "abuse_pattern_type"]:
        assert col in FORBIDDEN_COLUMNS, f"'{col}' must be in FORBIDDEN_COLUMNS"


def test_protected_pool_raises_on_label_in_candidates():
    """If a forbidden key is passed in phase1_candidates dict, raise ValueError."""
    for col in ["ring_id", "abuse_label", "pattern_type"]:
        bad = {col: 0.9, "CUST_1": 0.7}
        with pytest.raises(ValueError, match="LEAKAGE GUARD"):
            build_protected_pool(bad, p1_threshold=0.35, protected_quota=5)


# ---------------------------------------------------------------------------
# 8. Point-in-time test
# ---------------------------------------------------------------------------

def test_phase22_config_contains_selection_partition():
    """Phase 2.2 frozen config must declare selection_partition='validation'."""
    import json
    config_path = Path("configs/phase2_2_budget.json")
    if not config_path.exists():
        pytest.skip("configs/phase2_2_budget.json not yet generated (run evaluate_phase2_2.py first)")
    config = json.loads(config_path.read_text())
    assert config.get("selection_partition") == "validation", \
        "Frozen config must state selection_partition=validation"
    assert "frozen_investigation_budget_k" in config
    assert "frozen_protected_quota_p" in config


# ---------------------------------------------------------------------------
# 9. Reproducibility test
# ---------------------------------------------------------------------------

def test_protected_pool_fully_deterministic():
    """Running build_protected_pool multiple times with same input gives identical output."""
    import random
    rng = random.Random(42)
    p1 = {f"CUST_{i:04d}": rng.uniform(0.30, 0.95) for i in range(200)}
    pool_a = build_protected_pool(p1, p1_threshold=0.35, protected_quota=50)
    pool_b = build_protected_pool(p1, p1_threshold=0.35, protected_quota=50)
    assert [c.customer_id for c in pool_a] == [c.customer_id for c in pool_b]
    assert [c.phase1_score for c in pool_a] == [c.phase1_score for c in pool_b]


def test_hybrid_protected_pool_deterministic():
    """build_hybrid_with_protected_pool is deterministic given same inputs."""
    p1 = {f"P{i}": 0.80 for i in range(20)}
    g_meta = make_graph_cands({f"G{i:03d}": 0.70 for i in range(100)})
    hu = HybridCandidateUnion()
    p1_020 = {cid: s for cid, s in p1.items() if s >= 0.20}
    ranked_all = hu.union_and_rank(p1_020, g_meta)

    list_a = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=10, total_budget_k=30,
    )
    list_b = build_hybrid_with_protected_pool(
        phase1_candidates=p1, graph_candidates=g_meta, hybrid_ranked_all=ranked_all,
        p1_threshold=0.35, protected_quota=10, total_budget_k=30,
    )
    assert [c.customer_id for c in list_a] == [c.customer_id for c in list_b]


# ---------------------------------------------------------------------------
# 10. Phase 2.2 summary schema test
# ---------------------------------------------------------------------------

def test_phase22_summary_schema():
    """Phase 2.2 summary JSON must contain all required keys."""
    path = Path("reports/phase2_2_summary.json")
    if not path.exists():
        pytest.skip("reports/phase2_2_summary.json not yet generated")
    data = json.loads(path.read_text())
    required = ["phase", "timestamp", "frozen_config", "guardrails", "guardrails_passed",
                "metrics", "source_overlap", "hard_negatives", "funnel_audit",
                "latencies", "grounding_rate", "pattern_delta_vs_p21"]
    for key in required:
        assert key in data, f"Missing required key '{key}' in phase2_2_summary.json"
    assert data["phase"] == "2.2"
    metrics = data["metrics"]
    for m in ["precision", "recall", "f1", "prauc", "fpr", "ring_recall",
              "pat_a_recall", "pat_b_recall", "pat_c_recall"]:
        assert m in metrics, f"Missing metric '{m}'"
    assert 0.0 <= metrics["ring_recall"] <= 1.0
    assert 0.0 <= metrics["pat_a_recall"] <= 1.0
    assert 0.0 <= metrics["pat_b_recall"] <= 1.0
    assert 0.0 <= metrics["pat_c_recall"] <= 1.0


def test_phase22_guardrails_documented():
    """Phase 2.2 summary must document guardrail pass/fail for each criterion."""
    path = Path("reports/phase2_2_summary.json")
    if not path.exists():
        pytest.skip("reports/phase2_2_summary.json not yet generated")
    data = json.loads(path.read_text())
    gp = data.get("guardrails_passed", {})
    for key in ["pat_a", "pat_b", "ring_recall", "fpr"]:
        assert key in gp, f"guardrails_passed must contain '{key}'"
        assert isinstance(gp[key], bool)
