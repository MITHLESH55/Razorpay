# RiskOrbit — Phase 3.2: Hard Negative Evaluation Report

**Status:** Complete  
**Evaluation Scope:** Validation Partition (`data/splits/validation.csv`)  
**Total Hard Negative Transactions Evaluated:** 13,406 transactions  
**Date:** 2026-08-31  

---

## 1. Executive Summary

A critical failure mode of graph-based fraud detection systems is the collateral damage inflicted on legitimate users who share entities (IPs, devices, merchants) with high transaction volumes or high-velocity behavioral patterns.

In this evaluation, we measure the resilience of **Policy D (Phase 3.2 Tiered Response)** across 13,406 hard negative transactions against **Policy A (Point Model)**, **Policy B (Blanket Expansion)**, and **Policy C (Binary Gating)**.

---

## 2. Hard Negative Cohort Breakdown

| Hard Negative Cohort | Description | Transaction Count in Validation |
|---|---|---|
| **Household Sharing** | Family members sharing residential IP / devices | 879 |
| **Shared Network / Campus WiFi** | Unrelated users on enterprise/campus network | 1,174 |
| **High-Refund Legitimate Users** | Legitimate e-commerce shoppers with frequent returns | 1,149 |
| **Multi-Device Legitimate Users** | Power users transacting across multiple personal phones/laptops | 645 |
| **High-Volume Merchants** | Marketplace merchants with thousands of concurrent buyers | 9,559 |
| **Total Hard Negative Cohort** | — | **13,406** |

---

## 3. Policy Comparison on Hard Negatives

### 3.1 Hard Block Count & Block Rate

| Cohort | Transactions | Policy A Blocks | Policy B Blocks | Policy C Blocks | Policy D (Phase 3.2) Blocks | Policy D Hard Block Rate |
|---|---|---|---|---|---|---|
| **Household Sharing** | 879 | 0 (0.0%) | 11 (1.25%) | 0 (0.0%) | **0 (0.0%)** | **0.0%** |
| **Shared Network** | 1,174 | 0 (0.0%) | 5 (0.43%) | 0 (0.0%) | **0 (0.0%)** | **0.0%** |
| **High-Refund Customer** | 1,149 | 0 (0.0%) | 5 (0.44%) | 5 (0.44%) | **0 (0.0%)** | **0.0%** |
| **Multi-Device Customer** | 645 | 0 (0.0%) | 2 (0.31%) | 2 (0.31%) | **0 (0.0%)** | **0.0%** |
| **High-Volume Merchant** | 9,559 | 0 (0.0%) | 53 (0.55%) | 10 (0.10%) | **0 (0.0%)** | **0.0%** |
| **Total Hard Negatives** | **13,406** | **0 (0.0%)** | **76 (0.57%)** | **17 (0.13%)** | **0 (0.0%)** | **0.0%** |

### 3.2 False Positive Friction Cost (₹)

| Cohort | Policy A Cost (₹) | Policy B Cost (₹) | Policy C Cost (₹) | Policy D Cost (₹) | Cost Savings vs Policy B (₹) |
|---|---|---|---|---|---|
| **Household Sharing** | ₹0.00 | ₹1,430.00 | ₹0.00 | **₹0.00** | +₹1,430.00 |
| **Shared Network** | ₹0.00 | ₹650.00 | ₹0.00 | **₹0.00** | +₹650.00 |
| **High-Refund Customer** | ₹0.00 | ₹650.00 | ₹650.00 | **₹0.00** | +₹650.00 |
| **Multi-Device Customer** | ₹0.00 | ₹260.00 | ₹260.00 | **₹0.00** | +₹260.00 |
| **High-Volume Merchant** | ₹0.00 | ₹6,890.00 | ₹1,300.00 | **₹0.00** | +₹6,890.00 |
| **Total Friction Cost** | **₹0.00** | **₹9,880.00** | **₹2,210.00** | **₹0.00** | **+₹9,880.00 (100% Elimination)** |

---

## 4. Action Mix Distribution Under Policy D

Across all 13,406 hard negative transactions evaluated under Phase 3.2:
- **ALLOW:** 13,406 transactions (**100.0%**)
- **STEP_UP_2FA:** 0 transactions (0.0%)
- **DELAY_SETTLEMENT:** 0 transactions (0.0%)
- **MANUAL_REVIEW:** 0 transactions (0.0%)
- **BLOCK_TRANSACTION:** 0 transactions (0.0%)
- **RESTRICT_ACCOUNT:** 0 transactions (0.0%)
- **FREEZE_RING:** 0 transactions (0.0%)

---

## 5. Architectural Why: Why Phase 3.2 Succeeded on Hard Negatives

1. **Edge Diversity Gating:** In shared-entity environments (e.g. 100 users sharing one IP or merchant), the edge diversity score drops to near zero because connections are concentrated on a single generic relation. This prevents high confidence tier elevation.
2. **Decoupled Risk Scoring:** Legitimate users with high refund behavior have low individual fraud scores ($p_1 < 0.20$), which automatically prevents them from triggering the $p_1 \ge 0.35$ block thresholds.
3. **Tertiary Protection Rule:** Even if a household member shares an IP with a suspicious device, they are placed in `TERTIARY` tier and shielded from hard blocks unless they possess strong independent fraud signals.
