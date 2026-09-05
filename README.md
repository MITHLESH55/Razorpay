# RiskOrbit — Agentic Coordinated Refund-Abuse Sentinel

> **Track 02 — AI Risk Manager | Razorpay AI Buildathon 2026**

RiskOrbit is an agentic risk-management system designed to **detect, connect, investigate, explain, and safely respond to coordinated refund/return abuse rings**.

Individual refund transactions can look legitimate in isolation. RiskOrbit looks across related customers, devices, addresses, payment instruments, transactions, and refund behavior to identify coordinated patterns and turn them into **evidence-backed, auditable risk cases**.

---

## 🏆 Hackathon Reviewer Quick Start

> **This section is for HR/hackathon evaluators doing a clean repository clone.**
> No developer credentials, personal email, or existing browser session is required.

---

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.10 +  |
| Node.js     | 18 +    |
| npm         | 9 +     |

---

### 1. Clone the repository

```bash
git clone <repository-url>
cd riskorbit
```

---

### 2. Backend setup

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the example environment file (disposable evaluation credentials only)
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

---

### 3. Start the backend

```bash
uvicorn src.api.app_v2:app --host 0.0.0.0 --port 8000 --reload
```

The backend starts at **`http://localhost:8000`**.

On first startup the four disposable evaluation users are seeded automatically
into the local SQLite database. No manual database setup is required.

Verify it is healthy:

```bash
curl http://localhost:8000/health
# {"status":"model_not_loaded",...}   ← normal without ML artifacts
```

---

### 4. Frontend setup

```bash
cd frontend
npm install
```

Create a frontend env file:

```bash
# In the frontend/ directory
echo VITE_API_BASE_URL=http://localhost:8000 > .env.local
```

---

### 5. Start the frontend

```bash
# Still inside frontend/
npm run dev
```

The frontend starts at **`http://localhost:5173`** (or `3000` if configured).

---

### 6. Login — Hackathon Evaluation Access

Open **`http://localhost:5173`** in a fresh browser or incognito window.

The login page contains two authentication paths:

**Normal login form** — for enterprise credentials (not needed for evaluation).

**Hackathon Evaluation Access** — four one-click buttons:

| Button | Identity | Role |
|--------|----------|------|
| Sign in as Analyst | `analyst_01` | ANALYST |
| Sign in as Senior Analyst | `senior_analyst_01` | SENIOR_ANALYST |
| Sign in as Admin | `admin_01` | ADMIN |
| Sign in as Viewer | `viewer_01` | VIEWER |

Each button calls `POST /api/v2/ops/auth/evaluation-login` on the backend.
The backend authenticates the evaluation identity, creates a real session, and
returns a Bearer token. The frontend then validates the session via
`GET /api/v2/ops/auth/session` before displaying the dashboard.

**No passwords appear in the frontend. No frontend-only auth bypass exists.**

---

### 7. Role capability matrix

| Capability | VIEWER | ANALYST | SENIOR\_ANALYST | ADMIN |
|---|:---:|:---:|:---:|:---:|
| Read operational dashboard & overview | ✅ | ✅ | ✅ | ✅ |
| Queue triage & case search | ❌ | ✅ | ✅ | ✅ |
| Evidence graph & timeline inspection | ❌ | ✅ | ✅ | ✅ |
| Low-impact action approvals (2FA, Delay) | ❌ | ✅ | ✅ | ✅ |
| High-impact approvals (Block, Restrict, Freeze Ring) | ❌ | ❌ | ✅ | ✅ |
| Policy decision overrides & edit actions | ❌ | ❌ | ✅ | ✅ |
| Counterfactual simulation workbench | ❌ | ❌ | ✅ | ✅ |
| User management (create / disable accounts) | ❌ | ❌ | ❌ | ✅ |
| Kill switch activation | ❌ | ❌ | ❌ | ✅ |
| Shadow mode controls | ❌ | ❌ | ❌ | ✅ |
| Safe degradation controls | ❌ | ❌ | ❌ | ✅ |
| Audit ledger access | ✅ | ✅ | ✅ | ✅ |

RBAC is **server-authoritative**. The backend never trusts a client-supplied
role or actor.

---

### 8. Key routes to test

| URL | Expected behaviour |
|-----|-------------------|
| `/` | Redirects to `/login` when unauthenticated |
| `/login` | Login page with evaluation access panel |
| `/dashboard` | Operational overview (all roles) |
| `/queue` | Triage queue (ANALYST+) |
| `GET /api/v2/ops/auth/session` | Returns authenticated identity & role |
| `GET /api/v2/ops/auth/demo-users` | Lists evaluation identities (public, no secrets) |
| `GET /api/v2/ops/controls` | System state (all roles) |
| `POST /api/v2/ops/controls` | Mutate controls — ADMIN only (others → 403) |
| `GET /api/v2/ops/auth/users` | User list — ADMIN only (others → 403) |

---

### 9. Logout

Click the logout control in the application header.

The backend invalidates the session token immediately. Reusing the old token
returns `401 Unauthorized`.

You can then log in as a different evaluation role.

---

