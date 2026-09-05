# RiskOrbit — Agentic Coordinated Refund-Abuse Sentinel

> **Track 02 — AI Risk Manager | Razorpay AI Buildathon 2026**

RiskOrbit is an agentic risk-management system designed to **detect, connect, investigate, explain, and safely respond to coordinated refund/return abuse rings**.

Individual refund transactions can look legitimate in isolation. RiskOrbit looks across related customers, devices, addresses, payment instruments, transactions, and refund behavior to identify coordinated patterns and turn them into **evidence-backed, auditable risk cases**.

---

## 🎥 Demo

[Watch the RiskOrbit Demo]
https://drive.google.com/file/d/1A9ZDi-gJBdNOk2lzbyWCueFQJxbF3Y6R/view?usp=drive_link




## Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Risk Queue
![Risk Queue](docs/screenshots/risk_queue.png)

### Case Investigation
![Case Investigation](docs/screenshots/case_investigation.png)

### Audit Ledger
![Audit Ledger](docs/screenshots/audit_ledger.png)

### Model Evaluation
![Model Evaluation](docs/screenshots/model_evaluation.png)

### Policy Simulation
![Policy Simulation](docs/screenshots/policy_simulation.png)

### Governance & Kill Switches
![Governance & Kill Switches](docs/screenshots/governance_killswitches.png)



## What RiskOrbit Does

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
```

### Why It Matters

Coordinated refund abuse is difficult to detect when each transaction is evaluated independently.

A single refund may appear normal, while a group of accounts can reveal a much stronger pattern through shared devices, addresses, payment instruments, transaction behavior, and repeated refund activity.

RiskOrbit therefore treats risk as a **relationship and investigation problem**, not only a transaction-classification problem.

---

## Key Capabilities

- **Risk scoring** for suspicious refund/return activity
- **Entity and behavioral graph analysis** across related entities
- **Coordinated ring discovery** for multi-account abuse patterns
- **Investigation orchestration** for suspicious cases
- **Evidence-grounded findings** with explicit supporting signals
- **Deterministic policy decisions** separated from model scoring
- **Human-in-the-loop approval** for controlled interventions
- **Bounded and simulated defensive actions**
- **Audit trail** for decisions and interventions
- **Held-out evaluation** with precision, recall, FPR, and PR-AUC
- **False-positive cost analysis**
- **Hard-negative and failure-case analysis**
- **Model and policy versioning**

---

## Held-Out Evaluation Snapshot

| Metric | Result |
|---|---:|
| Ring Recall | **100% (24/24 rings)** |
| Intervention FPR | **0.45%** |
| Hard-block FPR | **0.04%** |
| Held-out Transactions | **28,591** |
| Model Version | `riskorbit-risk-v1` |
| Policy Version | `phase3_final_policy` |

> **Metric note:** Ring recall measures detection of coordinated abuse rings and should not be interpreted as transaction-level recall. Intervention FPR and hard-block FPR refer to their respective intervention policies.

---

## Safety & Scope

RiskOrbit is a **defensive risk-management system**.

- Evaluation uses synthetic transaction/event data.
- No real customer PII is required.
- Interventions are bounded and/or simulated.
- Human approval is preserved for controlled actions.
- Model scoring is separated from deterministic policy enforcement.
- The system does not provide offensive security capabilities.
- The system does not autonomously authorize irreversible production actions.

---

## Demo Flow

The intended product workflow is:

**Login → Risk Dashboard → Risk Queue → Case Investigation → Entity Graph → Evidence → Decision → Simulation/Approval → Audit**

This demonstrates the complete RiskOrbit loop:

**Detect → Connect → Investigate → Explain → Decide → Act → Audit**

---

## 1. Why RiskOrbit?

Payment systems generate large volumes of transactions, velocity signals, device fingerprints, and customer activity. However, coordinated refund abuse operates across groups of accounts and entities rather than isolated transactions.

RiskOrbit addresses this by combining:

1. Transaction-level risk scoring
2. Multi-entity relationship analysis
3. Behavioral graph construction
4. Coordinated ring discovery
5. Structured investigation
6. Evidence grounding
7. Deterministic policy evaluation
8. Human-controlled intervention
9. Complete auditability

The objective is not simply to label a transaction as risky.

The objective is to produce a **defensible risk case** that explains why related activity is suspicious and what controlled action should be considered.

---

## 2. Architecture: Detect → Connect → Investigate → Explain

```text
                         ┌───────────────────────┐
                         │   Transaction/Event   │
                         │        Intake         │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   Risk Detector v1    │
                         │      (LightGBM)       │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Suspicious Candidates │
                         └───────────┬───────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │       Point-in-Time Graph Engine    │
                  │     NetworkX + H3-based features    │
                  └─────────────────┬───────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
             Graph-Enhanced                 Bounded Local
                Scoring                      Traversal
                     │                             │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                         ┌───────────────────────┐
                         │ Coordinated Ring      │
                         │      Discovery        │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Investigation Agent   │
                         │  (Tool Calls + Budget)│
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Grounded Evidence     │
                         │  (EVID-xxx citations) │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Grounded Risk Case    │
                         │ /POST /risk/investigate│
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Deterministic Policy  │
                         │      Decision         │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Human Approval /      │
                         │ Bounded Intervention  │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      Audit Trail      │
                         └───────────────────────┘
