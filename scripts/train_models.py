"""
RiskOrbit — Model Training Script

Trains three models:
  1. Rule baseline
  2. Logistic regression
  3. LightGBM (main model)

Feature computation is performed on train/val partitions separately
to avoid leakage between partitions.

Threshold is selected on the validation set only.
Final artifacts are saved to artifacts/riskorbit-risk-v1/.

Usage:
    python scripts/train_models.py [--config configs/generation_config.yaml]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.cost_model import FPCostModel
from src.evaluation.metrics import (
    compute_metrics,
    plot_pr_curve,
    select_threshold,
)
from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.models.logistic_baseline import build_logistic_pipeline
from src.models.main_model import (
    MODEL_VERSION,
    save_artifact,
    train_main_model,
)
from src.models.rule_baseline import RuleBaseline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_models")


def load_data() -> tuple:
    """Load all reference tables and split CSVs."""
    raw = Path("data/raw")
    splits = Path("data/splits")

    # Reference tables
    customers = pd.read_csv(raw / "customers.csv")
    merchants = pd.read_csv(raw / "merchants.csv")
    devices = pd.read_csv(raw / "devices.csv")
    ip_entities = pd.read_csv(raw / "ip_entities.csv")
    instruments = pd.read_csv(raw / "instruments.csv")
    orders = pd.read_csv(raw / "orders.csv")
    refunds = pd.read_csv(raw / "refunds.csv")

    # Splits
    train = pd.read_csv(splits / "train.csv")
    val = pd.read_csv(splits / "validation.csv")
    # Deliberately NOT loading heldout_test.csv here

    for df in [train, val]:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    orders["created_at"] = pd.to_datetime(orders["created_at"], format="mixed")

    return customers, merchants, devices, ip_entities, instruments, orders, refunds, train, val


def build_feature_sets(
    train: pd.DataFrame,
    val: pd.DataFrame,
    orders: pd.DataFrame,
    refunds: pd.DataFrame,
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
) -> tuple:
    """
    Build feature matrices for train and val.
    
    Train features: computed using only train transactions as context (no leakage).
    Val features: computed using train context only (simulates real-time scoring).
    """
    logger.info("Building train features (%d rows) …", len(train))
    X_train = build_features(
        transactions=train,
        orders=orders,
        refunds=refunds,
        customers=customers,
        merchants=merchants,
        devices=devices,
        ip_entities=ip_entities,
        instruments=instruments,
        reference_transactions=train,
    )
    y_train = train["abuse_label"].values

    logger.info("Building validation features (%d rows) …", len(val))
    X_val = build_features(
        transactions=val,
        orders=orders,
        refunds=refunds,
        customers=customers,
        merchants=merchants,
        devices=devices,
        ip_entities=ip_entities,
        instruments=instruments,
        reference_transactions=train,  # use only train as context
    )
    y_val = val["abuse_label"].values

    logger.info("Feature matrix: %d train | %d val | %d features", len(X_train), len(X_val), len(FEATURE_COLUMNS))
    return X_train, y_train, X_val, y_val


def main(config_path: str = "configs/generation_config.yaml") -> None:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Check required files exist
    for required in ["data/raw/transactions.csv", "data/splits/train.csv", "data/splits/validation.csv"]:
        if not Path(required).exists():
            logger.error("Missing: %s — run generate_data.py and create_splits.py first", required)
            sys.exit(1)

    customers, merchants, devices, ip_entities, instruments, orders, refunds, train, val = load_data()

    X_train, y_train, X_val, y_val = build_feature_sets(
        train, val, orders, refunds, customers, merchants, devices, ip_entities, instruments
    )

    # Save feature matrices for reuse
    feat_dir = Path("data/processed")
    feat_dir.mkdir(parents=True, exist_ok=True)
    X_train_df = pd.DataFrame(X_train, columns=FEATURE_COLUMNS)
    X_val_df = pd.DataFrame(X_val, columns=FEATURE_COLUMNS)
    X_train_df["abuse_label"] = y_train
    X_val_df["abuse_label"] = y_val
    X_train_df.to_csv(feat_dir / "train_features.csv", index=False)
    X_val_df.to_csv(feat_dir / "val_features.csv", index=False)
    logger.info("Feature matrices saved to %s", feat_dir)

    cost_model = FPCostModel(cfg)
    comparison_rows = []

    # ----------------------------------------------------------------
    # Model 1: Rule Baseline
    # ----------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("MODEL 1: Rule Baseline")
    rule = RuleBaseline()
    y_pred_rule = rule.predict_from_features(X_val_df.drop(columns=["abuse_label"]))
    y_score_rule = rule.predict_proba_from_features(X_val_df.drop(columns=["abuse_label"]))
    m_rule = compute_metrics(y_val, y_pred_rule, label="RuleBaseline/val")
    fp_cost_rule = cost_model.total_fp_cost(m_rule["fp"])
    m_rule.update({"model": "RuleBaseline", "fp_cost": round(fp_cost_rule, 2)})
    comparison_rows.append(m_rule)

    # ----------------------------------------------------------------
    # Model 2: Logistic Regression
    # ----------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("MODEL 2: Logistic Regression")
    lr_pipeline = build_logistic_pipeline(cfg)
    lr_pipeline.fit(X_train_df.drop(columns=["abuse_label"]), y_train)
    y_score_lr = lr_pipeline.predict_proba(X_val_df.drop(columns=["abuse_label"]))[:, 1]
    y_pred_lr = (y_score_lr >= 0.5).astype(int)
    m_lr = compute_metrics(y_val, y_pred_lr, label="LogisticRegression/val")
    fp_cost_lr = cost_model.total_fp_cost(m_lr["fp"])
    m_lr.update({"model": "LogisticRegression", "fp_cost": round(fp_cost_lr, 2)})
    comparison_rows.append(m_lr)

    # ----------------------------------------------------------------
    # Model 3: LightGBM
    # ----------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("MODEL 3: LightGBM")
    lgbm_pipeline = train_main_model(
        X_train_df.drop(columns=["abuse_label"]),
        y_train,
        X_val_df.drop(columns=["abuse_label"]),
        y_val,
        cfg,
    )
    y_score_lgbm = lgbm_pipeline.predict_proba(
        lgbm_pipeline.named_steps["imputer"].transform(
            X_val_df.drop(columns=["abuse_label"])
        )
    )[:, 1]

    # ---- Threshold selection on validation ----
    threshold_cfg = cfg["threshold"]
    selected_threshold, sweep_df = select_threshold(
        y_true=y_val,
        y_score=y_score_lgbm,
        objective=threshold_cfg["objective"],
        fpr_max=threshold_cfg["fpr_max"],
        step=threshold_cfg["search_step"],
    )
    logger.info("THRESHOLD FROZEN at %.4f (selected on validation only)", selected_threshold)

    y_pred_lgbm = (y_score_lgbm >= selected_threshold).astype(int)
    m_lgbm = compute_metrics(y_val, y_pred_lgbm, label="LightGBM/val")
    fp_cost_lgbm = cost_model.total_fp_cost(m_lgbm["fp"])
    m_lgbm.update({"model": "LightGBM", "fp_cost": round(fp_cost_lgbm, 2)})
    comparison_rows.append(m_lgbm)

    # ---- PR curve ----
    plot_pr_curve(
        y_val, y_score_lgbm, selected_threshold,
        Path("reports/figures/precision_recall_curve.png"),
        partition="validation",
    )

    # ---- Cost sensitivity ----
    cost_table = cost_model.cost_sensitivity_table(sweep_df, int(y_val.sum()), int((1 - y_val).sum()))
    cost_table.to_csv(Path("reports/cost_sensitivity.csv"), index=False)

    # ---- Model comparison ----
    comp_df = pd.DataFrame(comparison_rows)
    logger.info("\n%s", comp_df[["model", "precision", "recall", "f1", "fpr", "fp_cost"]].to_string(index=False))
    comp_df.to_csv(Path("reports/model_comparison.csv"), index=False)

    # ---- Save LightGBM artifacts ----
    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    save_artifact(
        pipeline=lgbm_pipeline,
        threshold=selected_threshold,
        feature_names=FEATURE_COLUMNS,
        val_metrics=m_lgbm,
        cfg=cfg,
        artifact_dir=artifact_dir,
    )

    # Also save LR for completeness
    import joblib
    joblib.dump(lr_pipeline, artifact_dir / "logistic_baseline.pkl")

    logger.info("Training complete. Artifacts at %s", artifact_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/generation_config.yaml")
    args = parser.parse_args()
    main(args.config)
