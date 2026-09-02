"""
RiskOrbit — Automated Data Tests
Tests: unique IDs, referential integrity, temporal consistency, ground truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path("data/raw")
SPLITS_DIR = Path("data/splits")


@pytest.fixture(scope="session")
def raw_data():
    required = [
        "customers.csv", "merchants.csv", "devices.csv",
        "ip_entities.csv", "instruments.csv",
        "orders.csv", "transactions.csv", "refunds.csv",
    ]
    for f in required:
        if not (DATA_DIR / f).exists():
            pytest.skip(f"Raw data not found ({f}). Run generate_data.py first.")
    return {
        "customers": pd.read_csv(DATA_DIR / "customers.csv"),
        "merchants": pd.read_csv(DATA_DIR / "merchants.csv"),
        "devices": pd.read_csv(DATA_DIR / "devices.csv"),
        "ip_entities": pd.read_csv(DATA_DIR / "ip_entities.csv"),
        "instruments": pd.read_csv(DATA_DIR / "instruments.csv"),
        "orders": pd.read_csv(DATA_DIR / "orders.csv"),
        "transactions": pd.read_csv(DATA_DIR / "transactions.csv"),
        "refunds": pd.read_csv(DATA_DIR / "refunds.csv"),
    }


@pytest.fixture(scope="session")
def splits():
    for f in ["train.csv", "validation.csv", "heldout_test.csv"]:
        if not (SPLITS_DIR / f).exists():
            pytest.skip(f"Splits not found ({f}). Run create_splits.py first.")
    return {
        "train": pd.read_csv(SPLITS_DIR / "train.csv"),
        "val": pd.read_csv(SPLITS_DIR / "validation.csv"),
        "test": pd.read_csv(SPLITS_DIR / "heldout_test.csv"),
    }


# --------------------------------------------------------------------------
# Unique ID tests
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table,col", [
    ("customers", "customer_id"),
    ("merchants", "merchant_id"),
    ("devices", "device_id"),
    ("ip_entities", "ip_id"),
    ("instruments", "instrument_id"),
    ("orders", "order_id"),
    ("transactions", "transaction_id"),
    ("refunds", "refund_id"),
])
def test_unique_ids(raw_data, table, col):
    df = raw_data[table]
    assert col in df.columns, f"{table} missing column {col}"
    n_dup = df[col].duplicated().sum()
    assert n_dup == 0, f"{table}.{col} has {n_dup} duplicates"


# --------------------------------------------------------------------------
# Dataset size tests
# --------------------------------------------------------------------------

def test_transaction_count(raw_data):
    """Must have at least 50k transactions for statistical validity."""
    assert len(raw_data["transactions"]) >= 50_000, (
        f"Only {len(raw_data['transactions'])} transactions — expected >= 50,000"
    )


def test_customer_count(raw_data):
    assert len(raw_data["customers"]) >= 10_000


def test_refund_count(raw_data):
    assert len(raw_data["refunds"]) >= 5_000


# --------------------------------------------------------------------------
# Temporal consistency tests
# --------------------------------------------------------------------------

def test_refund_after_transaction(raw_data):
    """Refund requested_at must be >= transaction timestamp."""
    txn = raw_data["transactions"][["transaction_id", "timestamp"]].copy()
    txn["timestamp"] = pd.to_datetime(txn["timestamp"])
    ref = raw_data["refunds"][["transaction_id", "refund_requested_at"]].copy()
    ref["refund_requested_at"] = pd.to_datetime(ref["refund_requested_at"])
    merged = ref.merge(txn, on="transaction_id", how="inner")
    bad = merged[merged["refund_requested_at"] < merged["timestamp"]]
    assert len(bad) == 0, f"{len(bad)} refunds requested before transaction timestamp"


def test_refund_processed_after_requested(raw_data):
    """Refund processed_at must be >= refund_requested_at."""
    ref = raw_data["refunds"].copy()
    ref["refund_requested_at"] = pd.to_datetime(ref["refund_requested_at"])
    ref["refund_processed_at"] = pd.to_datetime(ref["refund_processed_at"])
    bad = ref[ref["refund_processed_at"] < ref["refund_requested_at"]]
    assert len(bad) == 0, f"{len(bad)} refunds processed before requested"


# --------------------------------------------------------------------------
# Amount tests
# --------------------------------------------------------------------------

def test_no_negative_transaction_amounts(raw_data):
    bad = (raw_data["transactions"]["amount"] < 0).sum()
    assert bad == 0, f"{bad} negative transaction amounts"


def test_no_negative_refund_amounts(raw_data):
    bad = (raw_data["refunds"]["refund_amount"] < 0).sum()
    assert bad == 0, f"{bad} negative refund amounts"


# --------------------------------------------------------------------------
# Ground truth tests
# --------------------------------------------------------------------------

def test_abuse_label_exists_in_transactions(raw_data):
    assert "abuse_label" in raw_data["transactions"].columns

def test_abuse_label_binary(raw_data):
    vals = raw_data["transactions"]["abuse_label"].dropna().unique()
    assert set(vals).issubset({0, 1, 0.0, 1.0}), f"Non-binary abuse_label values: {vals}"

def test_abuse_label_no_nulls(raw_data):
    nulls = raw_data["transactions"]["abuse_label"].isna().sum()
    assert nulls == 0, f"{nulls} null abuse_label values"

def test_abuse_prevalence_reasonable(raw_data):
    """Abuse should be 0.5–20% of all transactions (1% is realistic for payment fraud)."""
    rate = raw_data["transactions"]["abuse_label"].mean()
    assert 0.005 <= rate <= 0.20, f"Unusual abuse prevalence: {rate:.4f}"


# --------------------------------------------------------------------------
# Ring leakage tests
# --------------------------------------------------------------------------

def test_no_ring_leakage_between_train_and_test(splits):
    """No ring_id should appear in both train and test."""
    train = splits["train"]
    test = splits["test"]
    if "ring_id" not in train.columns or "ring_id" not in test.columns:
        pytest.skip("ring_id not in splits")
    train_rings = set(train[train["ring_id"].notna() & (train["ring_id"] != "")]["ring_id"])
    test_rings = set(test[test["ring_id"].notna() & (test["ring_id"] != "")]["ring_id"])
    leakage = train_rings & test_rings
    assert len(leakage) == 0, f"Ring leakage detected: {len(leakage)} rings in both train and test"


def test_no_ring_leakage_between_val_and_test(splits):
    val = splits["val"]
    test = splits["test"]
    if "ring_id" not in val.columns or "ring_id" not in test.columns:
        pytest.skip("ring_id not in splits")
    val_rings = set(val[val["ring_id"].notna() & (val["ring_id"] != "")]["ring_id"])
    test_rings = set(test[test["ring_id"].notna() & (test["ring_id"] != "")]["ring_id"])
    leakage = val_rings & test_rings
    assert len(leakage) == 0, f"Ring leakage (val/test): {len(leakage)} rings shared"


# --------------------------------------------------------------------------
# Forbidden column tests
# --------------------------------------------------------------------------

def test_forbidden_columns_not_in_splits(splits):
    """Metadata/leakage columns must never appear in the split data for model use."""
    # ring_id and hard_negative_type are allowed in splits (for analysis)
    # but generation metadata must not be present
    truly_forbidden = {"ring_generation_source", "abuse_pattern_type", "shared_devices"}
    for name, df in splits.items():
        found = truly_forbidden & set(df.columns)
        assert len(found) == 0, f"Forbidden columns in {name} split: {found}"
