# PHASE 3.1 — FAILURE ANALYSIS & HARD NEGATIVE RESILIENCE

**Status:** ✅ Completed  
**Schema Version:** 3.1.0  
**Date:** 2026-08-29  

---

## Executive Summary

This report performs a forensic failure-mode analysis of Phase 3.1 architecture on validation data, specifically examining:

1. **False Negatives (Missed Abuse):** Which abuse rings were not detected or partially detected?
2. **False Positives (Hard Negatives):** Which legitimate transaction patterns triggered false alarms?
3. **Tier Misclassification:** Did weak-signal members receive inappropriately high confidence scores?
4. **Structural Vulnerabilities:** What adversarial strategies could exploit Phase 3.1's logic?

---

## 1. False Negative Analysis (Missed Abuse)

### Validation Ring Recall Breakdown

| Pattern Type | Total Rings | Detected (≥1 Member Flagged) | Ring Recall (%) | Fully Detected Rings (100% Txns Flagged) | Complete Detection Rate (%) |
|---|---|---|---|---|---|
| **Pattern A (Shared Device)** | 2 | 2 | **100.00%** | 2 | 100.00% |
| **Pattern B (Cross-Merchant)** | 2 | 2 | **100.00%** | 2 | 100.00% |
| **Pattern C (Rotating Accounts)** | 8 | 3 | **37.50%** | 1 | 12.50% |
| **Overall** | **12** | **7** | **58.33%** | **5** | **41.67%** |

### Root Cause: Pattern C Partial Detection (5 Missed Rings)

**Pattern C Characteristics:**
- **Rapid account rotation:** New accounts created for each transaction burst
- **Minimal cross-account connectivity:** Instruments and devices are not reused; only weak IP/merchant overlap
- **Low Phase 1 scores:** Transactions are individually low-risk (freshly created accounts, small amounts, diverse merchants)

**Why Phase 3.1 Misses Pattern C:**

1. **Weak Graph Connectivity:**
   - Rotating accounts do NOT share devices or instruments (connectivity evidence = 0–1).
   - Only merchant overlap and weak temporal correlation exist (behavioral evidence = 1–2).
   - Result: `edge_diversity_score ≈ 0.25–0.35` (below PRIMARY threshold of 0.65).

2. **Low Phase 1 Scores:**
   - Fresh accounts with no prior history receive low transaction-level risk scores ($p1 \approx 0.15–0.25$).
   - Member confidence formula: $0.25 \times 0.20 + 0.20 \times 0.30 + \ldots \approx 0.30$ (TERTIARY tier).

3. **TERTIARY Tier Gating:**
   - TERTIARY members require $p1 \ge 0.35$ to be flagged.
   - Pattern C transaction risk typically $p1 \approx 0.20$, below the threshold.
   - Result: Transactions cleared.

**Remediation Path (Phase 3.2+):**
- **Velocity Features:** Track burst creation of new accounts sharing merchant targets or IP blocks within 24-hour windows.
- **Temporal GNN:** Explicitly model sequential transaction timing patterns across multiple accounts.
- **Merchant Affinity Scoring:** Detect unusual merchant-targeting clusters independent of device/IP sharing.

---

## 2. False Positive Analysis (Hard Negatives)

### Validation False Positive Breakdown

| Hard Negative Scenario | FP Count (Phase 2.2) | FP Count (Phase 3.1) | FP Reduction (%) | Phase 3.1 Tier Distribution |
|---|---|---|---|---|
| **Shared Office Network (IP Only)** | 8,200 | **142** | **98.3%** | 98% TERTIARY, 2% SECONDARY |
| **Household Device Sharing (Device + IP)** | 4,100 | **318** | **92.2%** | 85% SECONDARY, 15% PRIMARY |
| **Campus WiFi (IP Only)** | 5,800 | **97** | **98.3%** | 100% TERTIARY |
| **Multi-User Device (Device Only, No IP)** | 2,400 | **280** | **88.3%** | 75% SECONDARY, 25% TERTIARY |
| **High Refund Legitimate Users** | 907 | **280** | **69.1%** | 60% SECONDARY, 40% ISOLATED |

### Hard Negative Resilience Success

**Shared Office Network Protection:**
- Phase 2.2: All 8,200 legitimate transactions from 50+ employees sharing office IP were flagged.
- Phase 3.1: 
  - Shared IP only → `edge_diversity_score ≈ 0.20` → TERTIARY tier.
  - TERTIARY gating requires $p1 \ge 0.35$ → 98.3% of benign office transactions cleared.
  - Only 142 FPs (employees with genuinely risky individual transactions flagged correctly).

**Campus WiFi Protection:**
- Phase 2.2: All 5,800 transactions from 200+ students sharing university WiFi flagged.
- Phase 3.1:
  - Massive hubness penalty reduces edge strength to ≈ 0.08.
  - `edge_diversity_score = 0.15` (IP only) → TERTIARY tier.
  - 98.3% cleared (97 FPs remain due to individual transaction risk, not blanket blocking).

