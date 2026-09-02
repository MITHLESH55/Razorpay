"""
RiskOrbit — Abuse Engine
Generates coordinated refund abuse rings in THREE distinct patterns.

SECURITY NOTE: This module exists SOLELY for generating labeled training/evaluation
data for a defensive detection system. It does NOT constitute fraud tooling, attack
guidance, or evasion instructions. The patterns are simplified synthetic simulations.

Each ring gets a unique ring_id and abuse_pattern_type.
Generation metadata is tracked separately and NEVER leaks into model features.

Pattern A — shared-device coordinated refund ring
Pattern B — cross-merchant coordinated refund ring
Pattern C — rotating-account refund ring
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REFUND_REASONS = [
    "item_not_received", "item_damaged", "wrong_item",
    "changed_mind", "duplicate_order", "quality_issue",
]


def _refund_reason(rng: np.random.Generator) -> str:
    return rng.choice(_REFUND_REASONS)


def _payment_method(rng: np.random.Generator) -> str:
    return rng.choice(["upi", "credit_card", "debit_card"], p=[0.50, 0.30, 0.20])


# ---------------------------------------------------------------------------
# Pattern A — Shared-device coordinated refund ring
# ---------------------------------------------------------------------------

def generate_pattern_a_rings(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    abuse_metadata: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> list[str]:
    """
    Multiple accounts share one or more devices, purchase from same merchants,
    and repeatedly request refunds in coordinated timing bursts.

    Crucially, amounts are plausible and not obviously extreme.
    Individual accounts look borderline legitimate in isolation.
    """
    abuse_cfg = cfg["abuse"]
    pa = abuse_cfg["pattern_a"]
    n_rings = abuse_cfg["n_rings_pattern_a"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])
    amount_min = abuse_cfg["amount_min"]
    amount_max = abuse_cfg["amount_max"]

    device_ids = devices["device_id"].values
    merchant_ids = merchants["merchant_id"].values
    ip_ids = ip_entities["ip_id"].values
    instrument_ids = instruments["instrument_id"].values
    cust_ids = customers["customer_id"].values

    ring_ids_created: list[str] = []

    for ring_idx in range(n_rings):
        ring_id = f"RING_A_{ring_idx:04d}"
        ring_ids_created.append(ring_id)

        n_accts = int(rng.integers(pa["accounts_per_ring_min"], pa["accounts_per_ring_max"] + 1))
        n_shared_devs = pa["shared_devices_per_ring"]

        # Pick shared devices
        shared_devs = rng.choice(device_ids, size=n_shared_devs, replace=False)
        # Pick ring accounts
        ring_accounts = rng.choice(cust_ids, size=min(n_accts, len(cust_ids)), replace=False)
        # Ring merchants — same merchant targeted
        ring_merchant = rng.choice(merchant_ids)

        # Timing: ring bursts within a window
        jitter_h = pa["coordination_jitter_hours"]
        burst_start_offset = rng.integers(0, int((end - start).total_seconds()) - 7 * 86400)
        ring_base_ts = start + timedelta(seconds=int(burst_start_offset))

        for cid in ring_accounts:
            n_cycles = int(rng.integers(2, pa["refund_cycles_per_account"] + 1))
            ins_id = rng.choice(instrument_ids)
            # Each account may use the shared device OR its own — mostly shared
            use_shared = rng.random() < 0.75
            dev_id = rng.choice(shared_devs) if use_shared else rng.choice(device_ids)
            ip_id = rng.choice(ip_ids)

            for cycle in range(n_cycles):
                # Cycle spread over coordination window
                cycle_offset = timedelta(hours=float(rng.uniform(0, pa["timing_burst_hours"])))
                ts = ring_base_ts + cycle_offset + timedelta(days=cycle * 7)
                if ts >= end:
                    continue

                amount = round(rng.uniform(amount_min, amount_max), 2)
                oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
                tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"

                orders.append({
                    "order_id": oid, "customer_id": cid, "merchant_id": ring_merchant,
                    "created_at": ts, "amount": amount,
                    "product_category": rng.choice(["electronics", "fashion"]),
                    "delivery_region": rng.choice(["north", "south", "east", "west"]),
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                transactions.append({
                    "transaction_id": tid, "order_id": oid, "customer_id": cid,
                    "merchant_id": ring_merchant, "device_id": dev_id, "ip_id": ip_id,
                    "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                    "payment_method": _payment_method(rng),
                    "payment_status": "captured",
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                # Refund always requested (hallmark of refund abuse)
                delay_h = float(rng.uniform(
                    abuse_cfg["refund_delay_hours_min"],
                    abuse_cfg["refund_delay_hours_max"],
                ))
                refund_ts = ts + timedelta(hours=delay_h)
                if refund_ts < end:
                    refunds.append({
                        "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                        "transaction_id": tid,
                        "refund_requested_at": refund_ts,
                        "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 72)),
                        "refund_amount": round(amount * rng.uniform(0.85, 1.0), 2),
                        "refund_reason": _refund_reason(rng),
                        "refund_status": "completed",
                        "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                    })

        abuse_metadata.append({
            "ring_id": ring_id,
            "abuse_pattern_type": "pattern_a_shared_device",
            "n_accounts": n_accts,
            "generation_seed": rng.integers(0, 999999),
            "ring_base_timestamp": ring_base_ts.isoformat(),
            "shared_devices": shared_devs.tolist(),
            "ring_merchant": ring_merchant,
        })

    logger.info("Pattern A: generated %d rings", len(ring_ids_created))
    return ring_ids_created


# ---------------------------------------------------------------------------
# Pattern B — Cross-merchant coordinated refund ring
# ---------------------------------------------------------------------------

def generate_pattern_b_rings(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    abuse_metadata: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> list[str]:
    """
    Related accounts interact with multiple merchants and show similar
    purchase/refund patterns across the merchant set. Individual accounts
    look less suspicious in isolation — the pattern emerges collectively.
    """
    abuse_cfg = cfg["abuse"]
    pb = abuse_cfg["pattern_b"]
    n_rings = abuse_cfg["n_rings_pattern_b"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])
    amount_min = abuse_cfg["amount_min"]
    amount_max = abuse_cfg["amount_max"]

    device_ids = devices["device_id"].values
    merchant_ids = merchants["merchant_id"].values
    ip_ids = ip_entities["ip_id"].values
    instrument_ids = instruments["instrument_id"].values
    cust_ids = customers["customer_id"].values

    ring_ids_created: list[str] = []

    for ring_idx in range(n_rings):
        ring_id = f"RING_B_{ring_idx:04d}"
        ring_ids_created.append(ring_id)

        n_accts = int(rng.integers(pb["accounts_per_ring_min"], pb["accounts_per_ring_max"] + 1))
        n_merchants = pb["merchants_targeted_per_ring"]

        ring_accounts = rng.choice(cust_ids, size=min(n_accts, len(cust_ids)), replace=False)
        ring_merchants = rng.choice(merchant_ids, size=min(n_merchants, len(merchant_ids)), replace=False)

        # Amount cluster: similar amounts across the ring (a signature)
        base_amount = rng.uniform(amount_min, amount_max)
        coordination_window_days = pb["coordination_window_days"]

        ring_start_offset = rng.integers(0, int((end - start).total_seconds()) - coordination_window_days * 86400)
        ring_base_ts = start + timedelta(seconds=int(ring_start_offset))

        # Shared IP entity — links accounts without sharing devices
        shared_ip = rng.choice(ip_ids)

        for cid in ring_accounts:
            ins_id = rng.choice(instrument_ids)
            dev_id = rng.choice(device_ids)  # each account uses own device
            n_cycles = int(rng.integers(1, pb["refund_cycles_per_account"] + 1))

            for cycle in range(n_cycles):
                # Target different merchants per cycle
                m_id = ring_merchants[cycle % len(ring_merchants)]
                # Spread within coordination window
                ts = ring_base_ts + timedelta(
                    hours=float(rng.uniform(0, coordination_window_days * 24))
                )
                if ts >= end:
                    continue

                # Amount is similar to ring base but not identical
                amount = round(base_amount * rng.uniform(0.85, 1.15), 2)
                amount = max(amount, 50.0)
                oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
                tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"

                orders.append({
                    "order_id": oid, "customer_id": cid, "merchant_id": m_id,
                    "created_at": ts, "amount": amount,
                    "product_category": rng.choice(["electronics", "fashion", "travel"]),
                    "delivery_region": rng.choice(["north", "south", "east", "west"]),
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                transactions.append({
                    "transaction_id": tid, "order_id": oid, "customer_id": cid,
                    "merchant_id": m_id, "device_id": dev_id, "ip_id": shared_ip,
                    "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                    "payment_method": _payment_method(rng),
                    "payment_status": "captured",
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                delay_h = float(rng.uniform(
                    abuse_cfg["refund_delay_hours_min"],
                    abuse_cfg["refund_delay_hours_max"],
                ))
                refund_ts = ts + timedelta(hours=delay_h)
                if refund_ts < end:
                    refunds.append({
                        "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                        "transaction_id": tid,
                        "refund_requested_at": refund_ts,
                        "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 72)),
                        "refund_amount": round(amount * rng.uniform(0.80, 1.0), 2),
                        "refund_reason": _refund_reason(rng),
                        "refund_status": "completed",
                        "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                    })

        abuse_metadata.append({
            "ring_id": ring_id,
            "abuse_pattern_type": "pattern_b_cross_merchant",
            "n_accounts": n_accts,
            "generation_seed": rng.integers(0, 999999),
            "ring_base_timestamp": ring_base_ts.isoformat(),
            "ring_merchants": ring_merchants.tolist(),
            "shared_ip": shared_ip,
            "base_amount": round(base_amount, 2),
        })

    logger.info("Pattern B: generated %d rings", len(ring_ids_created))
    return ring_ids_created


# ---------------------------------------------------------------------------
# Pattern C — Rotating-account refund ring
# ---------------------------------------------------------------------------

def generate_pattern_c_rings(
    orders: list[dict],
    transactions: list[dict],
    refunds: list[dict],
    abuse_metadata: list[dict],
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    ip_entities: pd.DataFrame,
    instruments: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> list[str]:
    """
    Relatively new accounts appear over time and are linked by shared infrastructure
    (same IP entity or instrument family pattern). Accounts rotate through the ring,
    making account_age_days alone insufficient for detection.
    """
    abuse_cfg = cfg["abuse"]
    pc = abuse_cfg["pattern_c"]
    n_rings = abuse_cfg["n_rings_pattern_c"]

    start = datetime.fromisoformat(cfg["temporal"]["start_date"])
    end = datetime.fromisoformat(cfg["temporal"]["end_date"])
    amount_min = abuse_cfg["amount_min"]
    amount_max = abuse_cfg["amount_max"]

    merchant_ids = merchants["merchant_id"].values
    ip_ids = ip_entities["ip_id"].values
    instrument_ids = instruments["instrument_id"].values
    device_ids = devices["device_id"].values

    ring_ids_created: list[str] = []

    for ring_idx in range(n_rings):
        ring_id = f"RING_C_{ring_idx:04d}"
        ring_ids_created.append(ring_id)

        n_accts = int(rng.integers(pc["accounts_per_ring_min"], pc["accounts_per_ring_max"] + 1))
        rotation_interval = pc["rotation_interval_days"]
        max_age = pc["max_account_age_days"]

        # Shared infrastructure
        linking_ip = rng.choice(ip_ids)
        # "Instrument family" — same instrument prefix (simulated as same instrument_id for simplicity)
        linking_instrument = rng.choice(instrument_ids)

        # Ring merchant
        ring_merchant = rng.choice(merchant_ids)

        # Generate new synthetic customers for this ring (fresh accounts)
        ring_start_offset = rng.integers(
            90 * 86400,  # at least 90 days in
            int((end - start).total_seconds()) - (n_accts * rotation_interval + 30) * 86400,
        )
        ring_start = start + timedelta(seconds=int(ring_start_offset))

        ring_customer_ids: list[str] = []
        for acct_idx in range(n_accts):
            # Each account appears rotation_interval days after the previous
            acct_created = ring_start + timedelta(days=acct_idx * rotation_interval)
            if acct_created >= end - timedelta(days=max_age):
                break

            # Create a synthetic "new" customer just for this ring
            cust_id = f"CUS_RING_C_{ring_idx:04d}_{acct_idx:03d}"
            ring_customer_ids.append(cust_id)

            # Add to customers table (will need to merge later)
            # For now add to the customers dataframe via appending to the list
            # We signal this via a flag in the transactions

            dev_id = rng.choice(device_ids)
            # Use linking IP most of the time
            use_link_ip = rng.random() < 0.80
            ip_id = linking_ip if use_link_ip else rng.choice(ip_ids)
            # Use linking instrument most of the time
            use_link_ins = rng.random() < 0.70
            ins_id = linking_instrument if use_link_ins else rng.choice(instrument_ids)

            n_cycles = int(rng.integers(1, pc["refund_cycles_per_account"] + 1))
            for cycle in range(n_cycles):
                ts = acct_created + timedelta(
                    days=float(rng.uniform(1, min(max_age, 30)))
                )
                if ts >= end:
                    continue

                amount = round(rng.uniform(amount_min, amount_max), 2)
                oid = f"ORD_{rng.integers(100_000_000, 999_999_999)}"
                tid = f"TXN_{rng.integers(100_000_000, 999_999_999)}"

                orders.append({
                    "order_id": oid, "customer_id": cust_id, "merchant_id": ring_merchant,
                    "created_at": ts, "amount": amount,
                    "product_category": rng.choice(["electronics", "fashion"]),
                    "delivery_region": rng.choice(["north", "south", "east", "west"]),
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                transactions.append({
                    "transaction_id": tid, "order_id": oid, "customer_id": cust_id,
                    "merchant_id": ring_merchant, "device_id": dev_id, "ip_id": ip_id,
                    "instrument_id": ins_id, "timestamp": ts, "amount": amount,
                    "payment_method": _payment_method(rng),
                    "payment_status": "captured",
                    "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                })
                delay_h = float(rng.uniform(
                    abuse_cfg["refund_delay_hours_min"],
                    abuse_cfg["refund_delay_hours_max"],
                ))
                refund_ts = ts + timedelta(hours=delay_h)
                if refund_ts < end:
                    refunds.append({
                        "refund_id": f"REF_{rng.integers(100_000_000, 999_999_999)}",
                        "transaction_id": tid,
                        "refund_requested_at": refund_ts,
                        "refund_processed_at": refund_ts + timedelta(hours=rng.uniform(2, 72)),
                        "refund_amount": round(amount * rng.uniform(0.85, 1.0), 2),
                        "refund_reason": _refund_reason(rng),
                        "refund_status": "completed",
                        "abuse_label": 1, "ring_id": ring_id, "hard_negative_type": None,
                    })

        abuse_metadata.append({
            "ring_id": ring_id,
            "abuse_pattern_type": "pattern_c_rotating_account",
            "n_accounts": n_accts,
            "generation_seed": rng.integers(0, 999999),
            "ring_start_timestamp": ring_start.isoformat(),
            "linking_ip": linking_ip,
            "linking_instrument": linking_instrument,
            "ring_merchant": ring_merchant,
            "ring_customer_ids": ring_customer_ids,
        })

    logger.info("Pattern C: generated %d rings", len(ring_ids_created))
    return ring_ids_created
