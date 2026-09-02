"""
RiskOrbit — Phase 3.2: Outcome Verifier & Invariant Checker

Enforces business invariants, safety constraints, cost boundaries,
and leakage guards on policy simulation results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.decision.actions import ActionType
from src.decision.policy_config import PolicyConfig, get_default_phase3_policy
from src.decision.policy_engine import PolicyEvaluation
from src.simulation.counterfactual_simulator import PolicySimulationSummary


@dataclass
class InvariantCheckResult:
    """Result of an individual invariant verification check."""
    check_name: str
    passed: bool
    details: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationSuiteResult:
    """Aggregated verification results for Phase 3.2."""
    all_passed: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: list[InvariantCheckResult]

    def to_dict(self) -> dict[str, Any]:
        """Convert suite result to dictionary."""
        return {
            "all_passed": self.all_passed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "details": c.details,
                    "metadata": c.metadata,
                }
                for c in self.checks
            ],
        }


class OutcomeVerifier:
    """
    Verifies policy invariant guarantees and safety properties.
    """

    def __init__(self, policy_config: Optional[PolicyConfig] = None):
        self.policy_config = policy_config or get_default_phase3_policy()

    def verify_evaluations(
        self,
        evaluations: list[PolicyEvaluation],
    ) -> VerificationSuiteResult:
        """
        Verify safety invariants across a batch of policy evaluations.
        """
        checks: list[InvariantCheckResult] = []

        # Invariant 1: TERTIARY blast radius guardrail
        tertiary_violations = 0
        for ev in evaluations:
            if ev.tier == "TERTIARY" and ev.recommended_action in (
                ActionType.BLOCK_TRANSACTION,
                ActionType.RESTRICT_ACCOUNT,
                ActionType.FREEZE_RING,
            ):
                if ev.phase1_risk < self.policy_config.tertiary_p1_safety_threshold:
                    tertiary_violations += 1

        checks.append(
            InvariantCheckResult(
                check_name="TERTIARY Blast Radius Safety",
                passed=(tertiary_violations == 0),
                details=f"Found {tertiary_violations} violations where TERTIARY member with low p1 received hard block/freeze.",
                metadata={"tertiary_violations": tertiary_violations},
            )
        )

        # Invariant 2: High amount human escalation
        amount_violations = 0
        for ev in evaluations:
            if ev.amount >= self.policy_config.max_auto_action_amount_inr and not ev.requires_human_approval:
                amount_violations += 1

        checks.append(
            InvariantCheckResult(
                check_name="High Amount Human Approval Escalation",
                passed=(amount_violations == 0),
                details=f"Found {amount_violations} violations where amount >= Rs.{self.policy_config.max_auto_action_amount_inr:,.0f} lacked human gate.",
                metadata={"amount_violations": amount_violations},
            )
        )

        # Invariant 3: Cost boundedness
        cost_violations = 0
        for ev in evaluations:
            if ev.total_operational_cost_inr < 0.0 or ev.expected_friction_cost_inr < 0.0:
                cost_violations += 1

        checks.append(
            InvariantCheckResult(
                check_name="Non-negative Operational Costs",
                passed=(cost_violations == 0),
                details=f"Found {cost_violations} negative cost calculations.",
                metadata={"cost_violations": cost_violations},
            )
        )

        # Invariant 4: No null or unassigned actions
        invalid_actions = 0
        for ev in evaluations:
            if ev.recommended_action not in ActionType:
                invalid_actions += 1

        checks.append(
            InvariantCheckResult(
                check_name="Valid Action Type Integrity",
                passed=(invalid_actions == 0),
                details=f"Found {invalid_actions} invalid action types.",
                metadata={"invalid_actions": invalid_actions},
            )
        )

        passed_count = sum(1 for c in checks if c.passed)
        failed_count = len(checks) - passed_count
        all_passed = (failed_count == 0)

        return VerificationSuiteResult(
            all_passed=all_passed,
            total_checks=len(checks),
            passed_checks=passed_count,
            failed_checks=failed_count,
            checks=checks,
        )

    def verify_simulation_utility(
        self,
        summary_baseline: PolicySimulationSummary,
        summary_candidate: PolicySimulationSummary,
    ) -> InvariantCheckResult:
        """
        Verify that candidate policy achieves strictly superior net economic utility.
        """
        base_utility = summary_baseline.net_economic_utility_inr
        cand_utility = summary_candidate.net_economic_utility_inr
        delta = cand_utility - base_utility
        passed = delta > 0

        return InvariantCheckResult(
            check_name="Net Economic Utility Superiority",
            passed=passed,
            details=(
                f"Candidate utility (₹{cand_utility:,.2f}) vs Baseline utility (₹{base_utility:,.2f}), "
                f"Delta: +₹{delta:,.2f} (Superior: {passed})"
            ),
            metadata={
                "baseline_utility_inr": base_utility,
                "candidate_utility_inr": cand_utility,
                "utility_delta_inr": delta,
            },
        )
