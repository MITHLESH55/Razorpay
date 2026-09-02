"""
RiskOrbit — Phase 3.1 Validation Experiment

Evaluates the transaction gating mechanism on the validation set.

Compares:
    - Phase 2.2 Baseline (P=0): Blanket expansion, FPR 75.77%, Ring Recall 79.17%
    - Phase 3.1 Gating: Confidence-weighted + transaction-level gating

Validation-only tuning of:
    - Confidence tier thresholds (PRIMARY/SECONDARY/TERTIARY)
    - Transaction gate weights and thresholds
    - Member confidence formula weights

DOES NOT TOUCH HELD-OUT TEST SET.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import networkx as nx
import pandas as pd
from lightgbm import Booster

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.member_confidence import compute_ring_member_confidences
from src.decision.transaction_gate import TransactionGate
from src.evaluation.metrics import compute_ring_metrics


def load_validation_data():
    """Load validation set and Phase 1 predictions."""
    val_split = pd.read_csv("data/splits/validation.csv")
    val_features = pd.read_csv("data/processed/val_features.csv")

    # Load Phase 1 model for transaction risk scores
    phase1_model = Booster(model_file="artifacts/phase1/risk_model_v1.txt")

    # Get Phase 1 scores
    feature_cols = [c for c in val_features.columns if c not in [
        "transaction_id", "customer_id", "order_id", "timestamp",
        "abuse_label", "ring_id", "pattern_type"
    ]]
    X_val = val_features[feature_cols].values
    phase1_scores = phase1_model.predict(X_val)

    val_features["phase1_score"] = phase1_scores

    return val_split, val_features


def build_validation_graph(val_features: pd.DataFrame, as_of_time: datetime) -> nx.Graph:
    """Build point-in-time graph for validation set."""
    engine = PaymentGraphEngine.from_data_dir("data/raw")

    # Build graph using PaymentGraphEngine
    graph = engine.build_networkx_graph_as_of(
        as_of_timestamp=as_of_time,
        min_edge_strength=0.0,
    )

    return graph


def evaluate_phase2_2_baseline(val_split: pd.DataFrame, val_features: pd.DataFrame) -> dict:
    """
    Reproduce Phase 2.2 baseline on validation set.

    Uses P=0 (no protected pool) to match test set baseline.
    """
    # Load Phase 2.1 investigation results on validation set
    # (This would need to be run first with scripts/run_phase2_1_validation.py)
    # For now, simulate by loading ring candidates

    val_with_scores = val_split.merge(
        val_features[["transaction_id", "customer_id", "phase1_score"]],
        on="transaction_id",
        how="left"
    )

    # Simulate Phase 2.2 baseline: all ring member transactions flagged
    # (In practice, would load actual Phase 2.1/2.2 investigation results)

    # For validation experiment, we'll compute this properly
    # For now, return placeholder
    return {
        "approach": "Phase 2.2 Baseline (P=0)",
        "note": "Requires Phase 2.1 investigation run on validation set first"
    }


def evaluate_phase3_1_gating(
    val_split: pd.DataFrame,
    val_features: pd.DataFrame,
    graph: nx.Graph,
    gate_config: Optional[dict] = None,
) -> dict:
    """
    Evaluate Phase 3.1 gating mechanism on validation set.

    Args:
        val_split: Validation split with ground truth
        val_features: Features with Phase 1 scores
        graph: Point-in-time knowledge graph
        gate_config: Optional gate configuration (for ablation)

    Returns:
        Evaluation metrics dictionary
    """
    if gate_config is None:
        gate_config = {
            "weight_phase1": 0.40,
            "weight_member_conf": 0.30,
            "weight_edge_strength": 0.15,
            "weight_diversity": 0.15,
            "decision_threshold": 0.35,
            "primary_auto_gate_threshold": 0.20,
            "isolated_threshold": 0.35,
        }

    gate = TransactionGate(**gate_config)

    # Merge ground truth with features
    val_with_scores = val_split.merge(
        val_features[["transaction_id", "customer_id", "phase1_score"]],
        on="transaction_id",
        how="left"
    )

    # Get unique rings from validation set
    abuse_rings = val_split[val_split["abuse_label"] == 1]["ring_id"].dropna().unique()

    # For each ring, compute member confidences
    all_decisions = []

    for ring_id in abuse_rings:
        ring_customers = val_split[val_split["ring_id"] == ring_id]["customer_id"].unique()

        if len(ring_customers) == 0:
            continue

        # Pick primary suspect (highest Phase 1 score in ring)
        ring_scores = val_features[
            val_features["customer_id"].isin(ring_customers)
        ].groupby("customer_id")["phase1_score"].max()

        if len(ring_scores) == 0:
            continue

        primary_suspect = ring_scores.idxmax()

        # Compute member confidences
        phase1_scores_dict = val_features.set_index("customer_id")["phase1_score"].to_dict()

        confidences = compute_ring_member_confidences(
            primary_suspect_id=primary_suspect,
            member_customer_ids=list(ring_customers),
            graph=graph,
            phase1_scores=phase1_scores_dict,
            as_of_time=datetime(2024, 9, 1),  # Validation cutoff
            max_hops=2,
        )

        # Evaluate each transaction from ring members
        ring_txns = val_with_scores[val_with_scores["customer_id"].isin(ring_customers)]

        for _, txn in ring_txns.iterrows():
            customer_id = txn["customer_id"]
            member_conf = confidences.get(customer_id)

            decision = gate.evaluate_transaction(
                transaction_id=txn["transaction_id"],
                customer_id=customer_id,
                phase1_score=txn["phase1_score"],
                member_confidence=member_conf,
            )

            all_decisions.append({
                "transaction_id": txn["transaction_id"],
                "customer_id": customer_id,
                "ring_id": txn["ring_id"],
                "abuse_label": txn["abuse_label"],
                "pattern_type": txn.get("pattern_type"),
                "is_flagged": decision.is_flagged,
                "decision_score": decision.decision_score,
                "tier": decision.tier,
                "phase1_risk": decision.phase1_risk,
                "member_confidence": decision.member_confidence,
            })

    # Also evaluate isolated transactions (not in rings)
    isolated_txns = val_with_scores[
        (val_with_scores["abuse_label"] == 0) | (val_with_scores["ring_id"].isna())
    ]

    for _, txn in isolated_txns.iterrows():
        decision = gate.evaluate_transaction(
            transaction_id=txn["transaction_id"],
            customer_id=txn["customer_id"],
            phase1_score=txn["phase1_score"],
            member_confidence=None,
        )

        all_decisions.append({
            "transaction_id": txn["transaction_id"],
            "customer_id": txn["customer_id"],
            "ring_id": txn.get("ring_id"),
            "abuse_label": txn["abuse_label"],
            "pattern_type": txn.get("pattern_type"),
            "is_flagged": decision.is_flagged,
            "decision_score": decision.decision_score,
            "tier": decision.tier,
            "phase1_risk": decision.phase1_risk,
            "member_confidence": decision.member_confidence,
        })

    decisions_df = pd.DataFrame(all_decisions)

    # Compute confusion matrix
    y_true = decisions_df["abuse_label"].values
    y_pred = decisions_df["is_flagged"].astype(int).values

    TP = ((y_true == 1) & (y_pred == 1)).sum()
    TN = ((y_true == 0) & (y_pred == 0)).sum()
    FP = ((y_true == 0) & (y_pred == 1)).sum()
    FN = ((y_true == 1) & (y_pred == 0)).sum()

    total_legit = (y_true == 0).sum()
    FPR = (FP / total_legit * 100) if total_legit > 0 else 0.0

    # Compute ring-level recall
    ring_metrics = compute_ring_metrics(
        y_true=decisions_df["abuse_label"],
        y_pred=decisions_df["is_flagged"].astype(int),
        ring_ids=decisions_df["ring_id"],
    )

    # Compute pattern-level recall manually since the function signature differs
    pattern_recalls = {}
    for pattern in ["A", "B", "C"]:
        pattern_txns = decisions_df[decisions_df["pattern_type"] == pattern]
        if len(pattern_txns) > 0:
            pattern_rings = pattern_txns[pattern_txns["abuse_label"] == 1]["ring_id"].dropna().unique()
            if len(pattern_rings) > 0:
                detected_rings = 0
                for ring_id in pattern_rings:
                    ring_decisions = pattern_txns[pattern_txns["ring_id"] == ring_id]
                    if ring_decisions["is_flagged"].sum() > 0:
                        detected_rings += 1
                pattern_recalls[pattern] = round(detected_rings / len(pattern_rings), 4)
            else:
                pattern_recalls[pattern] = 0.0
        else:
            pattern_recalls[pattern] = 0.0

    return {
        "approach": "Phase 3.1 Gating",
        "config": gate_config,
        "confusion_matrix": {
            "TP": int(TP),
            "TN": int(TN),
            "FP": int(FP),
            "FN": int(FN),
        },
        "FPR": round(FPR, 2),
        "FP_count": int(FP),
        "FP_cost_inr": int(FP * 130),
        "ring_recall": ring_metrics["ring_recall"],
        "pattern_A_recall": pattern_recalls.get("A", 0.0),
        "pattern_B_recall": pattern_recalls.get("B", 0.0),
        "pattern_C_recall": pattern_recalls.get("C", 0.0),
        "tier_distribution": decisions_df["tier"].value_counts().to_dict(),
    }


def run_weight_ablation(
    val_split: pd.DataFrame,
    val_features: pd.DataFrame,
    graph: nx.Graph,
) -> list[dict]:
    """
    Run ablation study on gate weights.

    Tests different weight configurations to find optimal balance.
    """
    ablation_configs = [
        # Baseline (equal weighting philosophy)
        {"weight_phase1": 0.40, "weight_member_conf": 0.30, "weight_edge_strength": 0.15, "weight_diversity": 0.15},
        # Phase 1 heavy (trust transaction risk more)
        {"weight_phase1": 0.60, "weight_member_conf": 0.20, "weight_edge_strength": 0.10, "weight_diversity": 0.10},
        # Confidence heavy (trust ring membership more)
        {"weight_phase1": 0.30, "weight_member_conf": 0.40, "weight_edge_strength": 0.15, "weight_diversity": 0.15},
        # Diversity heavy (require multi-signal corroboration)
        {"weight_phase1": 0.35, "weight_member_conf": 0.25, "weight_edge_strength": 0.15, "weight_diversity": 0.25},
    ]

    results = []

    for config in ablation_configs:
        print(f"Running ablation: {config}")
        result = evaluate_phase3_1_gating(val_split, val_features, graph, config)
        results.append(result)

    return results


def main():
    print("="*80)
    print("RISKORBIT — PHASE 3.1 VALIDATION EXPERIMENT")
    print("="*80)
    print()

    print("Loading validation data...")
    val_split, val_features = load_validation_data()
    print(f"  Validation transactions: {len(val_split):,}")
    print(f"  Abuse transactions: {(val_split['abuse_label'] == 1).sum():,}")
    print(f"  Legitimate transactions: {(val_split['abuse_label'] == 0).sum():,}")
    print()

    print("Building point-in-time graph...")
    validation_cutoff = datetime(2024, 9, 1)  # End of validation period
    graph = build_validation_graph(val_features, validation_cutoff)
    print(f"  Graph nodes: {graph.number_of_nodes():,}")
    print(f"  Graph edges: {graph.number_of_edges():,}")
    print()

    print("Evaluating Phase 3.1 baseline configuration...")
    baseline_result = evaluate_phase3_1_gating(val_split, val_features, graph)
    print(json.dumps(baseline_result, indent=2))
    print()

    print("Running weight ablation study...")
    ablation_results = run_weight_ablation(val_split, val_features, graph)
    print()

    # Save results
    output_dir = Path("reports/phase3_1_validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "baseline_result.json", "w") as f:
        json.dump(baseline_result, f, indent=2)

    with open(output_dir / "ablation_results.json", "w") as f:
        json.dump(ablation_results, f, indent=2)

    print(f"Results saved to {output_dir}/")
    print()
    print("Phase 3.1 validation experiment complete.")


if __name__ == "__main__":
    main()
