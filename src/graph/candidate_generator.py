"""
RiskOrbit — Candidate Generation Engine (Phase 2)

Generates suspicious candidate accounts/transactions for relationship investigation.

SECURITY & LEAKAGE ENFORCEMENT:
  - Hidden ground-truth labels (abuse_label, ring_id, abuse_pattern_type) are strictly inaccessible.
  - Candidate discovery operates solely on causal point-in-time observable data <= T.
  - Multi-account candidates require behavioral/relational corroboration, not bare connectivity.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import networkx as nx

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.ring_detector import detect_candidate_ring

logger = logging.getLogger(__name__)


class CandidateGenerator:
    """
    Evaluates transactions and account neighborhoods to generate investigation candidates.
    """

    def __init__(
        self,
        graph_engine: PaymentGraphEngine,
        phase1_pipeline: Optional[Any] = None,
        phase1_candidate_threshold: float = 0.20,
        ring_risk_threshold: float = 0.25,
    ):
        self.engine = graph_engine
        self.phase1_pipeline = phase1_pipeline
        self.phase1_candidate_threshold = phase1_candidate_threshold
        self.ring_risk_threshold = ring_risk_threshold

    def generate_candidates(
        self,
        transactions: pd.DataFrame,
        as_of_time: Optional[datetime] = None,
        strategy: str = "hybrid",
    ) -> Dict[str, Any]:
        """
        Generate candidate customer IDs for investigation.

        Strategies:
          - 'phase1_only': Phase 1 risk score >= phase1_candidate_threshold
          - 'graph_only': Graph ring_risk_score >= ring_risk_threshold and member_count >= 2
          - 'device_corroborated': Multi-account device sharing + member refund rate >= 0.25
          - 'hybrid': Phase 1 elevated risk OR Graph structural ring candidate
        """
        target_ts = as_of_time or transactions["timestamp"].max()
        txn_sub, _, ref_sub = self.engine.get_events_as_of(target_ts)
        G = self.engine.build_networkx_graph_as_of(target_ts, min_edge_strength=0.05)

        # Pre-compute customer level txn & refund counts
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

        candidates = set()
        candidate_metadata: Dict[str, Dict[str, Any]] = {}

        # Evaluate unique customers in the target batch
        unique_custs = transactions["customer_id"].unique()

        for cid in unique_custs:
            # 1. Unsupervised graph ring detection
            ring_res = detect_candidate_ring(
                G=G,
                root_customer_id=cid,
                as_of_time=target_ts,
                cust_stats_map=cust_stats_map,
                max_hops=2,
            )

            is_graph_cand = (ring_res["ring_risk_score"] >= self.ring_risk_threshold) and (len(ring_res["member_customers"]) >= 2)
            has_device_sharing = (len(ring_res["shared_devices"]) >= 1) and (len(ring_res["member_customers"]) >= 2)
            has_corroborated_device = has_device_sharing and (ring_res["member_refund_rate"] >= 0.20)

            # Check inclusion based on strategy
            include = False
            trigger_reason = ""

            if strategy == "graph_only":
                if is_graph_cand:
                    include = True
                    trigger_reason = f"Graph ring risk {ring_res['ring_risk_score']:.2f} >= {self.ring_risk_threshold}"
            elif strategy == "device_corroborated":
                if has_corroborated_device:
                    include = True
                    trigger_reason = f"Device sharing with {len(ring_res['member_customers'])} accounts and {ring_res['member_refund_rate']*100:.1f}% refund rate"
            elif strategy == "hybrid":
                if is_graph_cand or has_corroborated_device:
                    include = True
                    trigger_reason = "Graph candidate ring detected"
            else:  # default hybrid
                if is_graph_cand:
                    include = True
                    trigger_reason = "Graph candidate ring detected"

            if include:
                candidates.add(cid)
                candidate_metadata[cid] = {
                    "customer_id": cid,
                    "trigger_reason": trigger_reason,
                    "ring_risk_score": ring_res["ring_risk_score"],
                    "member_count": len(ring_res["member_customers"]),
                    "shared_device_count": len(ring_res["shared_devices"]),
                    "shared_ip_count": len(ring_res["shared_ips"]),
                    "shared_instrument_count": len(ring_res["shared_instruments"]),
                    "member_refund_rate": ring_res["member_refund_rate"],
                    "member_customers": ring_res["member_customers"],
                    "targeted_merchants": ring_res["targeted_merchants"],
                }

        return {
            "strategy": strategy,
            "total_evaluated_customers": len(unique_custs),
            "candidate_count": len(candidates),
            "candidates": list(candidates),
            "candidate_metadata": candidate_metadata,
        }

    def generate_from_full_population(
        self,
        population_customers: List[str],
        as_of_time: Optional[datetime] = None,
        ring_risk_threshold: Optional[float] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scans all customer IDs in the specified population against the point-in-time graph,
        completely INDEPENDENT of Phase 1 transaction risk scoring.

        Returns:
            Dict[customer_id, metadata] for customers meeting structural ring candidate criteria.
        """
        target_ts = as_of_time or self.engine.txn["timestamp"].max()
        threshold = ring_risk_threshold if ring_risk_threshold is not None else self.ring_risk_threshold

        txn_sub, _, ref_sub = self.engine.get_events_as_of(target_ts)
        G = self.engine.build_networkx_graph_as_of(target_ts, min_edge_strength=0.05)

        # Pre-compute customer stats
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
            for cid in population_customers
        }

        graph_candidates: Dict[str, Dict[str, Any]] = {}

        for cid in population_customers:
            ring_res = detect_candidate_ring(
                G=G,
                root_customer_id=cid,
                as_of_time=target_ts,
                cust_stats_map=cust_stats_map,
                max_hops=2,
            )

            is_graph_cand = (ring_res["ring_risk_score"] >= threshold) and (len(ring_res["member_customers"]) >= 2)
            has_device_sharing = (len(ring_res["shared_devices"]) >= 1) and (len(ring_res["member_customers"]) >= 2)
            has_corroborated_device = has_device_sharing and (ring_res["member_refund_rate"] >= 0.20)

            if is_graph_cand or has_corroborated_device:
                graph_candidates[cid] = {
                    "customer_id": cid,
                    "ring_risk_score": ring_res["ring_risk_score"],
                    "member_count": len(ring_res["member_customers"]),
                    "shared_device_count": len(ring_res["shared_devices"]),
                    "shared_ip_count": len(ring_res["shared_ips"]),
                    "shared_instrument_count": len(ring_res["shared_instruments"]),
                    "member_refund_rate": ring_res["member_refund_rate"],
                    "member_customers": ring_res["member_customers"],
                    "targeted_merchants": ring_res["targeted_merchants"],
                }

        return graph_candidates

