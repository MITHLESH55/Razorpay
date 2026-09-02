"""
RiskOrbit — Phase 3.2: Policy Configuration & Versioning

Defines serializable, version-controlled policy specifications
mapping risk signals to concrete business actions.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.decision.actions import ActionType


@dataclass
class TierPolicyRule:
    """Action assignment thresholds for a specific member confidence tier."""
    tier: str
    block_threshold_decision: float
    block_threshold_p1: float
    delay_threshold_decision: float
    delay_threshold_p1: float
    step_up_threshold_decision: float
    step_up_threshold_p1: float
    restrict_account_min_evidence: float = 0.80
    freeze_ring_min_members: int = 5


@dataclass
class PolicyConfig:
    """Full decisioning policy specification."""
    policy_id: str = "phase3_tiered_response_v1"
    schema_version: str = "3.2.0"
    description: str = "Phase 3.2 Tiered Response Policy"
    max_auto_block_amount_inr: float = 50000.0
    max_auto_action_amount_inr: float = 100000.0
    tertiary_p1_safety_threshold: float = 0.35
    enable_human_gate: bool = True
    tier_rules: dict[str, TierPolicyRule] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert policy configuration to dictionary."""
        return {
            "policy_id": self.policy_id,
            "schema_version": self.schema_version,
            "description": self.description,
            "max_auto_block_amount_inr": self.max_auto_block_amount_inr,
            "max_auto_action_amount_inr": self.max_auto_action_amount_inr,
            "tertiary_p1_safety_threshold": self.tertiary_p1_safety_threshold,
            "enable_human_gate": self.enable_human_gate,
            "tier_rules": {k: asdict(v) for k, v in self.tier_rules.items()},
            "metadata": self.metadata,
        }

    def save_json(self, file_path: str | Path) -> None:
        """Save policy config to JSON."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyConfig:
        """Load policy config from dictionary."""
        tier_rules_raw = data.get("tier_rules", {})
        tier_rules = {
            k: TierPolicyRule(**v) for k, v in tier_rules_raw.items()
        }
        return cls(
            policy_id=data["policy_id"],
            schema_version=data.get("schema_version", "3.2.0"),
            description=data.get("description", ""),
            max_auto_block_amount_inr=data.get("max_auto_block_amount_inr", 50000.0),
            max_auto_action_amount_inr=data.get("max_auto_action_amount_inr", 100000.0),
            tertiary_p1_safety_threshold=data.get("tertiary_p1_safety_threshold", 0.35),
            enable_human_gate=data.get("enable_human_gate", True),
            tier_rules=tier_rules,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def load_json(cls, file_path: str | Path) -> PolicyConfig:
        """Load policy config from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# Alias for backwards compatibility
BoundedPolicyConfig = PolicyConfig


def get_default_phase3_policy() -> PolicyConfig:
    """Create the default recommended Phase 3.2 tiered response policy."""
    return PolicyConfig(
        policy_id="phase3_tiered_response_v1",
        schema_version="3.2.0",
        description="Phase 3.2 Proportional Tiered Interventions (2FA + Delay + Review + Targeted Block)",
        max_auto_block_amount_inr=50000.0,
        max_auto_action_amount_inr=100000.0,
        tertiary_p1_safety_threshold=0.35,
        enable_human_gate=True,
        tier_rules={
            "PRIMARY": TierPolicyRule(
                tier="PRIMARY",
                block_threshold_decision=0.60,
                block_threshold_p1=0.30,
                delay_threshold_decision=0.50,
                delay_threshold_p1=0.05,
                step_up_threshold_decision=0.40,
                step_up_threshold_p1=0.00,
                restrict_account_min_evidence=0.85,
            ),
            "SECONDARY": TierPolicyRule(
                tier="SECONDARY",
                block_threshold_decision=0.75,
                block_threshold_p1=0.40,
                delay_threshold_decision=0.55,
                delay_threshold_p1=0.25,
                step_up_threshold_decision=0.40,
                step_up_threshold_p1=0.15,
                restrict_account_min_evidence=0.90,
            ),
            "TERTIARY": TierPolicyRule(
                tier="TERTIARY",
                block_threshold_decision=0.85,
                block_threshold_p1=0.50,  # Elevated to ensure tertiary is protected
                delay_threshold_decision=0.65,
                delay_threshold_p1=0.35,
                step_up_threshold_decision=0.45,
                step_up_threshold_p1=0.20,
                restrict_account_min_evidence=0.95,
            ),
            "ISOLATED": TierPolicyRule(
                tier="ISOLATED",
                block_threshold_decision=0.70,
                block_threshold_p1=0.35,  # Matches Model E threshold
                delay_threshold_decision=0.55,
                delay_threshold_p1=0.25,
                step_up_threshold_decision=0.40,
                step_up_threshold_p1=0.15,
                restrict_account_min_evidence=0.99,
            ),
        },
        metadata={
            "author": "RiskOrbit Architecture Team",
            "tuning_dataset": "data/splits/validation.csv",
            "phase": "3.2",
        },
    )