```

### Core Design Principle

The system deliberately separates:

```text
Model Score
     ↓
Graph Evidence
     ↓
Investigation
     ↓
Policy Decision
     ↓
Human Approval
     ↓
Controlled Action
```

This prevents an unconstrained AI agent from directly making irreversible operational decisions.

---

## 3. Quick Start & Reproduction

### 3.1 Backend

Create and activate the Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the backend:

```powershell
uvicorn main:app --reload --port 8001
```

The API should be available at:

```text
http://127.0.0.1:8001
```

Health check:

```text
http://127.0.0.1:8001/health
```

---

### 3.2 Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Then open the frontend URL displayed by Vite.

---

### 3.3 Reproducibility Pipeline

The repository contains scripts for dataset generation, validation, model training, evaluation, and verification.

Typical workflow:

```text
1. Generate synthetic data
2. Validate dataset quality
3. Build graph-derived features
4. Train the risk model
5. Run controlled feature ablation
6. Evaluate on held-out data
7. Generate evaluation reports
8. Run automated tests
9. Start the API
10. Verify the live application
```

Use the project scripts and configuration files as the source of truth for the exact reproduction commands.

---

## 3.1 Live Application Workflow

After starting the application, the primary demonstration path is:

1. **Authenticate** into RiskOrbit.
2. **Review the risk dashboard** and operational posture.
3. **Open the risk queue** to inspect prioritized cases.
4. **Open a coordinated-abuse case**.
5. **Inspect the entity graph** connecting related accounts and behavioral signals.
6. **Review evidence and investigation findings**.
7. **Review the deterministic policy decision**.
8. **Simulate or approve a bounded intervention**, according to authorization.
9. **Inspect the resulting audit trail**.
10. **Review evaluation and system-health information**.

This workflow demonstrates the complete RiskOrbit loop:

**Detect → Connect → Investigate → Explain → Decide → Act → Audit**

---

## 4. Key Held-Out Benchmark Results

These results are reported on held-out evaluation data.

Metrics are intentionally separated by their measurement target. **Ring-level recall, transaction-level recall, intervention FPR, and hard-block FPR are not interchangeable.**

| Metric | Phase 1 (Frozen Baseline) | Phase 2 (Graph-Enhanced) | Delta / Impact |
|---|---:|---:|---:|
| Model Version | `riskorbit-risk-v1` | `riskorbit-risk-v2` | Versioned artifact |
| Operating Threshold | 0.3500 (Validation) | 0.3200 (Validation) | Validation-tuned |
| Held-Out Precision | 35.17% | 38.12% | +2.95% |
| Held-Out PR-AUC | 0.0969 | 0.1140 | +17.6% relative |
| Held-Out FPR | 0.54% | 0.40% | -0.14% |
| Modeled FP Cost (₹130/FP) | ₹19,890.00 | ₹14,560.00 | -₹5,330 savings |
| Complete Ring Detection Rate | 12.50% | 16.67% | +4.17% |
| Household Sharing FPR | 0.00% | 0.00% | Safe |
| Cross-User Shared Network FPR | 0.00% | 0.00% | Safe |
| Serial Returner FPR | 0.00% | 0.00% | Safe |
| Evidence Grounding Rate | N/A | 100.00% | Zero hallucinations |

### Operational Evaluation

The current operational evaluation snapshot additionally reports:

| Operational Metric | Result |
|---|---:|
| Ring Recall | **100% (24/24 rings)** |
| Intervention FPR | **0.45%** |
| Hard-block FPR | **0.04%** |
| Direct Transaction Recall | **26.21%** |
| Held-out Transactions | **28,591** |

> The operational metrics above should be interpreted according to their individual definitions. In particular, **100% ring recall does not mean 100% transaction recall**.

---

## 5. Phase 2 Capabilities & Features

1. **Point-in-Time Graph Engine** (`src/graph/`)  
   Multi-entity graph construction while respecting causal/time constraints.

2. **Hubness Discounting** (`src/graph/graph_strength.py`)  
   Normalizes common connections that would otherwise create excessive false positives.

3. **Candidate Ring Detection** (`src/graph/ring_detector.py`)  
   Unsupervised multi-account cluster extraction.

4. **Structured Investigation Toolkit** (`src/investigation/`)  
   Point-in-time historical queries and evidence collection.

5. **Grounded Evidence Agent** (`src/investigation/evidence_agent.py`)  
   Produces structured findings backed by explicit evidence identifiers.

6. **Case Management APIs**  
   Supports investigation, case retrieval, decisioning, simulation, approval, rejection, editing, monitoring, evaluation, and audit workflows.

---

## 6. Phase 2 Verification Reports

The repository includes detailed technical validation and audit reports:

- Master Report: [PHASE2_FINAL_REPORT.md](PHASE2_FINAL_REPORT.md)
- Delta Analysis (Phase 1 → Phase 2): [PHASE2_DELTA_REPORT.md](PHASE2_DELTA_REPORT.md)
- End-to-End Final Audit: [PHASE2_CANDIDATE_COVERAGE.md](PHASE2_CANDIDATE_COVERAGE.md)
- Feature Ablation: [PHASE2_GRAPH_ABLATION.md](PHASE2_GRAPH_ABLATION.md)
- Graph Data Quality: [GRAPH_DATA_QUALITY.md](GRAPH_DATA_QUALITY.md)
- Investigation Agent Benchmark: [INVESTIGATION_EVALUATION.md](INVESTIGATION_EVALUATION.md)
- Evidence Grounding & Anti-Hallucination: [EVIDENCE_GROUNDING_REPORT.md](EVIDENCE_GROUNDING_REPORT.md)
- Ring Detection Analysis: [RING_DETECTION_ANALYSIS.md](RING_DETECTION_ANALYSIS.md)
- Hard-Negative Safety: [HARD_NEGATIVE_GRAPH_REPORT.md](HARD_NEGATIVE_GRAPH_REPORT.md)
- Temporal Generalization: [TEMPORAL_PHASE2_REPORT.md](TEMPORAL_PHASE2_REPORT.md)
- Diagnostic Failure Analysis: [PHASE2_FAILURE_ANALYSIS.md](PHASE2_FAILURE_ANALYSIS.md)

Additional repository documentation covers data definitions, leakage auditing, false-positive cost, frontend integration, and engineering validation.

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
├── Dockerfile.backend
└── requirements.txt
```

