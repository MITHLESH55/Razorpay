"""
RiskOrbit — Build Features Script

Computes feature matrices for train and validation partitions
and saves them to data/processed/.

Usage:
    python scripts/build_features.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.pipeline import FEATURE_COLUMNS, build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_features")


def main() -> None:
    raw = Path("data/raw")
    splits = Path("data/splits")

    for required in ["train.csv", "validation.csv"]:
        if not (splits / required).exists():
            logger.error("Missing %s — run create_splits.py first", required)
            sys.exit(1)

    logger.info("Loading data …")
    customers = pd.read_csv(raw / "customers.csv", low_memory=False)
    merchants = pd.read_csv(raw / "merchants.csv", low_memory=False)
    devices = pd.read_csv(raw / "devices.csv", low_memory=False)
    ip_entities = pd.read_csv(raw / "ip_entities.csv", low_memory=False)
    instruments = pd.read_csv(raw / "instruments.csv", low_memory=False)
    orders = pd.read_csv(raw / "orders.csv", low_memory=False)
    refunds = pd.read_csv(raw / "refunds.csv", low_memory=False)
    orders["created_at"] = pd.to_datetime(orders["created_at"], format="mixed")

    train = pd.read_csv(splits / "train.csv", low_memory=False)
    val = pd.read_csv(splits / "validation.csv", low_memory=False)
    train["timestamp"] = pd.to_datetime(train["timestamp"], format="mixed")
    val["timestamp"] = pd.to_datetime(val["timestamp"], format="mixed")

    feat_dir = Path("data/processed")
    feat_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Building train features (%d rows) …", len(train))
    X_train = build_features(train, orders, refunds, customers, merchants, devices, ip_entities, instruments, reference_transactions=train)
    train_out = pd.DataFrame(X_train, columns=FEATURE_COLUMNS)
    train_out["abuse_label"] = train["abuse_label"].values
    train_out.to_csv(feat_dir / "train_features.csv", index=False)
    logger.info("Train features saved.")

    logger.info("Building validation features (%d rows) …", len(val))
    X_val = build_features(val, orders, refunds, customers, merchants, devices, ip_entities, instruments, reference_transactions=train)
    val_out = pd.DataFrame(X_val, columns=FEATURE_COLUMNS)
    val_out["abuse_label"] = val["abuse_label"].values
    val_out.to_csv(feat_dir / "val_features.csv", index=False)
    logger.info("Validation features saved.")


if __name__ == "__main__":
    main()
