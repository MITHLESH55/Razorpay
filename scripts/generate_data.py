"""
RiskOrbit — Data Generation Script

Generates the complete synthetic payment ecosystem.

Usage:
    python scripts/generate_data.py [--config configs/generation_config.yaml]

Output:
    data/raw/customers.csv
    data/raw/merchants.csv
    data/raw/devices.csv
    data/raw/ip_entities.csv
    data/raw/instruments.csv
    data/raw/orders.csv
    data/raw/transactions.csv
    data/raw/refunds.csv
    data/raw/generation_metadata/abuse_rings.csv

Reproducibility: all random state controlled by cfg["seed"].
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_generation.entities import (
    generate_customers,
    generate_devices,
    generate_instruments,
    generate_ip_entities,
    generate_merchants,
)
from src.data_generation.legitimate_engine import generate_legitimate_transactions
from src.data_generation.hard_negatives import (
    inject_household_sharing,
    inject_high_refund_customers,
    inject_high_volume_merchants,
    inject_multi_device_customers,
    inject_new_customer_high_value,
    inject_shared_network,
)
from src.data_generation.abuse_engine import (
    generate_pattern_a_rings,
    generate_pattern_b_rings,
    generate_pattern_c_rings,
)
from src.data_generation.ground_truth import assemble_ground_truth, save_raw_data

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("generate_data")


def main(config_path: str = "configs/generation_config.yaml") -> None:
    # ---- Load config -----------------------------------------------
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        logger.error("Config not found: %s", cfg_path)
        sys.exit(1)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    seed = cfg["seed"]
    rng = np.random.default_rng(seed)
    logger.info("RNG seeded with %d", seed)

    temporal = cfg["temporal"]
    start_date = datetime.fromisoformat(temporal["start_date"])
    end_date = datetime.fromisoformat(temporal["end_date"])
    scale = cfg["scale"]

    # ---- Step 1: Generate base entities ----------------------------
    logger.info("Generating entities …")
    customers = generate_customers(
        n=scale["n_customers"],
        segments=cfg["legitimate"]["customer_segments"],
        start_date=start_date,
        end_date=end_date,
        rng=rng,
    )
    merchants = generate_merchants(
        n=scale["n_merchants"],
        categories=cfg["legitimate"]["merchant_categories"],
        start_date=start_date,
        end_date=end_date,
        rng=rng,
    )
    devices = generate_devices(
        n=scale["n_devices"],
        start_date=start_date,
        end_date=end_date,
        rng=rng,
    )
    ip_entities = generate_ip_entities(
        n=scale["n_ip_entities"],
        start_date=start_date,
        end_date=end_date,
        rng=rng,
    )
    instruments = generate_instruments(
        n=scale["n_instruments"],
        rng=rng,
    )
    logger.info(
        "Entities: %d customers, %d merchants, %d devices, %d IPs, %d instruments",
        len(customers), len(merchants), len(devices), len(ip_entities), len(instruments),
    )

    # ---- Step 2: Generate legitimate baseline ----------------------
    logger.info("Generating legitimate transactions (this may take a few minutes) …")
    orders_list = []
    txn_list = []
    ref_list = []

    orders_legit, txn_legit, ref_legit = generate_legitimate_transactions(
        customers=customers,
        merchants=merchants,
        devices=devices,
        ip_entities=ip_entities,
        instruments=instruments,
        cfg=cfg,
        rng=rng,
    )
    orders_list.append(orders_legit)
    txn_list.append(txn_legit)
    ref_list.append(ref_legit)

    # ---- Step 3: Inject hard negatives ----------------------------
    logger.info("Injecting hard negatives …")
    hn_orders: list = []
    hn_txns: list = []
    hn_refs: list = []

    inject_household_sharing(hn_orders, hn_txns, hn_refs, customers, merchants, devices, instruments, cfg, rng)
    inject_shared_network(hn_orders, hn_txns, hn_refs, customers, merchants, ip_entities, instruments, cfg, rng)
    inject_high_refund_customers(hn_orders, hn_txns, hn_refs, customers, merchants, devices, instruments, cfg, rng)
    inject_high_volume_merchants(hn_orders, hn_txns, hn_refs, customers, merchants, devices, instruments, cfg, rng)
    inject_new_customer_high_value(hn_orders, hn_txns, hn_refs, customers, merchants, devices, instruments, cfg, rng)
    inject_multi_device_customers(hn_orders, hn_txns, hn_refs, customers, merchants, devices, instruments, cfg, rng)

    if hn_orders:
        orders_list.append(pd.DataFrame(hn_orders))
    if hn_txns:
        txn_list.append(pd.DataFrame(hn_txns))
    if hn_refs:
        ref_list.append(pd.DataFrame(hn_refs))

    logger.info("Hard negatives: %d txns injected", len(hn_txns))

    # ---- Step 4: Inject abuse rings --------------------------------
    logger.info("Generating abuse rings …")
    abuse_orders: list = []
    abuse_txns: list = []
    abuse_refs: list = []
    abuse_metadata: list = []

    generate_pattern_a_rings(
        abuse_orders, abuse_txns, abuse_refs, abuse_metadata,
        customers, merchants, devices, ip_entities, instruments, cfg, rng,
    )
    generate_pattern_b_rings(
        abuse_orders, abuse_txns, abuse_refs, abuse_metadata,
        customers, merchants, devices, ip_entities, instruments, cfg, rng,
    )
    generate_pattern_c_rings(
        abuse_orders, abuse_txns, abuse_refs, abuse_metadata,
        customers, merchants, devices, ip_entities, instruments, cfg, rng,
    )

    if abuse_orders:
        orders_list.append(pd.DataFrame(abuse_orders))
    if abuse_txns:
        txn_list.append(pd.DataFrame(abuse_txns))
    if abuse_refs:
        ref_list.append(pd.DataFrame(abuse_refs))

    logger.info("Abuse rings: %d total rings, %d txns injected", len(abuse_metadata), len(abuse_txns))

    # ---- Step 5: Assemble and save ---------------------------------
    orders_all = pd.concat(orders_list, ignore_index=True)
    txn_all = pd.concat(txn_list, ignore_index=True)
    ref_all = pd.concat(ref_list, ignore_index=True)

    orders_gt, txn_gt, ref_gt, meta_df = assemble_ground_truth(
        orders_all, txn_all, ref_all, abuse_metadata
    )

    output_dir = Path("data/raw")
    save_raw_data(
        customers, merchants, devices, ip_entities, instruments,
        orders_gt, txn_gt, ref_gt, meta_df,
        output_dir=output_dir,
    )

    # ---- Summary ---------------------------------------------------
    abuse_rate = txn_gt["abuse_label"].mean()
    logger.info(
        "DONE — %d transactions | %.2f%% abuse | %d rings | %d refunds",
        len(txn_gt), abuse_rate * 100, len(meta_df), len(ref_gt),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RiskOrbit synthetic dataset")
    parser.add_argument("--config", default="configs/generation_config.yaml")
    args = parser.parse_args()
    main(args.config)
