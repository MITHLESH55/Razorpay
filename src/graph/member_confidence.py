"""
RiskOrbit — Phase 3.1: Member Confidence Model

Computes deterministic, explainable confidence scores for ring members.

Distinguishes:
    PRIMARY: Strong direct + contextual evidence
    SECONDARY: Strong relational but weaker direct evidence
    TERTIARY: Weak/indirect graph relationship

Formula combines:
    - Phase 1 transaction risk
    - Edge strength (reusing existing hubness-corrected strength)
    - Edge diversity (multiple independent signal families)
    - Graph distance (closer = stronger)
    - Temporal relevance (recent relationships stronger)
    - Evidence strength

Does NOT use:
    - abuse_label
    - ring_id
    - pattern_type
    - future events
    - ground truth
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

import networkx as nx

from src.graph.edge_diversity import compute_edge_diversity, EdgeDiversityScore


MemberTier = Literal["PRIMARY", "SECONDARY", "TERTIARY"]


@dataclass
class MemberConfidence:
    """
    Member confidence assessment for a ring member.

    All scores in [0, 1] range.
    """
    customer_id: str
    confidence_score: float  # [0, 1] composite confidence
    tier: MemberTier
    phase1_risk: float  # Individual transaction risk from Phase 1
    supporting_edge_count: int
    edge_diversity_score: float
    avg_edge_strength: float
    max_edge_strength: float
    graph_distance: int  # Hops from primary suspect (1 or 2)
    temporal_relevance: float  # Recent activity weight
    evidence_strength: float  # Evidence quality score

    # Breakdown for explainability
    confidence_components: dict[str, float]


def compute_member_confidence(
    customer_id: str,
    primary_suspect_id: str,
    graph: nx.Graph,
    phase1_risk_score: float,
    graph_distance: int,
    as_of_time: datetime,
    connected_entities: list[str],  # Shared devices, IPs, instruments
    edge_strengths: dict[str, float],  # entity_id -> strength
    evidence_records: Optional[list] = None,
) -> MemberConfidence:
    """
    Compute deterministic confidence score for a ring member.

    Args:
        customer_id: Customer being assessed
        primary_suspect_id: Primary suspect (root of investigation)
        graph: NetworkX graph with edge attributes
        phase1_risk_score: Phase 1 individual transaction risk [0, 1]
        graph_distance: Hops from primary (1=direct, 2=2-hop)
        as_of_time: Point-in-time cutoff
        connected_entities: List of shared entity IDs (devices, IPs, etc)
        edge_strengths: Mapping of entity_id -> edge strength [0, 1]
        evidence_records: Optional evidence list for evidence strength

    Returns:
        MemberConfidence with tier assignment and explainability
    """
    # 1. Edge diversity (multi-signal corroboration)
    try:
        diversity = compute_edge_diversity(graph, primary_suspect_id, customer_id)
        edge_diversity_score = diversity.diversity_score
    except (ValueError, KeyError):
        # Customers not directly connected; assess via shared entities
        edge_diversity_score = 0.0
        if connected_entities:
            # Estimate diversity from entity types
            entity_types = set()
            for ent_id in connected_entities:
                if ent_id in graph.nodes:
                    node_data = graph.nodes[ent_id]
                    if "node_type" in node_data:
                        entity_types.add(node_data["node_type"].lower())
            # Diversity based on unique entity types
            edge_diversity_score = min(1.0, len(entity_types) * 0.25)

    # 2. Edge strength (reuse existing hubness-corrected strength)
    strengths = list(edge_strengths.values()) if edge_strengths else []
    avg_edge_strength = sum(strengths) / len(strengths) if strengths else 0.0
    max_edge_strength = max(strengths) if strengths else 0.0
    supporting_edge_count = len(connected_entities)

    # 3. Graph distance penalty (closer = stronger)
    # Distance 1 (direct) = no penalty, Distance 2 = moderate penalty
    if graph_distance == 1:
        distance_factor = 1.0
    elif graph_distance == 2:
        distance_factor = 0.70  # 30% penalty for 2-hop
    else:
        distance_factor = 0.40  # 60% penalty for 3+ hops (should not occur with max_hops=2)

    # 4. Temporal relevance
    # If we have recent activity, weight it higher
    # For now, use max_edge_strength as proxy (recent edges have higher strength due to recency_score)
    temporal_relevance = max_edge_strength  # Already includes recency in edge strength

    # 5. Evidence strength
    # If evidence_records provided, assess quality
    if evidence_records:
        # Count high-quality evidence (non-trivial, grounded evidence)
        evidence_strength = min(1.0, len(evidence_records) * 0.15)
    else:
        # Fallback: use edge diversity as evidence proxy
        evidence_strength = edge_diversity_score

    # 6. Composite confidence formula
    # Weighted combination of signals with validation-tunable weights
    # Current weights (to be validated on validation set):
    w_phase1 = 0.25      # Individual transaction risk
    w_diversity = 0.20   # Multiple independent signals
    w_strength = 0.20    # Edge strength (hubness-corrected)
    w_distance = 0.15    # Graph proximity
    w_temporal = 0.10    # Recency
    w_evidence = 0.10    # Evidence quality

    # Compute weighted score
    confidence_raw = (
        w_phase1 * phase1_risk_score +
        w_diversity * edge_diversity_score +
        w_strength * max_edge_strength +  # Use max (strongest connection)
        w_distance * distance_factor +
        w_temporal * temporal_relevance +
        w_evidence * evidence_strength
    )

    # Confidence must be in [0, 1]
    confidence_score = max(0.0, min(1.0, confidence_raw))

    # 7. Tier assignment (validation-tunable thresholds)
    # These thresholds should be selected from validation experiments
    # Current heuristic thresholds:
    PRIMARY_THRESHOLD = 0.65    # High confidence
    SECONDARY_THRESHOLD = 0.35  # Moderate confidence

    if confidence_score >= PRIMARY_THRESHOLD:
        tier = "PRIMARY"
    elif confidence_score >= SECONDARY_THRESHOLD:
        tier = "SECONDARY"
    else:
        tier = "TERTIARY"

    # 8. Explainability breakdown
    confidence_components = {
        "phase1_risk_contribution": round(w_phase1 * phase1_risk_score, 4),
        "diversity_contribution": round(w_diversity * edge_diversity_score, 4),
        "strength_contribution": round(w_strength * max_edge_strength, 4),
        "distance_contribution": round(w_distance * distance_factor, 4),
        "temporal_contribution": round(w_temporal * temporal_relevance, 4),
        "evidence_contribution": round(w_evidence * evidence_strength, 4),
    }

    return MemberConfidence(
        customer_id=customer_id,
        confidence_score=round(confidence_score, 4),
        tier=tier,
        phase1_risk=round(phase1_risk_score, 4),
        supporting_edge_count=supporting_edge_count,
        edge_diversity_score=round(edge_diversity_score, 4),
        avg_edge_strength=round(avg_edge_strength, 4),
        max_edge_strength=round(max_edge_strength, 4),
        graph_distance=graph_distance,
        temporal_relevance=round(temporal_relevance, 4),
        evidence_strength=round(evidence_strength, 4),
        confidence_components=confidence_components,
    )


def compute_ring_member_confidences(
    primary_suspect_id: str,
    member_customer_ids: list[str],
    graph: nx.Graph,
    phase1_scores: dict[str, float],  # customer_id -> phase1_risk
    as_of_time: datetime,
    max_hops: int = 2,
) -> dict[str, MemberConfidence]:
    """
    Compute confidence scores for all members of a detected ring.

    Args:
        primary_suspect_id: Root customer being investigated
        member_customer_ids: List of ring member customer IDs (including primary)
        graph: NetworkX graph
        phase1_scores: Mapping of customer_id -> Phase 1 risk score
        as_of_time: Point-in-time cutoff
        max_hops: Maximum graph distance to consider

    Returns:
        Dictionary mapping customer_id -> MemberConfidence
    """
    confidences = {}

    for member_id in member_customer_ids:
        if member_id == primary_suspect_id:
            # Primary suspect gets maximum confidence by definition
            confidences[member_id] = MemberConfidence(
                customer_id=member_id,
                confidence_score=1.0,
                tier="PRIMARY",
                phase1_risk=phase1_scores.get(member_id, 0.0),
                supporting_edge_count=0,
                edge_diversity_score=1.0,
                avg_edge_strength=1.0,
                max_edge_strength=1.0,
                graph_distance=0,
                temporal_relevance=1.0,
                evidence_strength=1.0,
                confidence_components={
                    "phase1_risk_contribution": phase1_scores.get(member_id, 0.0),
                    "diversity_contribution": 0.25,
                    "strength_contribution": 0.25,
                    "distance_contribution": 0.25,
                    "temporal_contribution": 0.125,
                    "evidence_contribution": 0.125,
                },
            )
            continue

        # Compute shortest path distance
        try:
            path_length = nx.shortest_path_length(graph, primary_suspect_id, member_id)
            graph_distance = min(path_length, max_hops)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Not connected in graph
            graph_distance = max_hops + 1

        # Find shared entities (intermediate nodes in paths)
        connected_entities = []
        edge_strengths = {}

        try:
            # Get all simple paths up to max_hops
            paths = nx.all_simple_paths(graph, primary_suspect_id, member_id, cutoff=max_hops)
            for path in paths:
                # Intermediate nodes are shared entities
                for node in path[1:-1]:  # Exclude source and target
                    if node not in connected_entities:
                        connected_entities.append(node)
                        # Get edge strength from graph
                        for i in range(len(path) - 1):
                            edge_data = graph.get_edge_data(path[i], path[i+1])
                            if edge_data and "strength" in edge_data:
                                edge_strengths[node] = max(
                                    edge_strengths.get(node, 0.0),
                                    edge_data["strength"]
                                )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Compute confidence
        phase1_risk = phase1_scores.get(member_id, 0.0)

        confidence = compute_member_confidence(
            customer_id=member_id,
            primary_suspect_id=primary_suspect_id,
            graph=graph,
            phase1_risk_score=phase1_risk,
            graph_distance=graph_distance,
            as_of_time=as_of_time,
            connected_entities=connected_entities,
            edge_strengths=edge_strengths,
            evidence_records=None,  # Can be passed from investigation agent
        )

        confidences[member_id] = confidence

    return confidences


def filter_members_by_tier(
    confidences: dict[str, MemberConfidence],
    min_tier: MemberTier = "SECONDARY",
) -> list[str]:
    """
    Filter ring members by minimum confidence tier.

    Args:
        confidences: Member confidence mapping
        min_tier: Minimum tier to include ("PRIMARY", "SECONDARY", or "TERTIARY")

    Returns:
        List of customer IDs meeting minimum tier threshold
    """
    tier_order = {"PRIMARY": 3, "SECONDARY": 2, "TERTIARY": 1}
    min_level = tier_order[min_tier]

    return [
        cid for cid, conf in confidences.items()
        if tier_order[conf.tier] >= min_level
    ]


def filter_members_by_confidence(
    confidences: dict[str, MemberConfidence],
    min_confidence: float = 0.35,
) -> list[str]:
    """
    Filter ring members by minimum confidence score.

    Args:
        confidences: Member confidence mapping
        min_confidence: Minimum confidence score threshold [0, 1]

    Returns:
        List of customer IDs meeting minimum confidence threshold
    """
    return [
        cid for cid, conf in confidences.items()
        if conf.confidence_score >= min_confidence
    ]
