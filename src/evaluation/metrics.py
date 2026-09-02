"""
RiskOrbit — Metrics Engine

Computes the complete evaluation suite:
  - Precision / Recall / F1 / FPR
  - Confusion matrix
  - PR curve
  - Abuse-pattern breakdown
  - Hard-negative breakdown
  - Cost-sensitivity analysis

CRITICAL RULE: held-out test data is NEVER accessed for threshold selection.
All threshold tuning uses validation data only.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server/script use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: Optional[np.ndarray] = None,
    label: str = "",
) -> dict:
    """
    Compute the standard evaluation suite.

    Headline metrics (in priority order):
      1. Precision
      2. Recall
      3. F1
      4. PR-AUC
      5. FPR (False-Positive Rate)

    Accuracy is computed but NOT used as the primary metric.

    Args:
        y_true: ground-truth binary labels
        y_pred: binary predictions at operating threshold
        y_score: continuous scores (optional, for PR curve and PR-AUC)
        label: partition name for logging

    Returns:
        dict with all metrics
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    accuracy = float((tp + tn) / len(y_true))

    support_positive = int(y_true.sum())
    support_negative = int((1 - y_true).sum())

    pr_auc = 0.0
    brier = 0.0
    if y_score is not None:
        y_score_arr = np.asarray(y_score, dtype=float)
        if support_positive > 0 and support_negative > 0:
            pr_auc = float(average_precision_score(y_true, y_score_arr))
            brier = float(brier_score_loss(y_true, y_score_arr))

    metrics = {
        "partition": label,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc, 4) if y_score is not None else None,
        "brier_score": round(brier, 4) if y_score is not None else None,
        "fpr": round(fpr, 4),
        "accuracy": round(accuracy, 4),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "support_positive": support_positive,
        "support_negative": support_negative,
    }

    if label:
        pr_str = f"  PR-AUC={pr_auc:.4f}" if y_score is not None else ""
        logger.info(
            "[%s] Precision=%.4f  Recall=%.4f  F1=%.4f%s  FPR=%.4f  "
            "TP=%d  FP=%d  FN=%d  TN=%d",
            label, precision, recall, f1, pr_str, fpr, tp, fp, fn, tn,
        )

    return metrics


# ---------------------------------------------------------------------------
# Ring-level metrics
# ---------------------------------------------------------------------------

def compute_ring_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    ring_ids: pd.Series,
) -> dict:
    """
    Compute ring-level detection metrics for coordinated abuse.

    Definitions:
      - Ring Recall: fraction of abuse rings with >= 1 detected member (TP >= 1)
      - Strong Ring Recall: fraction of abuse rings with >= 50% detected members
      - Complete Ring Detection: fraction of abuse rings with 100% detected members
      - Missed Rings: count and % of abuse rings with 0 detected members
      - Average Detected Fraction: mean percentage of ring transactions detected
    """
    df = pd.DataFrame({
        "y_true": np.asarray(y_true, dtype=int),
        "y_pred": np.asarray(y_pred, dtype=int),
        "ring_id": ring_ids.fillna("").astype(str).values,
    })

    abuse_df = df[(df["y_true"] == 1) & (df["ring_id"] != "")].copy()
    if len(abuse_df) == 0:
        return {
            "total_rings": 0,
            "detected_rings_at_least_1": 0,
            "ring_recall": 0.0,
            "strong_ring_recall": 0.0,
            "complete_ring_detection_rate": 0.0,
            "missed_rings_count": 0,
            "missed_rings_pct": 0.0,
            "avg_detected_fraction_per_ring": 0.0,
        }

    ring_stats = abuse_df.groupby("ring_id").agg(
        total_txns=("y_true", "count"),
        detected_txns=("y_pred", "sum"),
    ).reset_index()

    ring_stats["detected_frac"] = ring_stats["detected_txns"] / ring_stats["total_txns"]
    n_rings = len(ring_stats)
    detected_at_least_1 = int((ring_stats["detected_txns"] >= 1).sum())
    strong_detected = int((ring_stats["detected_frac"] >= 0.50).sum())
    complete_detected = int((ring_stats["detected_frac"] == 1.0).sum())
    missed_count = int((ring_stats["detected_txns"] == 0).sum())

    ring_recall = round(detected_at_least_1 / n_rings, 4) if n_rings > 0 else 0.0
    strong_ring_recall = round(strong_detected / n_rings, 4) if n_rings > 0 else 0.0
    complete_rate = round(complete_detected / n_rings, 4) if n_rings > 0 else 0.0
    missed_pct = round(missed_count / n_rings, 4) if n_rings > 0 else 0.0
    avg_frac = round(float(ring_stats["detected_frac"].mean()), 4)

    return {
        "total_rings": n_rings,
        "detected_rings_at_least_1": detected_at_least_1,
        "ring_recall": ring_recall,
        "strong_ring_recall": strong_ring_recall,
        "complete_ring_detection_rate": complete_rate,
        "missed_rings_count": missed_count,
        "missed_rings_pct": missed_pct,
        "avg_detected_fraction_per_ring": avg_frac,
    }


