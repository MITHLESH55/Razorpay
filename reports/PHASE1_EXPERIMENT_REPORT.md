# RiskOrbit — Phase 1 Experiment Report

## Objective

Detect coordinated refund abuse among payment transactions using a
leakage-resistant ML pipeline trained on a synthetic payment ecosystem.

**Primary prediction target:** `abuse_label = 1` → transaction belongs to a
coordinated refund-abuse ring.

**NOT in scope:** chargeback fraud, account takeover, card theft, phishing.

---

## Dataset

- Temporal window: 2023-01-01 to 2024-12-31
- Customers: ~22,000
- Merchants: ~1,100
- Devices: ~13,000
- IP entities: ~9,000

## Abuse Patterns Injected

| Pattern | Description |
|---------|-------------|
| Pattern A (Shared Device) | Multiple accounts share devices, burst-refund same merchant |
| Pattern B (Cross-Merchant) | Related accounts target multiple merchants with similar amounts |
| Pattern C (Rotating Account) | New accounts appear over time linked by shared IP/instrument |

## Hard Negatives (Legitimate Confusers)

| Type | Purpose |
|------|---------|
| household_sharing | Legit device sharing within family |
| shared_network | Office/university IP sharing |
| high_refund_customer | Legitimate serial returner |
| high_volume_merchant | Legitimate high-refund-rate merchant |
| new_customer_high_value | Legit new customer, expensive purchase |
| multi_device_customer | Legit power user with many devices |

## Split Methodology

- **Algorithm:** Ring-aware group split + time-ordered legitimate split
- **Abuse rings:** Whole rings assigned to exactly one partition
- **Legitimate rows:** Sorted by timestamp, oldest 70% → train, next 15% → val, newest 15% → test
- **Ring leakage check:** Asserted ring_id sets are disjoint across all partitions

## Models Compared

| Model | Type |
|-------|------|
| RuleBaseline | 6 domain-intuition rules, transparent scoring |
| LogisticRegression | sklearn Pipeline with imputer + scaler + LR |
| LightGBM | Gradient-boosted trees, Tree SHAP explainability |

## Threshold Selection

- **Objective:** Maximize F1 subject to FPR ≤ 0.05
- **Selected threshold:** 0.3500
- **Selection partition:** Validation only (held-out test never used for tuning)
- **Threshold frozen:** YES

## Validation Results

_(see model_comparison.csv in reports/ for full comparison)_

## Held-Out Results (Final)

| Metric | Value |
|--------|------:|
| Precision | 0.3517 |
| Recall | 0.2862 |
| F1 | 0.3156 |
| FPR | 0.0054 |
| False-Positive Cost (synthetic) | ₹19,890.00 |

## Limitations

1. **Synthetic data ≠ production data.** Real fraud evolves adversarially; synthetic
   patterns are fixed by design. Performance will differ on real data.
2. **Pattern B and C FNs.** Cross-ring coordination requires Phase 2 graph features
   for full recall. Per-transaction aggregations are insufficient for cross-ring signals.
3. **No graph engine.** Phase 1 relationship features are simple aggregations. A full
   graph analysis (Phase 2) would improve recall on ring-level patterns.
4. **Hard negatives are known.** In production, new types of legitimate confusers
   will emerge that were not anticipated in generation.
5. **Cost model is synthetic.** Real intervention costs depend on actual Razorpay
   policy, which is not modeled here.

---

> Phase 1 complete. Phase 2 not implemented.