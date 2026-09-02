# RiskOrbit — Phase 1 Initial Audit Report (Pre-Fix Baseline)

**Auditor Role:** Principal ML Engineer, Fintech Risk Engineer, Data Leakage Auditor  
**Date:** 2026-08-27  
**Artifact Status:** Phase 1 Hardening & Pre-Correction Assessment  

---

## Executive Summary

This initial audit report establishes the verified ground truth of the RiskOrbit Phase 1 codebase prior to hardening. We rigorously inspected the data generators, feature engineering pipelines, model training and thresholding scripts, evaluation suites, and test definitions.

The codebase provides a working baseline structure (clean modular code, FastAPI endpoint, reproducible random seeding, basic ring-leakage tests, and 43 passing pytest assertions). However, deep adversarial auditing revealed critical statistical, feature representation, evaluation, and operational gaps that must be addressed for a competition-grade fintech risk sentinel.

---

## A. Existing Architecture

The existing Phase 1 architecture comprises:
1. **Data Generation (`src/data_generation/`)**:
   - `entities.py`: Synthetic generator for customers, merchants, devices, IP entities, and instruments.
   - `legitimate_engine.py`: Baseline transaction simulator using customer segments and merchant categories with seasonal multipliers.
   - `hard_negatives.py`: Injects 6 confuser types (household sharing, shared networks, high-refund legitimate users, high-volume merchants, seasonal spikes, new customers with high value).
   - `abuse_engine.py`: Generates 3 coordinated refund abuse patterns:
     - Pattern A: Shared-device coordinated refund ring (60 rings).
     - Pattern B: Cross-merchant coordinated refund ring (50 rings).
     - Pattern C: Rotating-account refund ring (50 rings).
   - `ground_truth.py`: Merges entities and transactions, builds `generation_metadata/abuse_rings.csv`.
2. **Data Validation & Splitting (`src/validation/`)**:
   - `data_validator.py`: Integrity checks on types, bounds, uniqueness, and label balance.
   - `splitter.py`: Ring-aware time-ordered partitioner (70% train, 15% val, 15% test) ensuring no ring_id overlap across splits.
3. **Feature Engineering (`src/features/pipeline.py`)**:
   - Computes 36 canonical features across customer behavioral, velocity, device-level, IP-level, merchant-level, and transaction-level attributes.
   - Enforces a blacklist of forbidden columns (`_FORBIDDEN_COLUMNS`).
4. **Models & Baselines (`src/models/`)**:
   - `rule_baseline.py`: Transparent heuristic rule detector based on refund frequency, device sharing, and velocity thresholds.
   - `logistic_baseline.py`: Scaled L2-regularized Logistic Regression baseline.
   - `main_model.py`: LightGBM Classifier with Tree SHAP explainability.
5. **Evaluation & Cost Engine (`src/evaluation/`)**:
   - `cost_model.py`: False-positive cost model based on review cost (₹80) + customer friction cost (₹50) = ₹130 per FP.
   - `metrics.py`: Computes precision, recall, F1, PR-AUC, confusion matrix, and threshold selection on validation.
   - `error_analysis.py`: Breakdown of top false positives and false negatives.
6. **Inference API (`src/api/`)**:
   - `app.py` & `schema.py`: FastAPI service exposing `/health` and `POST /risk/score` with Pydantic contracts and SHAP top signal extraction.

---

## B. Existing Pipeline Execution Flow

```text
[configs/generation_config.yaml]
              │
              ▼
   [scripts/generate_data.py] ──> data/raw/ (transactions.csv, entities, abuse_rings.csv)
              │
              ▼
   [scripts/validate_data.py] ──> reports/DATA_QUALITY_REPORT.md
              │
              ▼
   [scripts/create_splits.py] ──> data/splits/ (train.csv, validation.csv, heldout_test.csv)
              │
              ▼
   [scripts/build_features.py] ──> data/processed/ (train_features.csv, val_features.csv)
              │
              ▼
   [scripts/train_models.py] ──> artifacts/riskorbit-risk-v1/ (model.pkl, threshold.json, etc.)
              │
              ▼
  [scripts/evaluate_heldout.py] ──> reports/HELDOUT_EVALUATION.md, reports/figures/
```

---

## C. Existing Tests Audit (43 Tests)

The 43 automated tests in `tests/` pass. Here is what they cover and what is NOT covered:

### Covered:
1. **`test_data.py` (22 tests)**:
   - Primary key uniqueness across 8 entities (customers, merchants, devices, IPs, instruments, orders, transactions, refunds).
   - Minimal row count checks (>50k txns, >10k customers, >5k refunds).
   - Temporal consistency (refund requested after transaction, refund processed after request).
   - Non-negative amounts.
   - Binary non-null `abuse_label` with reasonable prevalence [0.5%, 20%].
   - Ring ID disjointness between train/test and val/test splits.
   - Absence of explicit forbidden columns (`ring_generation_source`, `abuse_pattern_type`, `shared_devices`) in split CSVs.
