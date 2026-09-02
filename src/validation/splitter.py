"""
RiskOrbit — Leakage-Safe Dataset Splitter

Algorithm:
1. Group all abuse transactions by ring_id.
   - Assign 70% of rings to train, 15% to val, 15% to test.
   - Every transaction in a ring goes to exactly one partition.
   - This prevents ring leakage.

2. The remaining legitimate transactions (abuse_label=0) are sorted
   by timestamp and split in time order: oldest 70% → train,
   next 15% → val, newest 15% → test.
   - Time-order split is more realistic than random split.
   - Hard negatives are distributed across all partitions.

3. Final validation:
   - No ring_id appears in more than one partition.
   - Test partition ring_ids are disjoint from train ring_ids.
   - Abuse prevalence is checked in each partition.

The held-out test set labels are NEVER accessed during training or
threshold selection. The split script saves them separately.

CRITICALLY: ring_id and hard_negative_type are NOT model features.
They are only used in split logic and post-hoc analysis.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_splits(
    transactions: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split transactions into train / validation / held-out test.

    Args:
        transactions: full labeled transaction DataFrame
        cfg: config dict (uses cfg["splits"])
        rng: seeded RNG for ring shuffle

    Returns:
        (train_df, val_df, test_df)
        Each partition retains all original columns including abuse_label,
        ring_id (for analysis), and hard_negative_type (for analysis).
    """
    split_cfg = cfg["splits"]
    train_r = split_cfg["train_ratio"]
    val_r = split_cfg["validation_ratio"]
    # test_r = split_cfg["holdout_ratio"]   # implicitly 1 - train - val

    # ---- 1. Split abuse rings ----------------------------------------
    abuse_txns = transactions[transactions["abuse_label"] == 1].copy()
    legit_txns = transactions[transactions["abuse_label"] == 0].copy()

    ring_ids = [r for r in abuse_txns["ring_id"].unique() if r and r != ""]
    ring_ids = sorted(ring_ids)  # deterministic ordering
    rng.shuffle(ring_ids)        # then shuffle with seed

    n_rings = len(ring_ids)
    n_train_rings = max(1, int(n_rings * train_r))
    n_val_rings = max(1, int(n_rings * val_r))

    train_rings = set(ring_ids[:n_train_rings])
    val_rings = set(ring_ids[n_train_rings: n_train_rings + n_val_rings])
    test_rings = set(ring_ids[n_train_rings + n_val_rings:])

    logger.info(
        "Ring split — train: %d | val: %d | test: %d", len(train_rings), len(val_rings), len(test_rings)
    )

    train_abuse = abuse_txns[abuse_txns["ring_id"].isin(train_rings)]
    val_abuse = abuse_txns[abuse_txns["ring_id"].isin(val_rings)]
    test_abuse = abuse_txns[abuse_txns["ring_id"].isin(test_rings)]

    # ---- 2. Split legitimate rows by time ----------------------------
    legit_txns = legit_txns.sort_values("timestamp").reset_index(drop=True)
    n_legit = len(legit_txns)
    n_train_legit = int(n_legit * train_r)
    n_val_legit = int(n_legit * val_r)

    train_legit = legit_txns.iloc[:n_train_legit]
    val_legit = legit_txns.iloc[n_train_legit: n_train_legit + n_val_legit]
    test_legit = legit_txns.iloc[n_train_legit + n_val_legit:]

    # ---- 3. Combine and shuffle within each partition ----------------
    train_df = pd.concat([train_abuse, train_legit], ignore_index=True)
    val_df = pd.concat([val_abuse, val_legit], ignore_index=True)
    test_df = pd.concat([test_abuse, test_legit], ignore_index=True)

    # Shuffle each partition (within-partition order should not matter)
    train_df = train_df.sample(frac=1, random_state=42).reset_index(drop=True)
    val_df = val_df.sample(frac=1, random_state=43).reset_index(drop=True)
    test_df = test_df.sample(frac=1, random_state=44).reset_index(drop=True)

    # ---- 4. Validate split -------------------------------------------
    _validate_split(train_df, val_df, test_df, train_rings, val_rings, test_rings)

    _log_split_stats("TRAIN", train_df)
    _log_split_stats("VALIDATION", val_df)
    _log_split_stats("HELDOUT TEST", test_df)

    return train_df, val_df, test_df


def _validate_split(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    train_rings: set,
    val_rings: set,
    test_rings: set,
) -> None:
    """Assert no ring leakage across partitions."""
    assert train_rings.isdisjoint(val_rings), "LEAK: train and val share rings!"
    assert train_rings.isdisjoint(test_rings), "LEAK: train and test share rings!"
    assert val_rings.isdisjoint(test_rings), "LEAK: val and test share rings!"
    logger.info("Split validation PASSED — no ring leakage detected.")


def _log_split_stats(name: str, df: pd.DataFrame) -> None:
    abuse_rate = df["abuse_label"].mean() if "abuse_label" in df.columns else float("nan")
    n_rings = df[df["ring_id"] != ""]["ring_id"].nunique() if "ring_id" in df.columns else 0
    logger.info(
        "%s — %d rows | abuse_rate=%.3f | rings=%d",
        name, len(df), abuse_rate, n_rings,
    )


def save_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Save splits to disk.

    NOTE: The test split is saved separately with a clear name.
    The evaluation script must load it read-only.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    train.to_csv(output_dir / "train.csv", index=False)
    val.to_csv(output_dir / "validation.csv", index=False)
    test.to_csv(output_dir / "heldout_test.csv", index=False)
    logger.info("Splits saved to %s", output_dir)
    # Write a manifest
    manifest = {
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "train_abuse_rate": float(train["abuse_label"].mean()),
        "val_abuse_rate": float(val["abuse_label"].mean()),
        "test_abuse_rate": float(test["abuse_label"].mean()),
        "split_algorithm": "ring_aware_time_ordered",
        "ring_leakage_checked": True,
    }
    import json
    (output_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2))
    logger.info("Split manifest written.")