### 10. Testing in incognito / different browser

The application uses Bearer token authentication stored in `localStorage` /
`sessionStorage`. It does not depend on browser cookies.

Opening an incognito window gives a completely fresh state.
All four evaluation identities work from a fresh browser session.

---

### 11. Troubleshooting

**`401 Unauthorized` on evaluation login**

```
Cause:  Evaluation users not yet seeded.
Fix:    Restart the backend once. Seeding runs on every startup.
        If the problem persists, delete data/processed/riskorbit_users.db
        and restart — it will be recreated with correct hashes.
```

**`Unable to reach RiskOrbit API`**

```
Cause:  Backend is not running or is on a different port.
Fix:    Ensure uvicorn is running on port 8000.
        Ensure frontend .env.local has VITE_API_BASE_URL=http://localhost:8000.
```

**`CORS error` in browser console**

```
Cause:  Frontend origin not in CORS allow-list.
Fix:    Set RISKORBIT_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
        in your .env file.
```

**Evaluation users missing from DB**

```
Cause:  Old DB created before the seeding fix.
Fix:    Delete data/processed/riskorbit_users.db and restart the backend.
```

**Frontend won't start**

```
Fix:    cd frontend && npm install && npm run dev
        Ensure VITE_API_BASE_URL is set in frontend/.env.local
```

---

### 12. Evaluation credentials (disposable — safe for public repository)

These identities are intentionally disposable and scoped to local
evaluation only. They are **not** developer credentials.

| User ID | Password | Role |
|---------|----------|------|
| `analyst_01` | `RiskOrbit@Analyst2026` | ANALYST |
| `senior_analyst_01` | `RiskOrbit@Senior2026` | SENIOR_ANALYST |
| `admin_01` | `RiskOrbit@Admin2026` | ADMIN |
| `viewer_01` | `RiskOrbit@Viewer2026` | VIEWER |

These passwords can also be entered manually in the normal login form if needed.

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


## Problem Statement Alignment

RiskOrbit is designed around Track 02 — AI Risk Manager and focuses on
defense-only detection of coordinated refund/return abuse.

| Requirement (Track 02) | How RiskOrbit Addresses It |
|---|---|
| Build a working detector, verifier, or auto-responder for one class of loss. | RiskOrbit acts as an abuse-ring risk detector for coordinated refund/return abuse, connecting customers, devices, addresses, payment instruments, transactions, and refund behavior into risk cases. |
| Show measured precision and recall on a held-out test set. | RiskOrbit reports precision, recall, F1 and PR-AUC on held-out evaluation data. See the [Phase 2 Final Report](reports/PHASE2_FINAL_REPORT.md) and [Graph Feature Ablation Report](reports/PHASE2_GRAPH_ABLATION.md). |
| Example direction: Abuse-ring sentinel. | RiskOrbit specifically detects coordinated abuse rings using graph relationships and ring-level risk signals. |
| Honest metrics including false-positive cost. | RiskOrbit evaluates false-positive rate and false-positive cost alongside precision, recall and F1, making the operational cost of incorrect flags explicit. See the [Phase 2 Final Report](reports/PHASE2_FINAL_REPORT.md). |
| Strictly defense-only; anything offense-capable is disqualified. | RiskOrbit is a defensive risk-management and investigation system focused on detection, evidence, explainability, governance and auditable decisions. |



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

| Metric                |                 Result |
| --------------------- | ---------------------: |
| Ring Recall           | **100% (24/24 rings)** |
| Intervention FPR      |              **0.45%** |
| Hard-block FPR        |              **0.04%** |
| Held-out Transactions |             **28,591** |
| Model Version         |    `riskorbit-risk-v1` |
| Policy Version        |  `phase3_final_policy` |

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
uvicorn src.api.app_v2:app --reload --port 8001
```

The API should be available at:

```text
http://127.0.0.1:8001
```

## Hackathon Reviewer Quick Start

### Prerequisites

- Python 3.11+ and Node.js 18+
- PowerShell on Windows, or an equivalent shell

### Run the application

From the `riskorbit` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.api.app_v2:app --reload --port 8001
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --port 3000
```

