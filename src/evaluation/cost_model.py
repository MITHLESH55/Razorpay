"""
RiskOrbit — False-Positive Cost Model

A documented synthetic cost model for the financial impact of false positives.

IMPORTANT DISCLAIMER: These are synthetic/modeled estimates. They do NOT
represent real Razorpay financial data, actual loss figures, or production
operating costs. They exist to reason about the business trade-off between
precision and recall.

Formula (see FALSE_POSITIVE_COST.md for full derivation):
  FP_cost_per_row = friction_cost + review_cost
                  + (avg_legitimate_txn_value × block_rate_assumption)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FPCostModel:
    """
    Compute the estimated financial cost of false-positive interventions.

    Phase 1 assumption: intervention is a "soft hold" (flag for review),
    NOT an outright block. Therefore block_rate_assumption = 0.0 and
    the primary costs are friction + review.

    Parameters (all in INR, synthetic):
      avg_legitimate_txn_value: average value of a legitimate transaction
      friction_cost_per_fp: customer friction cost per incorrectly flagged txn
      review_cost_per_fp: analyst review cost per incorrectly flagged case
      block_rate_assumption: fraction of flagged transactions that get blocked
    """

    def __init__(self, cfg: dict) -> None:
        cost_cfg = cfg["cost_model"]
        self.avg_txn_value = float(cost_cfg["avg_legitimate_txn_value"])
        self.friction_cost = float(cost_cfg["friction_cost_per_fp"])
        self.review_cost = float(cost_cfg["review_cost_per_fp"])
        self.block_rate = float(cost_cfg["block_rate_assumption"])

    def cost_per_fp(self) -> float:
        """Cost of a single false positive (INR)."""
        return (
            self.friction_cost
            + self.review_cost
            + self.avg_txn_value * self.block_rate
        )

    def total_fp_cost(self, n_fp: int) -> float:
        """Total cost for n_fp false positives (INR)."""
        return n_fp * self.cost_per_fp()

    def cost_sensitivity_table(
        self,
        sweep_df: pd.DataFrame,
        y_true_count: int,
        y_neg_count: int,
    ) -> pd.DataFrame:
        """
        Produce a cost-sensitivity table across threshold values.

        Args:
            sweep_df: threshold sweep DataFrame from select_threshold()
            y_true_count: total positive examples in evaluation set
            y_neg_count: total negative examples in evaluation set

        Returns:
            DataFrame with threshold, precision, recall, fpr, fp_count, fp_cost.
        """
        rows = []
        for _, row in sweep_df.iterrows():
            fp_count = int(round(float(row["fpr"]) * y_neg_count))
            rows.append({
                "threshold": row["threshold"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "fpr": row["fpr"],
                "fp_count": fp_count,
                "fp_cost_inr": round(self.total_fp_cost(fp_count), 2),
            })
        return pd.DataFrame(rows)

    def summary(self, n_fp: int) -> dict:
        return {
            "n_false_positives": n_fp,
            "cost_per_fp_inr": self.cost_per_fp(),
            "total_fp_cost_inr": self.total_fp_cost(n_fp),
            "assumptions": {
                "avg_legitimate_txn_value_inr": self.avg_txn_value,
                "friction_cost_per_fp_inr": self.friction_cost,
                "review_cost_per_fp_inr": self.review_cost,
                "block_rate": self.block_rate,
                "intervention_type": "soft_hold_flag_only",
                "disclaimer": (
                    "SYNTHETIC ESTIMATE ONLY. Not actual Razorpay financial data."
                ),
            },
        }
