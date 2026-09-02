"""
RiskOrbit — Data Validation Script

Usage:
    python scripts/validate_data.py

Reads data/raw/ and runs all integrity checks.
Writes reports/DATA_QUALITY_REPORT.md.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.validation.data_validator import DataValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_data")


def main() -> None:
    data_dir = Path("data/raw")
    required = [
        "customers.csv", "merchants.csv", "devices.csv",
        "ip_entities.csv", "instruments.csv",
        "orders.csv", "transactions.csv", "refunds.csv",
    ]
    missing = [f for f in required if not (data_dir / f).exists()]
    if missing:
        logger.error("Missing data files: %s — run generate_data.py first", missing)
        sys.exit(1)

    logger.info("Loading data from %s …", data_dir)
    customers = pd.read_csv(data_dir / "customers.csv", low_memory=False)
    merchants = pd.read_csv(data_dir / "merchants.csv", low_memory=False)
    devices = pd.read_csv(data_dir / "devices.csv", low_memory=False)
    ip_entities = pd.read_csv(data_dir / "ip_entities.csv", low_memory=False)
    instruments = pd.read_csv(data_dir / "instruments.csv", low_memory=False)
    orders = pd.read_csv(data_dir / "orders.csv", low_memory=False)
    transactions = pd.read_csv(data_dir / "transactions.csv", low_memory=False)
    refunds = pd.read_csv(data_dir / "refunds.csv", low_memory=False)

    validator = DataValidator(
        customers, merchants, devices, ip_entities, instruments,
        orders, transactions, refunds,
    )
    report = validator.run()
    validator.save_report(report, Path("reports/DATA_QUALITY_REPORT.md"))

    if not report["passed"]:
        logger.error("Validation FAILED — check DATA_QUALITY_REPORT.md")
        sys.exit(1)
    else:
        logger.info("Validation PASSED")


if __name__ == "__main__":
    main()
