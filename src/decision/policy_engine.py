"""
RiskOrbit — Phase 3.2: Policy Engine

Evaluates transaction risk decisions against versioned policy configurations,
mapping composite scores to bounded interventions and applying safety guardrails.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.decision.actions import (
    ActionMetadata,
    ActionType,
    get_action_metadata,
    validate_action_guardrails,
)
from src.decision.policy_config import PolicyConfig, get_default_phase3_policy
from src.decision.transaction_gate import TransactionDecision


@dataclass
class PolicyEvaluation:
    """Structured result of policy evaluation on a transaction."""
    transaction_id: str
    customer_id: str
    tier: str
    decision_score: float
    phase1_risk: float
    amount: float
    recommended_action: ActionType
    requires_human_approval: bool
    escalation_reason: Optional[str]
    expected_friction_cost_inr: float
    expected_review_cost_inr: float
    total_operational_cost_inr: float
    policy_id: str
    audit_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize policy evaluation."""
        return {
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "tier": self.tier,
            "decision_score": self.decision_score,
            "phase1_risk": self.phase1_risk,
            "amount": self.amount,
            "recommended_action": self.recommended_action.value,
            "requires_human_approval": self.requires_human_approval,
            "escalation_reason": self.escalation_reason,
            "expected_friction_cost_inr": self.expected_friction_cost_inr,
            "expected_review_cost_inr": self.expected_review_cost_inr,
            "total_operational_cost_inr": self.total_operational_cost_inr,
            "policy_id": self.policy_id,
            "audit_metadata": self.audit_metadata,
        }


class PolicyEngine:
    """
    Evaluates TransactionDecision objects against a PolicyConfig
    to recommend bounded, tier-aware business actions.
    """

    def __init__(self, policy: Optional[PolicyConfig] = None):
        self.policy = policy or get_default_phase3_policy()

    def evaluate(
        self,
        decision: TransactionDecision,
        amount: float,
        evidence_strength: float = 0.0,
    ) -> PolicyEvaluation:
        """
        Evaluate a transaction decision and produce a concrete bounded action.
        """
        tier = decision.tier
        p1_risk = decision.phase1_risk
        d_score = decision.decision_score

        # Get rule for tier (fallback to ISOLATED)
        rule = self.policy.tier_rules.get(
            tier, self.policy.tier_rules.get("ISOLATED")
        )

        # 1. Base candidate action selection
        candidate_action = ActionType.ALLOW

        if rule:
            # Check for high-confidence account restriction (Primary tier only with extreme signals)
            if (
                tier == "PRIMARY"
                and d_score >= 0.85
                and p1_risk >= 0.60
                and evidence_strength >= rule.restrict_account_min_evidence
            ):
                candidate_action = ActionType.RESTRICT_ACCOUNT
            elif (
                d_score >= rule.block_threshold_decision
                and p1_risk >= rule.block_threshold_p1
            ):
                candidate_action = ActionType.BLOCK_TRANSACTION
            elif (
                d_score >= rule.delay_threshold_decision
                and p1_risk >= rule.delay_threshold_p1
            ):
                candidate_action = ActionType.DELAY_SETTLEMENT
            elif (
                d_score >= rule.step_up_threshold_decision
                and p1_risk >= rule.step_up_threshold_p1
            ):
                candidate_action = ActionType.STEP_UP_2FA
            else:
                candidate_action = ActionType.ALLOW

        # 2. Guardrails validation & blast-radius checks
        final_action, requires_approval, escalation_reason = validate_action_guardrails(
            action_type=candidate_action,
            tier=tier,
            phase1_risk=p1_risk,
            amount=amount,
            max_single_block_amount=self.policy.max_auto_action_amount_inr,
        )

        # 3. Cost modeling
        action_meta = get_action_metadata(final_action)
        friction_cost = action_meta.friction_cost_inr
        review_cost = action_meta.review_cost_inr if requires_approval or final_action == ActionType.MANUAL_REVIEW else 0.0

        return PolicyEvaluation(
            transaction_id=decision.transaction_id,
            customer_id=decision.customer_id,
            tier=tier,
            decision_score=d_score,
            phase1_risk=p1_risk,
            amount=amount,
            recommended_action=final_action,
            requires_human_approval=requires_approval,
            escalation_reason=escalation_reason,
            expected_friction_cost_inr=friction_cost,
            expected_review_cost_inr=review_cost,
            total_operational_cost_inr=friction_cost + review_cost,
            policy_id=self.policy.policy_id,
            audit_metadata={
                "candidate_action": candidate_action.value,
                "rule_triggered": decision.reason,
                "evidence_strength": evidence_strength,
            },
        )
