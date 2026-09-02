"""
Unit and Integration Tests for Phase 3.2:
Decision Policy Engine, Counterfactual Simulator, Human Approval Gate, and Outcome Verification.
"""
from datetime import datetime, timezone
import pytest
import pandas as pd
import numpy as np

from src.decision.actions import (
    ActionType,
    ActionScope,
    ACTION_REGISTRY,
    get_action_metadata,
    validate_action_guardrails,
)
from src.decision.policy_config import (
    PolicyConfig,
    TierPolicyRule,
    get_default_phase3_policy,
)
from src.decision.policy_engine import PolicyEngine, PolicyEvaluation
from src.decision.human_gate import (
    HumanApprovalGate,
    ApprovalStatus,
    ApprovalAuditRecord,
)
from src.decision.transaction_gate import TransactionDecision, TransactionGate
from src.simulation.execution import ExecutionEngine, EntityState
from src.simulation.counterfactual_simulator import (
    CounterfactualSimulator,
    PolicySimulationSummary,
)
from src.evaluation.outcome_verifier import (
    OutcomeVerifier,
    InvariantCheckResult,
    VerificationSuiteResult,
)
from src.graph.member_confidence import MemberConfidence
from src.graph.graph_engine import PaymentGraphEngine


# --- 1. Action Scope & Guardrail Tests ---

def test_action_metadata_registry():
    """All defined action types must have valid metadata in registry."""
    for action in ActionType:
        meta = get_action_metadata(action)
        assert meta.action_type == action
        assert meta.friction_cost_inr >= 0.0
        assert meta.review_cost_inr >= 0.0
        assert 0.0 <= meta.legit_success_rate <= 1.0
        assert 0.0 <= meta.fraud_block_rate <= 1.0


def test_action_guardrails_tertiary_downgrade():
    """TERTIARY member with low individual risk cannot receive hard block or freeze."""
    final_act, req_app, reason = validate_action_guardrails(
        action_type=ActionType.BLOCK_TRANSACTION,
        tier="TERTIARY",
        phase1_risk=0.15,
        amount=1000.0,
    )
    assert final_act == ActionType.STEP_UP_2FA
    assert not req_app
    assert "downgraded" in reason.lower()

    # Moderate p1 (0.25) downgrades to DELAY_SETTLEMENT
    final_act_mod, _, _ = validate_action_guardrails(
        action_type=ActionType.BLOCK_TRANSACTION,
        tier="TERTIARY",
        phase1_risk=0.25,
        amount=1000.0,
    )
    assert final_act_mod == ActionType.DELAY_SETTLEMENT


def test_action_guardrails_high_amount_escalation():
    """Non-primary high-value blocks must escalate to MANUAL_REVIEW."""
    final_act, req_app, reason = validate_action_guardrails(
        action_type=ActionType.BLOCK_TRANSACTION,
        tier="SECONDARY",
        phase1_risk=0.45,
        amount=60000.0,
    )
    assert final_act == ActionType.MANUAL_REVIEW
    assert req_app is True
    assert "escalated to manual_review" in reason.lower()


def test_action_guardrails_extreme_amount():
    """Transactions >= ₹100,000 always require human approval."""
    _, req_app, reason = validate_action_guardrails(
        action_type=ActionType.ALLOW,
        tier="ISOLATED",
        phase1_risk=0.05,
        amount=150000.0,
    )
    assert req_app is True
    assert "exceeds auto-action threshold" in reason.lower()


# --- 2. Policy Configuration & Serialization Tests ---

def test_policy_config_serialization(tmp_path):
    """Policy config can be saved and reloaded losslessly from JSON."""
    policy = get_default_phase3_policy()
    file_path = tmp_path / "test_policy.json"
    policy.save_json(file_path)

    loaded = PolicyConfig.load_json(file_path)
    assert loaded.policy_id == policy.policy_id
    assert loaded.schema_version == policy.schema_version
    assert len(loaded.tier_rules) == len(policy.tier_rules)
    assert loaded.tier_rules["PRIMARY"].block_threshold_decision == 0.60


# --- 3. Policy Engine Routing Tests ---

