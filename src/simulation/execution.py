"""
RiskOrbit — Phase 3.2: Simulated Execution Engine

Executes risk policies on transaction streams with stateful account & ring tracking,
simulating real-world cascading effects and downstream transaction lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from src.decision.actions import ActionType, get_action_metadata
from src.decision.policy_engine import PolicyEngine, PolicyEvaluation
from src.decision.transaction_gate import TransactionDecision


class EntityState(str, Enum):
    """Account or Entity operational state."""
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    FROZEN = "FROZEN"


@dataclass
class ExecutionResult:
    """Outcome of simulated execution on a single transaction."""
    transaction_id: str
    customer_id: str
    timestamp: str
    recommended_action: ActionType
    executed_action: ActionType
    entity_state_before: EntityState
    entity_state_after: EntityState
    friction_cost_inr: float
    review_cost_inr: float
    total_operational_cost_inr: float
    notes: Optional[str] = None


class ExecutionEngine:
    """
    Simulated stateful runtime execution engine for risk interventions.
    """

    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self.policy_engine = policy_engine or PolicyEngine()
        self.account_states: dict[str, EntityState] = {}
        self.ring_states: dict[str, EntityState] = {}
        self.execution_history: list[ExecutionResult] = []

    def get_account_state(self, customer_id: str) -> EntityState:
        """Get current operational state of a customer account."""
        return self.account_states.get(customer_id, EntityState.ACTIVE)

    def set_account_state(self, customer_id: str, state: EntityState) -> None:
        """Explicitly set customer account state."""
        self.account_states[customer_id] = state

    def unrestrict_account(self, customer_id: str, reason: str = "Investigation cleared") -> None:
        """Revert a restricted account back to ACTIVE state."""
        self.account_states[customer_id] = EntityState.ACTIVE

    def unfreeze_account(self, customer_id: str, reason: str = "False positive resolution") -> None:
        """Revert a frozen account back to ACTIVE state."""
        self.account_states[customer_id] = EntityState.ACTIVE

    def revert_account_state(
        self,
        customer_id: str,
        target_state: EntityState = EntityState.ACTIVE,
        reason: str = "Manual analyst intervention",
    ) -> None:
        """Audited state reversal for account remediation."""
        self.account_states[customer_id] = target_state

    def process_transaction(
        self,
        decision: TransactionDecision,
        amount: float,
        timestamp: Optional[datetime] = None,
        ring_members: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """
        Process a transaction through policy evaluation and stateful execution.
        """
        cust_id = decision.customer_id
        current_state = self.get_account_state(cust_id)
        ts_str = timestamp.isoformat() if timestamp else datetime.now(timezone.utc).isoformat()

        # 1. Check if account is already restricted or frozen
        if current_state in (EntityState.RESTRICTED, EntityState.FROZEN):
            executed_action = ActionType.BLOCK_TRANSACTION
            action_meta = get_action_metadata(executed_action)
            res = ExecutionResult(
                transaction_id=decision.transaction_id,
                customer_id=cust_id,
                timestamp=ts_str,
                recommended_action=ActionType.BLOCK_TRANSACTION,
                executed_action=executed_action,
                entity_state_before=current_state,
                entity_state_after=current_state,
                friction_cost_inr=0.0,  # Already restricted account incurs no new friction
                review_cost_inr=0.0,
                total_operational_cost_inr=0.0,
                notes=f"Transaction automatically blocked due to prior account state: {current_state.value}",
            )
            self.execution_history.append(res)
            return res

        # 2. Evaluate fresh policy
        eval_res = self.policy_engine.evaluate(decision=decision, amount=amount)
        rec_action = eval_res.recommended_action
        executed_action = rec_action
        new_state = current_state
        notes = None

        # 3. Apply stateful side-effects
        if rec_action == ActionType.RESTRICT_ACCOUNT:
            new_state = EntityState.RESTRICTED
            self.account_states[cust_id] = new_state
            notes = f"Account {cust_id} transitioned to RESTRICTED"
        elif rec_action == ActionType.FREEZE_RING:
            new_state = EntityState.FROZEN
            self.account_states[cust_id] = new_state
            notes = f"Account {cust_id} and ring members frozen"
            if ring_members:
                for member_id in ring_members:
                    self.account_states[member_id] = EntityState.FROZEN

        res = ExecutionResult(
            transaction_id=decision.transaction_id,
            customer_id=cust_id,
            timestamp=ts_str,
            recommended_action=rec_action,
            executed_action=executed_action,
            entity_state_before=current_state,
            entity_state_after=new_state,
            friction_cost_inr=eval_res.expected_friction_cost_inr,
            review_cost_inr=eval_res.expected_review_cost_inr,
            total_operational_cost_inr=eval_res.total_operational_cost_inr,
            notes=notes,
        )
        self.execution_history.append(res)
        return res
