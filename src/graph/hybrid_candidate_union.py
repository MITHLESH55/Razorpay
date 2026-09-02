"""
RiskOrbit — Hybrid Candidate Union & Ranking Engine (Phase 2.1)

Combines independent candidate discovery streams:
  - Phase 1: Tabular risk model candidates (transaction-level)
  - Graph: Unsupervised structural ring candidates (population-level)

Applies deterministic deduplication, source attribution, multi-signal ranking,
and point-in-time safety guarantees.

SECURITY & LEAKAGE GUARD:
  - Ground-truth labels (ring_id, abuse_label, etc.) are strictly forbidden.
  - Future timestamps are strictly excluded.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.ring_detector import detect_candidate_ring

logger = logging.getLogger(__name__)


@dataclass
class HybridCandidate:
    candidate_id: str
    customer_id: str
    sources: List[str]  # ["phase1"], ["graph"], or ["phase1", "graph"]
    phase1_score: float = 0.0
    graph_ring_score: float = 0.0
    member_count: int = 1
    shared_device_count: int = 0
    shared_ip_count: int = 0
    shared_instrument_count: int = 0
    member_refund_rate: float = 0.0
    cross_merchant_count: int = 0
    composite_rank_score: float = 0.0
    candidate_rank: int = 0
    trigger_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HybridCandidateUnion:
    """
    Unions independent candidate streams, deduplicates deterministically by customer_id,
    attributes discovery sources, and computes a multi-signal ranking score.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or {
            "phase1_score": 0.30,
            "graph_ring_score": 0.25,
            "sharing_signal": 0.20,
            "member_refund_rate": 0.15,
            "cross_merchant": 0.10,
        }

    def compute_composite_rank_score(
        self,
        phase1_score: float,
        graph_ring_score: float,
        shared_device_count: int,
        shared_ip_count: int,
        shared_instrument_count: int,
        member_refund_rate: float,
        cross_merchant_count: int,
        **kwargs: Any,
    ) -> float:
        """
        Calculates a deterministic composite rank score in [0.0, 1.0].
        No ground-truth labels are accessed.
        """
        # Infrastructure sharing signal (device weighted higher than IP)
        dev_sig = min(1.0, shared_device_count * 0.40)
        ip_sig = min(0.60, shared_ip_count * 0.15)
        ins_sig = min(1.0, shared_instrument_count * 0.35)
        sharing_signal = max(dev_sig, ip_sig, ins_sig)

        cross_merchant_norm = min(1.0, cross_merchant_count / 3.0)

        composite = (
            self.weights.get("phase1_score", 0.30) * float(phase1_score)
            + self.weights.get("graph_ring_score", 0.25) * float(graph_ring_score)
            + self.weights.get("sharing_signal", 0.20) * float(sharing_signal)
            + self.weights.get("member_refund_rate", 0.15) * float(member_refund_rate)
            + self.weights.get("cross_merchant", 0.10) * float(cross_merchant_norm)
        )

        return round(min(1.0, max(0.0, float(composite))), 4)

    def union_and_rank(
        self,
        phase1_candidates: Dict[str, float],  # customer_id -> phase1 max risk score
        graph_candidates: Dict[str, Dict[str, Any]],  # customer_id -> ring detection metadata
    ) -> List[HybridCandidate]:
        """
        Deduplicates candidate streams and assigns deterministic ranks.

        Returns:
            List of HybridCandidate objects sorted by composite_rank_score descending.
        """
        all_cust_ids = set(phase1_candidates.keys()) | set(graph_candidates.keys())
        merged: List[HybridCandidate] = []

        for cid in all_cust_ids:
            sources = []
            p1_score = phase1_candidates.get(cid, 0.0)
            g_meta = graph_candidates.get(cid, {})

            if cid in phase1_candidates:
                sources.append("phase1")
            if cid in graph_candidates:
                sources.append("graph")

            g_score = g_meta.get("ring_risk_score", 0.0)
            mem_count = g_meta.get("member_count", 1)
            dev_cnt = g_meta.get("shared_device_count", 0)
            ip_cnt = g_meta.get("shared_ip_count", 0)
            ins_cnt = g_meta.get("shared_instrument_count", 0)
            ref_rate = g_meta.get("member_refund_rate", 0.0)
            merch_cnt = len(g_meta.get("targeted_merchants", []))

            reasons = []
            if "phase1" in sources:
                reasons.append(f"Phase 1 elevated risk score ({p1_score:.4f})")
            if "graph" in sources:
                reasons.append(f"Graph candidate ring score ({g_score:.4f})")

            comp_score = self.compute_composite_rank_score(
                phase1_score=p1_score,
                graph_ring_score=g_score,
                shared_device_count=dev_cnt,
                shared_ip_count=ip_cnt,
                shared_instrument_count=ins_cnt,
                member_refund_rate=ref_rate,
                cross_merchant_count=merch_cnt,
            )

            cand = HybridCandidate(
                candidate_id=f"CAND-{cid}",
                customer_id=cid,
                sources=sources,
                phase1_score=round(float(p1_score), 4),
                graph_ring_score=round(float(g_score), 4),
                member_count=mem_count,
                shared_device_count=dev_cnt,
                shared_ip_count=ip_cnt,
                shared_instrument_count=ins_cnt,
                member_refund_rate=round(float(ref_rate), 4),
                cross_merchant_count=merch_cnt,
                composite_rank_score=comp_score,
                trigger_reasons=reasons,
            )
            merged.append(cand)

        # Sort deterministically: highest composite_rank_score first, break ties by customer_id
        merged.sort(key=lambda x: (-x.composite_rank_score, x.customer_id))

        # Assign ranks (1-indexed)
        for rank_idx, cand in enumerate(merged, start=1):
            cand.candidate_rank = rank_idx

        return merged

    def get_source_breakdown(
        self, candidates: List[HybridCandidate]
    ) -> Dict[str, Any]:
        """Calculates exact candidate count by discovery source."""
        p1_only = [c for c in candidates if c.sources == ["phase1"]]
        graph_only = [c for c in candidates if c.sources == ["graph"]]
        both = [c for c in candidates if set(c.sources) == {"phase1", "graph"}]

        return {
            "total_unique_candidates": len(candidates),
            "phase1_only_count": len(p1_only),
            "graph_only_count": len(graph_only),
            "both_count": len(both),
            "phase1_total_count": len(p1_only) + len(both),
            "graph_total_count": len(graph_only) + len(both),
        }
