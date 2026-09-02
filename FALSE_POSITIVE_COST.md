# RiskOrbit — False-Positive Cost Model

## Disclaimer

> **All cost figures in this document are synthetic/modeled estimates.**
> They do NOT represent real Razorpay financial data, actual operating costs,
> real loss figures, or any proprietary Razorpay information.
> This model exists solely to reason about the economic trade-off between
> precision and recall in the context of a financial risk system.

---

## Purpose

The false-positive (FP) cost model translates the model's FPR metric into
a synthetic economic cost. This helps justify threshold selection decisions
by making the precision-recall trade-off concrete.

---

## Intervention Model

Phase 1 assumes a **soft-hold (flag for review)** intervention model.
The system DOES NOT automatically block transactions.
A flagged transaction is routed for human review.

This means:
- No legitimate transaction is blocked purely by the Phase 1 model
- The economic impact of an FP is: review friction + analyst cost
- There is NO foregone transaction revenue from blocking (Phase 1 only)

---

## Formula

```
FP_cost_per_event = friction_cost + review_cost + (avg_txn_value × block_rate)

Where:
  friction_cost  = customer friction cost per false-positive (INR)
  review_cost    = analyst review cost per case (INR)
  block_rate     = fraction of flagged transactions that get blocked (= 0.0 in Phase 1)

Total_FP_cost = n_false_positives × FP_cost_per_event
```

---

## Assumed Values & Sensitivity Tiers

| Cost Scenario | Friction Cost | Review Cost | Block Rate | Cost Per FP | Basis |
|---|---|---|---|---|---|
| **Low Friction Scenario** | ₹25 | ₹50 | 0.0 | **₹75.00** | Optimistic automation & minimal user drop-off |
| **Base Assumption Scenario** | ₹50 | ₹80 | 0.0 | **₹130.00** | Standard analyst review & mild user friction |
| **High Friction Scenario** | ₹100 | ₹150 | 0.0 | **₹250.00** | Intensive manual verification & high churn risk |

---

## Held-Out Operating Point Sensitivity (153 False Positives)

| Scenario | Cost / FP | Held-Out Total FP Cost (153 FPs) |
|---|---|---|
| **Low Friction** | ₹75.00 | **₹11,475.00** |
| **Base Assumption** | ₹130.00 | **₹19,890.00** |
| **High Friction** | ₹250.00 | **₹38,250.00** |

---

## Threshold Sensitivity

The cost-sensitivity analysis (`reports/cost_sensitivity.csv`) shows how
total FP cost varies with threshold across the validation set.
The selected threshold was chosen to maximize F1 subject to FPR ≤ 5%,
not to minimize FP cost alone.

---

## Limitations

1. **Synthetic costs**: All values are illustrative. Real costs depend on
   Razorpay's actual operational policies.
2. **No opportunity cost**: We do not model the cost of missed fraud
   (false negatives), which in a real system may be much larger.
3. **No customer lifetime value**: Repeatedly flagging a legitimate
   customer damages trust and future revenue — not modeled here.
4. **Phase 1 only**: In Phase 2 (autonomous intervention), the block_rate
   will be non-zero, making FP costs substantially higher and justifying
   even higher precision requirements.

---

## Units

All monetary values are in **Indian Rupees (INR)** and are **synthetic estimates**.