# ---------------------------------------------------------------------------
# Calibration analysis (ECE & Reliability)
# ---------------------------------------------------------------------------

def compute_calibration_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    n_bins: int = 10,
) -> dict:
    """
    Compute Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    bin_details = []

    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]
        in_bin = (y_score >= bin_lower) & (y_score < bin_upper if i < n_bins - 1 else y_score <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = float(np.mean(y_true[in_bin]))
            bin_conf = float(np.mean(y_score[in_bin]))
            diff = abs(bin_acc - bin_conf)
            ece += (bin_size / len(y_true)) * diff
            mce = max(mce, diff)
            bin_details.append({
                "bin": f"[{bin_lower:.2f}, {bin_upper:.2f}]",
                "count": int(bin_size),
                "avg_confidence": round(bin_conf, 4),
                "true_prevalence": round(bin_acc, 4),
                "abs_error": round(diff, 4),
            })

    return {
        "expected_calibration_error": round(float(ece), 4),
        "max_calibration_error": round(float(mce), 4),
        "brier_score": round(float(brier_score_loss(y_true, y_score)), 4),
        "bin_details": bin_details,
    }


# ---------------------------------------------------------------------------
# Threshold selection
# ---------------------------------------------------------------------------

def select_threshold(
    y_true: np.ndarray,
    y_score: np.ndarray,
    objective: str = "maximize_f1",
    fpr_max: float = 0.05,
    step: float = 0.01,
) -> tuple[float, pd.DataFrame]:
    """
    Select operating threshold using VALIDATION DATA ONLY.

    Objective: maximize F1 subject to FPR ≤ fpr_max.
    If no threshold satisfies the FPR constraint, relax to best F1.

    Returns:
        (selected_threshold, threshold_sweep_df)
    """
    y_true = np.asarray(y_true, dtype=int)
    thresholds = np.arange(0.05, 0.95, step)
    rows = []
    for t in thresholds:
        y_pred = (y_score >= t).astype(int)
        m = compute_metrics(y_true, y_pred)
        m["threshold"] = round(float(t), 4)
        rows.append(m)

    sweep_df = pd.DataFrame(rows)

    # Select threshold satisfying FPR constraint first
    constrained = sweep_df[sweep_df["fpr"] <= fpr_max]
    if len(constrained) > 0:
        best_row = constrained.loc[constrained["f1"].idxmax()]
        logger.info("Threshold selected under FPR ≤ %.3f constraint", fpr_max)
    else:
        best_row = sweep_df.loc[sweep_df["f1"].idxmax()]
        logger.warning(
            "No threshold satisfies FPR ≤ %.3f — using best F1 threshold", fpr_max
        )

    selected = float(best_row["threshold"])
    logger.info(
        "Selected threshold=%.4f  P=%.4f  R=%.4f  F1=%.4f  FPR=%.4f",
        selected,
        float(best_row["precision"]),
        float(best_row["recall"]),
        float(best_row["f1"]),
        float(best_row["fpr"]),
    )
    return selected, sweep_df


# ---------------------------------------------------------------------------
# PR curve
# ---------------------------------------------------------------------------

def plot_pr_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    selected_threshold: float,
    output_path: Path,
    partition: str = "validation",
) -> None:
    """Generate and save a precision-recall curve with operating point marked."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    precision_pts, recall_pts, thresholds_pts = precision_recall_curve(y_true, y_score)

    # Operating point
    y_pred_op = (y_score >= selected_threshold).astype(int)
    op_precision = float(precision_score(y_true, y_pred_op, zero_division=0))
    op_recall = float(recall_score(y_true, y_pred_op, zero_division=0))
    prevalence = float(y_true.mean())

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(recall_pts, precision_pts, lw=2, label="PR curve", color="#2563EB")
    ax.axhline(prevalence, ls="--", color="#DC2626", label=f"Baseline prevalence ({prevalence:.3f})")
    ax.scatter(
        [op_recall], [op_precision],
        marker="*", s=250, color="#F59E0B", zorder=5,
        label=f"Operating point (t={selected_threshold:.2f})\nP={op_precision:.3f}, R={op_recall:.3f}",
    )
    ax.set_xlabel("Recall", fontsize=13)
    ax.set_ylabel("Precision", fontsize=13)
    ax.set_title(f"Precision-Recall Curve — {partition}", fontsize=14)
    ax.set_xlim([0, 1.02])
    ax.set_ylim([0, 1.05])
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("PR curve saved to %s", output_path)


