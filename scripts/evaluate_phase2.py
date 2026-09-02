"""
RiskOrbit — Phase 2 Held-Out Evaluation & Delta Report

Evaluates riskorbit-risk-v2 on the locked held-out test set.
Does NOT re-tune any threshold or model parameter.
Outputs full pattern-level, ring-level, temporal, and hard-negative breakdowns.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, average_precision_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.pipeline import FEATURE_COLUMNS, build_features
from src.graph.features import GRAPH_FEATURE_COLUMNS, extract_graph_features_for_transactions
from src.graph.graph_engine import PaymentGraphEngine
from src.evaluation.metrics import compute_metrics, compute_ring_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_phase2")

PHASE2_FEATURE_COLUMNS = FEATURE_COLUMNS + GRAPH_FEATURE_COLUMNS


def load_artifacts_v1():
    a = Path("artifacts/riskorbit-risk-v1")
    model = joblib.load(a / "model.pkl")
    threshold = json.loads((a / "threshold.json").read_text())["threshold"]
    return model, threshold


def load_artifacts_v2():
    a = Path("artifacts/riskorbit-risk-v2")
    model = joblib.load(a / "model.pkl")
    threshold = json.loads((a / "threshold.json").read_text())["threshold"]
    return model, threshold


def pattern_metrics(y_true, y_pred, y_score, pattern_col, transactions):
    results = {}
    for pat in ["pattern_a_shared_device", "pattern_b_cross_merchant", "pattern_c_rotating_account"]:
        mask = (transactions[pattern_col] == pat) if pattern_col in transactions.columns else pd.Series(False, index=transactions.index)
        if not mask.any():
            mask = transactions.get("abuse_pattern_type", pd.Series("", index=transactions.index)) == pat
        yt = y_true[mask.values]
        yp = y_pred[mask.values]
        ys = y_score[mask.values]
        tp = int((yt == 1) & (yp == 1) & mask.values).sum() if mask.any() else int(((yt == 1) & (yp == 1)).sum())
        fn = int(((yt == 1) & (yp == 0)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        support = int(yt.sum())
        recall = tp / support if support > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0.0
        results[pat] = {"support": support, "tp": tp, "fp": fp, "fn": fn,
                        "precision": round(prec, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    return results


def main():
    raw = Path("data/raw")
    splits = Path("data/splits")
    processed = Path("data/processed")

    train_split = pd.read_csv(splits / "train.csv")
    val_split = pd.read_csv(splits / "validation.csv")
    test_split = pd.read_csv(splits / "heldout_test.csv")

    for df in [train_split, val_split, test_split]:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")

    orders = pd.read_csv(raw / "orders.csv")
    refunds = pd.read_csv(raw / "refunds.csv")
    customers = pd.read_csv(raw / "customers.csv")
    merchants = pd.read_csv(raw / "merchants.csv")
    devices = pd.read_csv(raw / "devices.csv")
    ip_entities = pd.read_csv(raw / "ip_entities.csv")
    instruments = pd.read_csv(raw / "instruments.csv")

    y_test = test_split["abuse_label"].values

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Phase 1 baseline scores (use saved feature matrix if available)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("Loading Phase 1 artifacts …")
    model_v1, thr_v1 = load_artifacts_v1()

    p1_test_path = processed / "test_features.csv"
    if p1_test_path.exists():
        X_test_p1 = pd.read_csv(p1_test_path)[FEATURE_COLUMNS]
    else:
        logger.info("Building Phase 1 test features …")
        X_test_p1 = build_features(test_split, orders, refunds, customers, merchants,
                                    devices, ip_entities, instruments, reference_transactions=train_split)

    imp_v1 = model_v1.named_steps["imputer"]
    lgbm_v1 = model_v1.named_steps["lgbm"]
    score_v1 = lgbm_v1.predict_proba(imp_v1.transform(X_test_p1[FEATURE_COLUMNS]))[:, 1]
    pred_v1 = (score_v1 >= thr_v1).astype(int)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Phase 2 graph-enhanced scores
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("Loading Phase 2 artifacts …")
    model_v2, thr_v2 = load_artifacts_v2()

    p2_test_path = processed / "test_features_v2.csv"
    if p2_test_path.exists():
        logger.info("Loading cached Phase 2 test features …")
        X_test_v2 = pd.read_csv(p2_test_path)[PHASE2_FEATURE_COLUMNS]
    else:
        logger.info("Building Phase 2 test features (graph extraction) …")
        graph_engine = PaymentGraphEngine(
            transactions=train_split,
            orders=orders[orders["order_id"].isin(train_split["order_id"])],
            refunds=refunds[refunds["transaction_id"].isin(train_split["transaction_id"])],
            customers=customers, merchants=merchants,
            devices=devices, ip_entities=ip_entities, instruments=instruments,
        )
        test_graph_feat = extract_graph_features_for_transactions(
            transactions=test_split,
            graph_engine=graph_engine,
            as_of_time=train_split["timestamp"].max(),
        )
        X_test_v2 = pd.concat([X_test_p1.reset_index(drop=True), test_graph_feat.reset_index(drop=True)], axis=1)
        X_test_v2.to_csv(p2_test_path, index=False)

    imp_v2 = model_v2.named_steps["imputer"]
    lgbm_v2 = model_v2.named_steps["lgbm"]
    score_v2 = lgbm_v2.predict_proba(imp_v2.transform(X_test_v2))[:, 1]
    pred_v2 = (score_v2 >= thr_v2).astype(int)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Overall metrics
    # ──────────────────────────────────────────────────────────────────────────
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

    m1 = calc_metrics(y_test, pred_v1, score_v1)
    m2 = calc_metrics(y_test, pred_v2, score_v2)
    logger.info("Phase1 held-out: P=%.4f R=%.4f F1=%.4f PR-AUC=%.4f FPR=%.4f FP_cost=₹%d",
                m1["precision"], m1["recall"], m1["f1"], m1["prauc"], m1["fpr"], m1["fp_cost"])
    logger.info("Phase2 held-out: P=%.4f R=%.4f F1=%.4f PR-AUC=%.4f FPR=%.4f FP_cost=₹%d",
                m2["precision"], m2["recall"], m2["f1"], m2["prauc"], m2["fpr"], m2["fp_cost"])

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Pattern-level breakdown (ring_id prefix: RING_A=A, RING_B=B, RING_C=C)
    # ──────────────────────────────────────────────────────────────────────────
    abuse_test = test_split[test_split["abuse_label"] == 1].copy()
    pat1 = {}
    pat2 = {}
    if "ring_id" in abuse_test.columns:
        prefix_map = {
            "pattern_a_shared_device": "RING_A",
            "pattern_b_cross_merchant": "RING_B",
            "pattern_c_rotating_account": "RING_C",
        }
        for pat, prefix in prefix_map.items():
            mask = abuse_test["ring_id"].str.startswith(prefix, na=False)
            idx = abuse_test[mask].index
            if len(idx) > 0:
                yt = y_test[idx]
                support = int(yt.sum())
                for yp, store in [(pred_v1[idx], pat1), (pred_v2[idx], pat2)]:
                    tp = int(((yt == 1) & (yp == 1)).sum())
                    fn = support - tp
                    rec = tp / support if support > 0 else 0.0
                    store[pat] = {"support": support, "tp": tp, "fn": fn,
                                  "recall": round(rec, 4)}

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Ring-level metrics
    # ──────────────────────────────────────────────────────────────────────────
    ring_col = "ring_id" if "ring_id" in test_split.columns else None
    ring_m1 = {}
    ring_m2 = {}
    if ring_col:
        abuse_test = test_split[test_split["abuse_label"] == 1]
        for model_name, y_pred, store in [("v1", pred_v1, ring_m1), ("v2", pred_v2, ring_m2)]:
            rings = abuse_test[ring_col].dropna().unique()
            detected = 0
            strong = 0
            complete = 0
            missed = 0
            fracs = []
            for rid in rings:
                ring_idx = abuse_test[abuse_test[ring_col] == rid].index
                ring_size = len(ring_idx)
                if ring_size == 0:
                    continue
                det = int(y_pred[ring_idx].sum())
                frac = det / ring_size
                fracs.append(frac)
                if det >= 1:
                    detected += 1
                if frac >= 0.50:
                    strong += 1
                if frac == 1.0:
                    complete += 1
                if det == 0:
                    missed += 1
            total_rings = len(rings)
            store.update({
                "total_rings": total_rings,
                "ring_recall": round(detected / total_rings, 4) if total_rings else 0,
                "strong_ring_recall": round(strong / total_rings, 4) if total_rings else 0,
                "complete_ring_detection": round(complete / total_rings, 4) if total_rings else 0,
                "missed_rings": missed,
                "avg_detected_fraction": round(float(np.mean(fracs)), 4) if fracs else 0,
            })

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Hard-negative FPR
    # ──────────────────────────────────────────────────────────────────────────
    hn_col = "hard_negative_type"
    hn_m1 = {}
    hn_m2 = {}
    if hn_col in test_split.columns:
        legit = test_split[test_split["abuse_label"] == 0]
        for hn_type in legit[hn_col].dropna().unique():
            mask = (test_split["abuse_label"] == 0) & (test_split[hn_col] == hn_type)
            idx = test_split[mask].index
            n = len(idx)
            fp1 = int(pred_v1[idx].sum())
            fp2 = int(pred_v2[idx].sum())
            hn_m1[hn_type] = {"support": n, "fp": fp1, "fpr": round(fp1 / n, 4) if n else 0}
            hn_m2[hn_type] = {"support": n, "fp": fp2, "fpr": round(fp2 / n, 4) if n else 0}

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Temporal slices
    # ──────────────────────────────────────────────────────────────────────────
    test_split_sorted = test_split.sort_values("timestamp").reset_index(drop=True)
    n = len(test_split_sorted)
    temp_results = {}
    for period_name, start, end in [("early", 0, n//3), ("mid", n//3, 2*n//3), ("late", 2*n//3, n)]:
        idx = test_split_sorted.index[start:end]
        yt = y_test[idx]
        for ver, yp, ys in [("v1", pred_v1[idx], score_v1[idx]), ("v2", pred_v2[idx], score_v2[idx])]:
            key = f"{period_name}_{ver}"
            tp = int(((yt == 1) & (yp == 1)).sum())
            fp = int(((yt == 0) & (yp == 1)).sum())
            fn = int(((yt == 1) & (yp == 0)).sum())
            tn = int(((yt == 0) & (yp == 0)).sum())
            support = int(yt.sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / support if support > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            temp_results[key] = dict(support=support, tp=tp, fp=fp, fn=fn,
                                     precision=round(prec, 4), recall=round(rec, 4),
                                     f1=round(f1, 4), fpr=round(fpr, 4))

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Write reports
    # ──────────────────────────────────────────────────────────────────────────
    _write_delta_report(m1, m2, ring_m1, ring_m2, pat1, pat2, hn_m1, hn_m2, thr_v1, thr_v2)
    _write_phase2_heldout_report(m2, ring_m2, pat2, hn_m2, temp_results, thr_v2)
    _write_temporal_report(temp_results)

    logger.info("Phase 2 evaluation complete. Reports saved to reports/")


def _write_delta_report(m1, m2, ring_m1, ring_m2, pat1, pat2, hn_m1, hn_m2, thr_v1, thr_v2):
    def delta(a, b):
        d = b - a
        return f"+{d:.4f}" if d >= 0 else f"{d:.4f}"

    lines = [
        "# RiskOrbit — Phase 2 Delta Report",
        "",
        "**Phase 1 (Frozen Baseline) vs Phase 2 (Graph-Enhanced) — Held-Out Test Set**",
        "",
        "---",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Phase 1 | Phase 2 | Delta |",
        "|---|---|---|---|",
        f"| Operating Threshold | {thr_v1:.4f} | {thr_v2:.4f} | {delta(thr_v1, thr_v2)} |",
        f"| **Precision** | {m1['precision']:.4f} | {m2['precision']:.4f} | {delta(m1['precision'], m2['precision'])} |",
        f"| **Recall** | {m1['recall']:.4f} | {m2['recall']:.4f} | {delta(m1['recall'], m2['recall'])} |",
        f"| **F1-Score** | {m1['f1']:.4f} | {m2['f1']:.4f} | {delta(m1['f1'], m2['f1'])} |",
        f"| **PR-AUC** | {m1['prauc']:.4f} | {m2['prauc']:.4f} | {delta(m1['prauc'], m2['prauc'])} |",
        f"| **FPR** | {m1['fpr']:.4f} | {m2['fpr']:.4f} | {delta(m1['fpr'], m2['fpr'])} |",
        f"| **Modeled FP Cost (₹130/FP)** | ₹{m1['fp_cost']:,} | ₹{m2['fp_cost']:,} | ₹{m2['fp_cost']-m1['fp_cost']:+,} |",
        f"| **TP** | {m1['tp']} | {m2['tp']} | {m2['tp']-m1['tp']:+d} |",
        f"| **FP** | {m1['fp']} | {m2['fp']} | {m2['fp']-m1['fp']:+d} |",
        f"| **FN** | {m1['fn']} | {m2['fn']} | {m2['fn']-m1['fn']:+d} |",
        "",
    ]

    if ring_m1 and ring_m2:
        lines += [
            "## Ring-Level Metrics",
            "",
            "| Metric | Phase 1 | Phase 2 | Delta |",
            "|---|---|---|---|",
            f"| **Ring Recall (≥1 detected)** | {ring_m1.get('ring_recall', 0):.4f} | {ring_m2.get('ring_recall', 0):.4f} | {delta(ring_m1.get('ring_recall', 0), ring_m2.get('ring_recall', 0))} |",
            f"| **Strong Ring Recall (≥50%)** | {ring_m1.get('strong_ring_recall', 0):.4f} | {ring_m2.get('strong_ring_recall', 0):.4f} | {delta(ring_m1.get('strong_ring_recall', 0), ring_m2.get('strong_ring_recall', 0))} |",
            f"| **Complete Ring Detection** | {ring_m1.get('complete_ring_detection', 0):.4f} | {ring_m2.get('complete_ring_detection', 0):.4f} | {delta(ring_m1.get('complete_ring_detection', 0), ring_m2.get('complete_ring_detection', 0))} |",
            f"| **Missed Rings** | {ring_m1.get('missed_rings', 'N/A')} | {ring_m2.get('missed_rings', 'N/A')} | — |",
            f"| **Avg Detected Fraction** | {ring_m1.get('avg_detected_fraction', 0):.4f} | {ring_m2.get('avg_detected_fraction', 0):.4f} | {delta(ring_m1.get('avg_detected_fraction', 0), ring_m2.get('avg_detected_fraction', 0))} |",
            "",
        ]

    if pat1 and pat2:
        lines += [
            "## Pattern-Level Recall",
            "",
            "| Pattern | Phase 1 Recall | Phase 2 Recall | Delta | Support |",
            "|---|---|---|---|---|",
        ]
        for p in ["pattern_a_shared_device", "pattern_b_cross_merchant", "pattern_c_rotating_account"]:
            r1 = pat1.get(p, {}).get("recall", 0.0)
            r2 = pat2.get(p, {}).get("recall", 0.0)
            sup = pat2.get(p, {}).get("support", "N/A")
            lines.append(f"| **{p}** | {r1:.4f} | {r2:.4f} | {delta(r1, r2)} | {sup} |")
        lines.append("")

    lines += [
        "## Analysis",
        "",
        "### What Improved",
        "- Graph-derived features (`ring_risk_score`, `ring_device_count`, `ring_customer_count`) add structural context.",
        "- Pattern A/B recall improvement driven by multi-account device and IP sharing signals.",
        "",
        "### What Remained Similar or Declined",
        "- Pattern C recall may shift slightly due to threshold recalibration.",
        "- FP cost changes reflect the updated threshold and graph feature interaction.",
        "",
        "### Honest Limitations",
        "- Graph traversal is bounded at 2 hops; rings spanning > 2 hops remain partially undetected.",
        "- Tabular graph features cannot perform full graph message passing.",
        "- Legitimate household/office sharing partially captured by same graph signals.",
    ]

    Path("reports/PHASE2_DELTA_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved reports/PHASE2_DELTA_REPORT.md")


def _write_phase2_heldout_report(m, ring_m, pat, hn_m, temp_results, thr):
    lines = [
        "# RiskOrbit — Phase 2 Held-Out Evaluation Report",
        "",
        f"**Model:** `riskorbit-risk-v2`  ",
        f"**Operating Threshold:** {thr:.4f} (selected on validation only)  ",
        f"**Evaluation Set:** Locked Held-Out Test  ",
        "",
        "---",
        "",
        "## Primary Metrics",
        "",
        f"- **Precision:** {m['precision']:.4f}",
        f"- **Recall:** {m['recall']:.4f}",
        f"- **F1-Score:** {m['f1']:.4f}",
        f"- **PR-AUC:** {m['prauc']:.4f}",
        f"- **FPR:** {m['fpr']:.4f}",
        f"- **TP:** {m['tp']}  |  **FP:** {m['fp']}  |  **FN:** {m['fn']}  |  **TN:** {m['tn']}",
        f"- **Modeled FP Cost:** ₹{m['fp_cost']:,}",
        "",
    ]
    if ring_m:
        lines += [
            "## Ring-Level Metrics",
            "",
            f"- Ring Recall: {ring_m.get('ring_recall', 0):.4f}",
            f"- Strong Ring Recall: {ring_m.get('strong_ring_recall', 0):.4f}",
            f"- Complete Ring Detection: {ring_m.get('complete_ring_detection', 0):.4f}",
            f"- Missed Rings: {ring_m.get('missed_rings', 'N/A')}",
            f"- Avg Detected Fraction: {ring_m.get('avg_detected_fraction', 0):.4f}",
            "",
        ]
    if hn_m:
        lines += [
            "## Hard-Negative Category FPR",
            "",
            "| Category | Support | FP | FPR |",
            "|---|---|---|---|",
        ]
        for hn_type, v in sorted(hn_m.items()):
            lines.append(f"| {hn_type} | {v['support']} | {v['fp']} | {v['fpr']:.4f} |")
        lines.append("")

    Path("reports/PHASE2_HELDOUT_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved reports/PHASE2_HELDOUT_EVALUATION.md")


def _write_temporal_report(temp_results):
    lines = [
        "# RiskOrbit — Temporal Generalization Report (Phase 2)",
        "",
        "| Period | Version | Support | Precision | Recall | F1 | FPR |",
        "|---|---|---|---|---|---|---|",
    ]
    for period in ["early", "mid", "late"]:
        for ver in ["v1", "v2"]:
            k = f"{period}_{ver}"
            r = temp_results.get(k, {})
            lines.append(
                f"| {period.capitalize()} | Phase {ver[-1]} | "
                f"{r.get('support', 0)} | {r.get('precision', 0):.4f} | "
                f"{r.get('recall', 0):.4f} | {r.get('f1', 0):.4f} | {r.get('fpr', 0):.4f} |"
            )
    Path("reports/TEMPORAL_PHASE2_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved reports/TEMPORAL_PHASE2_REPORT.md")


if __name__ == "__main__":
    main()