Open [http://localhost:3000/login](http://localhost:3000/login). The backend provisions four disposable evaluation identities automatically in its local SQLite auth database. Use the **Hackathon Evaluation Access** buttons; each button calls the backend, verifies the evaluation identity, creates a normal Bearer session, and applies server-side RBAC.

For API-only verification, the identifiers and deliberately disposable passwords are:

| Role           | User ID             | Password                |
| -------------- | ------------------- | ----------------------- |
| Analyst        | `analyst_01`        | `RiskOrbit@Analyst2026` |
| Senior Analyst | `senior_analyst_01` | `RiskOrbit@Senior2026`  |
| Admin          | `admin_01`          | `RiskOrbit@Admin2026`   |
| Viewer         | `viewer_01`         | `RiskOrbit@Viewer2026`  |

These accounts are evaluation-only and must never be reused for production or personal services. They are marked `evaluation_only` in the backend database. No developer credentials, OAuth secrets, or production keys are required.

### Role capability matrix

| Role             | Access                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| `VIEWER`         | Read-only dashboard, queues, cases, evidence, audit, and evaluation views                             |
| `ANALYST`        | Viewer access plus queue triage, investigation, evidence inspection, feedback, and low-impact actions |
| `SENIOR_ANALYST` | Analyst access plus high-impact approvals and policy overrides                                        |
| `ADMIN`          | Full access, governance controls, safe mode, shadow mode, and kill switch controls                    |

### Routes and features to test

- `POST /api/v2/ops/auth/login` and `GET /api/v2/ops/auth/session`
- `POST /api/v2/ops/auth/evaluation-login`
- `POST /api/v2/ops/auth/logout`
- Dashboard, risk queue, case investigation, evidence graph, approvals, audit, evaluation, and system controls
- Anonymous protected requests return `401`; authenticated insufficient permissions return `403`; logout invalidates the token

### Troubleshooting

- If login cannot reach the API, confirm `uvicorn` is running on port `8001`.
- If the frontend uses another API port, set the frontend API base URL according to `frontend/src/api/client.ts`.
- To reset only local evaluation state, stop the backend and remove `data/processed/riskorbit_users.db`; the next startup recreates the four evaluation users. Existing real users are never removed by seeding.

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

| Metric                        | Phase 1 (Frozen Baseline) | Phase 2 (Graph-Enhanced) |      Delta / Impact |
| ----------------------------- | ------------------------: | -----------------------: | ------------------: |
| Model Version                 |       `riskorbit-risk-v1` |      `riskorbit-risk-v2` |  Versioned artifact |
| Operating Threshold           |       0.3500 (Validation) |      0.3200 (Validation) |    Validation-tuned |
| Held-Out Precision            |                    35.17% |                   38.12% |              +2.95% |
| Held-Out PR-AUC               |                    0.0969 |                   0.1140 |     +17.6% relative |
| Held-Out FPR                  |                     0.54% |                    0.40% |              -0.14% |
| Modeled FP Cost (₹130/FP)     |                ₹19,890.00 |               ₹14,560.00 |     -₹5,330 savings |
| Complete Ring Detection Rate  |                    12.50% |                   16.67% |              +4.17% |
| Household Sharing FPR         |                     0.00% |                    0.00% |                Safe |
| Cross-User Shared Network FPR |                     0.00% |                    0.00% |                Safe |
| Serial Returner FPR           |                     0.00% |                    0.00% |                Safe |
| Evidence Grounding Rate       |                       N/A |                  100.00% | Zero hallucinations |

### Operational Evaluation

The current operational evaluation snapshot additionally reports:

| Operational Metric        |                 Result |
| ------------------------- | ---------------------: |
| Ring Recall               | **100% (24/24 rings)** |
| Intervention FPR          |              **0.45%** |
| Hard-block FPR            |              **0.04%** |
| Direct Transaction Recall |             **26.21%** |
| Held-out Transactions     |             **28,591** |

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

## 6. Phase 2 Verification Reports

The repository includes detailed technical validation and audit reports:

- Master Report: [PHASE2_FINAL_REPORT.md](reports/PHASE2_FINAL_REPORT.md)
- Delta Analysis (Phase 1 → Phase 2): [PHASE2_DELTA_REPORT.md](reports/PHASE2_DELTA_REPORT.md)
- End-to-End Final Audit: [PHASE2_CANDIDATE_COVERAGE.md](reports/PHASE2_CANDIDATE_COVERAGE.md)
- Feature Ablation: [PHASE2_GRAPH_ABLATION.md](reports/PHASE2_GRAPH_ABLATION.md)
- Graph Data Quality: [GRAPH_DATA_QUALITY.md](reports/GRAPH_DATA_QUALITY.md)
- Investigation Agent Benchmark: [INVESTIGATION_EVALUATION.md](reports/INVESTIGATION_EVALUATION.md)
- Evidence Grounding & Anti-Hallucination: [EVIDENCE_GROUNDING_REPORT.md](reports/EVIDENCE_GROUNDING_REPORT.md)
- Ring Detection Analysis: [RING_DETECTION_ANALYSIS.md](reports/RING_DETECTION_ANALYSIS.md)
- Hard-Negative Safety: [HARD_NEGATIVE_GRAPH_REPORT.md](reports/HARD_NEGATIVE_GRAPH_REPORT.md)
- Temporal Generalization: [TEMPORAL_PHASE2_REPORT.md](reports/TEMPORAL_PHASE2_REPORT.md)
- Diagnostic Failure Analysis: [PHASE2_FAILURE_ANALYSIS.md](reports/PHASE2_FAILURE_ANALYSIS.md)

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


## Scope & Disclaimer

The project is intended as a **hackathon research/prototype implementation**, not a claim of production deployment or production certification.

---

**Built by Mithlesh Yadav** for Razorpay AI Buildathon 2026 — Track 02  
🔗 [LinkedIn](https://www.linkedin.com/in/mithleshyadav977/) · 📧 [mithleshyadav2062@gmail.com](mailto:mithleshyadav2062@gmail.com)
