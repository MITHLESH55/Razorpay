"""
RiskOrbit — Phase 3.1: Edge Diversity Scoring

Distinguishes multi-signal corroboration from repeated single-signal evidence.

Independent evidence families:
    - CONNECTIVITY: device, IP, instrument (infrastructure sharing)
    - BEHAVIORAL: temporal coordination, merchant overlap
    - OUTCOME: refund coordination

Do NOT double-count correlated signals (e.g., same-device events counted once).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import networkx as nx


EdgeType = Literal["device", "ip", "instrument", "merchant", "temporal", "refund"]


@dataclass
class EdgeDiversityScore:
    """Edge diversity analysis for a customer pair relationship."""

    customer_id: str
    related_customer_id: str
    total_edge_count: int
    unique_edge_types: set[str]
    diversity_score: float  # [0, 1]
    has_device: bool
    has_ip: bool
    has_instrument: bool
    has_merchant: bool
    has_temporal: bool
    has_refund: bool
    connectivity_evidence: int  # device + IP + instrument (max 3)
    behavioral_evidence: int    # temporal + merchant (max 2)
    outcome_evidence: int       # refund (max 1)


def compute_edge_diversity(
    graph: nx.Graph,
    customer_a: str,
    customer_b: str,
) -> EdgeDiversityScore:
    """
    Compute edge diversity score between two customers.

    Higher diversity = stronger evidence (multiple independent signal families).

    Evidence families:
        CONNECTIVITY: device, IP, instrument (share infrastructure)
        BEHAVIORAL: temporal coordination, merchant overlap
        OUTCOME: refund coordination

    Args:
        graph: NetworkX graph with edge 'type' attributes
        customer_a: First customer node ID
        customer_b: Second customer node ID (or intermediate entity)

    Returns:
        EdgeDiversityScore with diversity analysis

    Raises:
        ValueError: If customers not in graph
    """
    if customer_a not in graph:
        raise ValueError(f"Customer {customer_a} not in graph")
    if customer_b not in graph:
        raise ValueError(f"Customer {customer_b} not in graph")

    # Collect all edge types between the two nodes (direct or 1-hop paths through shared entities)
    edge_types = set()

    # Direct edge
    if graph.has_edge(customer_a, customer_b):
        edge_data = graph.get_edge_data(customer_a, customer_b)
        if edge_data and "type" in edge_data:
            edge_types.add(edge_data["type"])

    # 1-hop paths through intermediate entities (device, IP, instrument, merchant)
    # This captures shared infrastructure
    neighbors_a = set(graph.neighbors(customer_a))
    neighbors_b = set(graph.neighbors(customer_b))
    shared_entities = neighbors_a & neighbors_b

    for entity in shared_entities:
        # Check node type of shared entity
        node_type = graph.nodes[entity].get("node_type", "").lower()
        if node_type in ("device", "ip", "instrument", "merchant", "refund", "order"):
            edge_types.add("temporal" if node_type == "order" else node_type)

        # Get edge type from customer_a to shared entity
        edge_data_a = graph.get_edge_data(customer_a, entity) or {}
        rel_a = edge_data_a.get("relationship_type", "").lower()
        type_a = edge_data_a.get("type", "").lower()
        for s in (rel_a, type_a):
            if "device" in s: edge_types.add("device")
            elif "ip" in s: edge_types.add("ip")
            elif "instrument" in s: edge_types.add("instrument")
            elif "merchant" in s: edge_types.add("merchant")
            elif "refund" in s: edge_types.add("refund")
            elif "temporal" in s or "order" in s: edge_types.add("temporal")

        # Also check edge from customer_b to shared entity
        edge_data_b = graph.get_edge_data(customer_b, entity) or {}
        rel_b = edge_data_b.get("relationship_type", "").lower()
        type_b = edge_data_b.get("type", "").lower()
        for s in (rel_b, type_b):
            if "device" in s: edge_types.add("device")
            elif "ip" in s: edge_types.add("ip")
            elif "instrument" in s: edge_types.add("instrument")
            elif "merchant" in s: edge_types.add("merchant")
            elif "refund" in s: edge_types.add("refund")
            elif "temporal" in s or "order" in s: edge_types.add("temporal")

    # Categorize edge types into evidence families
    has_device = "device" in edge_types
    has_ip = "ip" in edge_types
    has_instrument = "instrument" in edge_types
    has_merchant = "merchant" in edge_types
    has_temporal = "temporal" in edge_types
    has_refund = "refund" in edge_types

    # Count independent evidence families (not individual edges)
    connectivity_evidence = sum([has_device, has_ip, has_instrument])
    behavioral_evidence = sum([has_temporal, has_merchant])
    outcome_evidence = int(has_refund)

    total_families = connectivity_evidence + behavioral_evidence + outcome_evidence

    # Diversity score: ratio of evidence families to maximum possible (6)
    # Weight families more than individual edge types to reward independent corroboration
    max_families = 3 + 2 + 1  # connectivity + behavioral + outcome

    if total_families == 0:
        diversity_score = 0.0
    else:
        # Non-linear scoring: reward multi-family evidence more
        # 1 family = 0.20, 2 families = 0.50, 3 families = 0.75, 4+ families = 0.90+
        diversity_score = min(1.0, 0.15 * total_families + 0.05 * len(edge_types))

    return EdgeDiversityScore(
        customer_id=customer_a,
        related_customer_id=customer_b,
        total_edge_count=len(edge_types),
        unique_edge_types=edge_types,
        diversity_score=round(diversity_score, 4),
        has_device=has_device,
        has_ip=has_ip,
        has_instrument=has_instrument,
        has_merchant=has_merchant,
        has_temporal=has_temporal,
        has_refund=has_refund,
        connectivity_evidence=connectivity_evidence,
        behavioral_evidence=behavioral_evidence,
        outcome_evidence=outcome_evidence,
    )


def compute_multi_member_diversity(
    graph: nx.Graph,
    primary_customer: str,
    member_customers: list[str],
) -> dict[str, EdgeDiversityScore]:
    """
    Compute edge diversity for primary customer against multiple ring members.

    Args:
        graph: NetworkX graph
        primary_customer: Primary suspect customer
        member_customers: List of ring member customer IDs

    Returns:
        Dictionary mapping member_customer_id -> EdgeDiversityScore
    """
    diversity_scores = {}

    for member in member_customers:
        if member == primary_customer:
            continue

        try:
            score = compute_edge_diversity(graph, primary_customer, member)
            diversity_scores[member] = score
        except ValueError:
            # Member not in graph (should not happen in practice)
            continue

    return diversity_scores


def aggregate_diversity_score(diversity_scores: list[EdgeDiversityScore]) -> float:
    """
    Aggregate diversity scores across multiple relationships.

    Used when a customer is connected to multiple ring members.
    Takes the maximum diversity score (strongest evidence path).

    Args:
        diversity_scores: List of EdgeDiversityScore objects

    Returns:
        Aggregated diversity score [0, 1]
    """
    if not diversity_scores:
        return 0.0

    # Use maximum diversity (strongest evidence path)
    return max(score.diversity_score for score in diversity_scores)