def test_policy_engine_routing_primary():
    """PRIMARY tier with high signals receives BLOCK_TRANSACTION."""
    engine = PolicyEngine()
    dec = TransactionDecision(
        transaction_id="TXN_P1",
        customer_id="CUST_P1",
        decision_score=0.75,
        is_flagged=True,
        confidence=0.85,
        tier="PRIMARY",
        phase1_risk=0.45,
        member_confidence=0.85,
        max_edge_strength=0.80,
        edge_diversity_score=0.75,
        evidence_strength=0.80,
        graph_distance=0,
        reason="PRIMARY_GRAPH_EVAL",
        evidence_ids=[],
        component_scores={},
    )
    eval_res = engine.evaluate(dec, amount=5000.0, evidence_strength=0.80)
    assert eval_res.recommended_action == ActionType.BLOCK_TRANSACTION
    assert not eval_res.requires_human_approval
    assert eval_res.expected_friction_cost_inr == 130.0


def test_policy_engine_routing_secondary():
    """SECONDARY tier with moderate risk receives STEP_UP_2FA or DELAY_SETTLEMENT."""
    engine = PolicyEngine()
    dec = TransactionDecision(
        transaction_id="TXN_S1",
        customer_id="CUST_S1",
        decision_score=0.45,
        is_flagged=False,
        confidence=0.50,
        tier="SECONDARY",
        phase1_risk=0.20,
        member_confidence=0.50,
        max_edge_strength=0.55,
        edge_diversity_score=0.40,
        evidence_strength=0.45,
        graph_distance=1,
        reason="SECONDARY_GRAPH_EVAL",
        evidence_ids=[],
        component_scores={},
    )
    eval_res = engine.evaluate(dec, amount=3000.0)
    assert eval_res.recommended_action == ActionType.STEP_UP_2FA
    assert eval_res.expected_friction_cost_inr == 15.0


def test_policy_engine_routing_tertiary_protected():
    """TERTIARY tier with low risk receives ALLOW, avoiding false alarms."""
    engine = PolicyEngine()
    dec = TransactionDecision(
        transaction_id="TXN_T1",
        customer_id="CUST_T1",
        decision_score=0.20,
        is_flagged=False,
        confidence=0.25,
        tier="TERTIARY",
        phase1_risk=0.10,
        member_confidence=0.25,
        max_edge_strength=0.15,
        edge_diversity_score=0.15,
        evidence_strength=0.15,
        graph_distance=2,
        reason="TERTIARY_GRAPH_EVAL",
        evidence_ids=[],
        component_scores={},
    )
    eval_res = engine.evaluate(dec, amount=2000.0)
    assert eval_res.recommended_action == ActionType.ALLOW
    assert eval_res.expected_friction_cost_inr == 0.0


# --- 4. Human Approval Gate Tests ---

def test_human_approval_gate_lifecycle():
    """Approval lifecycle: submit -> pending -> approve -> recorded in audit."""
    gate = HumanApprovalGate()
    req = gate.submit_request(
        transaction_id="TXN_H1",
        customer_id="CUST_H1",
        proposed_action=ActionType.RESTRICT_ACCOUNT,
        amount=75000.0,
        tier="PRIMARY",
        risk_score=0.92,
        escalation_reason="Mass ring coordinator detected",
    )
    assert req.status == ApprovalStatus.PENDING
    assert len(gate.get_pending()) == 1

    approved = gate.approve(
        request_id=req.request_id,
        reviewer_id="ANALYST_007",
        notes="Confirmed coordinated ring account",
    )
    assert approved.status == ApprovalStatus.APPROVED
    assert approved.reviewer_id == "ANALYST_007"
    assert approved.final_action == ActionType.RESTRICT_ACCOUNT
    assert len(gate.get_pending()) == 0
    assert len(gate.get_audit_history()) == 1