# ---------------------------------------------------------------------------
# Abuse-pattern breakdown
# ---------------------------------------------------------------------------

def pattern_breakdown(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    ring_ids: pd.Series,
    transactions: pd.DataFrame,
    abuse_metadata: pd.DataFrame,
) -> pd.DataFrame:
    """
    Report precision/recall per abuse pattern type.

    Requires abuse_metadata with ring_id → abuse_pattern_type mapping.
    """
    if len(abuse_metadata) == 0 or "abuse_pattern_type" not in abuse_metadata.columns:
        return pd.DataFrame()

    ring_pattern_map = dict(zip(
        abuse_metadata["ring_id"], abuse_metadata["abuse_pattern_type"]
    ))

    # Map each transaction's ring to its pattern
    patterns = ring_ids.map(ring_pattern_map).fillna("legitimate")
    results = []
    for pattern in sorted(patterns.unique()):
        mask = patterns == pattern
        yt = np.asarray(y_true)[mask]
        yp = np.asarray(y_pred)[mask]
        if yt.sum() == 0 and pattern != "legitimate":
            continue
        m = compute_metrics(yt, yp, label=f"pattern:{pattern}")
        m["pattern"] = pattern
        results.append(m)

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Hard-negative breakdown
# ---------------------------------------------------------------------------

def hard_negative_breakdown(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    hard_negative_types: pd.Series,
) -> pd.DataFrame:
    """
    Report false-positive rate per hard-negative type.

    Only legitimate rows (y_true=0) are included.
    The FPR within each hard-negative category shows how often
    the model incorrectly flags legitimate look-alikes.
    """
    results = []
    mask_legit = np.asarray(y_true) == 0
    hn_types = hard_negative_types.fillna("").astype(str)

    for hn_type in sorted(hn_types[mask_legit].unique()):
        if hn_type == "":
            hn_type_label = "other_legitimate"
        else:
            hn_type_label = hn_type

        mask = mask_legit & (hn_types == hn_type)
        yt = np.asarray(y_true)[mask]
        yp = np.asarray(y_pred)[mask]
        n = len(yt)
        n_fp = int(yp.sum())
        fpr_hn = round(n_fp / n, 4) if n > 0 else 0.0

        results.append({
            "hard_negative_type": hn_type_label,
            "n_legitimate_rows": n,
            "n_incorrectly_flagged": n_fp,
            "false_positive_rate": fpr_hn,
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Model comparison table
# ---------------------------------------------------------------------------

def print_model_comparison(comparison_rows: list[dict]) -> pd.DataFrame:
    """Format a model comparison table."""
    df = pd.DataFrame(comparison_rows)[
        ["model", "partition", "precision", "recall", "f1", "fpr", "fp_cost"]
    ].sort_values(["partition", "f1"], ascending=[True, False])

    logger.info("\n" + df.to_string(index=False))
    return df
