"""
RiskOrbit — Ring-Level & Calibration Metric Tests
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.evaluation.metrics import compute_calibration_metrics, compute_ring_metrics


def test_compute_ring_metrics_basic():
    # 2 rings: RING_1 has 4 txns (2 detected), RING_2 has 2 txns (0 detected)
    y_true = np.array([1, 1, 1, 1, 1, 1, 0, 0])
    y_pred = np.array([1, 1, 0, 0, 0, 0, 0, 0])
    ring_ids = pd.Series(["RING_1", "RING_1", "RING_1", "RING_1", "RING_2", "RING_2", "", ""])

    m = compute_ring_metrics(y_true, y_pred, ring_ids)

    assert m["total_rings"] == 2
    assert m["detected_rings_at_least_1"] == 1
    assert m["ring_recall"] == 0.50
    assert m["strong_ring_recall"] == 0.50  # RING_1 has 2/4 = 50%
    assert m["complete_ring_detection_rate"] == 0.0
    assert m["missed_rings_count"] == 1
    assert m["missed_rings_pct"] == 0.50


def test_compute_calibration_metrics():
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_score = np.array([0.1, 0.2, 0.1, 0.3, 0.7, 0.8, 0.9, 0.85])

    cal = compute_calibration_metrics(y_true, y_score, n_bins=5)
    assert 0.0 <= cal["expected_calibration_error"] <= 1.0
    assert 0.0 <= cal["brier_score"] <= 1.0
    assert len(cal["bin_details"]) > 0
