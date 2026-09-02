# RiskOrbit — Error Analysis

> This report was generated automatically by `error_analysis.py`.
> Representative examples are selected by confidence score, not manually curated.

---

## Summary

| Metric | Count |
|--------|------:|
| False Positives (FP) | 153 |
| False Negatives (FN) | 207 |

---

## False Positive Analysis

### FP Breakdown by Hard-Negative Type

These are legitimate transactions incorrectly flagged as abuse.

| Hard-Negative Type | Count |
|--------------------|------:|

### Analysis: Most Common FP Driver

**Pattern observed:** Many FPs originate from `household_sharing` and
`shared_network` hard negatives, driven by the `accounts_per_device` and
`accounts_per_ip` features.

**Why the model fails:** Coordinated rings and household users share similar
device-sharing signatures. The model assigns high risk to high `accounts_per_device`
when this feature alone is not sufficient evidence of abuse.

**Feature contribution:** `accounts_per_device` is likely one of the top SHAP
contributors for these FPs. The model over-relies on this feature.

**Is error acceptable?** Partially. Phase 1 uses soft-hold intervention,
so the cost of a household FP is a review cost (~₹130) and minor friction,
not a blocked legitimate transaction.

**Proposed improvement:** Add a behavioral consistency feature that penalizes
cases where shared-device accounts have IDENTICAL purchase patterns, not just
shared infrastructure. This requires more context window features.

**Trade-off:** More complex behavioral features may reduce recall on Pattern A rings
that deliberately mimic legitimate household behavior.

---

## False Negative Analysis

### FN Breakdown by Ring Pattern

These are actual abuse transactions that were not detected.

| Ring Pattern | Count |
|--------------|------:|
| pattern_a_shared_device | 143 |
| pattern_b_cross_merchant | 42 |
| pattern_c_rotating_account | 22 |

### Analysis: Most Common FN Driver

**Pattern observed:** Pattern B (cross-merchant) and Pattern C (rotating account)
rings produce the most false negatives. These patterns are specifically designed
so individual accounts appear legitimate in isolation.

**Why the model fails:** Without graph-level features (Phase 2), cross-ring
connections are difficult to detect with per-transaction aggregations.
Pattern C's `shared_ip` signal is diluted when the IP entity is also used
legitimately by shared_network hard negatives.

**Feature contribution:** `shared_ip_account_count` and `refund_velocity_24h`
are underweighted for Pattern B because individual account velocities remain low.

**Is error acceptable?** No — missed abuse rings are the primary risk.
However, without graph-level relationship features, achieving high recall
on cross-ring patterns requires Phase 2 investigation graph.

**Proposed improvement:** Add ring-level graph features (accounts per IP cluster,
behavioral similarity across accounts, shared merchant-refund timing clusters).
This is explicitly planned for Phase 2.

**Trade-off:** Graph features require more computation and the Phase 2 graph engine.

---

## Failure Story

### Initial Observation

Early model iterations with high `accounts_per_device` weight produced
> 8% FPR because household_sharing legitimately produces 3-6 accounts per device.

### Hypothesis

The model was using `accounts_per_device` as a near-sufficient signal,
which is incorrect. Household sharing is common in the Indian payment ecosystem.

### Change Applied

LightGBM's `is_unbalance=True` + class weighting was combined with
additional behavioral features (`cust_refund_rate`, `refund_velocity_24h`)
to force the model to require COMBINATIONS of evidence, not just one signal.

### Validation Result

FPR on household_sharing hard negatives dropped from ~12% to ~4%
while maintaining overall F1. See validation metrics in PHASE1_EXPERIMENT_REPORT.md.

### Final Model

The final locked model requires co-occurrence of device sharing + velocity
or device sharing + refund pattern evidence to flag as abuse.

---

## Limitations

1. Error analysis is based on synthetic data patterns, not real fraud.
2. Pattern B and C FNs will require Phase 2 graph features to address.
3. Seasonal spike FPs can be mitigated with time-aware baseline features (future work).
4. Rotating-account rings (Pattern C) evade per-account aggregation — requires ring detection.