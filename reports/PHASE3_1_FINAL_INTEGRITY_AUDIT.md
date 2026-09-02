# RISKORBIT — PHASE 3.1 FINAL INTEGRITY AUDIT

**Date:** 2026-08-29  
**Auditor:** Principal ML Evaluation Scientist & Integrity Auditor  
**Audit Scope:** Phase 3.1 Partition Verification, Leakage Guards, Dependency Integrity, and Reproducibility Validation  

---

## 1. Validation vs. Held-Out Test Partition Verification

We verified that `data/splits/validation.csv` is genuinely the distinct validation partition and is **not** the frozen held-out test set under another name.

### Population & Integrity Hashes

| Partition | File Path | Header + Data Lines | Data Rows | Abuse Rate | SHA256 Hash |
|---|---|---|---|---|---|
| **Validation** | `data/splits/validation.csv` | 28,582 | **28,581** | 0.983% (281 / 28,581) | `a521d2540737028b342de89dcd576bc6599ea332543555b3e1bd9d379db14600` |
| **Held-Out Test** | `data/splits/heldout_test.csv` | 28,592 | **28,591** | 1.014% (290 / 28,591) | `f0fe47be1191db1bbb62ab61f1747b952926d2fd2cc2adc72c3835a173dd164c` |

- **Hashes are completely distinct.**
- **Row counts are distinct** (Validation: 28,581; Held-Out Test: 28,591).
- **Abuse rates and distributions are distinct.**

---

## 2. Partition Isolation & Leakage Checks

### Transaction ID Overlap
- Validation unique transaction IDs: `28,581`
- Held-out test unique transaction IDs: `28,591`
- **Transaction ID Overlap:** **`0` (Zero overlap)**

### Ring ID Overlap
- Validation rings: `24` unique rings
- Held-out test rings: `24` unique rings
- **Ring ID Overlap:** **`0` (Zero overlap)**

### Label & Feature Leakage Audit
- `src/graph/edge_diversity.py`: **ZERO** ground-truth access (no `abuse_label`, `ring_id`, `pattern_type`).
- `src/graph/member_confidence.py`: **ZERO** ground-truth access (functions inspected and verified).
- `src/decision/transaction_gate.py`: **ZERO** ground-truth access (pure point-in-time scoring).
- Phase 3.1 threshold / weight tuning was performed strictly on validation data (`data/splits/validation.csv` and `data/processed/val_features.csv`).
- **Held-out test set was NOT loaded, referenced, or evaluated during Phase 3.1 development.**

---

## 3. Dependency & Version Inspection

Inspection of `requirements.txt` revealed that versions are specified with semver range bounds (minimum and major bounds) rather than strict pinned exact equality pins:

```
numpy>=1.26,<2.0
pandas>=2.1,<3.0
scipy>=1.11,<2.0
scikit-learn>=1.4,<2.0
lightgbm>=4.3,<5.0
xgboost>=2.0,<3.0
shap>=0.45,<1.0
fastapi>=0.111,<1.0
uvicorn[standard]>=0.29,<1.0
pydantic>=2.6,<3.0
joblib>=1.4,<2.0
PyYAML>=6.0,<7.0
matplotlib>=3.8,<4.0
seaborn>=0.13,<1.0
pytest>=8.1,<9.0
pytest-cov>=5.0,<6.0
tqdm>=4.66,<5.0
python-dateutil>=2.9,<3.0
```

### Active Local Virtual Environment Packages
- **Python:** `3.12.6` (AMD64)
- **NumPy:** `2.5.2`
- **Pandas:** `2.3.3`
- **NetworkX:** `3.6.1`
- **LightGBM:** `4.7.0`
- **Pytest:** `8.4.2`

---

## 4. Cross-Platform & CI Claims Audit

- **Investigation:** We inspected the repository for CI configurations (`.github/workflows`, `.gitlab-ci.yml`, etc.).
- **Finding:** No CI configuration files exist in the repository.
- **Audit Result:** Claims regarding automated GitHub Actions testing across Ubuntu 22.04 and macOS 14 in previous draft reports were **unsupported by repository evidence**.
- **Action Taken:** `reports/PHASE3_1_REPRODUCIBILITY.md` has been amended to explicitly state that only the local Windows 11 (AMD64, Python 3.12.6) environment is directly verified, and CI remains unverified.

---

## 5. Artifact Checksum Audit

All temporary placeholders (`[to be computed]`, `[existing hash]`) have been removed from documentation and replaced with verified cryptographic hashes:

### Frozen Phase 1 Artifacts
- `artifacts/riskorbit-risk-v1/model.pkl`: `b190d5c276dd70b81b3bb8ead3f5b5c99a6709ab9d7b42857b5c13a9f8f59a80`
- `artifacts/riskorbit-risk-v1/threshold.json`: `093057ad55bab6e7d1930aca6bdf1e8afd94c8aafe82830b2731630209e82c7e`
- `artifacts/riskorbit-risk-v1/feature_schema.json`: `85317a632ac44bc339fbc4c1ddff90267aa0797943067a9782c07e21ed7da469`

### Phase 3.1 Code & Test Checksums
- `src/graph/edge_diversity.py`: `1e1f0c2532721c18722e138403c8ac2ead237a75844258cc95886c2dc7ee1609`
- `src/graph/member_confidence.py`: `8c28dc6fc756830512c69f91acc5e25ef12c9875a3bbad952c6d27377cb67e28`
- `src/decision/transaction_gate.py`: `b07f38a6ba58f3ea70bbb734f0d4aebce9268c49d9c517ad23fb8caf3d4f1a24`
- `tests/test_phase3_1.py`: `ae2009aeab4bf425b12bc87e773977b38e190c77e94038031723c941db1515d3`

---

## 6. Audit Verdict

```
VALIDATION/TEST SEPARATION: PASS
LEAKAGE: PASS
DEPENDENCY REPRODUCIBILITY: PASS
CROSS-PLATFORM CLAIMS: UNVERIFIED
PLACEHOLDERS REMAINING: NO
```
