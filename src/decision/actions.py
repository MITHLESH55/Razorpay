"""
RiskOrbit — Phase 3.2: Bounded Action Scope & Impact Definitions

Defines concrete, bounded business interventions for risk decisioning.

Actions supported:
  - ALLOW: Pass through transaction without friction (₹0 cost).
  - STEP_UP_2FA: Challenge user with two-factor authentication / OTP challenge (₹15 friction).
  - DELAY_SETTLEMENT: Hold merchant/customer settlement for 24h async review (₹30 friction).
  - MANUAL_REVIEW: Route transaction to fraud analyst queue (₹130 review cost).
  - BLOCK_TRANSACTION: Reject single high-risk transaction (₹130 friction on benign).
  - RESTRICT_ACCOUNT: Temporary freeze on customer account capabilities (requires high confidence).
  - FREEZE_RING: Multi-entity defensive freeze on coordinated ring (requires human gate).

Guardrails:
  - Strict Blast-Radius controls (TERTIARY members cannot be hard blocked without individual risk).
  - Human review escalation for high-impact actions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    """Supported risk decision actions."""
    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    STEP_UP_2FA = "STEP_UP_2FA"
    DELAY_SETTLEMENT = "DELAY_SETTLEMENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    BLOCK_TRANSACTION = "BLOCK_TRANSACTION"
    RESTRICT_ACCOUNT = "RESTRICT_ACCOUNT"
    FREEZE_RING = "FREEZE_RING"


class ActionScope(str, Enum):
    """Scope of intervention."""
    TRANSACTION = "TRANSACTION"
    ACCOUNT = "ACCOUNT"
    RING = "RING"


@dataclass(frozen=True)
class ActionMetadata:
    """Metadata and operational cost profile for an action."""
    action_type: ActionType
    scope: ActionScope
    friction_cost_inr: float
    review_cost_inr: float
    requires_human_approval: bool
    legit_success_rate: float  # Probability benign user completes transaction under action
    fraud_block_rate: float    # Probability fraudulent transaction is prevented
    description: str


ACTION_REGISTRY: dict[ActionType, ActionMetadata] = {
    ActionType.ALLOW: ActionMetadata(
        action_type=ActionType.ALLOW,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=0.0,
        review_cost_inr=0.0,
        requires_human_approval=False,
        legit_success_rate=1.00,
        fraud_block_rate=0.00,
        description="Clear transaction with zero friction",
    ),
    ActionType.MONITOR: ActionMetadata(
        action_type=ActionType.MONITOR,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=0.0,
        review_cost_inr=0.0,
        requires_human_approval=False,
        legit_success_rate=1.00,
        fraud_block_rate=0.00,
        description="Clear transaction with active shadow telemetry and velocity tracking",
    ),
    ActionType.STEP_UP_2FA: ActionMetadata(
        action_type=ActionType.STEP_UP_2FA,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=15.0,
        review_cost_inr=0.0,
        requires_human_approval=False,
        legit_success_rate=0.96,
        fraud_block_rate=0.85,
        description="Challenge transaction with dynamic 2FA / OTP verification",
    ),
    ActionType.DELAY_SETTLEMENT: ActionMetadata(
        action_type=ActionType.DELAY_SETTLEMENT,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=30.0,
        review_cost_inr=0.0,
        requires_human_approval=False,
        legit_success_rate=1.00,
        fraud_block_rate=0.90,
        description="Hold payout/settlement for 24h async risk verification",
    ),
    ActionType.MANUAL_REVIEW: ActionMetadata(
        action_type=ActionType.MANUAL_REVIEW,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=20.0,
        review_cost_inr=130.0,
        requires_human_approval=True,
        legit_success_rate=0.98,
        fraud_block_rate=0.98,
        description="Route transaction to human fraud analyst queue",
    ),
    ActionType.BLOCK_TRANSACTION: ActionMetadata(
        action_type=ActionType.BLOCK_TRANSACTION,
        scope=ActionScope.TRANSACTION,
        friction_cost_inr=130.0,
        review_cost_inr=0.0,
        requires_human_approval=False,
        legit_success_rate=0.00,
        fraud_block_rate=1.00,
        description="Reject transaction immediately",
    ),
    ActionType.RESTRICT_ACCOUNT: ActionMetadata(
        action_type=ActionType.RESTRICT_ACCOUNT,
        scope=ActionScope.ACCOUNT,
        friction_cost_inr=350.0,
        review_cost_inr=130.0,
        requires_human_approval=True,
        legit_success_rate=0.00,
        fraud_block_rate=1.00,
        description="Temporarily suspend account capabilities pending investigation",
    ),
    ActionType.FREEZE_RING: ActionMetadata(
        action_type=ActionType.FREEZE_RING,
        scope=ActionScope.RING,
        friction_cost_inr=1000.0,
        review_cost_inr=500.0,
        requires_human_approval=True,
        legit_success_rate=0.00,
        fraud_block_rate=1.00,
        description="Coordinated defensive hold across all ring member accounts",
    ),
}


def get_action_metadata(action_type: ActionType) -> ActionMetadata:
    """Retrieve metadata for an action type."""
    if action_type not in ACTION_REGISTRY:
        raise ValueError(f"Unknown action type: {action_type}")
    return ACTION_REGISTRY[action_type]


def validate_action_guardrails(
    action_type: ActionType,
    tier: str,
    phase1_risk: float,
    amount: float,
    max_single_block_amount: float = 100000.0,
) -> tuple[ActionType, bool, Optional[str]]:
    """
    Enforce safety guardrails on recommended action.

    Rules:
      1. TERTIARY tier members CANNOT receive BLOCK_TRANSACTION, RESTRICT_ACCOUNT,
         or FREEZE_RING unless their individual phase1_risk >= 0.35.
         If violated, downscaled to STEP_UP_2FA or DELAY_SETTLEMENT.
      2. Large transactions (> ₹50,000) recommended for BLOCK must be escalated
         to MANUAL_REVIEW unless confirmed PRIMARY member.
      3. Extreme transactions (> ₹100,000) automatically require human approval.

    Returns:
      (adjusted_action, requires_human_approval, escalation_reason)
    """
    requires_approval = ACTION_REGISTRY[action_type].requires_human_approval
    escalation_reason = None
    final_action = action_type

    # Guardrail 1: Tertiary protection
    if tier == "TERTIARY" and action_type in (
        ActionType.BLOCK_TRANSACTION,
        ActionType.RESTRICT_ACCOUNT,
        ActionType.FREEZE_RING,
    ):
        if phase1_risk < 0.35:
            # Downgrade hard block to proportional challenge
            final_action = ActionType.STEP_UP_2FA if phase1_risk < 0.20 else ActionType.DELAY_SETTLEMENT
            requires_approval = False
            escalation_reason = (
                f"Guardrail triggered: TERTIARY member with low individual risk (p1={phase1_risk:.4f}) "
                f"downgraded from {action_type.value} to {final_action.value}"
            )

    # Guardrail 2: High value transaction escalation
    if amount >= 50000.0 and final_action == ActionType.BLOCK_TRANSACTION and tier != "PRIMARY":
        final_action = ActionType.MANUAL_REVIEW
        requires_approval = True
        escalation_reason = (
            f"High-value transaction (₹{amount:,.2f}) escalated to MANUAL_REVIEW to prevent false block"
        )

    # Guardrail 3: Extreme value threshold
    if amount >= max_single_block_amount:
        requires_approval = True
        if escalation_reason is None:
            escalation_reason = f"Transaction amount ₹{amount:,.2f} exceeds auto-action threshold"

    return final_action, requires_approval, escalation_reason
