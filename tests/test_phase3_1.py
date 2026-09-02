"""
RiskOrbit — Phase 3.1 Tests: Edge Diversity, Member Confidence, Transaction Gating

Tests for:
    - Edge diversity scoring
    - Member confidence calculation
    - Transaction gating logic
    - Determinism
    - Point-in-time safety
    - Hard negative protection
    - Leakage guards
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

import networkx as nx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.edge_diversity import (
    compute_edge_diversity,
    compute_multi_member_diversity,
    aggregate_diversity_score,
)
from src.graph.member_confidence import (
    compute_member_confidence,
    compute_ring_member_confidences,
    filter_members_by_tier,
    filter_members_by_confidence,
)
from src.decision.transaction_gate import TransactionGate, TransactionDecision


# ============================================================================
# EDGE DIVERSITY TESTS
# ============================================================================

def test_edge_diversity_single_type():
    """Single edge type should give low diversity score."""
    G = nx.Graph()
    G.add_node("CUST_A", node_type="CUSTOMER")
    G.add_node("CUST_B", node_type="CUSTOMER")
    G.add_node("DEV_1", node_type="DEVICE")

    G.add_edge("CUST_A", "DEV_1", type="device", strength=0.8)
    G.add_edge("CUST_B", "DEV_1", type="device", strength=0.8)

    div = compute_edge_diversity(G, "CUST_A", "CUST_B")

    assert div.has_device is True
    assert div.has_ip is False
    assert div.connectivity_evidence == 1  # Only device
    assert div.behavioral_evidence == 0
    assert div.outcome_evidence == 0
    assert div.diversity_score < 0.30  # Low diversity


def test_edge_diversity_multi_family():
    """Multiple independent evidence families should give high diversity."""
    G = nx.Graph()
    G.add_node("CUST_A", node_type="CUSTOMER")
    G.add_node("CUST_B", node_type="CUSTOMER")
    G.add_node("DEV_1", node_type="DEVICE")
    G.add_node("IP_1", node_type="IP")
    G.add_node("MERCH_1", node_type="MERCHANT")

    G.add_edge("CUST_A", "DEV_1", type="device", strength=0.7)
    G.add_edge("CUST_B", "DEV_1", type="device", strength=0.7)
    G.add_edge("CUST_A", "IP_1", type="ip", strength=0.5)
    G.add_edge("CUST_B", "IP_1", type="ip", strength=0.5)
    G.add_edge("CUST_A", "MERCH_1", type="merchant", strength=0.6)
    G.add_edge("CUST_B", "MERCH_1", type="merchant", strength=0.6)

    div = compute_edge_diversity(G, "CUST_A", "CUST_B")

    assert div.has_device is True
    assert div.has_ip is True
    assert div.has_merchant is True
    assert div.connectivity_evidence == 2  # Device + IP
    assert div.behavioral_evidence == 1    # Merchant
    assert div.diversity_score > 0.40  # Higher diversity with multiple families


def test_edge_diversity_deterministic():
    """Edge diversity must be deterministic."""
    G = nx.Graph()
    G.add_node("CUST_A", node_type="CUSTOMER")
    G.add_node("CUST_B", node_type="CUSTOMER")
    G.add_node("DEV_1", node_type="DEVICE")
    G.add_edge("CUST_A", "DEV_1", type="device", strength=0.8)
    G.add_edge("CUST_B", "DEV_1", type="device", strength=0.8)

    div1 = compute_edge_diversity(G, "CUST_A", "CUST_B")
    div2 = compute_edge_diversity(G, "CUST_A", "CUST_B")

    assert div1.diversity_score == div2.diversity_score
    assert div1.unique_edge_types == div2.unique_edge_types


def test_edge_diversity_no_connection():
    """Disconnected customers should have zero diversity."""
    G = nx.Graph()
    G.add_node("CUST_A", node_type="CUSTOMER")
    G.add_node("CUST_B", node_type="CUSTOMER")

    # Nodes exist but no shared entities - should give minimal diversity
    div = compute_edge_diversity(G, "CUST_A", "CUST_B")
    assert div.diversity_score == 0.0
    assert div.total_edge_count == 0


def test_aggregate_diversity_uses_maximum():
    """Aggregate diversity should use maximum (strongest evidence path)."""
    from src.graph.edge_diversity import EdgeDiversityScore

    scores = [
        EdgeDiversityScore("C1", "C2", 1, {"device"}, 0.20, True, False, False, False, False, False, 1, 0, 0),
        EdgeDiversityScore("C1", "C3", 3, {"device", "ip", "merchant"}, 0.60, True, True, False, True, False, False, 2, 1, 0),
        EdgeDiversityScore("C1", "C4", 2, {"device", "ip"}, 0.40, True, True, False, False, False, False, 2, 0, 0),
    ]

    agg_score = aggregate_diversity_score(scores)
    assert agg_score == 0.60  # Maximum diversity


# ============================================================================
# MEMBER CONFIDENCE TESTS
# ============================================================================

def test_member_confidence_high_risk_close_distance():
    """High Phase 1 risk + close distance + strong edges = high confidence."""
    G = nx.Graph()
    G.add_node("PRIMARY", node_type="CUSTOMER")
    G.add_node("MEMBER_1", node_type="CUSTOMER")
    G.add_node("DEV_1", node_type="DEVICE")
    G.add_edge("PRIMARY", "DEV_1", type="device", strength=0.85)
    G.add_edge("MEMBER_1", "DEV_1", type="device", strength=0.85)

    conf = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.75,
        graph_distance=1,
        as_of_time=datetime.now(),
        connected_entities=["DEV_1"],
        edge_strengths={"DEV_1": 0.85},
    )

    assert conf.customer_id == "MEMBER_1"
    assert conf.confidence_score >= 0.50  # Should be moderate to high
    assert conf.tier in ("PRIMARY", "SECONDARY")
    assert conf.graph_distance == 1
    assert conf.supporting_edge_count == 1


def test_member_confidence_low_risk_weak_edges():
    """Low Phase 1 risk + weak edges = low confidence."""
    G = nx.Graph()
    G.add_node("PRIMARY", node_type="CUSTOMER")
    G.add_node("MEMBER_1", node_type="CUSTOMER")
    G.add_node("IP_1", node_type="IP")
    G.add_edge("PRIMARY", "IP_1", type="ip", strength=0.15)
    G.add_edge("MEMBER_1", "IP_1", type="ip", strength=0.15)

    conf = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.10,
        graph_distance=2,
        as_of_time=datetime.now(),
        connected_entities=["IP_1"],
        edge_strengths={"IP_1": 0.15},
    )

    assert conf.confidence_score < 0.40  # Should be low
    assert conf.tier in ("SECONDARY", "TERTIARY")


def test_member_confidence_bounded():
    """Confidence score must be in [0, 1] range."""
    G = nx.Graph()
    G.add_node("PRIMARY", node_type="CUSTOMER")
    G.add_node("MEMBER_1", node_type="CUSTOMER")

    # Extreme high inputs
    conf = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=1.0,
        graph_distance=1,
        as_of_time=datetime.now(),
        connected_entities=["DEV_1", "IP_1", "INS_1"],
        edge_strengths={"DEV_1": 1.0, "IP_1": 1.0, "INS_1": 1.0},
    )

    assert 0.0 <= conf.confidence_score <= 1.0


def test_member_confidence_deterministic():
    """Member confidence must be deterministic."""
    G = nx.Graph()
    G.add_node("PRIMARY", node_type="CUSTOMER")
    G.add_node("MEMBER_1", node_type="CUSTOMER")
    G.add_node("DEV_1", node_type="DEVICE")
    G.add_edge("PRIMARY", "DEV_1", type="device", strength=0.70)
    G.add_edge("MEMBER_1", "DEV_1", type="device", strength=0.70)

    conf1 = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.50,
        graph_distance=1,
        as_of_time=datetime(2024, 1, 1),
        connected_entities=["DEV_1"],
        edge_strengths={"DEV_1": 0.70},
    )

    conf2 = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.50,
        graph_distance=1,
        as_of_time=datetime(2024, 1, 1),
        connected_entities=["DEV_1"],
        edge_strengths={"DEV_1": 0.70},
    )

    assert conf1.confidence_score == conf2.confidence_score
    assert conf1.tier == conf2.tier


def test_member_confidence_distance_penalty():
    """Greater graph distance should reduce confidence."""
    G = nx.Graph()
    G.add_node("PRIMARY", node_type="CUSTOMER")
    G.add_node("MEMBER_1", node_type="CUSTOMER")

    # Distance 1
    conf1 = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.50,
        graph_distance=1,
        as_of_time=datetime.now(),
        connected_entities=["DEV_1"],
        edge_strengths={"DEV_1": 0.70},
    )

    # Distance 2 (same other inputs)
    conf2 = compute_member_confidence(
        customer_id="MEMBER_1",
        primary_suspect_id="PRIMARY",
        graph=G,
        phase1_risk_score=0.50,
        graph_distance=2,
        as_of_time=datetime.now(),
        connected_entities=["DEV_1"],
        edge_strengths={"DEV_1": 0.70},
    )

    assert conf1.confidence_score > conf2.confidence_score


def test_filter_members_by_tier():
    """Tier filtering should correctly filter members."""
    from src.graph.member_confidence import MemberConfidence

    confidences = {
        "C1": MemberConfidence("C1", 0.80, "PRIMARY", 0.75, 2, 0.60, 0.70, 0.80, 1, 0.80, 0.70, {}),
        "C2": MemberConfidence("C2", 0.50, "SECONDARY", 0.40, 1, 0.30, 0.50, 0.60, 2, 0.50, 0.40, {}),
        "C3": MemberConfidence("C3", 0.25, "TERTIARY", 0.20, 1, 0.10, 0.30, 0.40, 2, 0.30, 0.20, {}),
    }

    primaries = filter_members_by_tier(confidences, "PRIMARY")
    assert primaries == ["C1"]

    secondaries_up = filter_members_by_tier(confidences, "SECONDARY")
    assert set(secondaries_up) == {"C1", "C2"}

    all_tiers = filter_members_by_tier(confidences, "TERTIARY")
    assert set(all_tiers) == {"C1", "C2", "C3"}


# ============================================================================
# TRANSACTION GATING TESTS
# ============================================================================

def test_transaction_gate_isolated_high_risk():
    """Isolated transaction with high Phase 1 risk should be flagged."""
    gate = TransactionGate(isolated_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_001",
        customer_id="CUST_A",
        phase1_score=0.70,
        member_confidence=None,
    )

    assert decision.is_flagged is True
    assert decision.tier == "ISOLATED"
    assert decision.decision_score == 0.70
    assert decision.phase1_risk == 0.70
    assert decision.member_confidence == 0.0


def test_transaction_gate_isolated_low_risk():
    """Isolated transaction with low Phase 1 risk should be cleared."""
    gate = TransactionGate(isolated_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_002",
        customer_id="CUST_B",
        phase1_score=0.10,
        member_confidence=None,
    )

    assert decision.is_flagged is False
    assert decision.tier == "ISOLATED"
    assert decision.decision_score == 0.10


def test_transaction_gate_primary_member_high_risk():
    """PRIMARY member with high transaction risk should be flagged."""
    from src.graph.member_confidence import MemberConfidence

    member_conf = MemberConfidence(
        customer_id="CUST_C",
        confidence_score=0.85,
        tier="PRIMARY",
        phase1_risk=0.65,
        supporting_edge_count=3,
        edge_diversity_score=0.70,
        avg_edge_strength=0.75,
        max_edge_strength=0.85,
        graph_distance=1,
        temporal_relevance=0.80,
        evidence_strength=0.75,
        confidence_components={},
    )

    gate = TransactionGate(decision_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_003",
        customer_id="CUST_C",
        phase1_score=0.65,
        member_confidence=member_conf,
    )

    assert decision.is_flagged is True
    assert decision.tier == "PRIMARY"
    assert decision.decision_score > 0.35


def test_transaction_gate_secondary_member_low_risk():
    """SECONDARY member with low transaction risk should be cleared."""
    from src.graph.member_confidence import MemberConfidence

    member_conf = MemberConfidence(
        customer_id="CUST_D",
        confidence_score=0.50,
        tier="SECONDARY",
        phase1_risk=0.05,
        supporting_edge_count=1,
        edge_diversity_score=0.30,
        avg_edge_strength=0.40,
        max_edge_strength=0.50,
        graph_distance=2,
        temporal_relevance=0.40,
        evidence_strength=0.30,
        confidence_components={},
    )

    gate = TransactionGate(decision_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_004",
        customer_id="CUST_D",
        phase1_score=0.05,
        member_confidence=member_conf,
    )

    assert decision.is_flagged is False  # Low transaction risk, cleared
    assert decision.tier == "SECONDARY"


def test_transaction_gate_tertiary_member_cleared():
    """TERTIARY member with weak connection should be cleared unless very high individual risk."""
    from src.graph.member_confidence import MemberConfidence

    member_conf = MemberConfidence(
        customer_id="CUST_E",
        confidence_score=0.25,
        tier="TERTIARY",
        phase1_risk=0.20,
        supporting_edge_count=1,
        edge_diversity_score=0.15,
        avg_edge_strength=0.20,
        max_edge_strength=0.25,
        graph_distance=2,
        temporal_relevance=0.20,
        evidence_strength=0.15,
        confidence_components={},
    )

    gate = TransactionGate(decision_threshold=0.35, isolated_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_005",
        customer_id="CUST_E",
        phase1_score=0.20,
        member_confidence=member_conf,
    )

    assert decision.is_flagged is False  # TERTIARY should not be blanket-blocked
    assert decision.tier == "TERTIARY"


def test_transaction_gate_deterministic():
    """Transaction gating must be deterministic."""
    from src.graph.member_confidence import MemberConfidence

    member_conf = MemberConfidence(
        customer_id="CUST_F",
        confidence_score=0.60,
        tier="SECONDARY",
        phase1_risk=0.40,
        supporting_edge_count=2,
        edge_diversity_score=0.50,
        avg_edge_strength=0.55,
        max_edge_strength=0.65,
        graph_distance=1,
        temporal_relevance=0.60,
        evidence_strength=0.50,
        confidence_components={},
    )

    gate = TransactionGate()

    d1 = gate.evaluate_transaction("TXN_006", "CUST_F", 0.40, member_conf)
    d2 = gate.evaluate_transaction("TXN_006", "CUST_F", 0.40, member_conf)

    assert d1.decision_score == d2.decision_score
    assert d1.is_flagged == d2.is_flagged
    assert d1.tier == d2.tier


def test_transaction_gate_decision_score_bounded():
    """Decision score must be in [0, 1] range."""
    from src.graph.member_confidence import MemberConfidence

    # Extreme inputs
    member_conf = MemberConfidence(
        customer_id="CUST_G",
        confidence_score=1.0,
        tier="PRIMARY",
        phase1_risk=1.0,
        supporting_edge_count=10,
        edge_diversity_score=1.0,
        avg_edge_strength=1.0,
        max_edge_strength=1.0,
        graph_distance=1,
        temporal_relevance=1.0,
        evidence_strength=1.0,
        confidence_components={},
    )

    gate = TransactionGate()
    decision = gate.evaluate_transaction("TXN_007", "CUST_G", 1.0, member_conf)

    assert 0.0 <= decision.decision_score <= 1.0


def test_transaction_gate_weights_sum_to_one():
    """Gate weights must sum to 1.0."""
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        TransactionGate(
            weight_phase1=0.50,
            weight_member_conf=0.30,
            weight_edge_strength=0.15,
            weight_diversity=0.10,  # Sum = 1.05
        )


def test_transaction_gate_hard_negative_shared_ip_only():
    """Shared IP alone (hard negative: office network) should not auto-flag low-risk transactions."""
    from src.graph.member_confidence import MemberConfidence

    # Simulate office network: weak IP-only connection, low diversity
    member_conf = MemberConfidence(
        customer_id="CUST_H",
        confidence_score=0.30,  # Low confidence due to weak shared IP
        tier="TERTIARY",
        phase1_risk=0.10,
        supporting_edge_count=1,
        edge_diversity_score=0.15,  # Single signal family
        avg_edge_strength=0.20,  # Weak hubness-penalized IP
        max_edge_strength=0.20,
        graph_distance=2,
        temporal_relevance=0.20,
        evidence_strength=0.15,
        confidence_components={},
    )

    gate = TransactionGate(decision_threshold=0.35)

    decision = gate.evaluate_transaction(
        transaction_id="TXN_008",
        customer_id="CUST_H",
        phase1_score=0.10,
        member_confidence=member_conf,
    )

    # Should be cleared: weak connection + low transaction risk
    assert decision.is_flagged is False
    assert decision.tier == "TERTIARY"


# ============================================================================
# LEAKAGE & SECURITY TESTS
# ============================================================================

def test_member_confidence_no_abuse_label_access():
    """Member confidence must not access abuse_label or ring_id in actual code."""
    import inspect
    from src.graph import member_confidence

    # Check function implementations, not docstrings
    for name, obj in inspect.getmembers(member_confidence, inspect.isfunction):
        if name.startswith("_"):
            continue
        source_lines = inspect.getsourcelines(obj)[0]
        # Skip docstring (first few lines after def)
        code_lines = [line for line in source_lines[3:] if not line.strip().startswith('"""') and not line.strip().startswith("'''")]
        code = "".join(code_lines)

        assert "abuse_label" not in code, f"Function {name} accesses abuse_label"
        assert "ring_id" not in code, f"Function {name} accesses ring_id"
        assert 'pattern_type' not in code, f"Function {name} accesses pattern_type"


def test_transaction_gate_no_ground_truth_access():
    """Transaction gate must not access ground truth labels."""
    import inspect
    from src.decision import transaction_gate

    source = inspect.getsource(transaction_gate)
    assert "abuse_label" not in source
    assert "ring_id" not in source
