# RiskOrbit — Data Dictionary

## Overview

All data is **100% synthetic**. No real customer data, real payment credentials,
real card numbers, real CVVs, real bank account numbers, or real OTPs exist anywhere
in this repository.

Entity identifiers are randomly generated tokens (e.g., `CUS_12345678`).
IP entities are synthetic anonymized identifiers (e.g., `IP_87654321`) — no actual
IP addresses are stored or inferred.

---

## Entities

### customers.csv

| Column | Type | Description |
|--------|------|-------------|
| customer_id | string | Synthetic customer identifier (e.g., CUS_12345678) |
| account_created_at | datetime | Timestamp of account creation |
| account_age_days | int | Days since account creation (relative to dataset end_date) |
| home_region | string | Synthetic region (north/south/east/west/central) |
| customer_segment | string | casual / regular / power_user / enterprise |
| normal_device_count | int | Expected number of devices for this customer |
| normal_merchant_count | int | Expected number of merchants for this customer |

### merchants.csv

| Column | Type | Description |
|--------|------|-------------|
| merchant_id | string | Synthetic merchant identifier |
| merchant_category | string | electronics / fashion / grocery / travel / food_delivery / services / gaming |
| merchant_region | string | Geographic region |
| baseline_transaction_volume | int | Expected monthly transaction count |
| baseline_refund_rate | float | Natural refund rate for this merchant (0–1) |
| average_order_value | float | Expected average order value (INR, synthetic) |

### devices.csv

| Column | Type | Description |
|--------|------|-------------|
| device_id | string | Synthetic device fingerprint token |
| first_seen_at | datetime | First observed timestamp |
| device_type | string | mobile_android / mobile_ios / desktop_windows / desktop_mac / tablet_* |
| device_age_days | int | Days since first seen |

### ip_entities.csv

| Column | Type | Description |
|--------|------|-------------|
| ip_id | string | Synthetic IP entity identifier — NOT an actual IP address |
| region | string | Synthetic region |
| ip_type | string | residential / corporate / mobile_carrier / shared_broadband / vpn_proxy / datacenter |
| first_seen_at | datetime | First observed timestamp |

**IMPORTANT:** No actual IP addresses are stored. `ip_id` is a random synthetic token.

### instruments.csv

| Column | Type | Description |
|--------|------|-------------|
| instrument_id | string | Synthetic payment instrument token |
| instrument_type | string | upi / credit_card / debit_card / net_banking / wallet / bnpl |
| synthetic_age | int | Days since first use (synthetic) |

**IMPORTANT:** No real card numbers, CVVs, bank credentials, OTPs, or payment
secrets of any kind are generated or stored.

---

## Events

### orders.csv

| Column | Type | Description |
|--------|------|-------------|
| order_id | string | Synthetic order identifier |
| customer_id | string | Reference to customers.csv |
| merchant_id | string | Reference to merchants.csv |
| created_at | datetime | Order creation timestamp |
| amount | float | Order amount (INR, synthetic) |
| product_category | string | Product category |
| delivery_region | string | Delivery destination region |
| abuse_label | int | 0=legitimate, 1=coordinated refund abuse |
| ring_id | string | Abuse ring identifier (empty for legitimate rows) |
| hard_negative_type | string | Hard-negative category (analysis only, not a model feature) |

### transactions.csv

| Column | Type | Description |
|--------|------|-------------|
| transaction_id | string | Synthetic transaction identifier |
| order_id | string | Reference to orders.csv |
| customer_id | string | Reference to customers.csv |
| merchant_id | string | Reference to merchants.csv |
| device_id | string | Reference to devices.csv (nullable) |
| ip_id | string | Reference to ip_entities.csv (nullable) |
| instrument_id | string | Reference to instruments.csv (nullable) |
| timestamp | datetime | Payment timestamp |
| amount | float | Transaction amount (INR, synthetic) |
| payment_method | string | upi / credit_card / debit_card / net_banking / wallet |
| payment_status | string | captured / failed |
| abuse_label | int | **Primary prediction target.** 0=legitimate, 1=coordinated abuse |
| ring_id | string | **Split key only. NOT a model feature.** |
| hard_negative_type | string | **Analysis only. NOT a model feature.** |

### refunds.csv

| Column | Type | Description |
|--------|------|-------------|
| refund_id | string | Synthetic refund identifier |
| transaction_id | string | Reference to transactions.csv |
| refund_requested_at | datetime | When refund was requested |
| refund_processed_at | datetime | When refund was processed |
| refund_amount | float | Amount refunded (INR, synthetic) |
| refund_reason | string | item_not_received / item_damaged / wrong_item / changed_mind / duplicate_order / quality_issue / delivery_delay |
| refund_status | string | completed |
| abuse_label | int | 0=legitimate, 1=associated with abuse ring |
| ring_id | string | Abuse ring identifier |
| hard_negative_type | string | Analysis only |

---

## Generation Metadata (INTERNAL ONLY)

### data/raw/generation_metadata/abuse_rings.csv

| Column | Type | Description |
|--------|------|-------------|
| ring_id | string | Abuse ring identifier |
| abuse_pattern_type | string | pattern_a_shared_device / pattern_b_cross_merchant / pattern_c_rotating_account |
| n_accounts | int | Number of accounts in this ring |
| generation_seed | int | Internal seed for reproducibility |

**CRITICAL:** This file and all columns in it MUST NEVER be merged into the
model feature matrix. It exists solely for split logic and post-hoc analysis.

---

## Label Definitions

### abuse_label
- `0`: Legitimate/non-abusive transaction
- `1`: Transaction associated with a coordinated refund abuse ring

### ring_id
- Non-empty string: the ring this transaction belongs to
- Empty string: not part of an abuse ring

**ring_id is used as a split key (to prevent ring leakage) but is
explicitly excluded from the model feature set.**

### hard_negative_type
- Identifies legitimate transactions that resemble abuse
- Values: household_sharing, shared_network, high_refund_customer,
  high_volume_merchant, new_customer_high_value, multi_device_customer
- Empty string: ordinary legitimate transaction

**hard_negative_type is used for error analysis only and is NEVER
a model input.**

---

## Out-of-Scope Fraud Types

The following fraud types are explicitly NOT in scope for this dataset:
- Chargeback fraud
- Account takeover (ATO)
- Card theft / stolen credentials
- Phishing
- Payment failure exploitation
- Cyberattack detection

The model classifies ONLY coordinated refund abuse.
