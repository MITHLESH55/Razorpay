"""
RiskOrbit — Logistic Regression Baseline
Simple ML baseline using proper preprocessing.

Provides a more principled lower bound than the rule baseline.
Uses sklearn Pipeline for preprocessing + LR in one object.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

logger = logging.getLogger(__name__)


def build_logistic_pipeline(cfg: dict) -> Pipeline:
    """
    Build a complete preprocessing + logistic regression pipeline.

    Returns an unfitted sklearn Pipeline.
    """
    lr_cfg = cfg["model"]["logistic"]
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    max_iter=lr_cfg["max_iter"],
                    C=lr_cfg["C"],
                    class_weight=lr_cfg["class_weight"],
                    random_state=lr_cfg["random_state"],
                    solver=lr_cfg["solver"],
                ),
            ),
        ]
    )


def get_feature_importance(pipeline: Pipeline, feature_names: list[str]) -> pd.DataFrame:
    """Return logistic regression coefficients as feature importance proxy."""
    lr = pipeline.named_steps["lr"]
    coefs = lr.coef_[0]
    return (
        pd.DataFrame({"feature": feature_names, "importance": np.abs(coefs)})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
