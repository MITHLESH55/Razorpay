# RiskOrbit — Agentic Coordinated Refund-Abuse Sentinel

> **Track 02 — AI Risk Manager | Razorpay AI Buildathon 2026**

RiskOrbit is an agentic risk-management system designed to detect, connect, investigate, explain, and safely respond to **coordinated refund/return abuse rings**.

Individual refund transactions can look legitimate in isolation. RiskOrbit looks across related customers, devices, addresses, payment instruments, transactions, and refund behavior to identify coordinated patterns and turn them into **evidence-backed, auditable risk cases**.

### What RiskOrbit Does

```text
Transaction / Event
        │
        ▼
Risk Scoring
        │
        ▼
Entity & Behavioral Graph
        │
        ▼
Coordinated Ring Discovery
        │
        ▼
Investigation Agent
        │
        ▼
Evidence-Grounded Case
        │
        ▼
Deterministic Risk Policy
        │
        ▼
Human Approval
        │
        ▼
Bounded / Simulated Intervention
        │
        ▼
Audit Trail + Evaluation

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


## 3.1 Live Application Workflow

After starting the application, the primary demonstration path is:

1. **Authenticate** into RiskOrbit.
2. **Review the risk dashboard** and current operational posture.
3. **Open the risk queue** to inspect prioritized cases.
4. **Open a coordinated-abuse case**.
5. **Inspect the entity graph** connecting related accounts and behavioral signals.
6. **Review evidence and investigation findings**.
7. **Review the deterministic policy decision**.
8. **Simulate or approve a bounded intervention**, according to the user's authorization.
9. **Inspect the resulting audit trail**.
10. **Review evaluation and system-health information**.

This workflow demonstrates the complete RiskOrbit loop:

**Detect → Connect → Investigate → Explain → Decide → Act → Audit**



## 4. Key Held-Out Benchmark Results

> These results are reported on held-out evaluation data. Metrics are separated by their measurement target; ring-level recall, transaction-level recall, intervention FPR, and hard-block FPR are not interchangeable.

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


---

## 7. Project Structure

```text
RiskOrbit/
├── frontend/                 # Risk operations dashboard
├── src/                      # Risk engine, graph, investigation and policy logic
├── configs/                  # Model and system configuration
├── artifacts/                # Versioned model artifacts and metadata
├── data/
│   ├── raw/                  # Generated input data
│   ├── processed/            # Generated processed data
│   └── splits/               # Dataset split metadata/manifests
├── reports/                  # Evaluation and validation reports
├── scripts/                  # Data generation, training and evaluation scripts
├── tests/                    # Backend and evaluation tests
├── docs/                     # Supporting technical documentation
├── prompts/                  # Investigation-agent prompt assets
├── README.md
├── .env.example
└── Dockerfile.backend


```markdown
## 8. Engineering Lessons

RiskOrbit was developed iteratively rather than assuming the first implementation was correct.

Key engineering issues addressed during development included:

- Preventing evaluation leakage between training and held-out data
- Separating ring-level metrics from transaction-level metrics
- Controlling false-positive cost for automated interventions
- Handling hard-negative cases that resemble coordinated abuse
- Grounding investigation outputs in explicit evidence
- Separating model scoring from deterministic policy decisions
- Preserving human approval for controlled interventions
- Maintaining an auditable record of risk decisions and actions

The resulting architecture intentionally favors **measurability, explainability, controlled action, and safe failure** over unconstrained autonomous behavior.


---

## 9. Defensive-Only Statement

RiskOrbit is built exclusively for defensive payment-risk management and research evaluation.

The project focuses on detecting and investigating coordinated refund/return abuse using synthetic data and controlled interventions. It does not provide offensive security capabilities and does not authorize irreversible production actions autonomously.





