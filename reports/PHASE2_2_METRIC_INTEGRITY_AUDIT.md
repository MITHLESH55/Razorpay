# Phase 2.2 — Metric Integrity Audit Report
**Date:** 2026-08-27  
**Role:** Principal ML Evaluation Scientist & Adversarial Hackathon Reviewer  
**Audited Artifacts:** rtifacts/riskorbit-risk-v1/, 
eports/phase2_1_summary.json, 
eports/phase2_2_summary.json, 
eports/PHASE2_FINAL_REPORT.md, 
eports/PHASE2_1_FINAL_REPORT.md  

---

## 1. Executive Summary & Auditor Decision

### Decision:
> ## 🟡 METRIC DEFINITIONS DIFFER — RECONCILIATION REQUIRED

### Key Findings:
1. **The 0.40% FPR and ₹14,560 FP Cost did NOT belong to Phase 2.1.**  
   They belonged to **Phase 2.0 (Model E — 
iskorbit-risk-v2)**, a pure *per-transaction* supervised LightGBM classifier (36 tabular + 10 graph features at threshold 0.32) evaluated in scripts/evaluate_phase2.py.
2. **Phase 2.1 was an entirely different architecture.**  
   Phase 2.1 (scripts/evaluate_phase2_1.py) introduced the **Hybrid Candidate Discovery + Investigation Agent (K=1000)** architecture. In Phase 2.1, when the agent flagged a candidate, it marked that customer **plus all graph-expanded ring members** as positive. When mapped back to the transaction level in heldout_test.csv, these flagged entities matched **21,575 legitimate transactions**, giving an FPR of **76.23%** and FP Cost of **₹28,04,750**.
3. **The Phase 2.2 evaluation faithfully and precisely reproduced the Phase 2.1 baseline.**  
   The Phase 2.1 baseline recorded in phase2_2_summary.json (FPR = 76.23%, FP Cost = ₹28,04,750, TP = 128, FP = 21,575, FN = 162, TN = 6,726) is the exact, uncorrupted output of scripts/evaluate_phase2_1.py recorded in 
eports/phase2_1_summary.json.
4. **No mathematical or coding bug exists in the calculation.**  
   FPR = FP / (FP + TN) and FP Cost = FP * ₹130 are mathematically exact across all phases on the identical evaluation population (28,591 transactions: 28,301 legitimate, 290 abuse).
5. **The perceived discrepancy stems from comparing two fundamentally different operating paradigms:**
   - **Transaction-Level Point Classifier (Phase 1 & Phase 2.0):** Evaluates whether each individual transaction is fraudulent based purely on row features. (Low recall ~24-28%, low FPR ~0.4-0.5%).
   - **Entity-Level Ring Investigation Pipeline (Phase 2.1 & Phase 2.2):** Evaluates an investigation budget of K=1,000 entities, expanding to connected graph members and flagging all subsequent transactions of those accounts. (High ring recall ~62-79%, higher transaction footprint).

---

## 2. Exact Metric & Cost Formulas

### 2.1 Transaction-Level Confusion Matrix & FPR Definition
For ground truth {\text{true}} \in \{0, 1\}$ and system prediction $\hat{y} \in \{0, 1\}$ over the entire held-out transaction population:
\text{TP} = \sum (y_{\text{true}} = 1 \land \hat{y} = 1)
\text{FP} = \sum (y_{\text{true}} = 0 \land \hat{y} = 1)
\text{FN} = \sum (y_{\text{true}} = 1 \land \hat{y} = 0)
\text{TN} = \sum (y_{\text{true}} = 0 \land \hat{y} = 0)

\text{FPR} = \frac{\text{FP}}{\text{FP} + \text{TN}} = \frac{\text{FP}}{N_{\text{legitimate}}}

### 2.2 Exact FP Cost Formula
Per the declared business cost model (₹130 per false positive transaction review / friction):
\text{FP Cost} = \text{FP} \times ₹130

---

## 3. Evaluation Population & Denominator Audit

All evaluations are conducted on the exact, frozen data/splits/heldout_test.csv partition:

| Population Dimension | Count | Note |
|----------------------|------:|------|
| **Total Held-Out Transactions ({\text{total}}$)** | **28,591** | Complete test partition |
| **Ground-Truth Abuse Transactions ($)** | **290** | {\text{true}} = 1$ |
| **Ground-Truth Legitimate Transactions ($)** | **28,301** | {\text{true}} = 0$ (FPR Denominator $\text{FP} + \text{TN}$) |
| **Unique Total Customers** | **13,407** | Customer entities in test set |
| **Unique Abuse Customers** | **158** | Abuse entities in test set |
| **Unique Legitimate Customers** | **13,304** | Legitimate entities in test set |
| **Total Ground-Truth Abuse Rings** | **24** | 12 Pattern A, 4 Pattern B, 8 Pattern C |

---

## 4. Side-by-Side Confusion Matrix & Metric Reproduction

Using the exact same held-out population (28,591 transactions) and the standard transaction-level metric definitions:

