"""
RiskOrbit — Bounded Multi-Hop Graph Traversal (Phase 2)

Extracts compact, explainable local case subgraphs around a candidate root entity.
Enforces:
  - Bounded traversal depth (default max_hops=2)
  - Infrastructure-based account bridging (via Devices, IPs, Instruments)
  - Merchant hubness protection (merchants are endpoints, not account bridges)
  - Edge strength attribution and event count preservation
"""
from __future__ import annotations

from typing import Any, Optional, Set
import networkx as nx


def extract_local_case_subgraph(
    G: nx.Graph,
    root_entity_id: str,
    max_hops: int = 2,
    min_edge_strength: float = 0.05,
    max_nodes: int = 50,
) -> dict[str, Any]:
    """
    Extract a bounded multi-hop neighborhood around root_entity_id.
    """
    if root_entity_id not in G:
        return {
            "root_entity": root_entity_id,
            "max_hops": max_hops,
            "nodes": [{"node_id": root_entity_id, "node_type": "UNKNOWN", "hop_distance": 0}],
            "edges": [],
            "paths": {},
            "statistics": {
                "total_nodes": 1,
                "total_edges": 0,
                "customer_count": 1 if root_entity_id.startswith("CUS") else 0,
                "device_count": 0,
                "ip_count": 0,
                "instrument_count": 0,
                "merchant_count": 0,
                "subgraph_density": 0.0,
            },
        }

    # 1. Direct 1-hop neighbors of root
    direct_neighbors = list(G.neighbors(root_entity_id))

    # Identify bridge infrastructure (devices, ips, instruments) and direct merchants
    bridge_nodes: Set[str] = set()
    direct_merchants: Set[str] = set()
    node_hops = {root_entity_id: 0}

    for n in direct_neighbors:
        ntype = G.nodes[n].get("node_type", "UNKNOWN")
        edge_data = G.get_edge_data(root_entity_id, n, {})
        strength = edge_data.get("strength", 1.0)
        if strength >= min_edge_strength:
            node_hops[n] = 1
            if ntype in ("DEVICE", "IP", "INSTRUMENT"):
                bridge_nodes.add(n)
            elif ntype == "MERCHANT":
                direct_merchants.add(n)

    # 2. 2-hop accounts connected via bridge infrastructure (NOT through merchants)
    connected_accounts: Set[str] = set()
    if max_hops >= 2:
        for b_node in bridge_nodes:
            for cand_cust in G.neighbors(b_node):
                if cand_cust != root_entity_id:
                    cand_type = G.nodes[cand_cust].get("node_type", "UNKNOWN")
                    if cand_type == "CUSTOMER":
                        edge_data = G.get_edge_data(b_node, cand_cust, {})
                        if edge_data.get("strength", 1.0) >= min_edge_strength:
                            connected_accounts.add(cand_cust)
                            if cand_cust not in node_hops:
                                node_hops[cand_cust] = 2

    # 3. Collect all active nodes in this local case graph
    active_nodes = {root_entity_id} | set(direct_neighbors) | connected_accounts
    if len(active_nodes) > max_nodes:
        # Prioritize root, customers, devices, ips, instruments, merchants
        sorted_active = sorted(
            active_nodes,
            key=lambda n: (
                node_hops.get(n, 3),
                0 if G.nodes[n].get("node_type") in ("CUSTOMER", "DEVICE") else 1
            )
        )[:max_nodes]
        active_nodes = set(sorted_active)

    subG = G.subgraph(active_nodes).copy()

    # Collect node representations
    nodes_out = []
    cust_count = 0
    dev_count = 0
    ip_count = 0
    ins_count = 0
    merch_count = 0

    for node_id in subG.nodes():
        attrs = G.nodes[node_id]
        ntype = attrs.get("node_type", "UNKNOWN")
        if ntype == "CUSTOMER":
            cust_count += 1
        elif ntype == "DEVICE":
            dev_count += 1
        elif ntype == "IP":
            ip_count += 1
        elif ntype == "INSTRUMENT":
            ins_count += 1
        elif ntype == "MERCHANT":
            merch_count += 1

        nodes_out.append({
            "node_id": node_id,
            "node_type": ntype,
            "hop_distance": node_hops.get(node_id, 2),
            "attributes": {k: v for k, v in attrs.items() if k != "node_type"},
        })

    # Collect edge representations
    edges_out = []
    for u, v, d in subG.edges(data=True):
        edges_out.append({
            "source_id": u,
            "target_id": v,
            "relationship_type": d.get("relationship_type", "CONNECTED_TO"),
            "strength": d.get("strength", 1.0),
            "event_count": d.get("event_count", 1),
            "first_seen": d.get("first_seen"),
            "last_seen": d.get("last_seen"),
            "strength_components": d.get("strength_components", {}),
        })

    n_nodes = len(nodes_out)
    n_edges = len(edges_out)
    possible_edges = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 1.0
    density = round(float(n_edges / possible_edges), 4)

    return {
        "root_entity": root_entity_id,
        "max_hops": max_hops,
        "nodes": nodes_out,
        "edges": edges_out,
        "statistics": {
            "total_nodes": n_nodes,
            "total_edges": n_edges,
            "customer_count": cust_count,
            "device_count": dev_count,
            "ip_count": ip_count,
            "instrument_count": ins_count,
            "merchant_count": merch_count,
            "subgraph_density": density,
        },
    }
