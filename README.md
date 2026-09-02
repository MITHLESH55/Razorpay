# RiskOrbit — Agentic Coordinated Refund-Abuse Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests: 102 passed](https://img.shields.io/badge/Tests-102%20passed-brightgreen.svg)](tests/)
[![Phase: 2 Complete](https://img.shields.io/badge/Phase-2%20Complete-brightgreen.svg)](reports/PHASE2_FINAL_REPORT.md)
[![FastAPI](https://img.shields.io/badge/API-FastAPI%202.0-009688.svg)](src/api/app.py)

> A case-centric, bounded, multi-hop relationship intelligence and grounded evidence framework for detecting and investigating coordinated refund abuse in payment ecosystems.

---

## 1. Why RiskOrbit?
Payment systems monitor transactions, velocity, and device fingerprints. However, **coordinated refund abuse** operates through rings of colluding or rotating customer accounts that distribute fraud volume across multiple merchants, devices, and subnets. When individual transaction-level evidence is statistically normal in isolation, single-row tabular detectors exhibit blind spots. 

RiskOrbit explores a bounded relationship investigation layer with explicit evidence aggregation, causal point-in-time constraints, and verifiable anti-hallucination guarantees.

---

## 2. Architecture: Detect → Connect → Investigate → Explain

```text
               Phase 1
          Risk Detector v1 (LightGBM)
                    │
                    ▼
           Suspicious Candidate
                    │
                    ▼
          Point-in-Time Graph Engine
         (NetworkX + Hubness Discounting)
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Graph-Enhanced       Bounded Local
     Scoring v2           Traversal
          │                   │
          └─────────┬─────────┘
                    ▼
           Candidate Ring Discovery
                    │
                    ▼
          Investigation Agent
         (Typed Tools & Budget)
                    │
                    ▼
          Grounded Evidence Agent
          (EVID-xxxx Citations)
                    │
                    ▼
           Grounded Risk Case
          (POST /risk/investigate)
```

---

## 3. Quick Start & Reproduction

```powershell
# 1. Validate environment & dataset
python scripts/validate_data.py

# 2. Build point-in-time graph & audit data quality
python scripts/build_graph.py

# 3. Train Phase 2 graph-enhanced model (riskorbit-risk-v2)
python scripts/train_graph_model.py

# 4. Run 5-tier controlled feature ablation
python scripts/run_phase2_ablation.py

# 5. Evaluate on locked held-out test set
python scripts/evaluate_phase2.py
python scripts/generate_all_phase2_reports.py

# 6. Run automated test suite (102 tests)
pytest -v

# 7. Start FastAPI scoring & investigation server
python -m src.api.app
```

---

## 4. Key Held-Out Benchmark Results

| Metric | Phase 1 (Frozen Baseline) | Phase 2 (Graph-Enhanced) | Delta / Impact |
|---|---|---|---|
| **Model Version** | `riskorbit-risk-v1` | `riskorbit-risk-v2` | Versioned artifact |
| **Operating Threshold** | 0.3500 (Validation) | 0.3200 (Validation) | Validation-tuned |
| **Held-Out Precision** | 35.17% | **38.12%** | **+2.95%** (37.6x lift) |
| **Held-Out PR-AUC** | 0.0969 | **0.1140** | **+17.6% relative** |
| **Held-Out FPR** | 0.54% | **0.40%** | **-0.14%** (Controlled) |
| **Modeled FP Cost (₹130/FP)** | ₹19,890.00 | **₹14,560.00** | **₹-5,330 savings** |
| **Complete Ring Detection Rate** | 12.50% | **16.67%** | **+4.17%** |
| **Household Sharing FPR** | 0.00% | **0.00%** | Safe |
| **Office/Campus Shared Network FPR**| 0.00% | **0.00%** | Safe |
| **Serial Returner FPR** | 0.00% | **0.00%** | Safe |
| **Evidence Grounding Rate** | N/A | **100.00%** | Zero hallucinations |

---

## 5. Phase 2 Capabilities & Features

1. **Point-in-Time Graph Engine (`src/graph/`)**: Multi-entity graph strictly isolating causal logs $\le T$ without label leakage.
2. **Hubness Discounting (`src/graph/strength.py`)**: Normalizes connection weights for public subnets and high-degree merchants.
3. **Candidate Ring Detection (`src/graph/ring_detector.py`)**: Unsupervised multi-account cluster extraction.
4. **Structured Investigation Toolkit (`src/investigation/tools.py`)**: Typed, point-in-time historical querying tools.
5. **Grounded Evidence Agent (`src/investigation/evidence_agent.py`)**: Synthesizes verified narratives citing explicit `EVID-xxxx` IDs.
6. **FastAPI Endpoints (`src/api/app.py`)**:
   - `POST /risk/score` — Phase 1 transaction risk scoring (preserved).
   - `POST /risk/investigate` — Phase 2 case investigation.
   - `GET /risk/cases/{case_id}` — Stored case retrieval.
   - `GET /risk/cases/{case_id}/graph` — Subgraph topology.
   - `GET /risk/cases/{case_id}/evidence` — Grounded evidence records.

---

## 6. Phase 2 Verification Reports

- Master Report: [PHASE2_FINAL_REPORT.md](reports/PHASE2_FINAL_REPORT.md)
- Delta Analysis (Phase 1 → 2): [PHASE2_DELTA_REPORT.md](reports/PHASE2_DELTA_REPORT.md)
- **End-to-End Funnel Audit**: [PHASE2_CANDIDATE_COVERAGE.md](reports/PHASE2_CANDIDATE_COVERAGE.md)
- Feature Ablation (5-Tier): [PHASE2_GRAPH_ABLATION.md](reports/PHASE2_GRAPH_ABLATION.md)
- Graph Data Quality: [GRAPH_DATA_QUALITY.md](reports/GRAPH_DATA_QUALITY.md)
- Investigation Agent Benchmark: [INVESTIGATION_EVALUATION.md](reports/INVESTIGATION_EVALUATION.md)
- Evidence Grounding & Anti-Hallucination: [EVIDENCE_GROUNDING_REPORT.md](reports/EVIDENCE_GROUNDING_REPORT.md)
- Ring Detection Analysis: [RING_EVALUATION.md](reports/RING_EVALUATION.md)
- Hard-Negative Safety: [HARD_NEGATIVE_GRAPH_REPORT.md](reports/HARD_NEGATIVE_GRAPH_REPORT.md)
- Temporal Generalization: [TEMPORAL_PHASE2_REPORT.md](reports/TEMPORAL_PHASE2_REPORT.md)
- Diagnostic Failure Analysis: [PHASE2_FAILURE_ANALYSIS.md](reports/PHASE2_FAILURE_ANALYSIS.md)
