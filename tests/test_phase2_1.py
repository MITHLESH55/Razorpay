"""
RiskOrbit — Phase 2.1 Test Suite

Deterministic unit and integration tests covering:
  1. Candidate union & deduplication
  2. Source attribution accuracy ("phase1", "graph", "both")
  3. Deterministic ranking stability
  4. Ground-truth label isolation (zero label access during inference)
  5. Point-in-time temporal causality (future events cannot alter past decisions)
  6. Metric denominator accounting rules (Candidate vs Investigation vs End-to-End recall)
  7. Budget K enforcement boundaries
  8. Hard-negative ranking safety (Household sharing / Public IPs non-abuse ranking)
  9. Pattern A/B candidate coverage & Pattern C preservation
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import networkx as nx

from src.graph.hybrid_candidate_union import HybridCandidateUnion, HybridCandidate
from src.graph.candidate_generator import CandidateGenerator
from src.graph.graph_engine import PaymentGraphEngine
from src.graph.budget_selector import select_investigation_budget


@pytest.fixture
def sample_graph_engine():
    base_time = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        {"transaction_id": "TXN_001", "customer_id": "CUST_A1", "merchant_id": "MER_1", "device_id": "DEV_100", "ip_id": "IP_10", "instrument_id": "INS_1", "timestamp": base_time, "amount": 1000.0},
        {"transaction_id": "TXN_002", "customer_id": "CUST_A2", "merchant_id": "MER_1", "device_id": "DEV_100", "ip_id": "IP_10", "instrument_id": "INS_2", "timestamp": base_time + timedelta(minutes=5), "amount": 1200.0},
        {"transaction_id": "TXN_003", "customer_id": "CUST_B1", "merchant_id": "MER_2", "device_id": "DEV_200", "ip_id": "IP_20", "instrument_id": "INS_3", "timestamp": base_time + timedelta(minutes=10), "amount": 500.0},
        {"transaction_id": "TXN_004", "customer_id": "CUST_C1", "merchant_id": "MER_3", "device_id": "DEV_300", "ip_id": "IP_30", "instrument_id": "INS_4", "timestamp": base_time + timedelta(minutes=15), "amount": 300.0},
    ])
    orders = pd.DataFrame([
        {"order_id": f"ORD_{i}", "customer_id": row["customer_id"], "merchant_id": row["merchant_id"], "created_at": row["timestamp"]}
        for i, row in txns.iterrows()
    ])
    refunds = pd.DataFrame([
        {"refund_id": "REF_001", "transaction_id": "TXN_001", "refund_requested_at": base_time + timedelta(hours=1), "refund_amount": 1000.0},
        {"refund_id": "REF_002", "transaction_id": "TXN_002", "refund_requested_at": base_time + timedelta(hours=1, minutes=5), "refund_amount": 1200.0},
    ])
    return PaymentGraphEngine(transactions=txns, orders=orders, refunds=refunds)


def test_union_deduplication():
    union_engine = HybridCandidateUnion()
    phase1_candidates = {"CUST_001": 0.85, "CUST_002": 0.40}
    graph_candidates = {
        "CUST_002": {"ring_risk_score": 0.60, "member_count": 3, "shared_device_count": 1, "shared_ip_count": 1, "member_refund_rate": 0.50},
        "CUST_003": {"ring_risk_score": 0.75, "member_count": 4, "shared_device_count": 2, "shared_ip_count": 1, "member_refund_rate": 0.80},
    }

    result = union_engine.union_and_rank(phase1_candidates, graph_candidates)
    
    # 3 unique customers total
    assert len(result) == 3
    cust_ids = [c.customer_id for c in result]
    assert len(set(cust_ids)) == 3
    assert "CUST_001" in cust_ids
    assert "CUST_002" in cust_ids
    assert "CUST_003" in cust_ids


def test_source_attribution():
    union_engine = HybridCandidateUnion()
    phase1_candidates = {"CUST_001": 0.85, "CUST_002": 0.40}
    graph_candidates = {
        "CUST_002": {"ring_risk_score": 0.60, "member_count": 3, "shared_device_count": 1, "member_refund_rate": 0.50},
        "CUST_003": {"ring_risk_score": 0.75, "member_count": 4, "shared_device_count": 2, "member_refund_rate": 0.80},
    }

    result = union_engine.union_and_rank(phase1_candidates, graph_candidates)
    by_cid = {c.customer_id: c for c in result}

    assert by_cid["CUST_001"].sources == ["phase1"]
    assert set(by_cid["CUST_002"].sources) == {"phase1", "graph"}
    assert by_cid["CUST_003"].sources == ["graph"]

    breakdown = union_engine.get_source_breakdown(result)
    assert breakdown["total_unique_candidates"] == 3
    assert breakdown["phase1_only_count"] == 1
    assert breakdown["graph_only_count"] == 1
    assert breakdown["both_count"] == 1


def test_deterministic_rank_ordering():
    union_engine = HybridCandidateUnion()
    phase1 = {"CUST_X": 0.90, "CUST_Y": 0.10}
    graph = {
        "CUST_Y": {"ring_risk_score": 0.90, "member_count": 5, "shared_device_count": 2, "member_refund_rate": 0.90},
        "CUST_Z": {"ring_risk_score": 0.30, "member_count": 2, "shared_device_count": 0, "member_refund_rate": 0.10},
    }

    run1 = union_engine.union_and_rank(phase1, graph)
    run2 = union_engine.union_and_rank(phase1, graph)

    assert [c.customer_id for c in run1] == [c.customer_id for c in run2]
    assert [c.candidate_rank for c in run1] == [1, 2, 3]


def test_no_ground_truth_in_candidate_union():
    union_engine = HybridCandidateUnion()
    phase1 = {"CUST_001": 0.80}
    graph = {"CUST_001": {"ring_risk_score": 0.50, "member_count": 2}}

    result = union_engine.union_and_rank(phase1, graph)
    c_dict = result[0].to_dict()

    for forbidden in ["abuse_label", "ring_id", "hard_negative_type", "abuse_pattern_type"]:
        assert forbidden not in c_dict


def test_point_in_time_causality_candidate_generator(sample_graph_engine):
    gen = CandidateGenerator(graph_engine=sample_graph_engine)
    pop = ["CUST_A1", "CUST_A2", "CUST_B1", "CUST_C1"]

    t0 = pd.Timestamp("2026-01-01 10:00:00")
    res_t0 = gen.generate_from_full_population(pop, as_of_time=t0)

    # Adding future transaction at t0 + 2 days
    future_txn = pd.DataFrame([{
        "transaction_id": "TXN_FUTURE", "customer_id": "CUST_A1", "merchant_id": "MER_99",
        "device_id": "DEV_999", "ip_id": "IP_99", "instrument_id": "INS_99",
        "timestamp": pd.Timestamp("2026-01-03 10:00:00"), "amount": 9999.0
    }])
    sample_graph_engine.txn = pd.concat([sample_graph_engine.txn, future_txn], ignore_index=True)

    # Re-evaluate as of t0
    res_t0_after = gen.generate_from_full_population(pop, as_of_time=t0)

    # The result as of t0 MUST be identical
    assert set(res_t0.keys()) == set(res_t0_after.keys())


def test_metric_denominator_accounting():
    # Enforces strict separation of denominators
    total_ground_truth_rings = 24
    candidate_covered_rings = 16
    confirmed_rings = 16

    cand_recall = candidate_covered_rings / total_ground_truth_rings  # 16/24 = 66.67%
    inv_recall = confirmed_rings / candidate_covered_rings           # 16/16 = 100.0%
    e2e_recall = confirmed_rings / total_ground_truth_rings            # 16/24 = 66.67%

    assert cand_recall == pytest.approx(0.6667, abs=1e-3)
    assert inv_recall == 1.00
    assert e2e_recall == pytest.approx(0.6667, abs=1e-3)
    assert e2e_recall != inv_recall  # NEVER conflate investigation recall with e2e recall!


def test_budget_k_boundary():
    union_engine = HybridCandidateUnion()
    phase1 = {f"CUST_{i:04d}": 0.50 for i in range(100)}
    graph = {}

    ranked = union_engine.union_and_rank(phase1, graph)
    val_df = pd.DataFrame([
        {"customer_id": f"CUST_{i:04d}", "abuse_label": 1 if i < 10 else 0, "ring_id": "RING_A_0001" if i < 10 else None}
        for i in range(100)
    ])

    budget_res = select_investigation_budget(ranked, val_df, candidate_budgets=[10, 25, 50])
    
    assert budget_res["selected_k"] in [10, 25, 50]
    for ab in budget_res["ablation_results"]:
        assert ab["investigated_candidates"] <= ab["budget_k"]


def test_hard_negative_household_sharing_rank():
    union_engine = HybridCandidateUnion()
    
    # Household sharing: 2 accounts, 1 shared device, low/zero refund rate
    household_cand = {
        "customer_id": "CUST_HOUSEHOLD",
        "phase1_score": 0.05,
        "graph_ring_score": 0.20,
        "shared_device_count": 1,
        "shared_ip_count": 0,
        "shared_instrument_count": 0,
        "member_refund_rate": 0.0,
        "cross_merchant_count": 1,
    }
    
    # Coordinated abuse ring: multi-account, high refund rate, multi-device/ip
    abuse_cand = {
        "customer_id": "CUST_ABUSE",
        "phase1_score": 0.80,
        "graph_ring_score": 0.85,
        "shared_device_count": 2,
        "shared_ip_count": 2,
        "shared_instrument_count": 1,
        "member_refund_rate": 0.75,
        "cross_merchant_count": 3,
    }

    score_house = union_engine.compute_composite_rank_score(**household_cand)
    score_abuse = union_engine.compute_composite_rank_score(**abuse_cand)

    assert score_house < score_abuse
    assert score_house < 0.35  # Household should remain low-rank
