"""
RiskOrbit — Entity Generators
Produces customer, merchant, device, IP, and instrument records.
All data is synthetic. No real credentials or PII.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_id(prefix: str, rng: np.random.Generator, size: int, start: int = 0) -> list[str]:
    """Generate guaranteed-unique synthetic IDs using sequential counters."""
    return [f"{prefix}_{start + i:08d}" for i in range(size)]


def _date_range_uniform(
    start: datetime,
    end: datetime,
    size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample `size` timestamps uniformly between start and end."""
    total_seconds = int((end - start).total_seconds())
    offsets = rng.integers(0, total_seconds, size=size)
    return np.array([start + timedelta(seconds=int(s)) for s in offsets])


# ---------------------------------------------------------------------------
# Customer generator
# ---------------------------------------------------------------------------

def generate_customers(
    n: int,
    segments: list[dict],
    start_date: datetime,
    end_date: datetime,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic customer records.

    Args:
        n: number of customers
        segments: list of segment dicts from config
        start_date / end_date: ecosystem time window
        rng: seeded numpy RNG

    Returns:
        DataFrame with customer_id as index column.
    """
    # Assign segments via weighted sampling
    seg_names = [s["name"] for s in segments]
    seg_weights = np.array([s["weight"] for s in segments], dtype=float)
    seg_weights /= seg_weights.sum()
    seg_idx = rng.choice(len(segments), size=n, p=seg_weights)

    # Account creation dates — uniformly spread over the window
    created_at = _date_range_uniform(start_date, end_date - timedelta(days=30), n, rng)

    # Account age in days relative to end_date
    account_age_days = [(end_date - c).days for c in created_at]

    regions = ["north", "south", "east", "west", "central"]
    region_weights = [0.20, 0.25, 0.20, 0.20, 0.15]
    home_region = rng.choice(regions, size=n, p=region_weights)

    # Normal device/merchant counts — not correlated with abuse
    normal_device_count = np.clip(rng.poisson(lam=1.8, size=n), 1, 6).astype(int)
    normal_merchant_count = np.clip(rng.poisson(lam=3.5, size=n), 1, 20).astype(int)

    df = pd.DataFrame(
        {
            "customer_id": _synthetic_id("CUS", rng, n),
            "account_created_at": created_at,
            "account_age_days": account_age_days,
            "home_region": home_region,
            "customer_segment": [seg_names[i] for i in seg_idx],
            "normal_device_count": normal_device_count,
            "normal_merchant_count": normal_merchant_count,
        }
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Merchant generator
# ---------------------------------------------------------------------------

def generate_merchants(
    n: int,
    categories: list[dict],
    start_date: datetime,
    end_date: datetime,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic merchant records.

    Returns:
        DataFrame with merchant_id as identifier.
    """
    cat_names = [c["name"] for c in categories]
    cat_weights = np.array([c["weight"] for c in categories], dtype=float)
    cat_weights /= cat_weights.sum()
    cat_idx = rng.choice(len(categories), size=n, p=cat_weights)

    regions = ["north", "south", "east", "west", "central", "metro"]
    merchant_region = rng.choice(regions, size=n)

    # Baseline refund rate from category + noise
    baseline_refund_rate = np.array(
        [categories[i]["refund_rate"] for i in cat_idx]
    ) + rng.normal(0, 0.02, size=n)
    baseline_refund_rate = np.clip(baseline_refund_rate, 0.01, 0.60)

    avg_order_value_multiplier = np.array(
        [categories[i]["avg_order_value_multiplier"] for i in cat_idx]
    )
    # baseline txn volume per month
    baseline_volume = np.clip(
        rng.lognormal(mean=4.0, sigma=1.2, size=n), 5, 5000
    ).astype(int)

    df = pd.DataFrame(
        {
            "merchant_id": _synthetic_id("MER", rng, n),
            "merchant_category": [cat_names[i] for i in cat_idx],
            "merchant_region": merchant_region,
            "baseline_transaction_volume": baseline_volume,
            "baseline_refund_rate": baseline_refund_rate.round(4),
            "average_order_value": (
                avg_order_value_multiplier * rng.lognormal(6.5, 0.4, size=n)
            ).round(2),
        }
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Device generator
# ---------------------------------------------------------------------------

def generate_devices(
    n: int,
    start_date: datetime,
    end_date: datetime,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic device fingerprint records.
    device_id is a synthetic hash-like identifier — not a real fingerprint.
    """
    device_types = ["mobile_android", "mobile_ios", "desktop_windows",
                    "desktop_mac", "tablet_android", "tablet_ios"]
    type_weights = [0.35, 0.25, 0.20, 0.10, 0.07, 0.03]

    first_seen = _date_range_uniform(start_date, end_date - timedelta(days=1), n, rng)
    device_age_days = [(end_date - f).days for f in first_seen]

    df = pd.DataFrame(
        {
            "device_id": _synthetic_id("DEV", rng, n),
            "first_seen_at": first_seen,
            "device_type": rng.choice(device_types, size=n, p=type_weights),
            "device_age_days": device_age_days,
        }
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# IP entity generator
# ---------------------------------------------------------------------------

def generate_ip_entities(
    n: int,
    start_date: datetime,
    end_date: datetime,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create anonymized IP entity records.
    IMPORTANT: No actual IP addresses are stored — only synthetic entity IDs.
    ip_type encodes residential, corporate, mobile, etc.
    """
    ip_types = ["residential", "corporate", "mobile_carrier",
                "shared_broadband", "vpn_proxy", "datacenter"]
    ip_type_weights = [0.45, 0.20, 0.20, 0.08, 0.04, 0.03]

    regions = ["north", "south", "east", "west", "central", "international"]
    region_weights = [0.20, 0.22, 0.18, 0.20, 0.15, 0.05]

    first_seen = _date_range_uniform(start_date, end_date - timedelta(days=1), n, rng)

    df = pd.DataFrame(
        {
            "ip_id": _synthetic_id("IP", rng, n),
            "region": rng.choice(regions, size=n, p=region_weights),
            "ip_type": rng.choice(ip_types, size=n, p=ip_type_weights),
            "first_seen_at": first_seen,
        }
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Payment instrument generator
# ---------------------------------------------------------------------------

def generate_instruments(
    n: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic payment instrument fingerprints.
    CRITICAL: No real card numbers, CVVs, bank credentials, OTPs, or
    any sensitive payment secrets are generated here.
    instrument_id is a random synthetic token only.
    """
    instrument_types = ["upi", "credit_card", "debit_card",
                        "net_banking", "wallet", "bnpl"]
    type_weights = [0.38, 0.22, 0.20, 0.08, 0.08, 0.04]

    synthetic_age = np.clip(rng.exponential(scale=365, size=n), 1, 3650).astype(int)

    df = pd.DataFrame(
        {
            "instrument_id": _synthetic_id("INS", rng, n),
            "instrument_type": rng.choice(instrument_types, size=n, p=type_weights),
            "synthetic_age": synthetic_age,      # days since first use, synthetic
        }
    )
    return df.reset_index(drop=True)