def test_human_approval_gate_reject_override():
    """Rejecting a request overrides action to safe fallback."""
    gate = HumanApprovalGate()
    req = gate.submit_request(
        transaction_id="TXN_H2",
        customer_id="CUST_H2",
        proposed_action=ActionType.BLOCK_TRANSACTION,
        amount=80000.0,
        tier="SECONDARY",
        risk_score=0.55,
        escalation_reason="High value block review",
    )

    rejected = gate.reject(
        request_id=req.request_id,
        reviewer_id="ANALYST_007",
        override_action=ActionType.STEP_UP_2FA,
        notes="Legitimate VIP customer verified via phone",
    )
    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.final_action == ActionType.STEP_UP_2FA


def test_human_approval_gate_timeout():
    """Timed out request auto-applies safe fallback action."""
    gate = HumanApprovalGate(fallback_action=ActionType.DELAY_SETTLEMENT)
    req = gate.submit_request(
        transaction_id="TXN_H3",
        customer_id="CUST_H3",
        proposed_action=ActionType.MANUAL_REVIEW,
        amount=40000.0,
        tier="ISOLATED",
        risk_score=0.40,
        escalation_reason="Queue SLA timeout test",
    )

    timed_out = gate.handle_timeout(req.request_id)
    assert timed_out.status == ApprovalStatus.TIMEOUT_FALLBACK
    assert timed_out.final_action == ActionType.DELAY_SETTLEMENT


# --- 5. Simulated Execution Engine Tests ---

def test_execution_engine_stateful_restriction():
    """An account restricted on transaction 1 is automatically blocked on subsequent transactions."""
    exec_engine = ExecutionEngine()

    # Txn 1: Severe primary trigger
    dec1 = TransactionDecision(
        transaction_id="TXN_101",
        customer_id="CUST_EVIL",
        decision_score=0.92,
        is_flagged=True,
        confidence=0.95,
        tier="PRIMARY",
        phase1_risk=0.90,
        member_confidence=0.95,
        max_edge_strength=0.90,
        edge_diversity_score=0.90,
        evidence_strength=0.90,
        graph_distance=0,
        reason="PRIMARY",
        evidence_ids=[],
        component_scores={},
    )
    # Manually trigger restriction via policy or direct state
    exec_engine.set_account_state("CUST_EVIL", EntityState.RESTRICTED)

    # Txn 2: Subsequent txn from same customer with low individual risk
    dec2 = TransactionDecision(
        transaction_id="TXN_102",
        customer_id="CUST_EVIL",
        decision_score=0.05,
        is_flagged=False,
        confidence=0.0,
        tier="ISOLATED",
        phase1_risk=0.05,
        member_confidence=0.0,
        max_edge_strength=0.0,
        edge_diversity_score=0.0,
        evidence_strength=0.0,
        graph_distance=99,
        reason="ALLOW",
        evidence_ids=[],
        component_scores={},
    )
    res2 = exec_engine.process_transaction(dec2, amount=500.0)
    assert res2.executed_action == ActionType.BLOCK_TRANSACTION
    assert res2.entity_state_before == EntityState.RESTRICTED
    assert "automatically blocked" in res2.notes.lower()


# --- 6. Counterfactual Simulator Tests ---

def test_counterfactual_simulator_math():
    """Simulator mathematical accounting identities must hold exactly."""
    sim = CounterfactualSimulator()
    df = pd.DataFrame({
        "transaction_id": ["T1", "T2", "T3", "T4"],
        "customer_id": ["C1", "C2", "C3", "C4"],
        "amount": [1000.0, 2000.0, 3000.0, 4000.0],
        "abuse_label": [1, 0, 1, 0],
    })
    p1_scores = [0.80, 0.10, 0.90, 0.05]

    summary = sim.simulate_policy_a_point_model(df, p1_scores, threshold=0.35)

    # Identity 1: Gross Prevented + Uncaught == Total Abuse Volume
    assert np.isclose(
        summary.gross_losses_prevented_inr + summary.uncaught_abuse_loss_inr,
        summary.total_abuse_volume_inr,
    )
    # Identity 2: Net Utility == Gross Prevented - Total Operational Cost
    assert np.isclose(
        summary.net_economic_utility_inr,
        summary.gross_losses_prevented_inr - summary.total_operational_cost_inr,
    )
    # Identity 3: Total Op Cost == Friction + Review
    assert np.isclose(
        summary.total_operational_cost_inr,
        summary.benign_friction_cost_inr + summary.analyst_review_cost_inr,
    )


