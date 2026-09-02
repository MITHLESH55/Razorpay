"""
RiskOrbit — Ground Truth Assembly
Assembles final labeled datasets ensuring no metadata leakage.

CRITICAL INVARIANT:
  The following columns exist ONLY in generation_metadata.parquet and
  are NEVER merged into the feature matrix or model training data:
    - ring_id (used for split, not as feature)
    - hard_negative_type
    - abuse_pattern_type
    - generation_seed
    - ring_base_timestamp
    - shared_devices
    - ring_merchants
    - linking_ip
    - linking_instrument
    - ring_customer_ids
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _make_unique_txn_ids(transactions: pd.DataFrame) -> pd.DataFrame:
    """Replace transaction_id with guaranteed-unique hash-based IDs."""
    txn = transactions.copy()
    # Hash of (original_id + row_index) guarantees uniqueness even on collision
    txn["transaction_id"] = [
        f"TXN_{hashlib.sha1(f'{row.transaction_id}_{i}'.encode()).hexdigest()[:10]}"
        for i, row in enumerate(txn.itertuples())
    ]
    return txn


def assemble_ground_truth(
    orders: pd.DataFrame,
    transactions: pd.DataFrame,
    refunds: pd.DataFrame,
    abuse_metadata: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Assemble final datasets with ground-truth labels.

    Returns:
        orders_gt, transactions_gt, refunds_gt, abuse_metadata_df

    The abuse_label column IS available in the datasets for evaluation.
    The ring_id column is kept for split logic but is NOT a model feature.
    The hard_negative_type column is kept for analysis but NOT a model feature.
    """
    # Ensure consistent dtypes
    for df in [orders, transactions, refunds]:
        df["abuse_label"] = df["abuse_label"].fillna(0).astype(int)
        df["ring_id"] = df["ring_id"].fillna("").astype(str)
        df["hard_negative_type"] = df["hard_negative_type"].fillna("").astype(str)

    # Sort by timestamp before dedup (keep first occurrence — typically the real one)
    if "timestamp" in transactions.columns:
        transactions["timestamp"] = pd.to_datetime(transactions["timestamp"], format="mixed", errors="coerce")
        transactions = transactions.sort_values("timestamp")
    if "created_at" in orders.columns:
        orders["created_at"] = pd.to_datetime(orders["created_at"], format="mixed", errors="coerce")
        orders = orders.sort_values("created_at")

    # Dedup on primary keys (keep first)
    transactions = transactions.drop_duplicates(subset=["transaction_id"], keep="first").reset_index(drop=True)
    orders = orders.drop_duplicates(subset=["order_id"], keep="first").reset_index(drop=True)
    refunds = refunds.drop_duplicates(subset=["refund_id"], keep="first").reset_index(drop=True)

    # Reassign transaction IDs using hash to ensure uniqueness within the final set
    # Build old_id → new_id mapping so refunds can be updated
    old_txn_ids = transactions["transaction_id"].tolist()
    new_txn_ids = [
        f"TXN_{hashlib.sha1(f'{tid}_{i}'.encode()).hexdigest()[:10]}"
        for i, tid in enumerate(old_txn_ids)
    ]
    txn_id_map = dict(zip(old_txn_ids, new_txn_ids))
    transactions["transaction_id"] = new_txn_ids

    # Reassign order IDs and update transaction references
    old_order_ids = orders["order_id"].tolist()
    new_order_ids = [f"ORD_{i:08d}" for i in range(len(orders))]
    order_id_map = dict(zip(old_order_ids, new_order_ids))
    orders["order_id"] = new_order_ids
    if "order_id" in transactions.columns:
        transactions["order_id"] = transactions["order_id"].map(order_id_map).fillna("")

    # Update refunds to reference new transaction IDs
    if len(refunds) > 0 and "transaction_id" in refunds.columns:
        refunds["transaction_id"] = refunds["transaction_id"].map(txn_id_map)
        # Drop refunds whose parent transaction was deduped out
        refunds = refunds[refunds["transaction_id"].notna()].reset_index(drop=True)

    # Parse refund timestamps
    if len(refunds) > 0:
        for col in ["refund_requested_at", "refund_processed_at"]:
            if col in refunds.columns:
                refunds[col] = pd.to_datetime(refunds[col], format="mixed", errors="coerce")

    # Fix temporal consistency: drop any refunds where requested_at < transaction timestamp
    if len(refunds) > 0 and "refund_requested_at" in refunds.columns:
        txn_ts = transactions.set_index("transaction_id")["timestamp"].to_dict()
        refunds["_txn_ts"] = refunds["transaction_id"].map(txn_ts)
        bad_timing = refunds["_txn_ts"].notna() & (refunds["refund_requested_at"] < refunds["_txn_ts"])
        n_bad = int(bad_timing.sum())
        if n_bad > 0:
            logger.warning("Dropping %d refunds with refund_requested_at < transaction timestamp", n_bad)
            refunds = refunds[~bad_timing].reset_index(drop=True)
        refunds.drop(columns=["_txn_ts"], inplace=True)

    refunds["refund_id"] = [f"REF_{i:08d}" for i in range(len(refunds))]

    abuse_metadata_df = pd.DataFrame(abuse_metadata)

    logger.info(
        "Ground truth assembled: %d orders | %d transactions | %d refunds | %d rings",
        len(orders), len(transactions), len(refunds), len(abuse_metadata_df),
    )
    logger.info(
        "Abuse prevalence in transactions: %.2f%%",
        100 * transactions["abuse_label"].mean(),
    )

    return orders, transactions, refunds, abuse_metadata_df


def save_raw_data(
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    orders: pd.DataFrame,
    transactions: pd.DataFrame,
    refunds: pd.DataFrame,
    abuse_metadata: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Persist all raw entity and event tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    customers.to_csv(output_dir / "customers.csv", index=False)
    merchants.to_csv(output_dir / "merchants.csv", index=False)
    devices.to_csv(output_dir / "devices.csv", index=False)
    ip_entities.to_csv(output_dir / "ip_entities.csv", index=False)
    instruments.to_csv(output_dir / "instruments.csv", index=False)
    orders.to_csv(output_dir / "orders.csv", index=False)
    transactions.to_csv(output_dir / "transactions.csv", index=False)
    refunds.to_csv(output_dir / "refunds.csv", index=False)
    # abuse_metadata goes to a separate folder — never accidentally merged
    meta_dir = output_dir / "generation_metadata"
    meta_dir.mkdir(exist_ok=True)
    abuse_metadata.to_csv(meta_dir / "abuse_rings.csv", index=False)
    logger.info("Raw data saved to %s", output_dir)