| Metric | Phase 1 (Frozen Baseline) | Phase 2.0 (Model E ML Classifier) | Phase 2.1 (Frozen Hybrid Pipeline) | Phase 2.2 (Final Protected Pipeline) |
|---|:---:|:---:|:---:|:---:|
| **Architecture** | Tabular LightGBM | Tabular + Graph LightGBM | Hybrid Candidates + Agent (K=1000) | Protected Pool (P=150) + Agent (K=1000) |
| **Decision Level** | Per-Transaction (thr=0.35) | Per-Transaction (thr=0.32) | Entity Ring Traversal + Flagging | Entity Ring Traversal + Protected Pool |
| **True Positives (TP)** | 83 | 69 | 128 | **142** |
| **True Negatives (TN)** | 28,148 | 28,189 | 6,726 | **6,858** |
| **False Positives (FP)** | 153 | 112 | 21,575 | **21,443** |
| **False Negatives (FN)** | 207 | 221 | 162 | **148** |
| **Precision** | 35.17% | 38.12% | 0.59% | **0.66%** |
| **Recall (Txn)** | 28.62% | 23.79% | 44.14% | **48.97%** |
| **F1 Score** | 0.3156 | 0.2930 | 0.0116 | **0.0130** |
| **FPR (Txn-Level)** | 0.54% | **0.40%** | **76.23%** | **75.77%** |
| **FP Cost (₹130/FP)** | ₹19,890 | **₹14,560** | **₹28,04,750** | **₹27,87,590** |
| **Pattern A Recall** | 0.69% | N/A | 91.67% | **100.00%** |
| **Pattern B Recall** | 4.55% | N/A | 100.00% | **100.00%** |
| **Pattern C Recall** | 78.43% | N/A | 0.00% | **37.50%** |
| **Overall Ring Recall** | 45.83% | 37.50% | 62.50% | **79.17%** |

---

## 5. In-Depth Discrepancy Breakdown

### 5.1 Why 0.40% Became 76.23%
1. **The 0.40% Number:**
   - Origin: 
eports/PHASE2_FINAL_REPORT.md (Phase 2.0).
   - Generated by: scripts/evaluate_phase2.py evaluating rtifacts/riskorbit-risk-v2/ (Model E).
   - Mechanism: A standard supervised tree model scored each test transaction independently. Transactions scoring $\ge 0.32$ were flagged. It flagged only **181 transactions total** (69 TP + 112 FP).
   - Calculation: $\text{FPR} = 112 / 28,301 = 0.3957\% \approx 0.40\%$.
2. **The 76.23% Number:**
   - Origin: 
eports/phase2_1_summary.json and 
eports/PHASE2_1_FINAL_REPORT.md (Phase 2.1).
   - Generated by: scripts/evaluate_phase2_1.py.
   - Mechanism: The unsupervised candidate generator generated 12,488 graph candidates from connected entities in data/splits/heldout_test.csv. The top K=1000 candidates were investigated. For flagged candidates, the agent performed 2-hop graph traversal in the historical transaction graph, expanding the ring to all co-connected customer accounts (case_resp.member_accounts).
   - All transactions belonging to any flagged or member customer were marked positive (hybrid_pred = 1).
   - Because 2-hop graph expansion traversed dense shared-infrastructure components (e.g. shared IPs/devices from large multi-customer networks), the flagged account set covered **21,575 legitimate transactions**.
   - Calculation: $\text{FPR} = 21,575 / 28,301 = 76.2348\% \approx 76.23\%$.

### 5.2 Why ₹14,560 Became ₹28,04,750
- In Phase 2.0: $\text{FP} = 112 \implies 112 \times ₹130 = ₹14,560$.
- In Phase 2.1: $\text{FP} = 21,575 \implies 21,575 \times ₹130 = ₹28,04,750$.
- In Phase 2.2: $\text{FP} = 21,443 \implies 21,443 \times ₹130 = ₹27,87,590$ (a net reduction of 132 FP transactions vs Phase 2.1).
- The arithmetic $\text{FP} \times 130$ is 100% exact in all cases.

---

## 6. Disentangling Transaction-Level vs Ring-Level vs Candidate-Level Metrics

To prevent future confusion, RiskOrbit metrics operate at three distinct conceptual levels:

| Level | Definition | Denominator | Phase 2.2 Result | Meaning |
|---|---|---|:---:|---|
| **Ring-Level (Detection)** | Fraction of ground-truth fraud syndicates discovered | 24 Rings (12 A, 4 B, 8 C) | **79.17% (19/24)** | Core fraud ring defense capability |
| **Candidate-Level (Ranking)** | Fraction of legitimate customers placed in investigation budget | 13,304 Legit Customers | **7.41% (988/13304)** | Quality of ranking & budget allocation |
| **Transaction-Level (Operation)** | Fraction of legitimate transactions flagged after ring expansion | 28,301 Legit Transactions | **75.77% (21443/28301)** | Impact of broad account-level ring blocking |

---

## 7. Conclusions & Strategic Recommendation

1. **Integrity Verified:** There is no bug or calculation error. Phase 2.2 did not introduce a sudden spike in FPR; it directly inherited and slightly improved upon Phase 2.1's transaction footprint (76.23% -> 75.77%) while surging Ring Recall from 62.50% to 79.17% and Pattern C from 0.00% to 37.50%.
2. **Defensive Documentation:** In reports, explicitly clarify that **Phase 2.0 (Model E)** was a pure transaction scoring model (FPR 0.40%), whereas **Phase 2.1 & Phase 2.2** are hybrid entity-investigation pipelines where ring expansion impacts account-level transaction volumes.
3. **Phase 3 Path Forward:** When transitioning to production / Phase 3, the account-level ring-expansion policy should apply confidence weighting (e.g. only blocking transactions above a combined risk threshold rather than blanket-flagging all 2-hop connected accounts) to dramatically lower transaction-level FPR while preserving 79.17% ring recall.
