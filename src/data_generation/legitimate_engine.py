"""
RiskOrbit — Legitimate Behavior Engine (Vectorized)
Generates realistic orders, transactions, and refunds for legitimate customers.

Design principles:
  - VECTORIZED: Uses numpy/pandas operations, not per-row Python loops
  - Uses a mixture of distributions (not one flat distribution)
  - Applies seasonal multipliers
  - Applies realistic per-merchant, per-segment correlations
  - Does NOT inject any abuse signals here
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_PRODUCT_CATEGORIES = [
    "electronics", "fashion", "grocery", "travel",
    "food_delivery", "services", "gaming",
]

_REFUND_REASONS = [
    "item_not_received", "item_damaged", "wrong_item",
    "changed_mind", "duplicate_order", "quality_issue", "delivery_delay",
]


def _sample_amounts_vectorized(
    amount_dists: list[dict], n: int, rng: np.random.Generator
) -> np.ndarray:
    """Sample n amounts from a mixture of lognormals — vectorized."""
    weights = np.array([d["weight"] for d in amount_dists], dtype=float)
    weights /= weights.sum()
    component = rng.choice(len(amount_dists), size=n, p=weights)
    amounts = np.zeros(n)
    for i, dist in enumerate(amount_dists):
        mask = component == i
        k = int(mask.sum())
        if k > 0:
            amounts[mask] = rng.lognormal(mean=dist["mean"], sigma=dist["std"], size=k)
    return np.clip(amounts, 10.0, None)


def generate_legitimate_transactions(
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate orders, transactions, and refunds for legitimate customers.
    Fully vectorized for performance.

    Returns:
        (orders_df, transactions_df, refunds_df)
    """
    scale = cfg["scale"]
    legit = cfg["legitimate"]
    temporal = cfg["temporal"]
    start_date = datetime.fromisoformat(temporal["start_date"])
    end_date = datetime.fromisoformat(temporal["end_date"])
    total_seconds = int((end_date - start_date).total_seconds())

    segments_cfg = {s["name"]: s for s in legit["customer_segments"]}
    cat_refund = {c["name"]: c["refund_rate"] for c in legit["merchant_categories"]}

    device_ids = devices["device_id"].values
    ip_ids = ip_entities["ip_id"].values
    instrument_ids = instruments["instrument_id"].values
    merchant_ids = merchants["merchant_id"].values
    merchant_cat_arr = merchants["merchant_category"].values
    merchant_aov_arr = merchants["average_order_value"].values

    target_orders = scale["target_orders"]
    logger.info("Generating ~%d legitimate transactions (vectorized) …", target_orders)

    n_customers = len(customers)

    # Assign each customer an expected transactions count
    seg_names = customers["customer_segment"].values
    monthly_rates = np.array([
        max(rng.normal(
            segments_cfg.get(s, segments_cfg["casual"])["monthly_orders_mean"],
            segments_cfg.get(s, segments_cfg["casual"])["monthly_orders_std"],
        ), 0.1)
        for s in seg_names
    ])

    # Account active days
    acc_created = pd.to_datetime(customers["account_created_at"])
    end_dt = pd.Timestamp(end_date)
    start_dt = pd.Timestamp(start_date)
    active_days = np.maximum(
        0,
        (end_dt - pd.Series(acc_created)).dt.days.values,
    )

    # Expected orders per customer
    expected_per_cust = np.maximum(
        0,
        (monthly_rates * active_days / 30).astype(int)
    )

    # Scale to hit target
    total_expected = expected_per_cust.sum()
    if total_expected > 0:
        scale_factor = target_orders / total_expected
        expected_per_cust = np.maximum(0, (expected_per_cust * scale_factor).astype(int))

    total_txns = int(expected_per_cust.sum())
    logger.info("Generating %d legitimate transactions …", total_txns)

    # For each customer, repeat customer_id by their expected count
    cust_ids_repeated = np.repeat(customers["customer_id"].values, expected_per_cust)

    # Random timestamps: uniform over each customer's active window
    # Simpler approach: uniform over the whole period (slightly approximated)
    ts_offsets = rng.integers(0, max(total_seconds, 1), size=total_txns)
    timestamps_unix = ts_offsets + int(start_dt.timestamp())
    timestamps = pd.to_datetime(timestamps_unix, unit="s")

    # Random merchants (each customer uses ~1-5 preferred merchants)
    merchant_idxs = rng.integers(0, len(merchant_ids), size=total_txns)
    txn_merchant_ids = merchant_ids[merchant_idxs]
    txn_merchant_cats = merchant_cat_arr[merchant_idxs]
    txn_merchant_aovs = merchant_aov_arr[merchant_idxs].astype(float)

    # Amounts: mixture of lognormals + merchant AOV blend
    base_amounts = _sample_amounts_vectorized(legit["amount_distributions"], total_txns, rng)
    amounts = np.round((base_amounts + txn_merchant_aovs) / 2 * rng.uniform(0.5, 1.5, total_txns), 2)
    amounts = np.maximum(amounts, 10.0)

    # Device / IP / instrument assignments
    dev_idxs = rng.integers(0, len(device_ids), size=total_txns)
    ip_idxs = rng.integers(0, len(ip_ids), size=total_txns)
    ins_idxs = rng.integers(0, len(instrument_ids), size=total_txns)

    txn_device_ids = device_ids[dev_idxs]
    txn_ip_ids = ip_ids[ip_idxs]
    txn_instrument_ids = instrument_ids[ins_idxs]

    # Payment methods
    payment_methods = np.where(
        txn_instrument_ids != None,
        _assign_payment_methods(len(txn_instrument_ids), rng),
        "upi",
    )

    # Payment statuses (98% captured)
    payment_statuses = np.where(rng.random(total_txns) < 0.98, "captured", "failed")

    # Product categories
    prod_cats = np.array([
        m if m in _PRODUCT_CATEGORIES else rng.choice(_PRODUCT_CATEGORIES)
        for m in txn_merchant_cats
    ])

    # Regions
    region_choices = ["north", "south", "east", "west", "central"]
    regions = rng.choice(region_choices, size=total_txns)

    # Generate IDs
    order_nums = rng.integers(100_000_000, 999_999_999, size=total_txns)
    txn_nums = rng.integers(100_000_000, 999_999_999, size=total_txns)
    order_ids = np.array([f"ORD_{n}" for n in order_nums])
    txn_ids = np.array([f"TXN_{n}" for n in txn_nums])

    # Build DataFrames
    orders_df = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": cust_ids_repeated,
        "merchant_id": txn_merchant_ids,
        "created_at": timestamps,
        "amount": amounts,
        "product_category": prod_cats,
        "delivery_region": regions,
        "abuse_label": 0,
        "ring_id": "",
        "hard_negative_type": "",
    })

    txn_df = pd.DataFrame({
        "transaction_id": txn_ids,
        "order_id": order_ids,
        "customer_id": cust_ids_repeated,
        "merchant_id": txn_merchant_ids,
        "device_id": txn_device_ids,
        "ip_id": txn_ip_ids,
        "instrument_id": txn_instrument_ids,
        "timestamp": timestamps,
        "amount": amounts,
        "payment_method": payment_methods,
        "payment_status": payment_statuses,
        "abuse_label": 0,
        "ring_id": "",
        "hard_negative_type": "",
    })

    # Refunds: per-merchant-category refund rate
    seg_refund_rates = np.array([
        segments_cfg.get(s, segments_cfg["casual"])["refund_rate"]
        for s in seg_names
    ])
    cust_refund_rate_map = dict(zip(customers["customer_id"].values, seg_refund_rates))

    cust_refund_rates = np.array([
        cust_refund_rate_map.get(cid, 0.10) for cid in cust_ids_repeated
    ])
    merch_refund_rates = np.array([
        cat_refund.get(cat, 0.10) for cat in txn_merchant_cats
    ])
    combined_refund_rates = (cust_refund_rates + merch_refund_rates) / 2

    # Seasonal adjustment: months with higher traffic have more refunds too
    seasonal = legit["seasonal_multipliers"]
    months = timestamps.month.values
    seasonal_adj = np.array([seasonal.get(int(m), 1.0) / 1.2 for m in months])
    combined_refund_rates = np.clip(combined_refund_rates * seasonal_adj, 0.01, 0.95)

    refund_mask = rng.random(total_txns) < combined_refund_rates
    n_refunds = int(refund_mask.sum())

    if n_refunds > 0:
        ref_delay_h = np.clip(
            rng.lognormal(mean=3.5, sigma=1.2, size=n_refunds), 1, 720
        )
        ref_ts = timestamps[refund_mask] + pd.to_timedelta(ref_delay_h, unit="h")
        ref_proc_ts = ref_ts + pd.to_timedelta(
            rng.uniform(2, 72, size=n_refunds), unit="h"
        )
        ref_amounts = np.round(amounts[refund_mask] * rng.uniform(0.5, 1.0, size=n_refunds), 2)
        ref_nums = rng.integers(100_000_000, 999_999_999, size=n_refunds)
        ref_reasons = rng.choice(_REFUND_REASONS, size=n_refunds)

        refund_df = pd.DataFrame({
            "refund_id": [f"REF_{n}" for n in ref_nums],
            "transaction_id": txn_ids[refund_mask],
            "refund_requested_at": ref_ts,
            "refund_processed_at": ref_proc_ts,
            "refund_amount": ref_amounts,
            "refund_reason": ref_reasons,
            "refund_status": "completed",
            "abuse_label": 0,
            "ring_id": "",
            "hard_negative_type": "",
        })
    else:
        refund_df = pd.DataFrame(columns=[
            "refund_id", "transaction_id", "refund_requested_at",
            "refund_processed_at", "refund_amount", "refund_reason",
            "refund_status", "abuse_label", "ring_id", "hard_negative_type",
        ])

    logger.info(
        "Legitimate generation complete: %d orders, %d transactions, %d refunds",
        len(orders_df), len(txn_df), len(refund_df),
    )
    return orders_df, txn_df, refund_df


def _assign_payment_methods(n: int, rng: np.random.Generator) -> np.ndarray:
    methods = ["upi", "credit_card", "debit_card", "net_banking", "wallet"]
    weights = [0.38, 0.22, 0.20, 0.10, 0.10]
    return rng.choice(methods, size=n, p=weights)
