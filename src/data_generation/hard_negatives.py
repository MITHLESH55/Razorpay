"""
RiskOrbit — Hard Negative Injection
Explicitly creates legitimate records that superficially resemble abuse.

Each hard negative type is tracked with an internal `hard_negative_type` label.
CRITICAL: This label is NEVER exposed to the model — it is for analysis only.

Types:
  1. household_sharing      — several legit customers share one device
  2. shared_network         — many legit users share one IP entity
  3. high_refund_customer   — legitimate serial returner
  4. high_volume_merchant   — legitimate merchant with large refund volume
  5. seasonal_spike         — burst during holiday season
  6. new_customer_high_value— legit new customer makes expensive purchase
  7. multi_device_customer  — legit customer uses many devices legitimately
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers shared with legitimate engine
# ---------------------------------------------------------------------------

def _refund_reason(rng: np.random.Generator) -> str:
    reasons = [
        "item_not_received", "item_damaged", "wrong_item",
        "changed_mind", "duplicate_order", "quality_issue", "delivery_delay",
    ]
    return rng.choice(reasons)


def _payment_method(rng: np.random.Generator) -> str:
    return rng.choice(
        ["upi", "credit_card", "debit_card", "net_banking", "wallet"],
        p=[0.38, 0.22, 0.20, 0.10, 0.10],
    )


def _payment_status(rng: np.random.Generator) -> str:
    return rng.choice(["captured", "failed"], p=[0.98, 0.02])


# ---------------------------------------------------------------------------
# 1. Household sharing
# ---------------------------------------------------------------------------

def inject_household_sharing(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Several legitimate customers share a physical device.
    This creates high accounts_per_device but is NOT abuse.
    """
    hn_cfg = cfg["hard_negatives"]["household_sharing"]
    n_households = hn_cfg["n_households"]
    mean_accts = hn_cfg["accounts_per_household_mean"]
    max_accts = hn_cfg["accounts_per_household_max"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    device_ids = devices["device_id"].values
    merchant_ids = merchants["merchant_id"].values
    instrument_ids = instruments["instrument_id"].values
    cust_ids = customers["customer_id"].values

    # Pick random devices to be shared
    shared_device_ids = rng.choice(device_ids, size=min(n_households, len(device_ids)), replace=False)

    for dev_id in shared_device_ids:
        n_accts = int(np.clip(rng.poisson(mean_accts), 2, max_accts))
        cust_subset = rng.choice(cust_ids, size=min(n_accts, len(cust_ids)), replace=False)
        for cid in cust_subset:
            # Each customer does 3–10 transactions on this shared device
            n_txns = int(rng.integers(3, 11))
            for _ in range(n_txns):
                ts = start + timedelta(seconds=int(rng.integers(0, int((end - start).total_seconds()))))
                amount = round(rng.lognormal(6.5, 0.8), 2)
                oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
                tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"
                m_id = rng.choice(merchant_ids)
                ins_id = rng.choice(instrument_ids)

                orders.append({
                    "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                    "created_at": ts, "amount": amount,
                    "product_category": rng.choice(["electronics", "fashion", "grocery"]),
                    "delivery_region": "north",
                    "abuse_label": 0, "ring_id": None, "hard_negative_type": "household_sharing",
                })
                transactions.append({
                    "transaction_id": tid, "order_id": oid, "customer_id": cid,
                    "merchant_id": m_id, "device_id": dev_id, "ip_id": None,
                    "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                    "payment_method": _payment_method(rng),
                    "payment_status": _payment_status(rng),
                    "abuse_label": 0, "ring_id": None, "hard_negative_type": "household_sharing",
                })
                # ~20% refund rate for household sharing users — legitimately high
                if rng.random() < 0.20:
                    delay_h = float(rng.uniform(2, 72))
                    refund_ts = ts + timedelta(hours=delay_h)
                    if refund_ts < end:
                        refunds.append({
                            "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                            "transaction_id": tid,
                            "refund_requested_at": refund_ts,
                            "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 48)),
                            "refund_amount": round(amount * rng.uniform(0.7, 1.0), 2),
                            "refund_reason": _refund_reason(rng),
                            "refund_status": "completed",
                            "abuse_label": 0, "ring_id": None, "hard_negative_type": "household_sharing",
                        })


# ---------------------------------------------------------------------------
# 2. Shared network
# ---------------------------------------------------------------------------

def inject_shared_network(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Many legitimate users share one IP entity (e.g., office, university).
    Creates high accounts_per_ip but is NOT abuse.
    """
    hn_cfg = cfg["hard_negatives"]["shared_network"]
    n_networks = hn_cfg["n_networks"]
    mean_accts = hn_cfg["accounts_per_network_mean"]
    max_accts = hn_cfg["accounts_per_network_max"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    ip_ids = ip_entities["ip_id"].values
    merchant_ids = merchants["merchant_id"].values
    device_ids_all = []  # will use random devices
    cust_ids = customers["customer_id"].values
    instrument_ids = instruments["instrument_id"].values

    shared_ip_ids = rng.choice(ip_ids, size=min(n_networks, len(ip_ids)), replace=False)
    for ip_id in shared_ip_ids:
        n_accts = int(np.clip(rng.poisson(mean_accts), 5, max_accts))
        cust_subset = rng.choice(cust_ids, size=min(n_accts, len(cust_ids)), replace=False)
        for cid in cust_subset:
            n_txns = int(rng.integers(2, 8))
            for _ in range(n_txns):
                ts = start + timedelta(seconds=int(rng.integers(0, int((end - start).total_seconds()))))
                amount = round(rng.lognormal(6.0, 0.9), 2)
                oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
                tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"
                m_id = rng.choice(merchant_ids)
                ins_id = rng.choice(instrument_ids)

                orders.append({
                    "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                    "created_at": ts, "amount": amount,
                    "product_category": rng.choice(["fashion", "food_delivery", "services"]),
                    "delivery_region": "west",
                    "abuse_label": 0, "ring_id": None, "hard_negative_type": "shared_network",
                })
                transactions.append({
                    "transaction_id": tid, "order_id": oid, "customer_id": cid,
                    "merchant_id": m_id, "device_id": None, "ip_id": ip_id,
                    "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                    "payment_method": _payment_method(rng),
                    "payment_status": _payment_status(rng),
                    "abuse_label": 0, "ring_id": None, "hard_negative_type": "shared_network",
                })


# ---------------------------------------------------------------------------
# 3. High-refund legitimate customer
# ---------------------------------------------------------------------------

def inject_high_refund_customers(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Some legitimate customers have genuinely high refund rates (serial returners).
    High refund_rate alone should NOT be sufficient for flagging.
    """
    hn_cfg = cfg["hard_negatives"]["high_refund_customer"]
    n_customers = hn_cfg["n_customers"]
    rate_min = hn_cfg["refund_rate_min"]
    rate_max = hn_cfg["refund_rate_max"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    cust_ids = customers["customer_id"].values
    merchant_ids = merchants["merchant_id"].values
    device_ids = devices["device_id"].values
    instrument_ids = instruments["instrument_id"].values

    chosen_custs = rng.choice(cust_ids, size=min(n_customers, len(cust_ids)), replace=False)
    for cid in chosen_custs:
        refund_rate = rng.uniform(rate_min, rate_max)
        n_txns = int(rng.integers(10, 30))
        dev_id = rng.choice(device_ids)
        ins_id = rng.choice(instrument_ids)
        m_id = rng.choice(merchant_ids)

        for _ in range(n_txns):
            ts = start + timedelta(seconds=int(rng.integers(0, int((end - start).total_seconds()))))
            amount = round(rng.lognormal(6.5, 0.6), 2)
            oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
            tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"

            orders.append({
                "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                "created_at": ts, "amount": amount,
                "product_category": rng.choice(["fashion", "electronics"]),
                "delivery_region": "south",
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_refund_customer",
            })
            transactions.append({
                "transaction_id": tid, "order_id": oid, "customer_id": cid,
                "merchant_id": m_id, "device_id": dev_id, "ip_id": None,
                "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                "payment_method": _payment_method(rng),
                "payment_status": "captured",
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_refund_customer",
            })
            if rng.random() < refund_rate:
                delay_h = float(rng.uniform(6, 120))
                refund_ts = ts + timedelta(hours=delay_h)
                if refund_ts < end:
                    refunds.append({
                        "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                        "transaction_id": tid,
                        "refund_requested_at": refund_ts,
                        "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 72)),
                        "refund_amount": round(amount * rng.uniform(0.8, 1.0), 2),
                        "refund_reason": _refund_reason(rng),
                        "refund_status": "completed",
                        "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_refund_customer",
                    })


# ---------------------------------------------------------------------------
# 4. High-volume merchant
# ---------------------------------------------------------------------------

def inject_high_volume_merchants(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Some legitimate merchants have high absolute refund volumes.
    High merchant_refund_rate or refund_volume alone is NOT abuse.
    """
    hn_cfg = cfg["hard_negatives"]["high_volume_merchant"]
    n_merchants = hn_cfg["n_merchants"]
    vol_min = hn_cfg["volume_multiplier_min"]
    vol_max = hn_cfg["volume_multiplier_max"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    merchant_ids = merchants["merchant_id"].values
    cust_ids = customers["customer_id"].values
    device_ids = devices["device_id"].values
    instrument_ids = instruments["instrument_id"].values

    chosen_merchants = rng.choice(merchant_ids, size=min(n_merchants, len(merchant_ids)), replace=False)
    for m_id in chosen_merchants:
        multiplier = rng.uniform(vol_min, vol_max)
        n_txns = int(300 * multiplier)
        for _ in range(n_txns):
            cid = rng.choice(cust_ids)
            ts = start + timedelta(seconds=int(rng.integers(0, int((end - start).total_seconds()))))
            amount = round(rng.lognormal(6.0, 0.8), 2)
            oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
            tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"
            dev_id = rng.choice(device_ids)
            ins_id = rng.choice(instrument_ids)

            orders.append({
                "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                "created_at": ts, "amount": amount,
                "product_category": "fashion",
                "delivery_region": rng.choice(["north", "south", "east", "west"]),
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_volume_merchant",
            })
            transactions.append({
                "transaction_id": tid, "order_id": oid, "customer_id": cid,
                "merchant_id": m_id, "device_id": dev_id, "ip_id": None,
                "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                "payment_method": _payment_method(rng),
                "payment_status": _payment_status(rng),
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_volume_merchant",
            })
            if rng.random() < 0.25:  # legitimate high-refund merchant
                delay_h = float(rng.uniform(4, 96))
                refund_ts = ts + timedelta(hours=delay_h)
                if refund_ts < end:
                    refunds.append({
                        "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                        "transaction_id": tid,
                        "refund_requested_at": refund_ts,
                        "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 48)),
                        "refund_amount": round(amount * rng.uniform(0.6, 1.0), 2),
                        "refund_reason": _refund_reason(rng),
                        "refund_status": "completed",
                        "abuse_label": 0, "ring_id": None, "hard_negative_type": "high_volume_merchant",
                    })


# ---------------------------------------------------------------------------
# 5. New customer high-value purchase
# ---------------------------------------------------------------------------

def inject_new_customer_high_value(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Legitimate new customers making expensive purchases.
    New account + high value should NOT alone be abuse.
    """
    hn_cfg = cfg["hard_negatives"]["new_customer_high_value"]
    n_customers = hn_cfg["n_customers"]
    max_age = hn_cfg["max_account_age_days"]
    min_amount = hn_cfg["min_amount"]

    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    merchant_ids = merchants["merchant_id"].values
    device_ids = devices["device_id"].values
    instrument_ids = instruments["instrument_id"].values

    # Select customers with young accounts
    young_custs = customers[customers["account_age_days"] <= max_age]
    if len(young_custs) == 0:
        return
    chosen = young_custs.sample(min(n_customers, len(young_custs)), random_state=int(rng.integers(0, 10000)))

    for _, cust in chosen.iterrows():
        ts = cust["account_created_at"] + timedelta(days=float(rng.uniform(0, min(max_age, 10))))
        if ts >= end:
            continue
        amount = round(float(min_amount) + rng.lognormal(7.5, 0.5), 2)
        oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
        tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"
        m_id = rng.choice(merchant_ids)
        dev_id = rng.choice(device_ids)
        ins_id = rng.choice(instrument_ids)

        orders.append({
            "order_id": oid, "customer_id": cust["customer_id"], "merchant_id": m_id,
            "created_at": ts, "amount": amount,
            "product_category": rng.choice(["electronics", "travel"]),
            "delivery_region": cust["home_region"],
            "abuse_label": 0, "ring_id": None, "hard_negative_type": "new_customer_high_value",
        })
        transactions.append({
            "transaction_id": tid, "order_id": oid, "customer_id": cust["customer_id"],
            "merchant_id": m_id, "device_id": dev_id, "ip_id": None,
            "instrument_id": ins_id, "timestamp": ts, "amount": amount,
            "payment_method": _payment_method(rng),
            "payment_status": "captured",
            "abuse_label": 0, "ring_id": None, "hard_negative_type": "new_customer_high_value",
        })


# ---------------------------------------------------------------------------
# 6. Multi-device customer
# ---------------------------------------------------------------------------

def inject_multi_device_customers(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> None:
    """
    Legitimate customers who use many different devices (power users, travelers).
    High device_count alone should NOT trigger abuse detection.
    """
    hn_cfg = cfg["hard_negatives"]["multi_device_customer"]
    n_customers = hn_cfg["n_customers"]
    min_devs = hn_cfg["min_devices"]
    max_devs = hn_cfg["max_devices"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])

    cust_ids = customers["customer_id"].values
    merchant_ids = merchants["merchant_id"].values
    device_ids = devices["device_id"].values
    instrument_ids = instruments["instrument_id"].values

    chosen_custs = rng.choice(cust_ids, size=min(n_customers, len(cust_ids)), replace=False)
    for cid in chosen_custs:
        n_devs = int(rng.integers(min_devs, max_devs + 1))
        cust_devices = rng.choice(device_ids, size=min(n_devs, len(device_ids)), replace=False)
        n_txns = int(rng.integers(5, 20))
        for _ in range(n_txns):
            ts = start + timedelta(seconds=int(rng.integers(0, int((end - start).total_seconds()))))
            amount = round(rng.lognormal(6.5, 0.8), 2)
            oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
            tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"
            m_id = rng.choice(merchant_ids)
            dev_id = rng.choice(cust_devices)
            ins_id = rng.choice(instrument_ids)

            orders.append({
                "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                "created_at": ts, "amount": amount,
                "product_category": rng.choice(["electronics", "travel", "services"]),
                "delivery_region": rng.choice(["north", "south", "east", "west"]),
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "multi_device_customer",
            })
            transactions.append({
                "transaction_id": tid, "order_id": oid, "customer_id": cid,
                "merchant_id": m_id, "device_id": dev_id, "ip_id": None,
                "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                "payment_method": _payment_method(rng),
                "payment_status": _payment_status(rng),
                "abuse_label": 0, "ring_id": None, "hard_negative_type": "multi_device_customer",
            })
