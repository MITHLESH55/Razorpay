# RiskOrbit — Leakage Audit

## Purpose

This document records the leakage review for every candidate feature.
A feature is classified as:
- **allowed**: available at detection time, computed from prior events only
- **rejected_due_to_leakage**: contains information only available after detection
- **rejected_due_to_unavailability**: field does not exist at scoring time
- **rejected_due_to_post_event_information**: reflects future outcomes

---

## Ground Truth Fields (Never Features)

| Field | Classification | Reason |
|-------|---------------|--------|
| abuse_label | rejected_due_to_leakage | This IS the target. Using it as a feature would be perfect label leakage. |
| ring_id | rejected_due_to_leakage | Assigned during generation, not observable at scoring time. Used only for split logic. |
| hard_negative_type | rejected_due_to_leakage | Internal generation tag. Not observable at scoring time. |
| ring_generation_source | rejected_due_to_leakage | Generation metadata. Never visible at scoring time. |
| abuse_pattern_type | rejected_due_to_leakage | Generation metadata. Not observable at scoring time. |
| generation_seed | rejected_due_to_leakage | Internal generation parameter. |
| ring_base_timestamp | rejected_due_to_leakage | Internal ring generation timestamp. |
| shared_devices | rejected_due_to_leakage | Internal ring construction metadata. |
| ring_merchants | rejected_due_to_leakage | Internal ring construction metadata. |
| linking_ip | rejected_due_to_leakage | Internal ring construction metadata. |
| linking_instrument | rejected_due_to_leakage | Internal ring construction metadata. |
| ring_customer_ids | rejected_due_to_leakage | Internal ring member list. |

---

## Post-Event Fields (Rejected)

| Field | Classification | Reason |
|-------|---------------|--------|
| final_chargeback_outcome | rejected_due_to_post_event_information | Final chargeback determination only known months later. |
| future_refund_count | rejected_due_to_post_event_information | Future refunds not available at scoring time. |
| future_transactions | rejected_due_to_post_event_information | Future transactions not available at scoring time. |
| post_investigation_decision | rejected_due_to_post_event_information | Investigation outcome is a future event. |
| refund_status (final) | rejected_due_to_post_event_information | Only the refund_requested_at is observable at transaction scoring time; the final status may be set later. |

---

## Rolling Window Features (Allowed with Caveats)

All rolling window features are computed ONLY from events strictly BEFORE the 
scoring timestamp (`timestamp < scoring_ts`). This is enforced in `pipeline.py`
via the `_count_in_window()` helper which uses `df[ts_col] < reference_ts`.

| Feature | Classification | Window | Note |
|---------|---------------|--------|------|
| refund_velocity_1h | allowed | 1h prior | Uses refund_requested_at < scoring_ts |
| refund_velocity_6h | allowed | 6h prior | Same |
| refund_velocity_24h | allowed | 24h prior | Same |
| refund_velocity_7d | allowed | 7d prior | Same |
| txn_velocity_24h | allowed | 24h prior | Uses transaction timestamp < scoring_ts |
| txn_velocity_7d | allowed | 7d prior | Same |
| time_since_last_refund_hours | allowed | Point-in-time | Last refund before scoring_ts |

---

## Customer-Level Features (Allowed)

These aggregate historical behavior available at scoring time.

| Feature | Classification | Note |
|---------|---------------|------|
| account_age_days | allowed | Fixed at account creation. Observable at scoring. |
| cust_txn_count | allowed | Count of all transactions before scoring_ts |
| cust_refund_count | allowed | Count of all refunds before scoring_ts |
| cust_refund_rate | allowed | Derived from above two |
| cust_avg_txn_value | allowed | Historical average |
| cust_median_txn_value | allowed | Historical median |
| cust_std_txn_value | allowed | Historical std dev |
| cust_device_count | allowed | Distinct devices used before scoring_ts |
| cust_ip_count | allowed | Distinct IPs used before scoring_ts |
| cust_merchant_count | allowed | Distinct merchants before scoring_ts |
| cust_median_days_to_refund | allowed | Historical refund delay pattern |

---

## Device-Level Features (Allowed)

Note: These are simple aggregations, not graph features. Phase 2 will
replace these with richer graph-based relationship features.

| Feature | Classification | Note |
|---------|---------------|------|
| accounts_per_device | allowed | Distinct customers who used this device |
| txns_per_device | allowed | Transaction count on this device |
| refunds_per_device | allowed | Refund count associated with this device |
| merchants_per_device | allowed | Distinct merchants accessed from this device |

**Phase 2 note:** These will be enhanced by the investigation graph to include
temporal ordering, behavioral similarity scoring, and ring membership probability.

---

## IP-Level Features (Allowed)

| Feature | Classification | Note |
|---------|---------------|------|
| accounts_per_ip | allowed | Distinct customers sharing this IP entity |
| txns_per_ip | allowed | Transaction count from this IP entity |
| refund_rate_per_ip | allowed | Refund rate for transactions from this IP entity |
| merchants_per_ip | allowed | Distinct merchants accessed from this IP entity |

---

## Merchant-Level Features (Allowed)

| Feature | Classification | Note |
|---------|---------------|------|
| merchant_refund_rate | allowed | Historical refund rate for this merchant |
| merchant_avg_order_value | allowed | Historical average order value |
| merchant_customer_concentration | allowed | Fraction of txns from top customer |
| merchant_recent_refund_rate_change | allowed | Change in refund rate over last 30 days vs overall |

---

## Transaction-Level Features (Allowed)

| Feature | Classification | Note |
|---------|---------------|------|
| amount | allowed | Transaction amount, observable at scoring time |
| amount_zscore_vs_cust | allowed | Z-score relative to customer history |
| amount_zscore_vs_merchant | allowed | Z-score relative to merchant history |
| is_first_txn_with_merchant | allowed | Whether customer has transacted with this merchant before |
| instrument_synthetic_age | allowed | Synthetic age of the payment instrument |

---

## Summary

| Classification | Count |
|---------------|------:|
| Allowed features | 36 |
| Rejected (leakage) | 12 |
| Rejected (post-event) | 5 |

**Total rejected: 17 fields explicitly excluded from model training.**
