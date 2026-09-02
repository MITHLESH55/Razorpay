"""
RiskOrbit — Train Phase 2 Graph-Enhanced Risk Model

Trains riskorbit-risk-v2 combining canonical Phase 1 features with point-in-time
graph-derived features. Selects threshold exclusively on Validation partition.

Outputs:
  - artifacts/riskorbit-risk-v2/ (model.pkl, threshold.json, etc.)
  - data/processed/train_features_v2.csv
  - data/processed/val_features_v2.csv
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.cost_model import FPCostModel
from src.evaluation.metrics import (
    compute_metrics,
    plot_pr_curve,
    select_threshold,
)
from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.graph.features import (
    GRAPH_FEATURE_COLUMNS,
    extract_graph_features_for_transactions,
)
from src.graph.graph_engine import PaymentGraphEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_graph_model")

PHASE2_FEATURE_COLUMNS = FEATURE_COLUMNS + GRAPH_FEATURE_COLUMNS
MODEL_VERSION = "riskorbit-risk-v2"


def main():
    with open("configs/generation_config.yaml") as f:
        cfg = yaml.safe_load(f)

    raw = Path("data/raw")
    splits = Path("data/splits")
    processed = Path("data/processed")
    processed.mkdir(parents=True, exist_ok=True)

    train_split = pd.read_csv(splits / "train.csv")
    val_split = pd.read_csv(splits / "validation.csv")
    train_split["timestamp"] = pd.to_datetime(train_split["timestamp"], format="mixed")
    val_split["timestamp"] = pd.to_datetime(val_split["timestamp"], format="mixed")

    orders = pd.read_csv(raw / "orders.csv")
    refunds = pd.read_csv(raw / "refunds.csv")
    customers = pd.read_csv(raw / "customers.csv")
    merchants = pd.read_csv(raw / "merchants.csv")
    devices = pd.read_csv(raw / "devices.csv")
    ip_entities = pd.read_csv(raw / "ip_entities.csv")
    instruments = pd.read_csv(raw / "instruments.csv")

    # Load Phase 1 features if existing, or build them
    p1_train_path = processed / "train_features.csv"
    p1_val_path = processed / "val_features.csv"

    if p1_train_path.exists() and p1_val_path.exists():
        logger.info("Loading existing Phase 1 feature matrices ...")
        X_tr_p1 = pd.read_csv(p1_train_path)[FEATURE_COLUMNS]
        X_va_p1 = pd.read_csv(p1_val_path)[FEATURE_COLUMNS]
    else:
        logger.info("Building Phase 1 feature matrices ...")
        X_tr_p1 = build_features(train_split, orders, refunds, customers, merchants, devices, ip_entities, instruments, reference_transactions=train_split)
        X_va_p1 = build_features(val_split, orders, refunds, customers, merchants, devices, ip_entities, instruments, reference_transactions=train_split)

    # Initialize Graph Engine from train context
    logger.info("Initializing Graph Engine from training data ...")
    graph_engine = PaymentGraphEngine(
        transactions=train_split,
        orders=orders[orders["order_id"].isin(train_split["order_id"])],
        refunds=refunds[refunds["transaction_id"].isin(train_split["transaction_id"])],
        customers=customers,
        merchants=merchants,
        devices=devices,
        ip_entities=ip_entities,
        instruments=instruments,
    )

    logger.info("Extracting graph features for Train partition (%d rows) ...", len(train_split))
    tr_graph_feat = extract_graph_features_for_transactions(
        transactions=train_split,
        graph_engine=graph_engine,
        as_of_time=train_split["timestamp"].max(),
    )

    logger.info("Extracting graph features for Validation partition (%d rows) ...", len(val_split))
    va_graph_feat = extract_graph_features_for_transactions(
        transactions=val_split,
        graph_engine=graph_engine,
        as_of_time=train_split["timestamp"].max(),  # Point-in-time train cutoff
    )

    # Combine features
    X_train_v2 = pd.concat([X_tr_p1.reset_index(drop=True), tr_graph_feat.reset_index(drop=True)], axis=1)
    X_val_v2 = pd.concat([X_va_p1.reset_index(drop=True), va_graph_feat.reset_index(drop=True)], axis=1)

    y_train = train_split["abuse_label"].values
    y_val = val_split["abuse_label"].values

    # Save processed Phase 2 feature matrices
    X_train_v2["abuse_label"] = y_train
    X_val_v2["abuse_label"] = y_val
    X_train_v2.to_csv(processed / "train_features_v2.csv", index=False)
    X_val_v2.to_csv(processed / "val_features_v2.csv", index=False)
    logger.info("Phase 2 feature matrices saved to %s", processed)

    X_train_clean = X_train_v2[PHASE2_FEATURE_COLUMNS]
    X_val_clean = X_val_v2[PHASE2_FEATURE_COLUMNS]

    # Train LightGBM v2 pipeline
    lgbm_cfg = cfg["model"]["lgbm"]
    lgbm_params = {k: v for k, v in lgbm_cfg.items() if k != "class_weight"}

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("lgbm", lgb.LGBMClassifier(**lgbm_params, is_unbalance=True)),
    ])

    pipeline.named_steps["imputer"].fit(X_train_clean)
    X_tr_imp = pipeline.named_steps["imputer"].transform(X_train_clean)
    X_va_imp = pipeline.named_steps["imputer"].transform(X_val_clean)

    logger.info("Fitting Phase 2 LightGBM model ...")
    pipeline.named_steps["lgbm"].fit(
        X_tr_imp, y_train,
        eval_set=[(X_va_imp, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )

    # Threshold selection on validation set only
    val_score = pipeline.named_steps["lgbm"].predict_proba(X_va_imp)[:, 1]
    selected_threshold, sweep_df = select_threshold(
        y_true=y_val,
        y_score=val_score,
        objective=cfg["threshold"]["objective"],
        fpr_max=cfg["threshold"]["fpr_max"],
        step=cfg["threshold"]["search_step"],
    )
    logger.info("PHASE 2 THRESHOLD FROZEN at %.4f (selected on validation only)", selected_threshold)

    val_pred = (val_score >= selected_threshold).astype(int)
    val_m = compute_metrics(y_val, val_pred, val_score, label="LightGBM_v2/val")

    # Save artifacts in artifacts/riskorbit-risk-v2/
    artifact_dir = Path("artifacts/riskorbit-risk-v2")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(pipeline, artifact_dir / "model.pkl")
    (artifact_dir / "threshold.json").write_text(
        json.dumps({"threshold": selected_threshold, "model_version": MODEL_VERSION}, indent=2)
    )
    (artifact_dir / "feature_schema.json").write_text(
        json.dumps({"feature_names": PHASE2_FEATURE_COLUMNS, "n_features": len(PHASE2_FEATURE_COLUMNS)}, indent=2)
    )

    meta = {
        "model_type": "LightGBMClassifier_GraphEnhanced",
        "model_version": MODEL_VERSION,
        "training_seed": cfg["seed"],
        "dataset_version": "phase1-v1",
        "graph_version": "graph-v2",
        "feature_version": "phase2-graph-v2",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "threshold": selected_threshold,
        "threshold_selection_partition": "validation",
        "validation_metrics": val_m,
    }
    (artifact_dir / "model_metadata.json").write_text(json.dumps(meta, indent=2))
    (artifact_dir / "training_config.json").write_text(json.dumps(cfg["model"], indent=2))

    # Copy dataset hashes
    if (Path("artifacts/riskorbit-risk-v1/dataset_hashes.json")).exists():
        (artifact_dir / "dataset_hashes.json").write_text(
            Path("artifacts/riskorbit-risk-v1/dataset_hashes.json").read_text()
        )

    logger.info("Phase 2 training complete. Artifacts saved to %s", artifact_dir)


if __name__ == "__main__":
    main()
