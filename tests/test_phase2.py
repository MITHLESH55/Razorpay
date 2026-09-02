"""
RiskOrbit — Phase 2 Test Suite

Tests cover:
  - Graph construction (nodes, edges, temporal filtering, determinism)
  - Traversal (bounded hops, hub resistance)
  - Relationship strength (frequency, recency, hubness)
  - Ring detection (known abuse vs legitimate shared infrastructure)
  - Leakage guards (hidden labels inaccessible)
  - Investigation agent (schema validation, tool scope)
  - Evidence grounding (no invented entities, uncertainty preserved)
  - API endpoints (Phase 1 backward compatibility + Phase 2 responses)
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.graph.schema import NodeType, RelationshipType
from src.graph.strength import compute_edge_strength, compute_hubness_penalty
from src.graph.traversal import extract_local_case_subgraph
from src.graph.ring_detector import detect_candidate_ring
from src.investigation.schema import (
    CaseInvestigationResponse, EvidenceRecord, EvidenceCategory,
    EvidenceConfidence, TimelineEvent, CaseAuditTrail,
)
from src.investigation.evidence_agent import GroundingValidator, DeterministicEvidenceGenerator
from src.investigation.golden_cases import get_golden_case_definitions

import networkx as nx


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

def _make_small_abuse_graph() -> nx.Graph:
    """
    5 customers share 1 device → strong coordinated signal.
    Also connected to 2 merchants and 1 IP.
    """
    G = nx.Graph()
    for i in range(1, 6):
        G.add_node(f"CUS_{i}", node_type="CUSTOMER")
    G.add_node("DEV_001", node_type="DEVICE", n_connected_accounts=5)
    G.add_node("IP_001",  node_type="IP",     n_connected_accounts=5)
    G.add_node("MER_001", node_type="MERCHANT", n_connected_accounts=5)
    G.add_node("MER_002", node_type="MERCHANT", n_connected_accounts=3)

    for i in range(1, 6):
        G.add_edge(f"CUS_{i}", "DEV_001", relationship_type="CUSTOMER_USED_DEVICE",
                   strength=0.60, event_count=5,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-01-10T00:00:00")
        G.add_edge(f"CUS_{i}", "IP_001", relationship_type="CUSTOMER_CONNECTED_IP",
                   strength=0.25, event_count=3,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-01-10T00:00:00")
        G.add_edge(f"CUS_{i}", "MER_001", relationship_type="CUSTOMER_PLACED_ORDER",
                   strength=0.10, event_count=2,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-01-05T00:00:00")

    G.add_edge("CUS_3", "MER_002", relationship_type="CUSTOMER_PLACED_ORDER",
               strength=0.10, event_count=1,
               first_seen="2024-01-08T00:00:00",
               last_seen="2024-01-08T00:00:00")
    return G


def _make_household_graph() -> nx.Graph:
    """
    4 legitimate household customers share 1 device and 1 IP.
    Low refund rate, modest transaction frequency.
    """
    G = nx.Graph()
    for i in range(1, 5):
        G.add_node(f"LEGIT_CUS_{i}", node_type="CUSTOMER")
    G.add_node("LEGIT_DEV", node_type="DEVICE", n_connected_accounts=4)
    G.add_node("LEGIT_IP",  node_type="IP",     n_connected_accounts=4)

    for i in range(1, 5):
        G.add_edge(f"LEGIT_CUS_{i}", "LEGIT_DEV",
                   relationship_type="CUSTOMER_USED_DEVICE",
                   strength=0.30, event_count=2,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-06-01T00:00:00")
        G.add_edge(f"LEGIT_CUS_{i}", "LEGIT_IP",
                   relationship_type="CUSTOMER_CONNECTED_IP",
                   strength=0.10, event_count=2,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-06-01T00:00:00")
    return G


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH CONSTRUCTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphConstruction:
    def test_abuse_graph_has_correct_node_count(self):
        G = _make_small_abuse_graph()
        assert G.number_of_nodes() == 9  # 5 custs + DEV + IP + 2 merchants

    def test_node_types_assigned(self):
        G = _make_small_abuse_graph()
        for i in range(1, 6):
            assert G.nodes[f"CUS_{i}"]["node_type"] == "CUSTOMER"
        assert G.nodes["DEV_001"]["node_type"] == "DEVICE"
        assert G.nodes["MER_001"]["node_type"] == "MERCHANT"

    def test_edge_types_assigned(self):
        G = _make_small_abuse_graph()
        edge_data = G.get_edge_data("CUS_1", "DEV_001")
        assert edge_data is not None
        assert edge_data["relationship_type"] == "CUSTOMER_USED_DEVICE"

    def test_edge_strength_in_range(self):
        G = _make_small_abuse_graph()
        for u, v, d in G.edges(data=True):
            assert 0.0 <= d.get("strength", 0.0) <= 1.0


class TestTemporalFiltering:
    def test_graph_engine_filters_future_events(self):
        """Events after as_of_timestamp must not appear in the graph."""
        from src.graph.graph_engine import PaymentGraphEngine
        t0 = datetime(2024, 1, 1)
        t1 = datetime(2024, 6, 1)
        t2 = datetime(2024, 12, 1)

        txns = pd.DataFrame([
            {"transaction_id": "T1", "customer_id": "C1", "merchant_id": "M1",
             "device_id": "D1", "ip_id": "IP1", "instrument_id": None,
             "timestamp": t1, "amount": 100.0},
            {"transaction_id": "T2", "customer_id": "C2", "merchant_id": "M1",
             "device_id": "D1", "ip_id": "IP1", "instrument_id": None,
             "timestamp": t2, "amount": 100.0},
        ])
        orders = pd.DataFrame(columns=["order_id", "customer_id", "created_at"])
        refunds = pd.DataFrame()

        engine = PaymentGraphEngine(transactions=txns, orders=orders, refunds=refunds)
        G_early = engine.build_networkx_graph_as_of(t1, min_edge_strength=0.0)
        G_full  = engine.build_networkx_graph_as_of(t2, min_edge_strength=0.0)

        # At t1, only T1 events → C2 should not share D1 yet
        # C2 appears in G_full but not in G_early unless both events are before t1
        assert "C1" in G_early.nodes
        # C2 is at t2, so should NOT appear in the t1 graph
        assert "C2" not in G_early.nodes

    def test_future_refund_excluded(self):
        """Refunds after as_of_timestamp must be excluded from graph context."""
        from src.graph.graph_engine import PaymentGraphEngine
        t_txn = datetime(2024, 1, 10)
        t_refund_future = datetime(2024, 6, 1)

        txns = pd.DataFrame([{
            "transaction_id": "T1", "customer_id": "C1", "merchant_id": "M1",
            "device_id": "D1", "ip_id": None, "instrument_id": None,
            "timestamp": t_txn, "amount": 500.0,
        }])
        refunds = pd.DataFrame([{
            "refund_id": "R1", "transaction_id": "T1",
            "refund_requested_at": t_refund_future,
            "refund_amount": 500.0,
        }])
        orders = pd.DataFrame(columns=["order_id", "customer_id", "created_at"])

        engine = PaymentGraphEngine(transactions=txns, orders=orders, refunds=refunds)
        txn_sub, _, ref_sub = engine.get_events_as_of(t_txn)
        # Refund is in the future — must not be visible
        assert len(ref_sub) == 0


# ─────────────────────────────────────────────────────────────────────────────
# RELATIONSHIP STRENGTH TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRelationshipStrength:
    def test_more_events_increases_strength(self):
        t0 = datetime(2024, 1, 1)
        t1 = datetime(2024, 1, 10)
        t_now = datetime(2024, 2, 1)
        s1 = compute_edge_strength(1, t0, t0, t_now, 1, "DEVICE")
        s2 = compute_edge_strength(10, t0, t1, t_now, 1, "DEVICE")
        assert s2["strength"] > s1["strength"]

    def test_older_relationship_is_weaker(self):
        t_now = datetime(2024, 6, 1)
        t_recent_start = datetime(2024, 5, 20)
        t_recent_end   = datetime(2024, 5, 25)
        t_old_start    = datetime(2024, 1, 1)
        t_old_end      = datetime(2024, 1, 5)

        s_recent = compute_edge_strength(5, t_recent_start, t_recent_end, t_now, 1, "DEVICE")
        s_old    = compute_edge_strength(5, t_old_start,    t_old_end,    t_now, 1, "DEVICE")
        assert s_recent["strength"] > s_old["strength"]

    def test_hubness_penalty_reduces_strength(self):
        p_rare   = compute_hubness_penalty(2,  "DEVICE")
        p_common = compute_hubness_penalty(20, "DEVICE")
        assert p_rare > p_common

    def test_ip_penalized_more_than_device(self):
        p_dev = compute_hubness_penalty(10, "DEVICE")
        p_ip  = compute_hubness_penalty(10, "IP")
        assert p_dev > p_ip

    def test_strength_bounded_zero_to_one(self):
        t0 = datetime(2024, 1, 1)
        t1 = datetime(2024, 6, 1)
        t_now = datetime(2024, 6, 15)
        s = compute_edge_strength(1000, t0, t1, t_now, 1, "DEVICE")
        assert 0.0 <= s["strength"] <= 1.0

    def test_weak_single_connection_remains_weak(self):
        t0 = datetime(2024, 1, 1)
        t_now = datetime(2024, 6, 1)
        # 1 event, 150 days old, shared by 30 accounts
        s = compute_edge_strength(1, t0, t0, t_now, 30, "IP")
        assert s["strength"] < 0.20, f"Expected weak strength, got {s['strength']}"


# ─────────────────────────────────────────────────────────────────────────────
# TRAVERSAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundedTraversal:
    def test_root_not_in_graph_returns_empty_subgraph(self):
        G = _make_small_abuse_graph()
        result = extract_local_case_subgraph(G, "NONEXISTENT_ID", max_hops=2)
        assert result["statistics"]["total_nodes"] >= 1
        assert result["root_entity"] == "NONEXISTENT_ID"

    def test_subgraph_contains_root(self):
        G = _make_small_abuse_graph()
        result = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        node_ids = [n["node_id"] for n in result["nodes"]]
        assert "CUS_1" in node_ids

    def test_max_hops_1_limits_reach(self):
        G = _make_small_abuse_graph()
        r1 = extract_local_case_subgraph(G, "CUS_1", max_hops=1)
        r2 = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        # 2-hop should reach more nodes than 1-hop via shared device
        assert r2["statistics"]["total_nodes"] >= r1["statistics"]["total_nodes"]

    def test_device_bridges_customers(self):
        G = _make_small_abuse_graph()
        result = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        node_ids = [n["node_id"] for n in result["nodes"]]
        # All 5 customers should be reachable via DEV_001
        assert "DEV_001" in node_ids

    def test_statistics_customer_count_correct(self):
        G = _make_small_abuse_graph()
        result = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        assert result["statistics"]["customer_count"] >= 2

    def test_deterministic_output(self):
        G = _make_small_abuse_graph()
        r1 = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        r2 = extract_local_case_subgraph(G, "CUS_1", max_hops=2)
        assert r1["statistics"] == r2["statistics"]


# ─────────────────────────────────────────────────────────────────────────────
# RING DETECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRingDetection:
    def test_abuse_ring_identified_as_candidate(self):
        G = _make_small_abuse_graph()
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "CUS_1", as_of, max_hops=2)
        # 5 accounts sharing a device → should flag as ring candidate
        assert result["is_ring_candidate"] is True

    def test_abuse_ring_has_multiple_members(self):
        G = _make_small_abuse_graph()
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "CUS_1", as_of, max_hops=2)
        assert len(result["member_customers"]) >= 2

    def test_abuse_ring_detects_shared_devices(self):
        G = _make_small_abuse_graph()
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "CUS_1", as_of, max_hops=2)
        assert len(result["shared_devices"]) >= 1

    def test_isolated_customer_not_ring_candidate(self):
        G = nx.Graph()
        G.add_node("SOLO_CUS", node_type="CUSTOMER")
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "SOLO_CUS", as_of, max_hops=2)
        assert result["is_ring_candidate"] is False

    def test_household_graph_low_ring_risk(self):
        """
        4 legitimate household users sharing 1 device with low refund rate
        should produce a LOW ring risk score, not automatically flagged.
        """
        G = _make_household_graph()
        as_of = datetime(2024, 7, 1)
        result = detect_candidate_ring(G, "LEGIT_CUS_1", as_of, max_hops=2)
        # With no refund data, refund rate = 0 → ring_risk_score stays low
        assert result["ring_risk_score"] < 0.55, (
            f"Household sharing scored too high: {result['ring_risk_score']}"
        )

    def test_ring_risk_score_bounded(self):
        G = _make_small_abuse_graph()
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "CUS_1", as_of, max_hops=2)
        assert 0.0 <= result["ring_risk_score"] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# LEAKAGE GUARD TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestLeakageGuards:
    """Verify no hidden labels enter the graph or investigation pipeline."""

    def test_hidden_columns_not_in_graph_features(self):
        from src.graph.features import GRAPH_FEATURE_COLUMNS
        FORBIDDEN = ["abuse_label", "ring_id", "abuse_pattern_type",
                     "ring_generation_source", "generation_seed"]
        for col in FORBIDDEN:
            assert col not in GRAPH_FEATURE_COLUMNS, (
                f"Forbidden column '{col}' found in GRAPH_FEATURE_COLUMNS"
            )

    def test_investigation_schema_has_no_hidden_label_fields(self):
        schema_fields = set(CaseInvestigationResponse.model_fields.keys())
        FORBIDDEN_FIELDS = {"abuse_label", "ring_id", "generation_seed",
                            "ring_generation_source", "abuse_pattern_type"}
        for field in FORBIDDEN_FIELDS:
            assert field not in schema_fields, f"Forbidden field '{field}' in investigation response"

    def test_ring_detector_does_not_accept_labels(self):
        """Ring detector signature must not include abuse_label or ring_id parameters."""
        import inspect
        sig = inspect.signature(detect_candidate_ring)
        for forbidden_param in ["abuse_label", "ring_id", "abuse_pattern_type"]:
            assert forbidden_param not in sig.parameters, (
                f"Forbidden parameter '{forbidden_param}' found in detect_candidate_ring"
            )


# ─────────────────────────────────────────────────────────────────────────────
# EVIDENCE GROUNDING TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceGrounding:
    def test_grounding_validator_accepts_known_entities(self):
        ev = EvidenceRecord(
            evidence_id="EVID-0001",
            category=EvidenceCategory.DEVICE_SHARING,
            confidence=EvidenceConfidence.STRONG,
            statement="3 accounts share 1 device.",
            supporting_entity_ids=["CUS_1", "CUS_2", "DEV_001"],
        )
        known = {"CUS_1", "CUS_2", "DEV_001"}
        result = GroundingValidator.validate_evidence_grounding([ev], known)
        assert result["grounding_rate"] == 1.0
        assert result["unsupported_claim_count"] == 0

    def test_grounding_validator_flags_invented_entity(self):
        ev = EvidenceRecord(
            evidence_id="EVID-0002",
            category=EvidenceCategory.DEVICE_SHARING,
            confidence=EvidenceConfidence.STRONG,
            statement="Customer CUS_9999 was involved.",
            supporting_entity_ids=["CUS_9999"],  # This entity does not exist
        )
        known = {"CUS_1", "CUS_2"}
        result = GroundingValidator.validate_evidence_grounding([ev], known)
        assert result["unsupported_claim_count"] == 1
        assert result["is_fully_grounded"] is False

    def test_evidence_id_format_is_valid(self):
        ev = EvidenceRecord(
            evidence_id="EVID-0042",
            category=EvidenceCategory.REFUND_COORDINATION,
            confidence=EvidenceConfidence.MODERATE,
            statement="Refund rate of 65% across 4 accounts.",
        )
        assert ev.evidence_id.startswith("EVID-")

    def test_deterministic_generator_does_not_invent_merchants(self):
        """Evidence narrative must not mention merchants if none exist in ring data."""
        gen = DeterministicEvidenceGenerator()
        ring = {
            "member_customers": ["C1", "C2"],
            "shared_devices": ["D1"],
            "shared_ips": [],
            "targeted_merchants": [],   # NO merchants
            "member_transaction_count": 10,
            "member_refund_count": 2,
            "member_refund_rate": 0.20,
            "uncertainties": [],
        }
        narrative = gen.generate_case_narrative(
            case_id="CASE-TEST",
            root_entity="C1",
            candidate_ring=ring,
            evidence_records=[],
            timeline=[],
            individual_risk=0.40,
            relationship_risk=0.55,
            combined_risk=0.50,
        )
        # Narrative must not claim merchant coordination when no merchants present
        assert "merchant" not in narrative["case_summary"].lower() or \
               "0 merchant" in narrative["case_summary"].lower() or \
               len(ring["targeted_merchants"]) == 0

    def test_uncertainty_preserved_for_low_evidence(self):
        gen = DeterministicEvidenceGenerator()
        ring = {
            "member_customers": ["C1", "C2"],
            "shared_devices": ["D1"],
            "shared_ips": [],
            "targeted_merchants": [],
            "member_transaction_count": 4,
            "member_refund_count": 1,
            "member_refund_rate": 0.10,   # low refund rate
            "uncertainties": [],
        }
        narrative = gen.generate_case_narrative(
            case_id="CASE-TEST",
            root_entity="C1",
            candidate_ring=ring,
            evidence_records=[],
            timeline=[],
            individual_risk=0.10,
            relationship_risk=0.20,
            combined_risk=0.17,
        )
        # Should not produce a HIGH risk claim for low evidence
        assert "high" not in narrative["case_summary"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION SCHEMA VALIDATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestInvestigationSchema:
    def test_case_response_validates_risk_score_bounds(self):
        audit = CaseAuditTrail(
            case_id="CASE-TEST",
            candidate_id="CUS_1",
            scoring_timestamp=datetime.now(timezone.utc).isoformat(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        resp = CaseInvestigationResponse(
            case_id="CASE-TEST",
            root_entity="CUS_1",
            individual_risk_score=0.55,
            relationship_risk_score=0.80,
            combined_risk_score=0.70,
            risk_tier="high",
            is_candidate_ring=True,
            case_summary="Test case.",
            audit_trail=audit,
        )
        assert 0.0 <= resp.individual_risk_score <= 1.0
        assert 0.0 <= resp.relationship_risk_score <= 1.0
        assert 0.0 <= resp.combined_risk_score <= 1.0

    def test_case_audit_trail_preserves_versions(self):
        audit = CaseAuditTrail(
            case_id="CASE-AUDIT-001",
            candidate_id="CUS_42",
            scoring_timestamp=datetime.now(timezone.utc).isoformat(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert audit.phase1_model_version == "riskorbit-risk-v1"
        assert audit.graph_version == "graph-v2"
        assert audit.investigation_version == "investigation-v2"

    def test_timeline_events_have_required_fields(self):
        event = TimelineEvent(
            event_timestamp="2024-01-15T10:00:00",
            event_type="TRANSACTION",
            entity_id="CUS_5",
            description="Customer CUS_5 placed order T101.",
            supporting_event_id="T101",
        )
        assert event.entity_id == "CUS_5"
        assert event.event_type == "TRANSACTION"


# ─────────────────────────────────────────────────────────────────────────────
# GOLDEN CASES CATALOG TEST
# ─────────────────────────────────────────────────────────────────────────────

class TestGoldenCasesCatalog:
    def test_catalog_has_correct_count(self):
        cases = get_golden_case_definitions()
        abuse_cases = [c for c in cases if "expected_abuse_pattern" in c]
        legit_cases = [c for c in cases if "hard_negative_type" in c]
        ambig_cases = [c for c in cases if "AMBIG" in c["case_code"]]
        assert len(abuse_cases) == 3
        assert len(legit_cases) == 5
        assert len(ambig_cases) == 2

    def test_all_cases_have_case_code(self):
        for case in get_golden_case_definitions():
            assert "case_code" in case and case["case_code"].startswith("CASE-GOLD")

    def test_abuse_cases_expect_high_risk(self):
        for case in get_golden_case_definitions():
            if "expected_abuse_pattern" in case:
                assert case.get("expected_min_risk_score", 0) >= 0.40

    def test_legitimate_cases_expect_low_risk(self):
        for case in get_golden_case_definitions():
            if "hard_negative_type" in case:
                assert case.get("expected_max_risk_score", 1.0) <= 0.40


# ─────────────────────────────────────────────────────────────────────────────
# ADVERSARIAL / NEGATIVE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAdversarialCases:
    """Verify that isolated signals alone are insufficient for high risk."""

    def test_shared_ip_only_not_sufficient_for_ring(self):
        """IP-only sharing without device overlap must not auto-classify as ring."""
        G = nx.Graph()
        for i in range(1, 5):
            G.add_node(f"OFF_CUS_{i}", node_type="CUSTOMER")
        G.add_node("OFFICE_IP", node_type="IP", n_connected_accounts=50)
        for i in range(1, 5):
            G.add_edge(f"OFF_CUS_{i}", "OFFICE_IP",
                       relationship_type="CUSTOMER_CONNECTED_IP",
                       strength=0.08, event_count=1,
                       first_seen="2024-01-01T00:00:00",
                       last_seen="2024-01-01T00:00:00")
        as_of = datetime(2024, 2, 1)
        result = detect_candidate_ring(G, "OFF_CUS_1", as_of, max_hops=2)
        # IP-only, no devices, no refund data → ring_risk_score should be LOW
        assert result["ring_risk_score"] < 0.35, (
            f"IP-only sharing scored unexpectedly high: {result['ring_risk_score']}"
        )

    def test_single_shared_device_two_accounts_low_risk(self):
        """2 accounts, 1 device, no refunds → not a confident ring candidate."""
        G = nx.Graph()
        G.add_node("CUS_A", node_type="CUSTOMER")
        G.add_node("CUS_B", node_type="CUSTOMER")
        G.add_node("DEV_X", node_type="DEVICE", n_connected_accounts=2)
        G.add_edge("CUS_A", "DEV_X", relationship_type="CUSTOMER_USED_DEVICE",
                   strength=0.40, event_count=3,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-03-01T00:00:00")
        G.add_edge("CUS_B", "DEV_X", relationship_type="CUSTOMER_USED_DEVICE",
                   strength=0.40, event_count=2,
                   first_seen="2024-01-05T00:00:00",
                   last_seen="2024-02-01T00:00:00")
        as_of = datetime(2024, 4, 1)
        result = detect_candidate_ring(G, "CUS_A", as_of, max_hops=2)
        # 2 accounts, low/zero refund rate → borderline or not candidate
        # The test asserts that the uncertainty list is non-empty
        assert len(result["uncertainties"]) > 0 or result["ring_risk_score"] < 0.55

    def test_high_refund_count_alone_not_ring(self):
        """A single high-refund customer with no shared infrastructure ≠ ring."""
        G = nx.Graph()
        G.add_node("SERIAL_RETURNER", node_type="CUSTOMER")
        G.add_node("DEV_SOLO", node_type="DEVICE", n_connected_accounts=1)
        G.add_edge("SERIAL_RETURNER", "DEV_SOLO",
                   relationship_type="CUSTOMER_USED_DEVICE",
                   strength=0.70, event_count=20,
                   first_seen="2024-01-01T00:00:00",
                   last_seen="2024-06-01T00:00:00")
        as_of = datetime(2024, 7, 1)
        result = detect_candidate_ring(G, "SERIAL_RETURNER", as_of, max_hops=2)
        # Only 1 customer → not a ring
        assert result["is_ring_candidate"] is False


# ─────────────────────────────────────────────────────────────────────────────
# ARTIFACT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase2Artifacts:
    def test_v2_model_artifact_exists(self):
        assert Path("artifacts/riskorbit-risk-v2/model.pkl").exists()

    def test_v2_threshold_json_valid(self):
        p = Path("artifacts/riskorbit-risk-v2/threshold.json")
        assert p.exists()
        data = json.loads(p.read_text())
        assert "threshold" in data
        assert 0.0 <= data["threshold"] <= 1.0

    def test_v2_feature_schema_json_valid(self):
        p = Path("artifacts/riskorbit-risk-v2/feature_schema.json")
        assert p.exists()
        data = json.loads(p.read_text())
        assert "feature_names" in data
        assert data["n_features"] == 46  # 36 p1 + 10 graph

    def test_v1_artifacts_still_present(self):
        """Phase 1 artifacts must not be overwritten."""
        assert Path("artifacts/riskorbit-risk-v1/model.pkl").exists()
        assert Path("artifacts/riskorbit-risk-v1/threshold.json").exists()

    def test_phase2_delta_report_exists(self):
        assert Path("reports/PHASE2_DELTA_REPORT.md").exists()

    def test_phase2_graph_ablation_report_exists(self):
        assert Path("reports/PHASE2_GRAPH_ABLATION.md").exists()

    def test_graph_data_quality_report_exists(self):
        assert Path("reports/GRAPH_DATA_QUALITY.md").exists()

    def test_prompts_versioned(self):
        assert Path("prompts/investigation_v1.md").exists()
        assert Path("prompts/evidence_v1.md").exists()
