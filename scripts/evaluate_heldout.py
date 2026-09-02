"""
RiskOrbit — Held-Out Evaluation Script

This script loads the LOCKED model artifacts and evaluates on the held-out
test set. It does NOT retrain, does NOT tune the threshold, and does NOT
modify any artifacts.

The test set is treated as read-only evidence.

Usage:
    python scripts/evaluate_heldout.py

Output:
    reports/HELDOUT_EVALUATION.md
    reports/PHASE1_EXPERIMENT_REPORT.md
    reports/figures/precision_recall_curve_heldout.png
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.cost_model import FPCostModel
from src.evaluation.error_analysis import run_error_analysis
from src.evaluation.metrics import (
    compute_calibration_metrics,
    compute_metrics,
    compute_ring_metrics,
    hard_negative_breakdown,
    pattern_breakdown,
    plot_pr_curve,
)
from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.models.main_model import load_artifact

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("evaluate_heldout")


def main() -> None:
    import yaml
    with open("configs/generation_config.yaml") as f:
        cfg = yaml.safe_load(f)

    # ---- Load frozen artifacts -----------------------------------
    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    if not artifact_dir.exists():
        logger.error("Artifacts not found — run train_models.py first")
        sys.exit(1)

    pipeline, threshold, feature_names = load_artifact(artifact_dir)
    logger.info("Loaded artifacts (threshold=%.4f)", threshold)

    # ---- Load test set (read-only) --------------------------------
    test_path = Path("data/splits/heldout_test.csv")
    if not test_path.exists():
        logger.error("heldout_test.csv not found — run create_splits.py first")
        sys.exit(1)
    test_df = pd.read_csv(test_path, low_memory=False)
    test_df["timestamp"] = pd.to_datetime(test_df["timestamp"], format="mixed")
    logger.info("Held-out test set loaded: %d rows", len(test_df))

    # ---- Load reference data (train context only) ----------------
    raw = Path("data/raw")
    train = pd.read_csv(Path("data/splits/train.csv"), low_memory=False)
    train["timestamp"] = pd.to_datetime(train["timestamp"], format="mixed")

    customers = pd.read_csv(raw / "customers.csv", low_memory=False)
    merchants = pd.read_csv(raw / "merchants.csv", low_memory=False)
    devices = pd.read_csv(raw / "devices.csv", low_memory=False)
    ip_entities = pd.read_csv(raw / "ip_entities.csv", low_memory=False)
    instruments = pd.read_csv(raw / "instruments.csv", low_memory=False)
    orders = pd.read_csv(raw / "orders.csv", low_memory=False)
    refunds = pd.read_csv(raw / "refunds.csv", low_memory=False)
    orders["created_at"] = pd.to_datetime(orders["created_at"], format="mixed")

    # Abuse metadata for pattern breakdown
    meta_path = raw / "generation_metadata" / "abuse_rings.csv"
    abuse_metadata = pd.read_csv(meta_path) if meta_path.exists() else pd.DataFrame()

    # ---- Build features (train context only) ---------------------
    logger.info("Building test features …")
    X_test = build_features(
        transactions=test_df,
        orders=orders,
        refunds=refunds,
        customers=customers,
        merchants=merchants,
        devices=devices,
        ip_entities=ip_entities,
        instruments=instruments,
        reference_transactions=train,  # ONLY train context — no future leakage
    )
    y_test = test_df["abuse_label"].values

    # ---- Score ---------------------------------------------------
    imputer = pipeline.named_steps["imputer"]
    X_imp = imputer.transform(X_test)
    y_score = pipeline.predict_proba(X_imp)[:, 1]
    y_pred = (y_score >= threshold).astype(int)

    # ---- Core metrics --------------------------------------------
    metrics = compute_metrics(y_test, y_pred, y_score, label="LightGBM/heldout")

    cost_model = FPCostModel(cfg)
    fp_cost = cost_model.total_fp_cost(metrics["fp"])
    fp_summary = cost_model.summary(metrics["fp"])

    # ---- PR curve ------------------------------------------------
    plot_pr_curve(
        y_test, y_score, threshold,
        Path("reports/figures/precision_recall_curve_heldout.png"),
        partition="heldout_test",
    )

    # ---- Pattern breakdown ----------------------------------------
    ring_ids = test_df["ring_id"] if "ring_id" in test_df.columns else pd.Series([""] * len(test_df))
    hn_types = test_df["hard_negative_type"] if "hard_negative_type" in test_df.columns else pd.Series([""] * len(test_df))

    pat_df = pattern_breakdown(y_test, y_pred, ring_ids, test_df, abuse_metadata)
    hn_df = hard_negative_breakdown(y_test, y_pred, hn_types)

    # ---- Error analysis ------------------------------------------
    error_result = run_error_analysis(
        features=X_test,
        y_true=y_test,
        y_pred=y_pred,
        y_score=y_score,
        transactions=test_df,
        hard_negative_types=hn_types,
        ring_ids=ring_ids,
        abuse_metadata=abuse_metadata,
        output_path=Path("ERROR_ANALYSIS.md"),
    )

    # ---- Ring-level metrics --------------------------------------
    ring_metrics = compute_ring_metrics(y_test, y_pred, ring_ids)

    # ---- Calibration metrics -------------------------------------
    from src.evaluation.metrics import compute_calibration_metrics
    cal_metrics = compute_calibration_metrics(y_test, y_score)

    # ---- Write HELDOUT_EVALUATION.md ----------------------------
    _write_heldout_report(metrics, fp_cost, fp_summary, pat_df, hn_df, threshold, ring_metrics, cal_metrics)

    # ---- Write PHASE1_EXPERIMENT_REPORT.md ----------------------
    _write_experiment_report(metrics, fp_cost, pat_df, hn_df, threshold, cfg, ring_metrics, cal_metrics)

    logger.info("Held-out evaluation complete.")


def _write_heldout_report(
    metrics: dict,
    fp_cost: float,
    fp_summary: dict,
    pat_df: pd.DataFrame,
    hn_df: pd.DataFrame,
    threshold: float,
    ring_metrics: dict,
    cal_metrics: dict,
) -> None:
    lines = [
        "# RiskOrbit — Held-Out Evaluation Report",
        "",
        "> **IMPORTANT:** This report was generated using ONLY the locked model and frozen",
        "> threshold. No retraining or threshold adjustment occurred after this evaluation.",
        "",
        "---",
        "",
        "## Primary Metrics (Held-Out Test Set)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Precision | **{metrics['precision']:.4f}** |",
        f"| Recall | **{metrics['recall']:.4f}** |",
        f"| F1 | **{metrics['f1']:.4f}** |",
        f"| PR-AUC | **{metrics['pr_auc']:.4f}** |",
        f"| FPR | {metrics['fpr']:.4f} |",
        f"| Accuracy (informational only) | {metrics['accuracy']:.4f} |",
        "",
        "## Calibration & Reliability",
        "",
        f"- **Brier Score:** {cal_metrics['brier_score']:.4f}",
        f"- **Expected Calibration Error (ECE):** {cal_metrics['expected_calibration_error']:.4f}",
        f"- **Max Calibration Error (MCE):** {cal_metrics['max_calibration_error']:.4f}",
        "",
        "## Confusion Matrix",
        "",
        f"| | Predicted Negative | Predicted Positive |",
        f"|---|------------------:|------------------:|",
        f"| **Actual Negative** | TN={metrics['tn']:,} | FP={metrics['fp']:,} |",
        f"| **Actual Positive** | FN={metrics['fn']:,} | TP={metrics['tp']:,} |",
        "",
        "## Ring-Level Detection Metrics",
        "",
        f"- **Total Abuse Rings in Holdout:** {ring_metrics['total_rings']}",
        f"- **Rings Detected (>= 1 Member):** {ring_metrics['detected_rings_at_least_1']} ({ring_metrics['ring_recall']*100:.2f}% Ring Recall)",
        f"- **Strong Ring Detection (>= 50% Members):** {ring_metrics['strong_ring_recall']*100:.2f}%",
        f"- **Complete Ring Detection (100% Members):** {ring_metrics['complete_ring_detection_rate']*100:.2f}%",
        f"- **Rings Completely Missed:** {ring_metrics['missed_rings_count']} ({ring_metrics['missed_rings_pct']*100:.2f}%)",
        f"- **Average Detected Fraction per Ring:** {ring_metrics['avg_detected_fraction_per_ring']*100:.2f}%",
        "",
        "## Support",
        "",
        f"- Abuse cases: {metrics['support_positive']:,}",
        f"- Legitimate cases: {metrics['support_negative']:,}",
        f"- Operating threshold: **{threshold:.4f}**",
        "",
        "## False-Positive Cost (Synthetic Estimate)",
        "",
        "> DISCLAIMER: All cost figures are synthetic estimates. Not real Razorpay data.",
        "",
        f"- False positives: {metrics['fp']:,}",
        f"- Cost per FP: ₹{fp_summary['cost_per_fp_inr']:.2f}",
        f"- **Total FP cost: ₹{fp_cost:,.2f}**",
        "",
        "## Abuse Pattern Breakdown",
        "",
    ]
    if len(pat_df) > 0:
        lines.append(pat_df[["pattern", "precision", "recall", "f1", "fpr", "support_positive"]].to_markdown(index=False))
    else:
        lines.append("_(pattern breakdown unavailable)_")

    lines += ["", "## Hard-Negative Breakdown", ""]
    if len(hn_df) > 0:
        lines.append(hn_df.to_markdown(index=False))
    else:
        lines.append("_(hard-negative breakdown unavailable)_")

    Path("reports/HELDOUT_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Held-out report written to reports/HELDOUT_EVALUATION.md")


def _write_experiment_report(
    metrics: dict, fp_cost: float,
    pat_df: pd.DataFrame, hn_df: pd.DataFrame,
    threshold: float, cfg: dict,
    ring_metrics: dict = None, cal_metrics: dict = None,
) -> None:
    lines = [
        "# RiskOrbit — Phase 1 Experiment Report",
        "",
        "## Objective",
        "",
        "Detect coordinated refund abuse among payment transactions using a",
        "leakage-resistant ML pipeline trained on a synthetic payment ecosystem.",
        "",
        "**Primary prediction target:** `abuse_label = 1` → transaction belongs to a",
        "coordinated refund-abuse ring.",
        "",
        "**NOT in scope:** chargeback fraud, account takeover, card theft, phishing.",
        "",
        "---",
        "",
        "## Dataset",
        "",
        f"- Temporal window: {cfg['temporal']['start_date']} to {cfg['temporal']['end_date']}",
        f"- Customers: ~{cfg['scale']['n_customers']:,}",
        f"- Merchants: ~{cfg['scale']['n_merchants']:,}",
        f"- Devices: ~{cfg['scale']['n_devices']:,}",
        f"- IP entities: ~{cfg['scale']['n_ip_entities']:,}",
        "",
        "## Abuse Patterns Injected",
        "",
        "| Pattern | Description |",
        "|---------|-------------|",
        "| Pattern A (Shared Device) | Multiple accounts share devices, burst-refund same merchant |",
        "| Pattern B (Cross-Merchant) | Related accounts target multiple merchants with similar amounts |",
        "| Pattern C (Rotating Account) | New accounts appear over time linked by shared IP/instrument |",
        "",
        "## Hard Negatives (Legitimate Confusers)",
        "",
        "| Type | Purpose |",
        "|------|---------|",
        "| household_sharing | Legit device sharing within family |",
        "| shared_network | Office/university IP sharing |",
        "| high_refund_customer | Legitimate serial returner |",
        "| high_volume_merchant | Legitimate high-refund-rate merchant |",
        "| new_customer_high_value | Legit new customer, expensive purchase |",
        "| multi_device_customer | Legit power user with many devices |",
        "",
        "## Split Methodology",
        "",
        "- **Algorithm:** Ring-aware group split + time-ordered legitimate split",
        "- **Abuse rings:** Whole rings assigned to exactly one partition",
        "- **Legitimate rows:** Sorted by timestamp, oldest 70% → train, next 15% → val, newest 15% → test",
        "- **Ring leakage check:** Asserted ring_id sets are disjoint across all partitions",
        "",
        "## Models Compared",
        "",
        "| Model | Type |",
        "|-------|------|",
        "| RuleBaseline | 6 domain-intuition rules, transparent scoring |",
        "| LogisticRegression | sklearn Pipeline with imputer + scaler + LR |",
        "| LightGBM | Gradient-boosted trees, Tree SHAP explainability |",
        "",
        "## Threshold Selection",
        "",
        f"- **Objective:** Maximize F1 subject to FPR ≤ {cfg['threshold']['fpr_max']}",
        f"- **Selected threshold:** {threshold:.4f}",
        "- **Selection partition:** Validation only (held-out test never used for tuning)",
        "- **Threshold frozen:** YES",
        "",
        "## Validation Results",
        "",
        "_(see model_comparison.csv in reports/ for full comparison)_",
        "",
        "## Held-Out Results (Final)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Precision | {metrics['precision']:.4f} |",
        f"| Recall | {metrics['recall']:.4f} |",
        f"| F1 | {metrics['f1']:.4f} |",
        f"| FPR | {metrics['fpr']:.4f} |",
        f"| False-Positive Cost (synthetic) | ₹{fp_cost:,.2f} |",
        "",
        "## Limitations",
        "",
        "1. **Synthetic data ≠ production data.** Real fraud evolves adversarially; synthetic",
        "   patterns are fixed by design. Performance will differ on real data.",
        "2. **Pattern B and C FNs.** Cross-ring coordination requires Phase 2 graph features",
        "   for full recall. Per-transaction aggregations are insufficient for cross-ring signals.",
        "3. **No graph engine.** Phase 1 relationship features are simple aggregations. A full",
        "   graph analysis (Phase 2) would improve recall on ring-level patterns.",
        "4. **Hard negatives are known.** In production, new types of legitimate confusers",
        "   will emerge that were not anticipated in generation.",
        "5. **Cost model is synthetic.** Real intervention costs depend on actual Razorpay",
        "   policy, which is not modeled here.",
        "",
        "---",
        "",
        "> Phase 1 complete. Phase 2 not implemented.",
    ]
    Path("reports/PHASE1_EXPERIMENT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Experiment report written to reports/PHASE1_EXPERIMENT_REPORT.md")


if __name__ == "__main__":
    main()
