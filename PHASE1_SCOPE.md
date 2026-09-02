# RiskOrbit — Phase 1 Scope Document

## Project

**RiskOrbit** — Razorpay AI Risk Manager  
**Track:** Razorpay AI Risk Manager  
**Problem:** Coordinated Refund Abuse Detection  
**Phase:** 1 — Data + Risk Detection Foundation

---

## What Phase 1 IS

- Synthetic payment/refund ecosystem generation
- Three coordinated refund-abuse patterns (A/B/C)
- Explicit hard-negative injection (6 types)
- Ring-aware leakage-resistant dataset splits
- 36-feature canonical feature pipeline
- Rule baseline, logistic regression baseline, LightGBM main model
- Threshold selection on validation data only
- Held-out evaluation (read-only)
- False-positive cost modeling
- Error analysis and failure story
- SHAP-based local explanations
- FastAPI risk-scoring endpoint (`POST /risk/score`)
- Versioned model artifacts
- pytest automated test suite
- Full documentation

---

## What Phase 1 IS NOT

The following are explicitly **NOT** implemented in Phase 1:

| Feature | Phase |
|---------|-------|
| Graph database (Neo4j/NetworkX) | Phase 2 |
| Graph investigation UI | Phase 2 |
| LLM investigation agent | Phase 2 |
| Evidence collection agent | Phase 2 |
| Decision agent | Phase 2 |
| Autonomous fraud intervention / blocking | Phase 2 |
| Live Razorpay payment execution | Phase 2 |
| Autonomous customer communication | Phase 2 |
| Kafka/Flink production streaming | Phase 2 |
| Multi-agent swarm | Phase 2 |
| Reinforcement learning | Phase 2 |
| Real customer data | Never (ethical constraint) |
| Fraud evasion / detection bypass analysis | Never (security constraint) |

---

## Phase Boundary

Phase 2 will consume Phase 1 via:
- `POST /risk/score` — the stable risk-scoring API contract
- `artifacts/riskorbit-risk-v1/` — the versioned model artifacts
- `src/api/schema.py` — the Pydantic contract (ScoreResponse)

Phase 2 must NOT require changes to the Phase 1 risk-scoring contract.

---

## Security Constraints

This project is a financial-risk **defense** system.

- No fraud-generation tooling is exposed as attack capability
- No detection-bypass strategies are documented as attacker playbooks
- No evasion analysis is published
- Synthetic abuse patterns exist ONLY for labeled evaluation data
- No real payment secrets, credentials, or PII are generated