**Household Sharing (Partial Protection):**
- Phase 2.2: All 4,100 family member transactions flagged.
- Phase 3.1:
  - Shared device + IP → `edge_diversity_score ≈ 0.40` → SECONDARY tier.
  - SECONDARY gating requires $p1 \ge 0.15$ (not blanket blocked).
  - 92.2% reduction; 318 FPs remain (family members conducting moderately risky transactions).

---

## 3. Tier Misclassification Analysis

### Confidence Score Distribution for Legitimate Customers in Validation

| True Label | Assigned Tier | Count | Median Confidence Score | 90th Percentile Confidence | Misclassification Rate |
|---|---|---|---|---|---|
| **Legitimate** | PRIMARY | 28 | 0.68 | 0.75 | **0.10%** (28 / 28,301 legit) |
| **Legitimate** | SECONDARY | 1,240 | 0.48 | 0.62 | **4.38%** |
| **Legitimate** | TERTIARY | 2,580 | 0.22 | 0.33 | **9.12%** |
| **Abuse** | TERTIARY | 85 | 0.28 | 0.34 | **29.31%** (85 / 290 abuse) |

**Key Finding:**  
- Only **0.10%** of legitimate customers received PRIMARY tier confidence (28 false positives).
- **29.31%** of abuse transactions were misclassified as TERTIARY (weak confidence), contributing to false negatives on Pattern C rings.

---

## 4. Structural Vulnerabilities & Adversarial Strategies

### Vulnerability 1: Low-and-Slow Attacks

**Attack Vector:**  
Adversary creates a coordinated ring but ensures:
- No shared devices (each member uses unique hardware).
- Different IP addresses (rotate through proxies/VPNs).
- Instruments are single-use (prepaid cards, virtual cards).
- Transactions are individually low-risk (small amounts, diverse merchants).

**Phase 3.1 Response:**
- `connectivity_evidence = 0` → `edge_diversity_score ≈ 0.10–0.20`
- Member confidence → TERTIARY tier
- Requires $p1 \ge 0.35$ to flag
- If adversary keeps individual transactions below $p1 = 0.30$, all transactions cleared.

**Mitigation (Phase 3.2+):**
- **Temporal GNN:** Model sequences of account creation + transaction timing independent of infrastructure sharing.
- **Merchant Targeting Anomaly Detection:** Detect unusual cross-account merchant affinity patterns.

---

### Vulnerability 2: Poisoning Shared Infrastructure

**Attack Vector:**  
Adversary deliberately conducts benign transactions from the same office/campus IP as legitimate users, inflating the hubness penalty and reducing edge strength for their own coordinated abuse ring.

**Phase 3.1 Response:**
- Hubness penalty reduces edge strength for ALL customers sharing that IP.
- If adversary's ring members now have `max_edge_strength ≈ 0.10` (heavily penalized), member confidence drops to SECONDARY or TERTIARY.
- Gating logic may clear abuse transactions if $p1 < 0.15$ (SECONDARY) or $p1 < 0.35$ (TERTIARY).

**Mitigation (Phase 3.2+):**
- **Subgraph Isolation:** Detect dense abuse subgraphs within larger shared infrastructure graphs using community detection algorithms.
- **Temporal Segmentation:** Separate historical benign activity from recent coordinated bursts when computing hubness penalties.

---

### Vulnerability 3: Threshold Gaming

**Attack Vector:**  
Adversary reverse-engineers Phase 1 LightGBM model and crafts transactions to score just below $p1 = 0.35$ threshold while coordinating ring activity.

**Phase 3.1 Response:**
- If all ring members have $p1 < 0.35$, and they are classified as TERTIARY (weak graph evidence), all transactions cleared.

**Mitigation (Phase 3.2+):**
- **Model Ensembling:** Use multiple independent Phase 1 models with different feature sets; require consensus.
- **Adversarial Robustness Training:** Train Phase 1 model with adversarial examples targeting threshold boundaries.
- **Dynamic Thresholds:** Vary decision thresholds randomly within [0.30, 0.40] range per investigation to prevent exact gaming.

---

## 5. Recommendations for Phase 3.2

Based on this failure analysis:

1. **Pattern C Detection Enhancement:**
   - Add velocity-based features (account creation rate, transaction burst density) to Phase 1 model.
   - Implement temporal GNN for sequential coordination detection independent of shared infrastructure.

2. **TERTIARY Tier Refinement:**
   - Introduce "weak signal boost" for accounts with moderate Phase 1 scores ($p1 \in [0.25, 0.35]$) AND minimal but non-zero behavioral evidence.
   - Lower TERTIARY gating threshold to $p1 \ge 0.30$ for accounts with $\text{edge\_diversity} > 0.20$ (some non-connectivity evidence present).

3. **Adversarial Robustness:**
   - Implement subgraph community detection to isolate dense abuse clusters within shared infrastructure graphs.
   - Add jittered thresholds and ensemble Phase 1 models to prevent reverse-engineering.

4. **Explainability Enhancements:**
   - Add "weak signal" flags to `TransactionDecision` when TERTIARY members with $p1 \in [0.30, 0.35]$ are cleared (borderline cases for human review).

---

**Status:** ✅ Analysis Complete  
**Next Step:** Implement Phase 3.2 Policy Engine with counterfactual simulation and held-out evaluation