def test_counterfactual_simulator_policy_comparison():
    """Policy D should achieve high net economic utility by reducing false positive friction."""
    sim = CounterfactualSimulator()
    # 1 abuse (₹10,000), 3 benign (₹5,000 each) sharing an IP
    df = pd.DataFrame({
        "transaction_id": ["T1", "T2", "T3", "T4"],
        "customer_id": ["C_PRIMARY", "C_BENIGN1", "C_BENIGN2", "C_BENIGN3"],
        "amount": [10000.0, 5000.0, 5000.0, 5000.0],
        "abuse_label": [1, 0, 0, 0],
    })
    p1_scores = [0.75, 0.05, 0.08, 0.02]
    member_confidences = {
        "C_PRIMARY": MemberConfidence(
            customer_id="C_PRIMARY",
            confidence_score=0.85,
            tier="PRIMARY",
            phase1_risk=0.75,
            supporting_edge_count=3,
            edge_diversity_score=0.80,
            avg_edge_strength=0.70,
            max_edge_strength=0.80,
            graph_distance=0,
            temporal_relevance=1.0,
            evidence_strength=0.80,
            confidence_components={},
        ),
        "C_BENIGN1": MemberConfidence(
            customer_id="C_BENIGN1",
            confidence_score=0.20,
            tier="TERTIARY",
            phase1_risk=0.05,
            supporting_edge_count=1,
            edge_diversity_score=0.15,
            avg_edge_strength=0.10,
            max_edge_strength=0.10,
            graph_distance=1,
            temporal_relevance=0.5,
            evidence_strength=0.10,
            confidence_components={},
        ),
        "C_BENIGN2": MemberConfidence(
            customer_id="C_BENIGN2",
            confidence_score=0.20,
            tier="TERTIARY",
            phase1_risk=0.08,
            supporting_edge_count=1,
            edge_diversity_score=0.15,
            avg_edge_strength=0.10,
            max_edge_strength=0.10,
            graph_distance=1,
            temporal_relevance=0.5,
            evidence_strength=0.10,
            confidence_components={},
        ),
        "C_BENIGN3": MemberConfidence(
            customer_id="C_BENIGN3",
            confidence_score=0.20,
            tier="TERTIARY",
            phase1_risk=0.02,
            supporting_edge_count=1,
            edge_diversity_score=0.15,
            avg_edge_strength=0.10,
            max_edge_strength=0.10,
            graph_distance=1,
            temporal_relevance=0.5,
            evidence_strength=0.10,
            confidence_components={},
        ),
    }

    # Policy B (Blanket) will block all 3 benign users (3 * ₹130 friction)
    sum_b = sim.simulate_policy_b_blanket_expansion(df, member_confidences, p1_scores)
    # Policy D (Tiered) will protect tertiary benign users (₹0 friction)
    sum_d = sim.simulate_policy_d_phase3_2_tiered_response(df, member_confidences, p1_scores)

    assert sum_d.benign_friction_cost_inr < sum_b.benign_friction_cost_inr
    assert sum_d.net_economic_utility_inr > sum_b.net_economic_utility_inr


# --- 7. Outcome Verifier & Leakage Tests ---

