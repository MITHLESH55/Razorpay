"""
RiskOrbit — Graph-Derived Features Generator (Phase 2)

Extracts point-in-time graph features for transactions by querying the local
relationship graph surrounding each customer at scoring timestamp T.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.ring_detector import detect_candidate_ring

logger = logging.getLogger(__name__)

GRAPH_FEATURE_COLUMNS = [
    "ring_customer_count",
    "ring_device_count",
    "ring_ip_count",
    "ring_instrument_count",
    "ring_merchant_count",
    "ring_member_refund_rate",
    "ring_subgraph_density",
    "ring_edge_strength_mean",
    "ring_edge_strength_max",
    "ring_risk_score",
]


def extract_graph_features_for_transactions(
    transactions: pd.DataFrame,
    graph_engine: PaymentGraphEngine,
    max_hops: int = 2,
    as_of_time: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Extract graph-derived features for a batch of transactions.
    
    If as_of_time is provided, builds the graph as of that time.
    Otherwise, builds the graph as of the maximum timestamp in transactions.
    """
    if len(transactions) == 0:
        return pd.DataFrame(columns=GRAPH_FEATURE_COLUMNS)

    target_ts = as_of_time or transactions["timestamp"].max()
    G = graph_engine.build_networkx_graph_as_of(target_ts, min_edge_strength=0.05)

    txn_sub, _, ref_sub = graph_engine.get_events_as_of(target_ts)

    # Pre-compute customer level transaction and refund counts for lightning-fast lookups
    cust_txn_counts = txn_sub.groupby("customer_id").size().to_dict()
    if len(ref_sub) > 0 and "transaction_id" in ref_sub.columns:
        ref_merged = ref_sub.merge(txn_sub[["transaction_id", "customer_id"]], on="transaction_id", how="inner")
        cust_ref_counts = ref_merged.groupby("customer_id").size().to_dict()
    else:
        cust_ref_counts = {}

    cust_stats_map = {
        cid: {
            "txn_count": cust_txn_counts.get(cid, 0),
            "ref_count": cust_ref_counts.get(cid, 0),
        }
        for cid in txn_sub["customer_id"].unique()
    }

    # Cache ring detection per customer_id to avoid redundant graph traversals
    unique_custs = transactions["customer_id"].unique()
    cust_ring_map = {}

    for cid in unique_custs:
        res = detect_candidate_ring(
            G=G,
            root_customer_id=cid,
            as_of_time=target_ts,
            cust_stats_map=cust_stats_map,
            max_hops=max_hops,
        )
        sub_stats = res["case_subgraph"]["statistics"]
        edges = res["case_subgraph"]["edges"]
        edge_strengths = [e["strength"] for e in edges if e.get("strength", 0) > 0]

        cust_ring_map[cid] = {
            "ring_customer_count": float(len(res["member_customers"])),
            "ring_device_count": float(len(res["shared_devices"])),
            "ring_ip_count": float(len(res["shared_ips"])),
            "ring_instrument_count": float(len(res["shared_instruments"])),
            "ring_merchant_count": float(len(res["targeted_merchants"])),
            "ring_member_refund_rate": float(res.get("member_refund_rate", 0.0)),
            "ring_subgraph_density": float(sub_stats.get("subgraph_density", 0.0)),
            "ring_edge_strength_mean": float(np.mean(edge_strengths)) if edge_strengths else 0.0,
            "ring_edge_strength_max": float(np.max(edge_strengths)) if edge_strengths else 0.0,
            "ring_risk_score": float(res.get("ring_risk_score", 0.0)),
        }

    rows = []
    for cid in transactions["customer_id"]:
        feat_dict = cust_ring_map.get(cid, {col: 0.0 for col in GRAPH_FEATURE_COLUMNS})
        rows.append(feat_dict)

    df_out = pd.DataFrame(rows, columns=GRAPH_FEATURE_COLUMNS)
    return df_out.reset_index(drop=True)
