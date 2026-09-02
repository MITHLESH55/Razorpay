"""
RiskOrbit — Rule-Based Baseline
A transparent, interpretable baseline using domain-intuition rules.

Rules are combined with AND/OR logic. No threshold tuning on test data.
Evaluated using the same precision/recall/F1 framework as the ML models.

The rule baseline answers the question:
  "How much of the problem can simple heuristics solve?"

Rules use ONLY the same features available in the feature pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RuleBaseline:
    """
    Conservative rule-based detector for coordinated refund abuse.

    A transaction is flagged (score=1) if it satisfies a weighted
    combination of suspicious indicators. Each rule contributes a
    severity score; the total score is compared to a threshold.

    Rules:
      R1. Very high refund velocity in 24h (≥ 3 refunds)
      R2. Shared device with many accounts (≥ 4)
      R3. Young account (≤ 14 days) with multiple refunds
      R4. Very high refund rate (≥ 0.8)
      R5. High IP-account count (≥ 8) + elevated refund rate on IP
      R6. Amount > 3σ above merchant average + refund_velocity_24h > 1

    A transaction is flagged when total_score ≥ flagging_threshold.
    """

    flagging_threshold: float = 2.0  # sum of rule weights needed to flag

    # Rule weights
    _RULE_WEIGHTS: dict = field(default_factory=lambda: {
        "high_refund_velocity_24h": 1.5,
        "shared_device_many_accounts": 1.2,
        "young_account_with_refunds": 1.0,
        "very_high_refund_rate": 1.0,
        "shared_ip_high_refund": 1.0,
        "suspicious_amount_with_velocity": 0.8,
    })

    def predict_proba_from_features(self, features: pd.DataFrame) -> np.ndarray:
        """
        Compute a heuristic 'score' in [0, 1] by normalizing rule totals.

        Returns array of shape (n,) — abuse probability approximation.
        """
        scores = self._compute_rule_scores(features)
        # Normalize to [0,1] by dividing by max possible score
        max_score = sum(self._RULE_WEIGHTS.values())
        return np.clip(scores / max_score, 0.0, 1.0)

    def predict_from_features(self, features: pd.DataFrame) -> np.ndarray:
        """Binary predictions using flagging_threshold."""
        scores = self._compute_rule_scores(features)
        return (scores >= self.flagging_threshold).astype(int)

    def _compute_rule_scores(self, features: pd.DataFrame) -> np.ndarray:
        """Compute aggregate rule score for each row."""
        n = len(features)
        scores = np.zeros(n, dtype=float)
        weights = self._RULE_WEIGHTS

        # R1: High refund velocity 24h
        if "refund_velocity_24h" in features.columns:
            scores += weights["high_refund_velocity_24h"] * (
                features["refund_velocity_24h"] >= 3
            ).values.astype(float)

        # R2: Shared device with many accounts
        if "accounts_per_device" in features.columns:
            scores += weights["shared_device_many_accounts"] * (
                features["accounts_per_device"] >= 4
            ).values.astype(float)

        # R3: Young account with refunds
        if "account_age_days" in features.columns and "cust_refund_count" in features.columns:
            scores += weights["young_account_with_refunds"] * (
                (features["account_age_days"] <= 14) & (features["cust_refund_count"] >= 2)
            ).values.astype(float)

        # R4: Very high refund rate
        if "cust_refund_rate" in features.columns:
            scores += weights["very_high_refund_rate"] * (
                features["cust_refund_rate"] >= 0.8
            ).values.astype(float)

        # R5: Shared IP with high refund rate
        if "accounts_per_ip" in features.columns and "refund_rate_per_ip" in features.columns:
            scores += weights["shared_ip_high_refund"] * (
                (features["accounts_per_ip"] >= 8) & (features["refund_rate_per_ip"] >= 0.4)
            ).values.astype(float)

        # R6: Suspicious amount z-score + velocity
        if "amount_zscore_vs_merchant" in features.columns and "refund_velocity_24h" in features.columns:
            scores += weights["suspicious_amount_with_velocity"] * (
                (features["amount_zscore_vs_merchant"] >= 3.0)
                & (features["refund_velocity_24h"] >= 1)
            ).values.astype(float)

        return scores

    def feature_importance(self) -> dict:
        """Return rule weights as a proxy for feature importance."""
        return dict(self._RULE_WEIGHTS)