2. **`test_features.py` (7 tests)**:
   - Feature count > 30.
   - Forbidden column exclusion in `FEATURE_COLUMNS` and output matrix.
   - Deterministic output on minimal mock DataFrames.
   - Finite numeric outputs and amount z-score clipping in [-10, 10].
3. **`test_evaluation.py` (6 tests)**:
   - Model metadata specifies threshold selected on validation.
   - `select_threshold` determinism.
   - Metric consistency ($F_1 = 2PR/(P+R)$) and confusion matrix summation.
   - Source code inspection ensuring `evaluate_heldout.py` does not call `save_artifact` or `.fit()`.
   - Positive FP cost in cost model.
4. **`test_models.py` (8 tests)**:
   - Artifact loading, threshold valid range (0, 1).
   - Existence of `threshold.json`, `feature_schema.json`, `model_metadata.json`.
   - Model prediction output valid in [0, 1].
   - Rule baseline produces binary outputs.
   - Pydantic schema validation for `ScoreResponse`.

### Gaps / NOT Covered in Existing Tests:
- **No Temporal Generalization Test**: No verification of performance over shifting time horizons (earlier vs latest window).
- **No Ring-Level Detection Metrics**: No tests verifying Ring Recall, Strong Ring Recall, or Ring Miss Rate.
- **No API vs Batch Equivalence Test**: No automated test ensuring `POST /risk/score` produces exact floating point parity with batch feature evaluation.
- **No Feature Availability / Rolling Window Causal Test**: No test checking that rolling statistics do not leak future intra-split events.
- **No Dataset Hash Fingerprinting**: No automated hash checking ensuring train/val/test data files remain unaltered.
- **No Resampling Protocol Guard**: No test checking that test sets are never resampled.

---

## D. Current Verified Metrics (Held-Out Test Set)

We verified the current metrics by executing `evaluate_heldout.py`:

| Metric | Measured Baseline Value |
|---|---|
| **Total Test Transactions** | 28,591 |
| **Abuse Transactions (Support)** | 290 (1.01% prevalence) |
| **Legitimate Transactions (Support)** | 28,301 |
| **Operating Threshold** | 0.3500 (selected on validation) |
| **Precision** | **0.3517** (35.17%) |
| **Recall** | **0.2862** (28.62%) |
| **F1-Score** | **0.3156** |
| **FPR** | **0.0054** (0.54%) |
| **True Positives (TP)** | 83 |
| **False Positives (FP)** | 153 |
| **False Negatives (FN)** | 207 |
| **True Negatives (TN)** | 28,148 |
| **Modeled Synthetic FP Cost** | ₹19,890.00 (@ ₹130/FP) |

### Breakdown by Abuse Pattern:
- **Pattern A (Shared Device)**: Recall = **0.0069** (Only 1 of 144 detected! 99.3% missed).
- **Pattern B (Cross-Merchant)**: Recall = **0.0455** (Only 2 of 44 detected! 95.5% missed).
- **Pattern C (Rotating Account)**: Recall = **0.7843** (80 of 102 detected).

---

## E. Potential Statistical Weaknesses

1. **Extreme Pattern A & B Blindness**: The current tabular model fails almost completely on Patterns A (0.69% recall) and B (4.55% recall). The overall 28.6% recall is almost solely driven by Pattern C.
2. **Global Rate Velocity Approximation vs Real Rolling Windows**: In `src/features/pipeline.py`, `_add_velocity_features` approximates 1h/6h/24h/7d velocities by dividing customer total refunds by total dataset time span (`ctx_span_hours`). This dilutes localized burst signals for coordinated attacks.
3. **Imbalance Calibration**: While LightGBM uses `is_unbalance=True`, the raw output probabilities are uncalibrated (isotonic or Platt scaling is absent).
4. **Lack of Controlled Feature Ablations**: No formal multi-tier ablation study exists to systematically attribute performance differences to behavioral, device/IP, relationship aggregate, and full feature sets.

---

## F. Potential Leakage Risks

1. **Intra-Partition Future Aggregation**: In `build_features`, static aggregations (`_customer_agg`, `_merchant_agg`) are computed across the entire partition rather than strictly causal event-by-event historical rollups.
2. **Context Window Strategy**: In test feature construction, `reference_transactions=train` prevents test-to-train leakage, but because test rings are disjoint from train rings, test ring entities have 0 prior transactions in `train`. If feature definitions only look at `train`, they cannot observe intra-test ring co-occurrences without a causal sliding event cache.

---

## G. Potential Data-Generator Weaknesses

