"""
RiskOrbit — Main LightGBM Risk Model

LightGBM is chosen for:
  - Native handling of class imbalance (scale_pos_weight or class_weight)
  - Tree SHAP for local explanations (exact, not approximate)
  - Fast training on tabular data
  - No need for deep learning complexity

The model is trained once, artifacts are saved with version metadata,
and the threshold is selected on validation data only.

No deep learning. No LLM classification.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

MODEL_VERSION = "riskorbit-risk-v1"


def build_lgbm_pipeline(cfg: dict) -> Pipeline:
    """
    Build preprocessing + LightGBM pipeline.

    LightGBM handles missing values natively after imputation,
    but we apply median imputation for compatibility.
    """
    lgbm_cfg = cfg["model"]["lgbm"]
    lgbm_params = {k: v for k, v in lgbm_cfg.items() if k != "class_weight"}

    model = lgb.LGBMClassifier(**lgbm_params, is_unbalance=True)

    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("lgbm", model),
        ]
    )


def train_main_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    cfg: dict,
) -> Pipeline:
    """
    Train the main LightGBM model with early stopping on validation set.
    """
    pipeline = build_lgbm_pipeline(cfg)
    lgbm_cfg = cfg["model"]["lgbm"]

    # Fit imputer first to get transformed arrays for eval set
    pipeline.named_steps["imputer"].fit(X_train)
    X_train_imp = pipeline.named_steps["imputer"].transform(X_train)
    X_val_imp = pipeline.named_steps["imputer"].transform(X_val)

    pipeline.named_steps["lgbm"].fit(
        X_train_imp,
        y_train,
        eval_set=[(X_val_imp, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )
    logger.info(
        "LightGBM trained — best iteration: %d",
        pipeline.named_steps["lgbm"].best_iteration_,
    )
    return pipeline


def get_feature_importance(pipeline: Pipeline, feature_names: list[str]) -> pd.DataFrame:
    """Return LightGBM feature importances (gain-based)."""
    lgbm = pipeline.named_steps["lgbm"]
    importances = lgbm.feature_importances_
    return (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def compute_shap_values(
    pipeline: Pipeline,
    X: pd.DataFrame,
    max_rows: int = 1000,
) -> np.ndarray:
    """
    Compute Tree SHAP values for explainability.

    Returns shap_values array of shape (n_rows, n_features) for class=1.
    Uses a sample if X is large.
    """
    lgbm = pipeline.named_steps["lgbm"]
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(X)
    if len(X_imp) > max_rows:
        idx = np.random.choice(len(X_imp), max_rows, replace=False)
        X_imp = X_imp[idx]

    explainer = shap.TreeExplainer(lgbm)
    shap_vals = explainer.shap_values(X_imp)
    # For binary classification LightGBM returns list [neg_class, pos_class]
    if isinstance(shap_vals, list):
        return shap_vals[1]
    return shap_vals


def get_top_signals(
    pipeline: Pipeline,
    row: pd.DataFrame,
    feature_names: list[str],
    top_n: int = 5,
) -> list[dict]:
    """
    Return top SHAP signals for a single transaction row.

    This is the Phase 2-facing explanation contract.
    """
    lgbm = pipeline.named_steps["lgbm"]
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(row)
    explainer = shap.TreeExplainer(lgbm)
    shap_vals = explainer.shap_values(X_imp)
    if isinstance(shap_vals, list):
        sv = shap_vals[1][0]
    else:
        sv = shap_vals[0]

    abs_sv = np.abs(sv)
    top_idx = np.argsort(abs_sv)[::-1][:top_n]

    signals = []
    row_vals = X_imp[0]
    total = abs_sv.sum() if abs_sv.sum() > 0 else 1.0
    for i in top_idx:
        signals.append(
            {
                "feature": feature_names[i],
                "value": round(float(row_vals[i]), 4),
                "importance": round(float(abs_sv[i]) / total, 4),
            }
        )
    return signals


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------

def save_artifact(
    pipeline: Pipeline,
    threshold: float,
    feature_names: list[str],
    val_metrics: dict,
    cfg: dict,
    artifact_dir: Path,
) -> None:
    """Save versioned model artifacts."""
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Model
    joblib.dump(pipeline, artifact_dir / "model.pkl")

    # Threshold
    (artifact_dir / "threshold.json").write_text(
        json.dumps({"threshold": threshold, "model_version": MODEL_VERSION}, indent=2)
    )

    # Feature schema
    (artifact_dir / "feature_schema.json").write_text(
        json.dumps({"feature_names": feature_names, "n_features": len(feature_names)}, indent=2)
    )

    # Model metadata
    lgbm_cfg = cfg["model"]["lgbm"]
    meta = {
        "model_type": "LightGBMClassifier",
        "model_version": MODEL_VERSION,
        "training_seed": lgbm_cfg["random_state"],
        "dataset_version": "phase1-v1",
        "feature_version": "phase1-v1",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "threshold_selection_objective": cfg["threshold"]["objective"],
        "threshold_selection_partition": "validation",
        "validation_metrics": val_metrics,
        "library_versions": {
            "lightgbm": lgb.__version__,
            "shap": shap.__version__,
        },
    }
    (artifact_dir / "model_metadata.json").write_text(json.dumps(meta, indent=2))

    # Training config snapshot
    (artifact_dir / "training_config.json").write_text(json.dumps(cfg["model"], indent=2))

    logger.info("Artifacts saved to %s", artifact_dir)


def load_artifact(artifact_dir: Path) -> tuple:
    """
    Load pipeline, threshold, and feature schema from artifact directory.

    Returns:
        (pipeline, threshold, feature_names)
    """
    pipeline = joblib.load(artifact_dir / "model.pkl")
    threshold_data = json.loads((artifact_dir / "threshold.json").read_text())
    feature_data = json.loads((artifact_dir / "feature_schema.json").read_text())
    return pipeline, threshold_data["threshold"], feature_data["feature_names"]
