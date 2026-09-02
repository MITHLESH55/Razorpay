"""
RiskOrbit — Dataset Splitting Script

Usage:
    python scripts/create_splits.py [--config configs/generation_config.yaml]

Reads data/raw/transactions.csv and creates ring-aware time-ordered splits.

Output:
    data/splits/train.csv
    data/splits/validation.csv
    data/splits/heldout_test.csv
    data/splits/split_manifest.json

IMPORTANT: The held-out test set is written to disk and should be treated
as a read-only evaluation resource. Never use it for threshold tuning.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.validation.splitter import create_splits, save_splits

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("create_splits")


def main(config_path: str = "configs/generation_config.yaml") -> None:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    txn_path = Path("data/raw/transactions.csv")
    if not txn_path.exists():
        logger.error("transactions.csv not found — run generate_data.py first")
        sys.exit(1)

    transactions = pd.read_csv(txn_path, low_memory=False)
    transactions["timestamp"] = pd.to_datetime(transactions["timestamp"], format="mixed")

    rng = np.random.default_rng(cfg["seed"])
    train, val, test = create_splits(transactions, cfg, rng)
    save_splits(train, val, test, Path("data/splits"))
    logger.info("Splits created successfully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/generation_config.yaml")
    args = parser.parse_args()
    main(args.config)