1. **Pattern A Device Sharing Realism**: Pattern A rings use fixed shared devices among 3–8 accounts. However, in legitimate data, household sharing also shares devices. Without subtle velocity and cross-merchant concentration signals, the tabular model struggles to separate them.
2. **Pattern B IP Overlap**: Pattern B relies on shared IP across distinct accounts. In large ISP/residential pools, shared IP alone is noisy.
3. **Ground Truth Provenance**: While `abuse_rings.csv` stores generation parameters, individual transaction rows lack cryptographic provenance linking the injection rule to the generated record.

---

## H. Potential Model Weaknesses

1. **Rule Baseline Simplicity**: The rule baseline uses crude hardcoded cuts (`cust_refund_count >= 3 & accounts_per_device >= 2`) yielding low precision/recall.
2. **Single Tree Architecture**: Only LightGBM is benchmarked; no comparison against XGBoost or CatBoost is documented.
3. **No Explainability Validation**: Feature importances exist, but top SHAP signals are not systematically audited against ground truth injection causes.

---

## I. Potential Evaluation Weaknesses

1. **Absence of Ring-Level Metrics**: Evaluates only transaction-level precision/recall. If a ring has 8 transactions and the model detects 2, the ring may be stopped in production, but transaction recall looks like 25%. Ring-level metrics (Ring Recall, Strong Ring Recall, Complete Ring Detection) are missing.
2. **Single Static Split vs Temporal Drift Evaluation**: No time-based out-of-time evaluation assessing performance drift across sequential quarterly or seasonal periods.
3. **Cost Sensitivity Simplicity**: Cost model assumes static ₹130 without low/base/high friction sensitivity ranges.

---

## J. Missing Evidence Required for Competition-Grade Submission

1. Full Data Audit Report (`DATA_AUDIT.md` & `data_audit.json`).
2. Comprehensive Leakage Audit (`LEAKAGE_AUDIT_FINAL.md`).
3. Ground Truth Provenance Audit (`GROUND_TRUTH_AUDIT.md`).
4. Controlled 4-tier Feature Ablation Study (`FEATURE_ABLATION.md`).
5. Multi-Model Benchmark (`MODEL_COMPARISON.md` & `model_comparison.csv`).
6. Hard Negative Performance Benchmark (`HARD_NEGATIVE_REPORT.md`).
7. Full Diagnostic Error Analysis (`ERROR_ANALYSIS_FINAL.md`).
8. Dataset Cryptographic Fingerprints (`dataset_hashes.json`).
9. Expanded Comprehensive Test Suite (50+ tests covering API equivalence, dataset hashing, causal availability, and ring metrics).
10. Definitive Master Report (`PHASE1_FINAL_REPORT.md`).

---

## K. Recommended Step-by-Step Corrections Plan

1. **Step 1 — Deep Data & Ground Truth Audit**: Compute exact entity, transaction, refund, and hard-negative statistics; generate `reports/data_audit.json`, `reports/DATA_AUDIT.md`, and `reports/GROUND_TRUTH_AUDIT.md`.
2. **Step 2 — Feature Engineering & Causal Hardening**:
   - Refactor feature engineering in `src/features/pipeline.py` to support relationship features, co-occurrence density, cross-merchant entropy, device-velocity burstiness, and causal rolling aggregations.
   - Maintain strict leakage guard and produce `reports/LEAKAGE_AUDIT_FINAL.md`.
3. **Step 3 — Controlled Feature Ablation Study**:
   - Run Models A (Behavioral), B (+Device/IP), C (+Relationship Aggregates), and D (Full Engineered). Document in `reports/FEATURE_ABLATION.md`.
4. **Step 4 — Multi-Model & Calibration Hardening**:
   - Benchmark Rule Baseline, Logistic Regression, LightGBM (and alternative boosting candidate).
   - Perform probability calibration on validation and freeze deterministic threshold. Produce `reports/MODEL_COMPARISON.md`.
5. **Step 5 — Ring-Level & Temporal Generalization Metrics**:
   - Implement Ring Recall, Strong Ring Recall (>=50% members), Complete Ring Detection (100%), and Time-Based Generalization holdout.
6. **Step 6 — Hard Negatives & Cost Sensitivity**:
   - Produce `reports/HARD_NEGATIVE_REPORT.md` and detailed sensitivity analysis in `FALSE_POSITIVE_COST.md`.
7. **Step 7 — API Consistency & Reproducibility**:
   - Ensure `POST /risk/score` produces identical output to batch inference.
   - Implement dataset hashing (`dataset_hashes.json`).
8. **Step 8 — Expand Test Suite**:
   - Add new tests for API consistency, leakage guards, ring metrics, temporal splits, and hashing.
9. **Step 9 — Final Synthesis & Go/No-Go Decision**:
   - Compile `reports/PHASE1_FINAL_REPORT.md` and deliver the master completion report.
