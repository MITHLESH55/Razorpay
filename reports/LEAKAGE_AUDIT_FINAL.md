# RiskOrbit — Comprehensive Feature Availability & Leakage Audit (Final)

**Audit Date:** 2026-08-27  
**Auditor:** Data Leakage Auditor & Software Architect  
**Status:** PASSED (Zero Leakage Enforced)  

---

## 1. Feature Availability Matrix

Every candidate feature evaluated for the Phase 1 model has been audited against point-in-time scoring constraints:

| Feature Name | Feature Group | Available at Scoring $T$? | Uses Future Data? | Audit Decision | Rationale |
|---|---|---|---|---|---|
| `account_age_days` | Customer | Yes | No | **Allowed** | Recorded at customer registration timestamp ($T_{reg} \le T$). |
| `cust_txn_count` | Customer | Yes | No | **Allowed** | Prior transaction count strictly before $T$. |
| `cust_refund_count` | Customer | Yes | No | **Allowed** | Prior refund requests strictly before $T$. |
| `cust_refund_rate` | Customer | Yes | No | **Allowed** | Safe division of historical refunds / historical txns. |
| `cust_avg_txn_value` | Customer | Yes | No | **Allowed** | Mean of prior transactions before $T$. |
| `cust_median_txn_value` | Customer | Yes | No | **Allowed** | Median of prior transactions before $T$. |
| `cust_std_txn_value` | Customer | Yes | No | **Allowed** | Standard deviation of prior transactions before $T$. |
| `cust_device_count` | Customer | Yes | No | **Allowed** | Distinct devices associated with customer prior to $T$. |
| `cust_ip_count` | Customer | Yes | No | **Allowed** | Distinct IPs associated with customer prior to $T$. |
| `cust_merchant_count` | Customer | Yes | No | **Allowed** | Distinct merchants transacted with prior to $T$. |
| `cust_median_days_to_refund` | Customer | Yes | No | **Allowed** | Historical elapsed days between order and refund request. |
| `refund_velocity_1h` | Velocity | Yes | No | **Allowed** | Rolling window refund count in $[T - 1h, T)$. |
| `refund_velocity_6h` | Velocity | Yes | No | **Allowed** | Rolling window refund count in $[T - 6h, T)$. |
| `refund_velocity_24h` | Velocity | Yes | No | **Allowed** | Rolling window refund count in $[T - 24h, T)$. |
| `refund_velocity_7d` | Velocity | Yes | No | **Allowed** | Rolling window refund count in $[T - 7d, T)$. |
| `txn_velocity_24h` | Velocity | Yes | No | **Allowed** | Rolling window transaction count in $[T - 24h, T)$. |
| `txn_velocity_7d` | Velocity | Yes | No | **Allowed** | Rolling window transaction count in $[T - 7d, T)$. |
| `time_since_last_refund_hours` | Velocity | Yes | No | **Allowed** | Elapsed hours since most recent prior refund request. |
| `burstiness_24h` | Velocity | Yes | No | **Allowed** | Normalized ratio of 24h velocity to 7d velocity. |
| `accounts_per_device` | Device | Yes | No | **Allowed** | Distinct accounts observed on device up to $T$. |
| `txns_per_device` | Device | Yes | No | **Allowed** | Historical transactions on device up to $T$. |
| `refunds_per_device` | Device | Yes | No | **Allowed** | Historical refunds on device up to $T$. |
| `merchants_per_device` | Device | Yes | No | **Allowed** | Distinct merchants accessed on device up to $T$. |
| `accounts_per_ip` | IP | Yes | No | **Allowed** | Distinct accounts observed on IP up to $T$. |
| `txns_per_ip` | IP | Yes | No | **Allowed** | Historical transactions on IP up to $T$. |
| `refund_rate_per_ip` | IP | Yes | No | **Allowed** | Historical refund rate on IP up to $T$. |
| `merchants_per_ip` | IP | Yes | No | **Allowed** | Distinct merchants accessed on IP up to $T$. |
| `merchant_refund_rate` | Merchant | Yes | No | **Allowed** | Historical merchant baseline refund rate up to $T$. |
| `merchant_avg_order_value` | Merchant | Yes | No | **Allowed** | Historical average ticket size for merchant up to $T$. |
| `merchant_customer_concentration` | Merchant | Yes | No | **Allowed** | Top customer volume share for merchant up to $T$. |
| `merchant_recent_refund_rate_change` | Merchant | Yes | No | **Allowed** | 30-day refund rate minus all-time baseline rate up to $T$. |
| `amount` | Transaction | Yes | No | **Allowed** | Current transaction amount. |
| `amount_zscore_vs_cust` | Transaction | Yes | No | **Allowed** | Current amount standardized against customer history. |
| `amount_zscore_vs_merchant` | Transaction | Yes | No | **Allowed** | Current amount standardized against merchant history. |
| `is_first_txn_with_merchant` | Transaction | Yes | No | **Allowed** | Binary flag indicating no prior transaction with merchant. |
| `instrument_synthetic_age` | Instrument | Yes | No | **Allowed** | Instrument issuance age at $T$. |

---

## 2. Explicitly Rejected Candidate Features (Leakage Audit)

| Rejected Field | Rejection Category | Vulnerability / Failure Mode Prevented |
|---|---|---|
| `abuse_label` | **Direct Target Leakage** | Primary target variable. |
| `ring_id` | **Split / Target Leakage** | Synthetic cluster key; perfect shortcut to ring identity. |
| `abuse_pattern_type` | **Synthetic Metadata Leakage** | Generator pattern label (e.g. `pattern_a_shared_device`). |
| `ring_generation_source` | **Synthetic Metadata Leakage** | Internal generator provenance tag. |
| `generation_seed` | **Synthetic Metadata Leakage** | RNG state key used during simulation. |
| `ring_base_timestamp` | **Synthetic Metadata Leakage** | Injection anchor timestamp. |
| `shared_devices` | **Synthetic Metadata Leakage** | Pre-selected cluster device list. |
| `linking_ip` | **Synthetic Metadata Leakage** | Pre-selected cluster IP entity. |
| `linking_instrument` | **Synthetic Metadata Leakage** | Pre-selected cluster instrument family. |
| `ring_customer_ids` | **Synthetic Metadata Leakage** | Ring member enumeration list. |
| `ring_merchants` | **Synthetic Metadata Leakage** | Targeted merchant cluster roster. |
| `hard_negative_type` | **Evaluation Tag Leakage** | Ground-truth benchmarking category tag. |
| `final_chargeback_outcome` | **Post-Event Leakage** | Chargeback dispute results occurring 30–90 days post-transaction. |
| `post_investigation_decision`| **Post-Event Leakage** | Human analyst risk review decision occurring post-detection. |
| `future_refund_count` | **Temporal Leakage** | Refunds requested after scoring timestamp $T$. |
| `future_transactions` | **Temporal Leakage** | Transactions occurring after scoring timestamp $T$. |
| `refund_status` (final) | **Post-Event Leakage** | Completed/settled status timestamped after scoring moment. |

---

## 3. Defense-in-Depth Leakage Guard Enforcement

The feature pipeline enforces leakage prevention at three independent boundaries:
1. **Source Filtering**: `_FORBIDDEN_COLUMNS` frozenset automatically removes forbidden identifiers.
2. **Context Isolation**: Inference on validation and test sets strictly passes `reference_transactions=train` or causally historical event sets.
3. **Automated Assertion**: Feature generation raises a runtime `ValueError` if any forbidden column exists in the output schema.
