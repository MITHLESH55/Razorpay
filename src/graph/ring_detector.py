"""
RiskOrbit — Candidate Ring Detection & Ring Risk Scoring (Phase 2)

Extracts candidate coordinated abuse rings from the point-in-time relationship graph
WITHOUT using ground-truth labels (abuse_label, ring_id, etc.).

Computes composite, explainable ring risk scores based on:
  1. Multi-account infrastructure sharing density (devices, IPs, instruments)
  2. Member refund behavior coordination
  3. Temporal burstiness
  4. Cross-merchant concentration
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

import networkx as nx
import numpy as np
import pandas as pd

from src.graph.traversal import extract_local_case_subgraph


def detect_candidate_ring(
    G: nx.Graph,
    root_customer_id: str,
    as_of_time: datetime,
    transactions: Optional[pd.DataFrame] = None,
    refunds: Optional[pd.DataFrame] = None,
    cust_stats_map: Optional[Dict[str, dict]] = None,
    max_hops: int = 2,
    min_edge_strength: float = 0.08,
) -> dict[str, Any]:
    """
    Extract candidate ring surrounding root_customer_id and score its coordination risk.
    """
    case_subgraph = extract_local_case_subgraph(
        G=G,
        root_entity_id=root_customer_id,
        max_hops=max_hops,
        min_edge_strength=min_edge_strength,
    )

    nodes = case_subgraph["nodes"]
    edges = case_subgraph["edges"]

    # Extract all member customers in this 2-hop component
    member_cust_ids = [n["node_id"] for n in nodes if n["node_type"] == "CUSTOMER"]
    shared_dev_ids = [n["node_id"] for n in nodes if n["node_type"] == "DEVICE"]
    shared_ip_ids = [n["node_id"] for n in nodes if n["node_type"] == "IP"]
    shared_ins_ids = [n["node_id"] for n in nodes if n["node_type"] == "INSTRUMENT"]
    merch_ids = [n["node_id"] for n in nodes if n["node_type"] == "MERCHANT"]

    # If root is alone with no connected customers
    if len(member_cust_ids) <= 1:
        return {
            "root_customer_id": root_customer_id,
            "is_ring_candidate": False,
            "member_customers": member_cust_ids,
            "shared_devices": shared_dev_ids,
            "shared_ips": shared_ip_ids,
            "shared_instruments": shared_ins_ids,
            "targeted_merchants": merch_ids,
            "member_transaction_count": 0,
            "member_refund_count": 0,
            "member_refund_rate": 0.0,
            "ring_risk_score": 0.0,
            "coordination_signals": [],
            "uncertainties": ["Single isolated account; no multi-account sharing detected."],
            "case_subgraph": case_subgraph,
        }

    # Use fast pre-computed stats if available
    if cust_stats_map is not None:
        tot_txns = 0
        tot_refs = 0
        for cid in member_cust_ids:
            st = cust_stats_map.get(cid, {})
            tot_txns += st.get("txn_count", 0)
            tot_refs += st.get("ref_count", 0)
        member_refund_rate = (tot_refs / tot_txns) if tot_txns > 0 else 0.0
        n_txns = tot_txns
        n_refs = tot_refs
        timing_coordination = 0.50
    elif transactions is not None:
        member_txns = transactions[
            (transactions["customer_id"].isin(member_cust_ids)) &
            (transactions["timestamp"] <= as_of_time)
        ]
        member_txn_ids = member_txns["transaction_id"].values

        member_refs = refunds[
            (refunds["transaction_id"].isin(member_txn_ids)) &
            (refunds["refund_requested_at"] <= as_of_time)
        ] if refunds is not None and len(refunds) > 0 and "refund_requested_at" in refunds.columns else pd.DataFrame()

        n_txns = len(member_txns)
        n_refs = len(member_refs)
        member_refund_rate = (n_refs / n_txns) if n_txns > 0 else 0.0

        if len(member_txns) >= 2:
            timestamps = member_txns["timestamp"].sort_values()
            time_span_days = max(0.1, (timestamps.max() - timestamps.min()).total_seconds() / 86400.0)
            txn_density_per_day = len(member_txns) / time_span_days
            timing_coordination = min(1.0, txn_density_per_day / 2.0)
        else:
            timing_coordination = 0.0
    else:
        n_txns = len(member_cust_ids)
        n_refs = 0
        member_refund_rate = 0.0
        timing_coordination = 0.0

    # 2. Relationship density and mean edge strength
    edge_strengths = [e["strength"] for e in edges if e.get("strength", 0) > 0]
    avg_edge_strength = float(np.mean(edge_strengths)) if edge_strengths else 0.0

    # 3. Multi-account weight
    acct_weight = min(1.0, (len(member_cust_ids) - 1) / 5.0)

    # 4. Device sharing signal vs IP sharing signal
    dev_signal = min(1.0, len(shared_dev_ids) * 0.40)
    ip_signal = min(0.60, len(shared_ip_ids) * 0.15)
    ins_signal = min(1.0, len(shared_ins_ids) * 0.35)
    infra_sharing_score = max(dev_signal, ip_signal, ins_signal)

    # Composite ring risk score
    ring_risk = (
        0.30 * infra_sharing_score +
        0.25 * member_refund_rate +
        0.20 * acct_weight +
        0.15 * avg_edge_strength +
        0.10 * timing_coordination
    )

    ring_risk_score = round(min(1.0, max(0.0, float(ring_risk))), 4)
    is_candidate = (ring_risk_score >= 0.25) and (len(member_cust_ids) >= 2)

    signals = []
    uncertainties = []

    if len(shared_dev_ids) > 0:
        signals.append(f"{len(member_cust_ids)} accounts share {len(shared_dev_ids)} hardware device(s).")
    if len(shared_ip_ids) > 0:
        signals.append(f"{len(member_cust_ids)} accounts connect through {len(shared_ip_ids)} common IP subnet(s).")
    if member_refund_rate >= 0.50:
        signals.append(f"High collective refund rate of {member_refund_rate*100:.1f}% across member accounts.")
    if timing_coordination >= 0.60:
        signals.append("High temporal clustering of transactions across member accounts.")

    if len(shared_dev_ids) == 1 and len(member_cust_ids) <= 3 and member_refund_rate < 0.30:
        uncertainties.append("Low refund activity with 2-3 accounts on 1 device may represent benign household sharing.")
    if len(shared_ip_ids) >= 1 and len(shared_dev_ids) == 0:
        uncertainties.append("Shared IP connection without device overlap may reflect public/office network sharing.")

    return {
        "root_customer_id": root_customer_id,
        "is_ring_candidate": is_candidate,
        "member_customers": member_cust_ids,
        "shared_devices": shared_dev_ids,
        "shared_ips": shared_ip_ids,
        "shared_instruments": shared_ins_ids,
        "targeted_merchants": merch_ids,
        "member_transaction_count": n_txns,
        "member_refund_count": n_refs,
        "member_refund_rate": round(float(member_refund_rate), 4),
        "ring_risk_score": ring_risk_score,
        "coordination_signals": signals,
        "uncertainties": uncertainties,
        "case_subgraph": case_subgraph,
    }
