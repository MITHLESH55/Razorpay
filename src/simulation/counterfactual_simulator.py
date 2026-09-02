"""
RiskOrbit — Phase 3.2: Counterfactual Intervention Simulator

Simulates counterfactual business outcomes across multiple policy paradigms:
  - Policy A: Phase 1 Point Classifier Only (Model E)
  - Policy B: Phase 2.2 Blanket Expansion
  - Policy C: Phase 3.1 Binary Gating (Hard Blocks Only)
  - Policy D: Phase 3.2 Tiered Response (Proportional Multi-Action)

Computes:
  - Gross Abuse Losses Prevented (₹)
  - False Friction Cost on Benign Users (₹)
  - Analyst Manual Review Costs (₹)
  - Net Economic Utility (₹)
  - Ring Containment Rates & FPR
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from src.decision.actions import ActionType, get_action_metadata
from src.decision.policy_config import PolicyConfig, get_default_phase3_policy
from src.decision.policy_engine import PolicyEngine
from src.decision.transaction_gate import TransactionDecision, TransactionGate
from src.graph.member_confidence import MemberConfidence


@dataclass
class PolicySimulationSummary:
    """Aggregated financial and operational performance of a policy simulation."""
    policy_name: str
    total_transactions: int
    abuse_transactions: int
    benign_transactions: int

    # Financial metrics
    total_abuse_volume_inr: float
    gross_losses_prevented_inr: float
    uncaught_abuse_loss_inr: float
    loss_prevention_rate_pct: float

    # Operational costs
    benign_friction_cost_inr: float
    analyst_review_cost_inr: float
    total_operational_cost_inr: float
    net_economic_utility_inr: float

    # Precision & recall metrics
    false_positives: int
    false_positive_rate_pct: float
    abuse_transactions_caught: int
    transaction_recall_pct: float

    # Action distribution
    action_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "policy_name": self.policy_name,
            "total_transactions": self.total_transactions,
            "abuse_transactions": self.abuse_transactions,
            "benign_transactions": self.benign_transactions,
            "total_abuse_volume_inr": round(self.total_abuse_volume_inr, 2),
            "gross_losses_prevented_inr": round(self.gross_losses_prevented_inr, 2),
            "uncaught_abuse_loss_inr": round(self.uncaught_abuse_loss_inr, 2),
            "loss_prevention_rate_pct": round(self.loss_prevention_rate_pct, 2),
            "benign_friction_cost_inr": round(self.benign_friction_cost_inr, 2),
            "analyst_review_cost_inr": round(self.analyst_review_cost_inr, 2),
            "total_operational_cost_inr": round(self.total_operational_cost_inr, 2),
            "net_economic_utility_inr": round(self.net_economic_utility_inr, 2),
            "false_positives": self.false_positives,
            "false_positive_rate_pct": round(self.false_positive_rate_pct, 2),
            "abuse_transactions_caught": self.abuse_transactions_caught,
            "transaction_recall_pct": round(self.transaction_recall_pct, 2),
            "action_counts": self.action_counts,
        }


class CounterfactualSimulator:
    """
    Simulates counterfactual policy interventions on a dataset of transactions.
    """

    def __init__(
        self,
        transaction_gate: Optional[TransactionGate] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.gate = transaction_gate or TransactionGate()
        self.policy_engine = policy_engine or PolicyEngine()

    def simulate_policy_a_point_model(
        self,
        df: pd.DataFrame,
        p1_scores: list[float] | pd.Series,
        threshold: float = 0.35,
    ) -> PolicySimulationSummary:
        """
        Policy A: Phase 1 Point Classifier Only (Model E)
        p1 >= threshold -> BLOCK_TRANSACTION, else ALLOW
        """
        actions = []
        for p1 in p1_scores:
            if p1 >= threshold:
                actions.append(ActionType.BLOCK_TRANSACTION)
            else:
                actions.append(ActionType.ALLOW)
        return self._compute_simulation_metrics("Policy A (Point Model E Only)", df, actions)

    def simulate_policy_b_blanket_expansion(
        self,
        df: pd.DataFrame,
        member_confidences: dict[str, MemberConfidence],
        p1_scores: list[float] | pd.Series,
        p1_threshold: float = 0.35,
    ) -> PolicySimulationSummary:
        """
        Policy B: Phase 2.2 Blanket Expansion
        Any connected ring member in graph is BLOCKED.
        """
        actions = []
        for cust_id, p1 in zip(df["customer_id"], p1_scores):
            mem_conf = member_confidences.get(cust_id)
            if mem_conf and mem_conf.tier in ("PRIMARY", "SECONDARY", "TERTIARY"):
                actions.append(ActionType.BLOCK_TRANSACTION)
            elif p1 >= p1_threshold:
                actions.append(ActionType.BLOCK_TRANSACTION)
            else:
                actions.append(ActionType.ALLOW)
        return self._compute_simulation_metrics("Policy B (Phase 2.2 Blanket Expansion)", df, actions)

    def simulate_policy_c_phase3_1_binary_gating(
        self,
        df: pd.DataFrame,
        member_confidences: dict[str, MemberConfidence],
        p1_scores: list[float] | pd.Series,
    ) -> PolicySimulationSummary:
        """
        Policy C: Phase 3.1 Binary Gating (Hard Block on is_flagged)
        """
        actions = []
        for txn_id, cust_id, p1 in zip(df["transaction_id"], df["customer_id"], p1_scores):
            mem_conf = member_confidences.get(cust_id)
            dec = self.gate.evaluate_transaction(
                transaction_id=txn_id,
                customer_id=cust_id,
                phase1_score=p1,
                member_confidence=mem_conf,
            )
            if dec.is_flagged:
                actions.append(ActionType.BLOCK_TRANSACTION)
            else:
                actions.append(ActionType.ALLOW)
        return self._compute_simulation_metrics("Policy C (Phase 3.1 Binary Gating)", df, actions)

    def simulate_policy_d_phase3_2_tiered_response(
        self,
        df: pd.DataFrame,
        member_confidences: dict[str, MemberConfidence],
        p1_scores: list[float] | pd.Series,
    ) -> PolicySimulationSummary:
        """
        Policy D: Phase 3.2 Tiered Response Policy
        Full action suite with proportional friction & guardrails.
        """
        actions = []
        for txn_id, cust_id, p1, amt in zip(
            df["transaction_id"], df["customer_id"], p1_scores, df["amount"]
        ):
            mem_conf = member_confidences.get(cust_id)
            dec = self.gate.evaluate_transaction(
                transaction_id=txn_id,
                customer_id=cust_id,
                phase1_score=p1,
                member_confidence=mem_conf,
            )
            ev_strength = mem_conf.evidence_strength if mem_conf else 0.0
            eval_res = self.policy_engine.evaluate(
                decision=dec,
                amount=float(amt),
                evidence_strength=ev_strength,
            )
            actions.append(eval_res.recommended_action)
        return self._compute_simulation_metrics("Policy D (Phase 3.2 Tiered Response)", df, actions)

    def _compute_simulation_metrics(
        self,
        policy_name: str,
        df: pd.DataFrame,
        actions: list[ActionType],
    ) -> PolicySimulationSummary:
        """Compute financial and operational outcome metrics."""
        total_txns = len(df)
        labels = df["abuse_label"].values if "abuse_label" in df.columns else [0] * total_txns
        amounts = df["amount"].values

        gross_losses_prevented = 0.0
        uncaught_abuse_loss = 0.0
        total_abuse_volume = 0.0

        benign_friction_cost = 0.0
        analyst_review_cost = 0.0

        false_positives = 0
        abuse_caught = 0
        abuse_total = 0
        benign_total = 0

        action_counts: dict[str, int] = {}

        for act, label, amt in zip(actions, labels, amounts):
            act_name = act.value
            action_counts[act_name] = action_counts.get(act_name, 0) + 1
            meta = get_action_metadata(act)

            if label == 1:
                # Fraudulent transaction
                abuse_total += 1
                total_abuse_volume += amt
                prevented = meta.fraud_block_rate * amt
                missed = (1.0 - meta.fraud_block_rate) * amt
                gross_losses_prevented += prevented
                uncaught_abuse_loss += missed
                if meta.fraud_block_rate > 0.50:
                    abuse_caught += 1
                if meta.review_cost_inr > 0:
                    analyst_review_cost += meta.review_cost_inr
            else:
                # Benign transaction
                benign_total += 1
                if act != ActionType.ALLOW:
                    false_positives += 1
                benign_friction_cost += meta.friction_cost_inr
                if meta.review_cost_inr > 0:
                    analyst_review_cost += meta.review_cost_inr

        total_op_cost = benign_friction_cost + analyst_review_cost
        net_utility = gross_losses_prevented - total_op_cost

        fpr = (false_positives / benign_total * 100.0) if benign_total > 0 else 0.0
        recall = (abuse_caught / abuse_total * 100.0) if abuse_total > 0 else 0.0
        loss_prev_rate = (gross_losses_prevented / total_abuse_volume * 100.0) if total_abuse_volume > 0 else 0.0

        return PolicySimulationSummary(
            policy_name=policy_name,
            total_transactions=total_txns,
            abuse_transactions=abuse_total,
            benign_transactions=benign_total,
            total_abuse_volume_inr=gross_losses_prevented + uncaught_abuse_loss,
            gross_losses_prevented_inr=gross_losses_prevented,
            uncaught_abuse_loss_inr=uncaught_abuse_loss,
            loss_prevention_rate_pct=loss_prev_rate,
            benign_friction_cost_inr=benign_friction_cost,
            analyst_review_cost_inr=analyst_review_cost,
            total_operational_cost_inr=total_op_cost,
            net_economic_utility_inr=net_utility,
            false_positives=false_positives,
            false_positive_rate_pct=fpr,
            abuse_transactions_caught=abuse_caught,
            transaction_recall_pct=recall,
            action_counts=action_counts,
        )
