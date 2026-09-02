# RiskOrbit — Phase 3.2: Reproducibility & Determinism Report

**Status:** Complete  
**Evaluation Scope:** Validation Partition  
**Date:** 2026-08-31  

---

## 1. Executive Summary

Reproducibility is a core requirement of the RiskOrbit validation framework. This report documents the exact runtime environment, dependency manifest, cryptographic hashes, random seed settings, and duplicate-run bitwise determinism proofs.

---

## 2. Environment Specification

| Component | Specification |
|---|---|
| **Operating System** | Windows 11 Home Single Language (10.0.26200) |
| **Shell Environment** | Git Bash / POSIX sh (UTF-8) |
| **Python Runtime** | Python 3.12.6 (tags/v3.12.6:a4a8b2f, 64-bit) |
| **Primary Libraries** | `numpy==1.26.4`, `pandas==2.2.2`, `scipy==1.13.1`, `scikit-learn==1.5.1`, `lightgbm==4.5.0`, `networkx==3.3`, `pydantic==2.8.2`, `pytest==8.3.2` |
| **Global Random Seed** | `42` (Enforced across NumPy, Python standard library, and LightGBM) |

---

## 3. Cryptographic Artifact Hashes

### 3.1 Input Datasets
- **Validation Dataset (`data/splits/validation.csv`):**  
  `SHA256: a521d2540737028b342de89dcd576bc6599ea332543555b3e1bd9d379db14600`
- **Validation Features (`data/processed/val_features.csv`):**  
  `SHA256: e8dbdf2a9bb40b9df441c2c31e9c80d46816ecb79361ad2ea1fa8f8a84ebffb9`
- **Locked Held-Out Test Set (`data/splits/heldout_test.csv`):**  
  `SHA256: f0fe47be1191db1bbb62ab61f1747b952926d2fd2cc2adc72c3835a173dd164c`

### 3.2 Output Validation Artifacts
- **Validation Results JSON (`results/phase3_2_validation/validation_results.json`):**  
  `SHA256: 0eecdb804f5869389278bf9703c5ae1ca2756d11f8e28cb487f9859f77f022ef`

---

## 4. Duplicate Run Bitwise Determinism

To verify that the simulation pipeline is strictly deterministic, the full validation experiment was executed in duplicate passes under identical conditions.

| Parameter | Run 1 | Run 2 | Status |
|---|---|---|---|
| **Validation Transactions Evaluated** | 28,581 | 28,581 | Identical |
| **Policy D Hard Blocks** | 30 | 30 | Identical |
| **Policy D 2FA Step-Ups** | 59 | 59 | Identical |
| **Policy D Settlement Delays** | 52 | 52 | Identical |
| **Policy D Account Restrictions** | 3 | 3 | Identical |
| **Policy D Allows** | 28,437 | 28,437 | Identical |
| **Action Stream SHA256** | `2a2652080cfce04590840da2c75f7c3b95ef61c64712e41ce2eccfc1fb591909` | `2a2652080cfce04590840da2c75f7c3b95ef61c64712e41ce2eccfc1fb591909` | **Bitwise Identical** |
| **Metric Invariance** | 100.0% | 100.0% | **Exact Match** |

---

## 5. Execution Command

To re-run the entire validation suite reproducibly:

```bash
py -3.12 scripts/phase3_2_validation_experiment.py
py -3.12 -m pytest tests/test_phase3_2.py -v
```
