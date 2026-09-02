# RiskOrbit — Phase 3.2: Economic Utility & Cost Modeling Report

**Status:** Complete  
**Evaluation Scope:** Validation Dataset Only (`data/splits/validation.csv`)  
**Held-Out Test Set:** LOCKED & UNTOUCHED  
**Date:** 2026-08-31  

---

## 1. Executive Summary

This report provides the economic utility and cost-benefit evaluation of the Phase 3.2 Decisioning Architecture. 

### Critical Methodological Distinction:
We explicitly distinguish between:
1. **Observed Synthetic Loss:** Ground-truth monetary amount associated with synthetic abuse transactions ($y_i = 1$) in the validation partition.
2. **Modeled Loss Prevention:** Estimated losses prevented based on action-specific prevention efficacy ($\kappa_{\text{fraud}}$).
3. **Assumed Friction Cost:** Unit operational friction penalty ($c_{\text{friction}}$) incurred when a benign customer ($y_i = 0$) encounters an intervention.
4. **Assumed Pass Rate:** Modeled completion probability for legitimate and fraudulent users under stepped-up verification.

---

## 2. Explicit Economic Assumptions

| Action Type | Scope | Assumed Legit Pass-Rate ($\rho_{\text{legit}}$) | Assumed Fraud Block-Rate ($\kappa_{\text{fraud}}$) | Assumed Benign Friction Cost ($c_{\text{friction}}$) | Assumed Analyst Review Cost ($c_{\text{review}}$) |
|---|---|---|---|---|---|
| **ALLOW** | Transaction | 100.0% | 0.0% | ₹0.00 | ₹0.00 |
| **STEP_UP_2FA** | Transaction | 96.0% | 85.0% | ₹15.00 | ₹0.00 |
| **DELAY_SETTLEMENT** | Transaction | 100.0% | 90.0% | ₹30.00 | ₹0.00 |
| **MANUAL_REVIEW** | Transaction | 98.0% | 98.0% | ₹20.00 | ₹130.00 |
| **BLOCK_TRANSACTION** | Transaction | 0.0% | 100.0% | ₹130.00 | ₹0.00 |
| **RESTRICT_ACCOUNT** | Account | 0.0% | 100.0% | ₹350.00 | ₹130.00 |
| **FREEZE_RING** | Ring | 0.0% | 100.0% | ₹1,000.00 | ₹500.00 |

### Mathematical Accounting Identities:
1. $\text{Gross Abuse Volume} = \sum_{i \in \text{Abuse}} \text{Amount}_i = \text{Gross Prevented} + \text{Uncaught Loss}$
2. $\text{Gross Losses Prevented} = \sum_{i \in \text{Abuse}} \kappa_{\text{fraud}}(a_i) \cdot \text{Amount}_i$
3. $\text{Benign Friction Cost} = \sum_{i \in \text{Benign}} c_{\text{friction}}(a_i)$
4. $\text{Analyst Review Cost} = \sum_{i} c_{\text{review}}(a_i) \cdot \mathbb{I}(\text{Human Review Required})$
5. $\text{Total Operational Cost} = \text{Benign Friction Cost} + \text{Analyst Review Cost}$
6. $\text{Net Economic Utility} = \text{Gross Losses Prevented} - \text{Total Operational Cost}$

---

## 3. Counterfactual Economic Outcomes (Validation Partition)

| Policy Paradigm | Gross Abuse Volume (₹) | Estimated Prevented Loss (₹) | Uncaught Abuse Loss (₹) | Benign Friction Cost (₹) | Analyst Review Cost (₹) | Total Op Cost (₹) | Net Economic Utility (₹) |
|---|---|---|---|---|---|---|---|
| **NO ACTION** | ₹1,183,999.71 | ₹0.00 | ₹1,183,999.71 | ₹0.00 | ₹0.00 | ₹0.00 | **₹0.00** |
| **Policy A (Point Model)** | ₹1,183,999.71 | ₹314,402.70 | ₹869,597.01 | ₹20,670.00 | ₹0.00 | ₹20,670.00 | **₹293,732.70** |
| **Policy B (Blanket Exp)** | ₹1,183,999.71 | ₹1,183,999.71 | ₹0.00 | ₹38,740.00 | ₹0.00 | ₹38,740.00 | **₹1,145,259.71** |
| **Policy C (Binary Gate)** | ₹1,183,999.71 | ₹174,351.60 | ₹1,009,648.11 | ₹25,090.00 | ₹0.00 | ₹25,090.00 | **₹149,261.60** |
| **Policy D (Phase 3.2)** | ₹1,183,999.71 | ₹87,913.87 | ₹1,096,085.84 | ₹4,590.00 | ₹390.00 | ₹4,980.00 | **₹82,933.87** |

---

## 4. Cost Sensitivity & Robustness Sweeps

We tested Policy D economic utility across varying operational cost regimes:
- **2FA Challenge Friction ($c_{\text{2FA}}$):** ₹10, ₹15, ₹20
- **Hard Block Friction ($c_{\text{block}}$):** ₹100, ₹130, ₹160
- **Analyst Review Cost ($c_{\text{review}}$):** ₹100, ₹130, ₹160

| Cost Regime | $c_{\text{2FA}}$ (₹) | $c_{\text{block}}$ (₹) | $c_{\text{review}}$ (₹) | Policy A Net Utility (₹) | Policy D Net Utility (₹) | Policy D Op Cost (₹) |
|---|---|---|---|---|---|---|
| **Low Operational Cost** | ₹10.00 | ₹100.00 | ₹100.00 | ₹298,502.70 | ₹84,243.87 | ₹3,670.00 |
| **Baseline Standard** | **₹15.00** | **₹130.00** | **₹130.00** | **₹293,732.70** | **₹82,933.87** | **₹4,980.00** |
| **High Operational Cost**| ₹20.00 | ₹160.00 | ₹160.00 | ₹288,962.70 | ₹81,623.87 | ₹6,290.00 |

### Sensitivity Insights:
1. **Friction Insensitivity:** Because Policy D limits hard blocks to just 30 transactions, its net utility varies by only $\pm 1.6\%$ even when unit operational costs swing by $\pm 30\%$.
2. **Operational Expense Cap:** Total operational expense for Policy D remains under ₹6,300 across all 28,581 transactions under high-cost assumptions.