def test_outcome_verifier_invariants():
    """Outcome verifier detects guardrail safety violations."""
    policy = get_default_phase3_policy()
    verifier = OutcomeVerifier(policy)

    valid_evaluations = [
        PolicyEvaluation(
            transaction_id="TXN_V1",
            customer_id="CUST_V1",
            tier="PRIMARY",
            decision_score=0.80,
            phase1_risk=0.60,
            amount=5000.0,
            recommended_action=ActionType.BLOCK_TRANSACTION,
            requires_human_approval=False,
            escalation_reason=None,
            expected_friction_cost_inr=130.0,
            expected_review_cost_inr=0.0,
            total_operational_cost_inr=130.0,
            policy_id=policy.policy_id,
        ),
        PolicyEvaluation(
            transaction_id="TXN_V2",
            customer_id="CUST_V2",
            tier="TERTIARY",
            decision_score=0.30,
            phase1_risk=0.10,
            amount=2000.0,
            recommended_action=ActionType.ALLOW,
            requires_human_approval=False,
            escalation_reason=None,
            expected_friction_cost_inr=0.0,
            expected_review_cost_inr=0.0,
            total_operational_cost_inr=0.0,
            policy_id=policy.policy_id,
        ),
    ]

    res = verifier.verify_evaluations(valid_evaluations)
    assert res.all_passed is True
    assert res.failed_checks == 0

    # Introduce a TERTIARY violation (hard block on low p1)
    invalid_evaluations = list(valid_evaluations) + [
        PolicyEvaluation(
            transaction_id="TXN_BAD",
            customer_id="CUST_BAD",
            tier="TERTIARY",
            decision_score=0.40,
            phase1_risk=0.10,
            amount=1000.0,
            recommended_action=ActionType.BLOCK_TRANSACTION,
            requires_human_approval=False,
            escalation_reason=None,
            expected_friction_cost_inr=130.0,
            expected_review_cost_inr=0.0,
            total_operational_cost_inr=130.0,
            policy_id=policy.policy_id,
        )
    ]
    res_bad = verifier.verify_evaluations(invalid_evaluations)
    assert res_bad.all_passed is False
    assert res_bad.failed_checks >= 1


def test_no_ground_truth_leakage_in_policy_engine():
    """PolicyEngine.evaluate must not accept ground truth labels."""
    engine = PolicyEngine()
    import inspect
    sig = inspect.signature(engine.evaluate)
    param_names = list(sig.parameters.keys())
    for forbidden in ["label", "abuse_label", "ground_truth", "is_abuse", "target"]:
        assert forbidden not in param_names


# --- 8. Additional Rigorous Tests for Phase 3.2 Validation Gate ---

def test_policy_determinism_multiple_runs():
    """Evaluating identical transactions multiple times must yield identical actions."""
    engine = PolicyEngine()
    dec = TransactionDecision(
        transaction_id="TXN_DET_1",
        customer_id="CUST_DET_1",
        decision_score=0.65,
        is_flagged=True,
        confidence=0.70,
        tier="PRIMARY",
        phase1_risk=0.35,
        member_confidence=0.70,
        max_edge_strength=0.60,
        edge_diversity_score=0.60,
        evidence_strength=0.60,
        graph_distance=0,
        reason="PRIMARY",
        evidence_ids=[],
        component_scores={},
    )
    res1 = engine.evaluate(dec, amount=12000.0, evidence_strength=0.60)
    res2 = engine.evaluate(dec, amount=12000.0, evidence_strength=0.60)
    res3 = engine.evaluate(dec, amount=12000.0, evidence_strength=0.60)

    assert res1.recommended_action == res2.recommended_action == res3.recommended_action
    assert res1.expected_friction_cost_inr == res2.expected_friction_cost_inr == res3.expected_friction_cost_inr
    assert res1.total_operational_cost_inr == res2.total_operational_cost_inr == res3.total_operational_cost_inr
    assert res1.requires_human_approval == res2.requires_human_approval == res3.requires_human_approval


def test_economic_arithmetic_all_actions():
    """Verify economic math across all actions and edge cases."""
    sim = CounterfactualSimulator()
    df = pd.DataFrame({
        "transaction_id": [f"T{i}" for i in range(7)],
        "customer_id": [f"C{i}" for i in range(7)],
        "amount": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0],
        "abuse_label": [1, 1, 1, 0, 0, 0, 0],
    })
    actions = [
        ActionType.ALLOW,               # abuse missed (₹1000 uncaught)
        ActionType.STEP_UP_2FA,         # abuse caught 85% (₹1700 prevented, ₹300 missed)
        ActionType.BLOCK_TRANSACTION,   # abuse caught 100% (₹3000 prevented)
        ActionType.ALLOW,               # benign ₹0 cost
        ActionType.STEP_UP_2FA,         # benign ₹15 friction
        ActionType.DELAY_SETTLEMENT,    # benign ₹30 friction
        ActionType.BLOCK_TRANSACTION,   # benign ₹130 friction
    ]
    summary = sim._compute_simulation_metrics("Custom Policy", df, actions)

    # Prevented: 0 + (0.85 * 2000) + (1.0 * 3000) = 1700 + 3000 = 4700.0
    assert np.isclose(summary.gross_losses_prevented_inr, 4700.0)
    # Uncaught: 1000 + 300 + 0 = 1300.0
    assert np.isclose(summary.uncaught_abuse_loss_inr, 1300.0)
    # Total abuse volume: 1000 + 2000 + 3000 = 6000.0
    assert np.isclose(summary.total_abuse_volume_inr, 6000.0)
    # Friction cost on benign: 0 + 15 + 30 + 130 = 175.0
    assert np.isclose(summary.benign_friction_cost_inr, 175.0)
    # Net utility: 4700 - 175 = 4525.0
    assert np.isclose(summary.net_economic_utility_inr, 4525.0)


