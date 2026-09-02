"""
RiskOrbit — Phase 2 Graph Feature Ablation Study

Models:
  A = Phase 1 (Frozen baseline)
  B = Phase 1 + simple relationship aggregates (customer graph degree counts)
  C = Phase 1 + full graph-derived features (ring_risk_score, ring_device_count, etc.)
  D = Phase 1 + ring_risk_score only (single graph score integration)
  E = Phase 2 v2 (full graph features + retrained model)

All models evaluated on the same locked held-out test set.
No parameter tuning against test set.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.pipeline import FEATURE_COLUMNS
from src.graph.features import GRAPH_FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase2_ablation")

PHASE2_FEATURE_COLUMNS = FEATURE_COLUMNS + GRAPH_FEATURE_COLUMNS


def calc_metrics(y_true, y_pred, y_score):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    prauc = float(average_precision_score(y_true, y_score))
    return dict(precision=round(prec, 4), recall=round(rec, 4), f1=round(f1, 4),
                prauc=round(prauc, 4), fpr=round(fpr, 4),
                tp=tp, fp=fp, fn=fn, tn=tn, fp_cost=fp * 130)


def pattern_recall(y_true, y_pred, test_split, prefix):
    mask = test_split.get("ring_id", pd.Series("", index=test_split.index)).str.startswith(prefix, na=False)
    idx = test_split[mask].index
    if len(idx) == 0:
        return 0.0, 0
    yt = y_true[idx]
    yp = y_pred[idx]
    support = int(yt.sum())
    tp = int(((yt == 1) & (yp == 1)).sum())
    return round(tp / support, 4) if support > 0 else 0.0, support


def train_lgbm(X_tr, y_tr, X_va, y_va, n_features_for_log):
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("lgbm", lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            is_unbalance=True,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )),
    ])
    imp = pipeline.named_steps["imputer"]
    imp.fit(X_tr)
    X_tr_imp = imp.transform(X_tr)
    X_va_imp = imp.transform(X_va)
    pipeline.named_steps["lgbm"].fit(
        X_tr_imp, y_tr,
        eval_set=[(X_va_imp, y_va)],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )
    val_score = pipeline.named_steps["lgbm"].predict_proba(X_va_imp)[:, 1]

    # Select threshold on validation
    best_thr, best_f1 = 0.35, -1.0
    for thr in np.arange(0.05, 0.80, 0.01):
        yp = (val_score >= thr).astype(int)
        tp = int(((y_va == 1) & (yp == 1)).sum())
        fp = int(((y_va == 0) & (yp == 1)).sum())
        fn = int(((y_va == 1) & (yp == 0)).sum())
        tn = int(((y_va == 0) & (yp == 0)).sum())
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        if fpr > 0.05:
            continue
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_thr = round(thr, 2)

    logger.info("  n_features=%d → val_threshold=%.2f val_F1=%.4f", n_features_for_log, best_thr, best_f1)
    return pipeline, best_thr


def main():
    processed = Path("data/processed")
    splits = Path("data/splits")

    # Load feature matrices
    train_v1 = pd.read_csv(processed / "train_features.csv")
    val_v1 = pd.read_csv(processed / "val_features.csv")
    test_v1 = pd.read_csv(processed / "test_features.csv")

    train_v2 = pd.read_csv(processed / "train_features_v2.csv")
    val_v2 = pd.read_csv(processed / "val_features_v2.csv")
    test_v2 = pd.read_csv(processed / "test_features_v2.csv")

    train_split = pd.read_csv(splits / "train.csv")
    val_split = pd.read_csv(splits / "validation.csv")
    test_split = pd.read_csv(splits / "heldout_test.csv")

    y_train = train_split["abuse_label"].values
    y_val = val_split["abuse_label"].values
    y_test = test_split["abuse_label"].values

    X_tr_p1 = train_v1[FEATURE_COLUMNS].values
    X_va_p1 = val_v1[FEATURE_COLUMNS].values
    X_te_p1 = test_v1[FEATURE_COLUMNS].values

    X_tr_p2 = train_v2[PHASE2_FEATURE_COLUMNS].values
    X_va_p2 = val_v2[PHASE2_FEATURE_COLUMNS].values
    X_te_p2 = test_v2[PHASE2_FEATURE_COLUMNS].values

    # Compute simple relationship aggregate features (customer graph degree from ring_* columns)
    graph_simple_cols = ["ring_customer_count", "ring_device_count", "ring_ip_count"]
    X_tr_gs = train_v2[graph_simple_cols].values
    X_va_gs = val_v2[graph_simple_cols].values
    X_te_gs = test_v2[graph_simple_cols].values

    # Single score: ring_risk_score only
    X_tr_rs = train_v2[["ring_risk_score"]].values
    X_va_rs = val_v2[["ring_risk_score"]].values
    X_te_rs = test_v2[["ring_risk_score"]].values

    results = {}

    # Model A: Phase 1 frozen (load artifacts, no retraining)
    logger.info("Model A: Phase 1 Frozen Baseline (no retraining) …")
    model_a = joblib.load("artifacts/riskorbit-risk-v1/model.pkl")
    thr_a = json.loads(Path("artifacts/riskorbit-risk-v1/threshold.json").read_text())["threshold"]
    imp_a = model_a.named_steps["imputer"]
    score_te_a = model_a.named_steps["lgbm"].predict_proba(imp_a.transform(X_te_p1))[:, 1]
    pred_te_a = (score_te_a >= thr_a).astype(int)
    results["A"] = {**calc_metrics(y_test, pred_te_a, score_te_a),
                    "n_features": len(FEATURE_COLUMNS), "threshold": thr_a,
                    "pat_a": pattern_recall(y_test, pred_te_a, test_split, "RING_A")[0],
                    "pat_b": pattern_recall(y_test, pred_te_a, test_split, "RING_B")[0],
                    "pat_c": pattern_recall(y_test, pred_te_a, test_split, "RING_C")[0]}

    # Model B: Phase 1 + simple graph degree aggregates
    logger.info("Model B: Phase 1 + Simple Graph Aggregates (ring_customer_count, ring_device_count, ring_ip_count) …")
    X_tr_b = np.hstack([X_tr_p1, X_tr_gs])
    X_va_b = np.hstack([X_va_p1, X_va_gs])
    X_te_b = np.hstack([X_te_p1, X_te_gs])
    model_b, thr_b = train_lgbm(X_tr_b, y_train, X_va_b, y_val, X_tr_b.shape[1])
    imp_b = model_b.named_steps["imputer"]
    score_te_b = model_b.named_steps["lgbm"].predict_proba(imp_b.transform(X_te_b))[:, 1]
    pred_te_b = (score_te_b >= thr_b).astype(int)
    results["B"] = {**calc_metrics(y_test, pred_te_b, score_te_b),
                    "n_features": X_tr_b.shape[1], "threshold": thr_b,
                    "pat_a": pattern_recall(y_test, pred_te_b, test_split, "RING_A")[0],
                    "pat_b": pattern_recall(y_test, pred_te_b, test_split, "RING_B")[0],
                    "pat_c": pattern_recall(y_test, pred_te_b, test_split, "RING_C")[0]}

    # Model C: Phase 1 + full graph features (10 graph-derived columns)
    logger.info("Model C: Phase 1 + Full Graph-Derived Features (%d graph cols) …", len(GRAPH_FEATURE_COLUMNS))
    model_c, thr_c = train_lgbm(X_tr_p2, y_train, X_va_p2, y_val, X_tr_p2.shape[1])
    imp_c = model_c.named_steps["imputer"]
    score_te_c = model_c.named_steps["lgbm"].predict_proba(imp_c.transform(X_te_p2))[:, 1]
    pred_te_c = (score_te_c >= thr_c).astype(int)
    results["C"] = {**calc_metrics(y_test, pred_te_c, score_te_c),
                    "n_features": X_tr_p2.shape[1], "threshold": thr_c,
                    "pat_a": pattern_recall(y_test, pred_te_c, test_split, "RING_A")[0],
                    "pat_b": pattern_recall(y_test, pred_te_c, test_split, "RING_B")[0],
                    "pat_c": pattern_recall(y_test, pred_te_c, test_split, "RING_C")[0]}

    # Model D: Phase 1 features + ring_risk_score only (single graph signal)
    logger.info("Model D: Phase 1 + ring_risk_score only …")
    X_tr_d = np.hstack([X_tr_p1, X_tr_rs])
    X_va_d = np.hstack([X_va_p1, X_va_rs])
    X_te_d = np.hstack([X_te_p1, X_te_rs])
    model_d, thr_d = train_lgbm(X_tr_d, y_train, X_va_d, y_val, X_tr_d.shape[1])
    imp_d = model_d.named_steps["imputer"]
    score_te_d = model_d.named_steps["lgbm"].predict_proba(imp_d.transform(X_te_d))[:, 1]
    pred_te_d = (score_te_d >= thr_d).astype(int)
    results["D"] = {**calc_metrics(y_test, pred_te_d, score_te_d),
                    "n_features": X_tr_d.shape[1], "threshold": thr_d,
                    "pat_a": pattern_recall(y_test, pred_te_d, test_split, "RING_A")[0],
                    "pat_b": pattern_recall(y_test, pred_te_d, test_split, "RING_B")[0],
                    "pat_c": pattern_recall(y_test, pred_te_d, test_split, "RING_C")[0]}

    # Model E: Phase 2 full (locked v2 artifact)
    logger.info("Model E: Phase 2 full (riskorbit-risk-v2) …")
    model_e = joblib.load("artifacts/riskorbit-risk-v2/model.pkl")
    thr_e = json.loads(Path("artifacts/riskorbit-risk-v2/threshold.json").read_text())["threshold"]
    imp_e = model_e.named_steps["imputer"]
    score_te_e = model_e.named_steps["lgbm"].predict_proba(imp_e.transform(X_te_p2))[:, 1]
    pred_te_e = (score_te_e >= thr_e).astype(int)
    results["E"] = {**calc_metrics(y_test, pred_te_e, score_te_e),
                    "n_features": X_tr_p2.shape[1], "threshold": thr_e,
                    "pat_a": pattern_recall(y_test, pred_te_e, test_split, "RING_A")[0],
                    "pat_b": pattern_recall(y_test, pred_te_e, test_split, "RING_B")[0],
                    "pat_c": pattern_recall(y_test, pred_te_e, test_split, "RING_C")[0]}

    # Write CSV
    rows = []
    labels = {
        "A": "Phase 1 Frozen Baseline",
        "B": "Phase 1 + Simple Graph Aggregates",
        "C": "Phase 1 + Full Graph Features",
        "D": "Phase 1 + ring_risk_score Only",
        "E": "Phase 2 Full (riskorbit-risk-v2)",
    }
    for k, v in results.items():
        rows.append({"model": k, "description": labels[k], **v})
    pd.DataFrame(rows).to_csv("reports/phase2_graph_ablation.csv", index=False)

    # Write report
    md = [
        "# RiskOrbit — Phase 2 Graph Feature Ablation Report",
        "",
        "Controlled experiment: same held-out test set, same evaluation methodology.",
        "Threshold selected on validation partition for each model.",
        "",
        "| Model | Description | N Features | Threshold | Precision | Recall | F1 | PR-AUC | FPR | FP Cost | Pat A Recall | Pat B Recall | Pat C Recall |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for k, v in results.items():
        md.append(
            f"| **{k}** | {labels[k]} | {v['n_features']} | {v['threshold']:.2f} | "
            f"{v['precision']:.4f} | {v['recall']:.4f} | {v['f1']:.4f} | {v['prauc']:.4f} | "
            f"{v['fpr']:.4f} | ₹{v['fp_cost']:,} | {v['pat_a']:.4f} | {v['pat_b']:.4f} | {v['pat_c']:.4f} |"
        )

    md.extend([
        "",
        "## Analysis",
        "",
        "### Graph vs Agent Value",
        "Models A–E isolate the contribution of each component:",
        "- **Model B–D vs A**: Graph feature value over Phase 1 baseline.",
        "- **Model E vs C**: Effect of end-to-end retraining with graph features vs ad-hoc column addition.",
        "- The LLM/Evidence Agent adds case interpretability but does NOT change the detection model.",
        "",
        "### Scientific Honesty",
        "> Any metric improvement in Phase 2 should be attributed to the graph feature engineering,",
        "> not to the LLM evidence agent. The evidence agent serves case presentation, not detection.",
    ])

    Path("reports/PHASE2_GRAPH_ABLATION.md").write_text("\n".join(md), encoding="utf-8")
    logger.info("Saved reports/PHASE2_GRAPH_ABLATION.md")
    logger.info("Saved reports/phase2_graph_ablation.csv")


if __name__ == "__main__":
    main()
