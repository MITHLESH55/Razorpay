"""
RiskOrbit — Phase 3.1: Transaction-Level Gating

Combines individual transaction risk with ring membership context and evidence
to produce structured, explainable per-transaction decision scores.

Core Principle:
    A customer being a ring member does NOT automatically mean every transaction is blocked.
    The system answers:
        1. "How risky is this transaction itself?" (Phase 1 score)
        2. "How strong is the customer's relationship to the ring?" (Member confidence)
        3. "How strong is the connecting evidence?" (Edge strength & diversity)

Outputs a structured TransactionDecision without applying final action policies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from src.graph.member_confidence import MemberConfidence, MemberTier


DecisionTier = Literal["PRIMARY", "SECONDARY", "TERTIARY", "ISOLATED", "CLEARED"]


@dataclass
class TransactionDecision:
    """
    Structured per-transaction decision assessment.

    All component scores in [0, 1].
    """
    transaction_id: str
    customer_id: str
    decision_score: float  # [0, 1] Composite transaction decision score
    is_flagged: bool       # Whether transaction meets gating threshold
    confidence: float      # Overall confidence in decision
    tier: DecisionTier     # Member tier or ISOLATED

    # Component breakdown for explainability
    phase1_risk: float
    member_confidence: float
    max_edge_strength: float
    edge_diversity_score: float
    evidence_strength: float
    graph_distance: int

    # Explainability & Audit trail
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    component_scores: dict[str, float] = field(default_factory=dict)
    schema_version: str = "3.1.0"

    @property
    def transaction_risk(self) -> float:
        """Alias for individual transaction risk."""
        return self.phase1_risk

    @property
    def membership_confidence_score(self) -> float:
        """Alias for graph membership confidence score."""
        return self.member_confidence

    @property
    def intervention_confidence(self) -> float:
        """Alias for evidence corroboration strength justifying intervention."""
        return self.evidence_strength


class TransactionGate:
    """
    Evaluates transactions using combined transaction-risk and ring-context gating.

    Configurable weights allow validation-based tuning.
    """

    def __init__(
        self,
        weight_phase1: float = 0.40,
        weight_member_conf: float = 0.30,
        weight_edge_strength: float = 0.15,
        weight_diversity: float = 0.15,
        decision_threshold: float = 0.35,
        primary_auto_gate_threshold: float = 0.20,
        isolated_threshold: float = 0.35,
        schema_version: str = "3.1.0",
    ):
        """
        Initialize transaction gate with configurable weights.

        Args:
            weight_phase1: Weight for individual transaction risk
            weight_member_conf: Weight for ring membership confidence
            weight_edge_strength: Weight for maximum edge strength
            weight_diversity: Weight for edge diversity score
            decision_threshold: Score threshold for flagging ring-connected transactions
            primary_auto_gate_threshold: Phase 1 threshold floor for PRIMARY tier members
            isolated_threshold: Phase 1 threshold for customers with no ring context
            schema_version: Policy/schema version identifier
        """
        self.weight_phase1 = weight_phase1
        self.weight_member_conf = weight_member_conf
        self.weight_edge_strength = weight_edge_strength
        self.weight_diversity = weight_diversity
        self.decision_threshold = decision_threshold
        self.primary_auto_gate_threshold = primary_auto_gate_threshold
        self.isolated_threshold = isolated_threshold
        self.schema_version = schema_version

        # Verify weights sum to 1.0 (approximate)
        total_w = weight_phase1 + weight_member_conf + weight_edge_strength + weight_diversity
        if abs(total_w - 1.0) > 1e-4:
            raise ValueError(f"Weights must sum to 1.0, got {total_w}")

    def evaluate_transaction(
        self,
        transaction_id: str,
        customer_id: str,
        phase1_score: float,
        member_confidence: Optional[MemberConfidence] = None,
        evidence_ids: Optional[list[str]] = None,
    ) -> TransactionDecision:
        """
        Evaluate a single transaction with or without ring membership context.

        Args:
            transaction_id: Unique transaction identifier
            customer_id: Customer identifier
            phase1_score: Individual LightGBM risk score [0, 1]
            member_confidence: Optional MemberConfidence object if customer is in a ring
            evidence_ids: Supporting evidence record IDs

        Returns:
            TransactionDecision structured assessment
        """
        ev_ids = evidence_ids or []

        # Case 1: Customer has NO ring context (Isolated / Non-ring account)
        if member_confidence is None:
            decision_score = phase1_score
            is_flagged = phase1_score >= self.isolated_threshold
            tier: DecisionTier = "ISOLATED"

            if is_flagged:
                reason = f"Isolated transaction flagged on high individual risk (p1={phase1_score:.4f} >= {self.isolated_threshold:.2f})"
            else:
                reason = f"Cleared: Isolated transaction with low individual risk (p1={phase1_score:.4f})"

            return TransactionDecision(
                transaction_id=transaction_id,
                customer_id=customer_id,
                decision_score=round(decision_score, 4),
                is_flagged=is_flagged,
                confidence=round(phase1_score, 4),
                tier=tier,
                phase1_risk=round(phase1_score, 4),
                member_confidence=0.0,
                max_edge_strength=0.0,
                edge_diversity_score=0.0,
                evidence_strength=0.0,
                graph_distance=999,
                reason=reason,
                evidence_ids=ev_ids,
                component_scores={
                    "phase1_contribution": round(phase1_score, 4),
                    "ring_context_contribution": 0.0,
                },
                schema_version=self.schema_version,
            )

        # Case 2: Customer is connected to a ring
        mem_conf = member_confidence.confidence_score
        max_edge = member_confidence.max_edge_strength
        div_score = member_confidence.edge_diversity_score
        ev_str = member_confidence.evidence_strength
        dist = member_confidence.graph_distance
        tier_str = member_confidence.tier

        # Composite decision score calculation
        composite_score = (
            self.weight_phase1 * phase1_score +
            self.weight_member_conf * mem_conf +
            self.weight_edge_strength * max_edge +
            self.weight_diversity * div_score
        )

        # Determine gating rules based on tier
        if tier_str == "PRIMARY":
            # Primary suspects: flagged if composite >= threshold OR (phase1 >= floor AND confidence is strong)
            is_flagged = (composite_score >= self.decision_threshold) or (
                phase1_score >= self.primary_auto_gate_threshold and mem_conf >= 0.70
            )
            reason = (
                f"PRIMARY ring member flagged (composite={composite_score:.4f}, "
                f"p1={phase1_score:.4f}, conf={mem_conf:.4f})"
            ) if is_flagged else (
                f"PRIMARY member cleared due to very low transaction risk (p1={phase1_score:.4f})"
            )
            tier_val: DecisionTier = "PRIMARY"

        elif tier_str == "SECONDARY":
            # Secondary members: require BOTH moderate transaction risk AND solid relational evidence
            is_flagged = (composite_score >= self.decision_threshold) and (phase1_score >= 0.15)
            reason = (
                f"SECONDARY ring member flagged with corroborating risk (composite={composite_score:.4f}, "
                f"p1={phase1_score:.4f})"
            ) if is_flagged else (
                f"SECONDARY member cleared: insufficient transaction risk (p1={phase1_score:.4f} < 0.15)"
            )
            tier_val = "SECONDARY"

        else:  # TERTIARY
            # Tertiary members: weak graph relation; NEVER blanket block; require high individual risk
            is_flagged = (phase1_score >= self.isolated_threshold) and (composite_score >= self.decision_threshold)
            reason = (
                f"TERTIARY member flagged solely due to high individual risk (p1={phase1_score:.4f})"
            ) if is_flagged else (
                f"TERTIARY member cleared: weak indirect connection with insufficient individual risk"
            )
            tier_val = "TERTIARY"

        component_scores = {
            "phase1_contribution": round(self.weight_phase1 * phase1_score, 4),
            "member_conf_contribution": round(self.weight_member_conf * mem_conf, 4),
            "edge_strength_contribution": round(self.weight_edge_strength * max_edge, 4),
            "diversity_contribution": round(self.weight_diversity * div_score, 4),
        }

        return TransactionDecision(
            transaction_id=transaction_id,
            customer_id=customer_id,
            decision_score=round(composite_score, 4),
            is_flagged=is_flagged,
            confidence=round(mem_conf, 4),
            tier=tier_val,
            phase1_risk=round(phase1_score, 4),
            member_confidence=round(mem_conf, 4),
            max_edge_strength=round(max_edge, 4),
            edge_diversity_score=round(div_score, 4),
            evidence_strength=round(ev_str, 4),
            graph_distance=dist,
            reason=reason,
            evidence_ids=ev_ids,
            component_scores=component_scores,
            schema_version=self.schema_version,
        )
