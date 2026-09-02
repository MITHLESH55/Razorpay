"""
RiskOrbit — Threshold Selection Script

Runs threshold sweep on validation set and saves cost-sensitivity table.

Usage:
    python scripts/select_threshold.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.cost_model import FPCostModel
from src.evaluation.metrics import plot_pr_curve, select_threshold
from src.models.main_model import load_artifact

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("select_threshold")


def main() -> None:
    with open("configs/generation_config.yaml") as f:
        cfg = yaml.safe_load(f)

    feat_val_path = Path("data/processed/val_features.csv")
    if not feat_val_path.exists():
        logger.error("Validation features not found — run train_models.py first")
        sys.exit(1)

    val_feat = pd.read_csv(feat_val_path)
    X_val = val_feat.drop(columns=["abuse_label"])
    y_val = val_feat["abuse_label"].values

    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    pipeline, threshold, feature_names = load_artifact(artifact_dir)
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(X_val[feature_names])
    y_score = pipeline.named_steps["lgbm"].predict_proba(X_imp)[:, 1]

    threshold_cfg = cfg["threshold"]
    selected, sweep_df = select_threshold(
        y_val, y_score,
        objective=threshold_cfg["objective"],
        fpr_max=threshold_cfg["fpr_max"],
        step=threshold_cfg["search_step"],
    )

    cost_model = FPCostModel(cfg)
    cost_table = cost_model.cost_sensitivity_table(
        sweep_df, int(y_val.sum()), int((1 - y_val).sum())
    )
    cost_table.to_csv(Path("reports/cost_sensitivity.csv"), index=False)

    plot_pr_curve(
        y_val, y_score, selected,
        Path("reports/figures/precision_recall_curve.png"),
        partition="validation",
    )

    logger.info("Selected threshold: %.4f — see reports/cost_sensitivity.csv", selected)


if __name__ == "__main__":
    main()