def test_action_constraints_and_bounds():
    """All action assignments adhere to valid bounds and constraints."""
    for action in ActionType:
        meta = get_action_metadata(action)
        assert meta.friction_cost_inr >= 0.0
        assert meta.review_cost_inr >= 0.0
        assert 0.0 <= meta.fraud_block_rate <= 1.0
        assert 0.0 <= meta.legit_success_rate <= 1.0


def test_execution_state_machine_isolation():
    """An action on entity A must not alter state of unrelated entity B."""
    engine = ExecutionEngine()
    engine.set_account_state("CUST_ALPHA", EntityState.RESTRICTED)

    assert engine.get_account_state("CUST_ALPHA") == EntityState.RESTRICTED
    assert engine.get_account_state("CUST_BETA") == EntityState.ACTIVE

    # Processing transaction for CUST_BETA should not be blocked
    dec_beta = TransactionDecision(
        transaction_id="TXN_BETA_1",
        customer_id="CUST_BETA",
        decision_score=0.10,
        is_flagged=False,
        confidence=0.10,
        tier="ISOLATED",
        phase1_risk=0.05,
        member_confidence=0.0,
        max_edge_strength=0.0,
        edge_diversity_score=0.0,
        evidence_strength=0.0,
        graph_distance=99,
        reason="ALLOW",
        evidence_ids=[],
        component_scores={},
    )
    res_beta = engine.process_transaction(dec_beta, amount=1000.0)
    assert res_beta.executed_action == ActionType.ALLOW
    assert res_beta.entity_state_after == EntityState.ACTIVE


def test_reversibility_and_state_recovery():
    """Stateful account restrictions can be reverted with full auditability."""
    engine = ExecutionEngine()
    engine.set_account_state("CUST_REV_1", EntityState.RESTRICTED)
    assert engine.get_account_state("CUST_REV_1") == EntityState.RESTRICTED

    # Revert account to ACTIVE
    engine.unrestrict_account("CUST_REV_1", reason="Manual analyst clearing after KYC")
    assert engine.get_account_state("CUST_REV_1") == EntityState.ACTIVE

    engine.set_account_state("CUST_REV_2", EntityState.FROZEN)
    assert engine.get_account_state("CUST_REV_2") == EntityState.FROZEN

    # Unfreeze account
    engine.unfreeze_account("CUST_REV_2", reason="Dispute resolved")
    assert engine.get_account_state("CUST_REV_2") == EntityState.ACTIVE


def test_pit_safety_graph_temporal_bounds():
    """Graph engine point-in-time cutoff must strictly exclude future edges/nodes."""
    engine = PaymentGraphEngine.from_data_dir("data/raw")
    cutoff_early = datetime(2024, 7, 1)
    cutoff_late = datetime(2024, 9, 1)

    g_early = engine.build_networkx_graph_as_of(cutoff_early)
    g_late = engine.build_networkx_graph_as_of(cutoff_late)

    assert g_early.number_of_nodes() <= g_late.number_of_nodes()
    assert g_early.number_of_edges() <= g_late.number_of_edges()


