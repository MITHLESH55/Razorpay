"""
RiskOrbit — Golden Case Benchmark Catalog (Phase 2)

Provides deterministic, grounded golden test cases:
  - 3 Coordinated Abuse Cases (Pattern A, Pattern B, Pattern C)
  - 5 Legitimate Cases (Household sharing, Shared network, Serial returner, High-volume merchant, Multi-device)
  - 2 Ambiguous Boundary Cases (Occasional sharing, Public Wi-Fi return)
"""
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd


def get_golden_case_definitions() -> List[Dict[str, Any]]:
    """Return catalog of standardized golden cases for regression and demo suites."""
    return [
        # --- ABUSE CASES ---
        {
            "case_code": "CASE-GOLD-ABUSE-A",
            "name": "Coordinated Shared-Device Ring",
            "expected_abuse_pattern": "pattern_a_shared_device",
            "expected_is_candidate": True,
            "expected_min_risk_score": 0.60,
            "expected_min_members": 3,
            "expected_min_shared_devices": 1,
            "description": "7 colluding customer accounts transacting across 2 shared devices with coordinated refund bursts.",
        },
        {
            "case_code": "CASE-GOLD-ABUSE-B",
            "name": "Cross-Merchant Coordinated Ring",
            "expected_abuse_pattern": "pattern_b_cross_merchant",
            "expected_is_candidate": True,
            "expected_min_risk_score": 0.45,
            "expected_min_members": 3,
            "expected_min_merchants": 2,
            "description": "5 accounts sharing network infrastructure targeting 3 merchants with synchronized order timing.",
        },
        {
            "case_code": "CASE-GOLD-ABUSE-C",
            "name": "Rotating Burner Account Ring",
            "expected_abuse_pattern": "pattern_c_rotating_account",
            "expected_is_candidate": True,
            "expected_min_risk_score": 0.70,
            "expected_min_members": 4,
            "description": "Sequential burner accounts rotating on common IP and payment instrument family.",
        },

        # --- LEGITIMATE CASES ---
        {
            "case_code": "CASE-GOLD-LEGIT-HOUSEHOLD",
            "name": "Legitimate Household Device Sharing",
            "hard_negative_type": "household_sharing",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.35,
            "description": "Family members sharing a single household tablet with normal low refund frequency.",
        },
        {
            "case_code": "CASE-GOLD-LEGIT-NETWORK",
            "name": "Office / Campus Shared Network",
            "hard_negative_type": "shared_network",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.30,
            "description": "Independent employees connecting via common corporate IP gateway with independent devices.",
        },
        {
            "case_code": "CASE-GOLD-LEGIT-SERIAL-RETURNER",
            "name": "Legitimate High-Refund Customer",
            "hard_negative_type": "high_refund_customer",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.35,
            "description": "Single benign customer with 60%+ apparel refund rate on a personal dedicated device.",
        },
        {
            "case_code": "CASE-GOLD-LEGIT-MERCHANT",
            "name": "High-Volume Merchant Customer",
            "hard_negative_type": "high_volume_merchant",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.25,
            "description": "Regular shopper at a high-throughput electronics retailer with baseline return rate.",
        },
        {
            "case_code": "CASE-GOLD-LEGIT-MULTI-DEV",
            "name": "Multi-Device Benign Power User",
            "hard_negative_type": "multi_device_customer",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.25,
            "description": "Single legitimate user transacting across phone, laptop, and tablet.",
        },

        # --- AMBIGUOUS BOUNDARY CASES ---
        {
            "case_code": "CASE-GOLD-AMBIG-OCCASIONAL-DEVICE",
            "name": "Occasional Shared Device with Single Return",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.45,
            "description": "Two accounts with one historical shared device and a single isolated refund.",
        },
        {
            "case_code": "CASE-GOLD-AMBIG-PUBLIC-WIFI",
            "name": "Public Wi-Fi Temporal Return Co-occurrence",
            "expected_is_candidate": False,
            "expected_max_risk_score": 0.40,
            "description": "Two unrelated accounts on coffee shop Wi-Fi with coincidentally near refund times.",
        },
    ]
