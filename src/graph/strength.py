"""
RiskOrbit — Relationship Strength & Hubness Normalization (Phase 2)

Computes explainable, non-binary relationship strength scores.
Incorporate:
  1. Event frequency (repetition)
  2. Temporal recency relative to scoring timestamp
  3. Hubness normalization (discounting massive corporate/campus IPs and high-volume devices)
  4. Entity specificity
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional


def compute_hubness_penalty(n_connected_accounts: int, entity_type: str) -> float:
    """
    Compute hubness discount factor in [0.05, 1.0].
    
    A rare personal device with 2 accounts -> penalty ~ 1.0 (high specificity)
    A massive university / office campus IP with 50 accounts -> penalty ~ 0.15 (low specificity)
    """
    if n_connected_accounts <= 1:
        return 1.0

    if entity_type in ("DEVICE", "INSTRUMENT"):
        # Devices are expected to be personal / household (1-4 users typical)
        # Moderate sharing (2-8) is penalized gently, extreme sharing (>15) is penalized
        return max(0.10, 1.0 / (1.0 + 0.15 * math.log1p(n_connected_accounts)))
    elif entity_type == "IP":
        # IPs are often public / corporate (10-50 users normal)
        # We discount shared IPs much more aggressively to protect benign networks
        return max(0.05, 1.0 / (1.0 + 0.35 * math.log1p(n_connected_accounts)))
    elif entity_type == "MERCHANT":
        # Merchants legitimately serve thousands of users
        return max(0.01, 1.0 / (1.0 + 0.50 * math.log1p(n_connected_accounts)))
    return 1.0


def compute_edge_strength(
    event_count: int,
    first_seen: datetime,
    last_seen: datetime,
    as_of_time: Optional[datetime] = None,
    n_connected_accounts: int = 1,
    target_entity_type: str = "DEVICE",
    half_life_days: float = 30.0,
) -> dict[str, float]:
    """
    Calculate composite explainable edge strength in [0.0, 1.0].

    Components:
      - frequency_score: log-scaled event count
      - recency_score: exponential time decay from as_of_time
      - duration_score: span between first and last seen
      - hubness_factor: inverse popularity discount
    """
    # 1. Frequency (capped log-scaling)
    freq_score = min(1.0, math.log1p(event_count) / math.log1p(20))

    # 2. Recency decay
    if as_of_time is not None and last_seen <= as_of_time:
        days_since_last = max(0.0, (as_of_time - last_seen).total_seconds() / 86400.0)
        recency_score = math.exp(-math.log(2.0) * days_since_last / half_life_days)
    else:
        recency_score = 1.0

    # 3. Duration/span score
    span_days = max(0.0, (last_seen - first_seen).total_seconds() / 86400.0)
    duration_score = min(1.0, math.log1p(span_days) / math.log1p(60))

    # 4. Hubness penalty
    hubness_factor = compute_hubness_penalty(n_connected_accounts, target_entity_type)

    # Composite strength
    raw_strength = (0.50 * freq_score + 0.35 * recency_score + 0.15 * duration_score)
    final_strength = round(float(raw_strength * hubness_factor), 4)

    return {
        "strength": final_strength,
        "frequency_score": round(float(freq_score), 4),
        "recency_score": round(float(recency_score), 4),
        "duration_score": round(float(duration_score), 4),
        "hubness_factor": round(float(hubness_factor), 4),
    }