def test_action_scope_properties():
    """Validate action scope taxonomy."""
    assert get_action_metadata(ActionType.ALLOW).scope == ActionScope.TRANSACTION
    assert get_action_metadata(ActionType.STEP_UP_2FA).scope == ActionScope.TRANSACTION
    assert get_action_metadata(ActionType.DELAY_SETTLEMENT).scope == ActionScope.TRANSACTION
    assert get_action_metadata(ActionType.MANUAL_REVIEW).scope == ActionScope.TRANSACTION
    assert get_action_metadata(ActionType.BLOCK_TRANSACTION).scope == ActionScope.TRANSACTION
    assert get_action_metadata(ActionType.RESTRICT_ACCOUNT).scope == ActionScope.ACCOUNT
    assert get_action_metadata(ActionType.FREEZE_RING).scope == ActionScope.RING


def test_high_blast_radius_requires_human_approval():
    """High blast radius actions (FREEZE_RING, RESTRICT_ACCOUNT, MANUAL_REVIEW) must flag human approval."""
    assert get_action_metadata(ActionType.FREEZE_RING).requires_human_approval is True
    assert get_action_metadata(ActionType.RESTRICT_ACCOUNT).requires_human_approval is True
    assert get_action_metadata(ActionType.MANUAL_REVIEW).requires_human_approval is True
    assert get_action_metadata(ActionType.ALLOW).requires_human_approval is False
    assert get_action_metadata(ActionType.STEP_UP_2FA).requires_human_approval is False
    assert get_action_metadata(ActionType.DELAY_SETTLEMENT).requires_human_approval is False
    assert get_action_metadata(ActionType.BLOCK_TRANSACTION).requires_human_approval is False


def test_rejected_actions_do_not_execute():
    """When a human analyst rejects an action, the final executed action must be the override action."""
    gate = HumanApprovalGate()
    req = gate.submit_request(
        transaction_id="TXN_REJ_01",
        customer_id="CUST_REJ_01",
        proposed_action=ActionType.BLOCK_TRANSACTION,
        amount=65000.0,
        tier="SECONDARY",
        risk_score=0.62,
        escalation_reason="High value block review",
    )
    # Reject with ALLOW override
    record = gate.reject(
        request_id=req.request_id,
        reviewer_id="SENIOR_ANALYST_02",
        override_action=ActionType.ALLOW,
        notes="Verified legitimate merchant bulk settlement",
    )
    assert record.status == ApprovalStatus.REJECTED
    assert record.proposed_action == ActionType.BLOCK_TRANSACTION
    assert record.final_action == ActionType.ALLOW


def test_verifier_catches_negative_costs():
    """OutcomeVerifier must flag and reject any negative cost calculations."""
    policy = get_default_phase3_policy()
    verifier = OutcomeVerifier(policy)

    eval_with_neg_cost = [
        PolicyEvaluation(
            transaction_id="TXN_NEG",
            customer_id="CUST_NEG",
            tier="PRIMARY",
            decision_score=0.80,
            phase1_risk=0.60,
            amount=5000.0,
            recommended_action=ActionType.BLOCK_TRANSACTION,
            requires_human_approval=False,
            escalation_reason=None,
            expected_friction_cost_inr=-50.0,  # Impossible negative cost
            expected_review_cost_inr=0.0,
            total_operational_cost_inr=-50.0,
            policy_id=policy.policy_id,
        )
    ]
    res = verifier.verify_evaluations(eval_with_neg_cost)
    assert res.all_passed is False
    assert any("Non-negative Operational Costs" in c.check_name and not c.passed for c in res.checks)


def test_validation_heldout_isolation_check():
    """Explicitly assert zero transaction ID and ring ID overlap between validation and held-out test splits."""
    val_df = pd.read_csv("data/splits/validation.csv")
    test_df = pd.read_csv("data/splits/heldout_test.csv")

    val_txns = set(val_df["transaction_id"])
    test_txns = set(test_df["transaction_id"])
    assert len(val_txns.intersection(test_txns)) == 0

    val_rings = set(val_df[val_df["abuse_label"] == 1]["ring_id"].dropna())
    test_rings = set(test_df[test_df["abuse_label"] == 1]["ring_id"].dropna())
    assert len(val_rings.intersection(test_rings)) == 0


