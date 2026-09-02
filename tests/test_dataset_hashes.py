"""
RiskOrbit — Dataset Hashing & Integrity Tests
Verifies cryptographic fingerprints of dataset splits.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_dataset_hashes_match():
    splits_dir = Path("data/splits")
    hashes_file = splits_dir / "dataset_hashes.json"
    if not hashes_file.exists():
        pytest.skip("dataset_hashes.json not found")

    manifest = json.loads(hashes_file.read_text())

    assert compute_sha256(splits_dir / "train.csv") == manifest["train_csv_sha256"]
    assert compute_sha256(splits_dir / "validation.csv") == manifest["validation_csv_sha256"]
    assert compute_sha256(splits_dir / "heldout_test.csv") == manifest["heldout_test_csv_sha256"]


def test_artifact_hashes_match():
    artifact_dir = Path("artifacts/riskorbit-risk-v1")
    hashes_file = artifact_dir / "dataset_hashes.json"
    if not hashes_file.exists():
        pytest.skip("dataset_hashes.json not found in artifacts")

    manifest = json.loads(hashes_file.read_text())
    assert manifest["algorithm"] == "SHA256"
    assert manifest["dataset_version"] == "phase1-v1"