Large generated datasets are intentionally excluded from version control. Dataset generation scripts, manifests, hashes, and reproducibility metadata are retained instead.

---

## 8. Engineering Lessons

RiskOrbit was developed iteratively rather than assuming that the first implementation was correct.

Key engineering issues addressed during development include:

- Preventing evaluation leakage between training and held-out data
- Separating ring-level metrics from transaction-level metrics
- Controlling false-positive cost for automated interventions
- Handling hard-negative cases that resemble coordinated abuse
- Grounding investigation outputs in explicit evidence
- Separating model scoring from deterministic policy decisions
- Preserving human approval for controlled interventions
- Maintaining an auditable record of risk decisions and actions
- Evaluating temporal and graph-based generalization
- Keeping defensive actions bounded and reversible/simulatable

The resulting architecture intentionally favors **measurability, explainability, controlled action, and safe failure** over unconstrained autonomous behavior.

---

## 9. Defensive-Only Statement

RiskOrbit is built exclusively for defensive payment-risk management and research evaluation.

The project focuses on detecting and investigating coordinated refund/return abuse using synthetic data and controlled interventions.

It does not provide offensive security capabilities and does not authorize irreversible production actions autonomously.

---

## 10. Status

**Current implementation includes:**

- Risk scoring
- Graph-based entity analysis
- Coordinated ring discovery
- Investigation workflow
- Evidence grounding
- Case management
- Deterministic policy decisioning
- Human approval workflow
- Bounded intervention simulation
- Audit trail
- Operational monitoring
- Evaluation metrics
- Drift monitoring
- Automated test coverage
- Reproducibility metadata
- Versioned model artifacts

The project is intended as a **hackathon research/prototype implementation**, not a claim of production deployment or production certification.

---

## License

This repository is provided for hackathon, research, and evaluation purposes.
