"""
RiskOrbit — Validation Evaluation Script

Evaluates all three models on the validation set.
Records model comparison table.

Usage:
    python scripts/evaluate_validation.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.cost_model import FPCostModel
from src.evaluation.metrics import compute_metrics
from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.models.rule_baseline import RuleBaseline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_validation")


def main() -> None:
    with open("configs/generation_config.yaml") as f:
        cfg = yaml.safe_load(f)

    # Check for processed features first (faster)
    feat_val_path = Path("data/processed/val_features.csv")
    if feat_val_path.exists():
        logger.info("Loading pre-computed validation features …")
        val_feat = pd.read_csv(feat_val_path)
        X_val = val_feat.drop(columns=["abuse_label"])
        y_val = val_feat["abuse_label"].values
    else:
        logger.error("Validation features not found — run train_models.py first")
        sys.exit(1)

    cost_model = FPCostModel(cfg)

    # Rule baseline
    rule = RuleBaseline()
    y_pred_rule = rule.predict_from_features(X_val)
    m_rule = compute_metrics(y_val, y_pred_rule, label="RuleBaseline/val")
    m_rule.update({"model": "RuleBaseline", "fp_cost": cost_model.total_fp_cost(m_rule["fp"])})

    # LightGBM
    from src.models.main_model import load_artifact
    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    if not artifact_dir.exists():
        logger.error("Artifacts not found — run train_models.py first")
        sys.exit(1)
    pipeline, threshold, feature_names = load_artifact(artifact_dir)
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(X_val[feature_names])
    y_score_lgbm = pipeline.named_steps["lgbm"].predict_proba(X_imp)[:, 1]
    y_pred_lgbm = (y_score_lgbm >= threshold).astype(int)
    m_lgbm = compute_metrics(y_val, y_pred_lgbm, label="LightGBM/val")
    m_lgbm.update({"model": "LightGBM", "fp_cost": cost_model.total_fp_cost(m_lgbm["fp"])})

    comp_df = pd.DataFrame([m_rule, m_lgbm])
    logger.info("\n%s", comp_df[["model", "precision", "recall", "f1", "fpr", "fp_cost"]].to_string(index=False))


if __name__ == "__main__":
    main()
