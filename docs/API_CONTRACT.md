# RiskOrbit — API Contract Specification

**Version:** `v3.2.0-frozen`  
**Status:** Control-Plane Gate 100% Certified  
**Base URL:** `/` or `/api/v2/ops`

---

## Overview

The RiskOrbit API provides a control-plane gate for risk investigation, non-LLM evidence grounding, counterfactual policy simulation, human approval workflows, and audit logging.

---

## Health & Governance Endpoints

### 1. Readiness Probe
`GET /ready`

- **Description:** Verifies that all risk models, graph datasets, feature pipelines, and storage engines are online.
- **Response 200 OK:**
  ```json
  {
    "status": "READY",
    "timestamp": "2026-09-01T09:00:00Z",
    "components": {
      "phase1_pipeline": true,
      "phase2_graph_engine": true,
      "case_storage": true
    }
  }
  ```

### 2. Liveness Probe
`GET /live`

- **Description:** Basic process liveness health check.
- **Response 200 OK:**
  ```json
  {
    "status": "UP",
    "timestamp": "2026-09-01T09:00:00Z"
  }
  ```

### 3. Governance State API
`GET /risk/governance`

- **Description:** Exposes system governance state, versioning, shadow mode, kill switch status, and release manifest signature.
- **Response 200 OK:**
  ```json
  {
    "environment": "Local / Replay Benchmark",
    "model_version": "riskorbit-risk-v1",
    "graph_version": "graph-v2",
    "evidence_version": "evidence-grounded-v2",
    "policy_version": "v3.2.0-frozen",
    "shadow_mode": false,
    "safe_mode": false,
    "action_pause": false,
    "release_manifest_hash": "sha256_manifest_signature",
    "artifact_hashes": {}
  }
  ```

---

## Risk Queue & Investigation Endpoints

### 4. Risk Investigation Queue
`GET /risk/queue`

- **Query Parameters:**
  - `status_filter` (optional): `RECOMMENDED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `VERIFIED`
  - `priority_filter` (optional): `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - `min_confidence` (optional): Minimum risk decision score `[0, 1]`
  - `page` (default: 1): Page number
  - `page_size` (default: 50): Number of items per page
- **Response 200 OK:** `RiskQueueResponse`
  ```json
  {
    "total": 25,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "case_id": "CASE-RING-A-01",
        "priority": "CRITICAL",
        "transaction_id": "TXN-DEMO-A9901",
        "customer_id": "CUST-FARMA-101",
        "merchant_id": "MERCH_DEMO_01",
        "ring_id": "RING_A_001",
        "pattern": "PATTERN_A_DEVICE_FARM",
        "transaction_risk": 0.88,
        "membership_confidence": 0.94,
        "evidence_strength": 0.92,
        "recommended_action": "BLOCK_TRANSACTION",
        "amount": 48500.0,
        "exposure": 48500.0,
        "status": "RECOMMENDED",
        "created_at": "2026-09-01T09:15:00Z",
        "updated_at": "2026-09-01T09:15:00Z"
      }
    ]
  }
  ```

### 5. Candidate Investigation API
`POST /risk/investigate`

- **Request Body:** `CaseInvestigationRequest`
  ```json
  {
    "candidate_id": "CUST_1001",
    "as_of_timestamp": "2026-09-01T09:15:00Z",
    "max_hops": 2
  }
  ```
- **Response 200 OK:** `CaseInvestigationResponse`
  ```json
  {
    "case_id": "CASE-39CC4C85",
    "root_entity": "CUST_1001",
    "is_candidate_ring": true,
    "relationship_risk_score": 0.895,
    "individual_risk_score": 0.88,
    "member_accounts": ["CUST_1001", "CUST_1002"],
    "evidence_records": [],
    "graph_statistics": {}
  }
  ```

---

## Non-LLM Verification & Action Impact Preview

### 6. Evidence Verification API
`GET /risk/cases/{case_id}/verification`

- **Description:** Strict non-LLM evidence verifier check with artifact hash grounding.
- **Response 200 OK:** `VerificationResultResponse`
  ```json
  {
    "case_id": "CASE-RING-A-01",
    "status": "PASSED",
    "evidence_sufficient": true,
    "contradiction_count": 0,
    "contradictions": [],
    "provenance_valid": true,
    "pit_valid": true,
    "policy_constraints_valid": true,
    "safety_constraints_valid": true,
    "verifier_version": "verifier-v2"
  }
  ```

### 7. Action Preview API
`GET /risk/cases/{case_id}/action-preview`

- **Description:** Side-effect free estimate of friction cost, review cost, and blast radius.
- **Response 200 OK:** `ActionPreviewResponse`
  ```json
  {
    "case_id": "CASE-RING-A-01",
    "action": "BLOCK_TRANSACTION",
    "target": "CUST-FARMA-101",
    "scope": "TRANSACTION",
    "rationale": "High confidence device farm collusion",
    "evidence_ids": ["EVID-DEV-001"],
    "policy_version": "v3.2.0-frozen",
    "friction_cost": 48500.0,
    "estimated_review_cost": 130.0,
    "approval_required": true,
    "expiration": "24h",
    "blast_radius": "1 account impacted"
  }
  ```

---

## Human Approval Gate APIs

### 8. Approve Case Action API
`POST /risk/cases/{case_id}/approve`

- **Headers:** `X-User-ID`, `X-User-Role` (ANALYST, SENIOR_ANALYST, ADMIN)
- **Request Body:** `ApprovalCommandRequest`
  ```json
  {
    "actor": "sr_analyst_rajesh",
    "role": "SENIOR_ANALYST",
    "reason": "Confirmed ring collusion via shared device cluster",
    "idempotency_key": "IDEM-0019283",
    "expected_version": 1
  }
  ```
- **Response 200 OK:**
  ```json
  {
    "status": "SUCCESS",
    "case": {
      "case_id": "CASE-RING-A-01",
      "version": 2,
      "status": "APPROVED",
      "final_action": "BLOCK_TRANSACTION",
      "reviewed_by": "sr_analyst_rajesh",
      "reviewed_at": "2026-09-01T09:20:00Z"
    }
  }
  ```
- **Errors:**
  - `403 Forbidden`: VIEWER role or insufficient permission for high-impact action.
  - `409 Conflict`: Version mismatch (optimistic locking failure).

### 9. Reject Case Action API
`POST /risk/cases/{case_id}/reject`

- **Response 200 OK:** Rejects proposed intervention, falling back to `ALLOW` with audit log.

### 10. Edit / Override Case Action API
`POST /risk/cases/{case_id}/edit`

- **Response 200 OK:** Senior Analyst action override.

---

## Counterfactual Simulation & Audit APIs

### 11. Counterfactual Simulation API
`POST /risk/cases/{case_id}/simulate`

- **Description:** Non-monetary counterfactual policy evaluation tagged with `status_tag: "SIMULATED"`.
- **Response 200 OK:** `SimulationResultResponse`
  ```json
  {
    "case_id": "CASE-RING-A-01",
    "predicted_action": "BLOCK_TRANSACTION",
    "estimated_protected_loss": 48500.0,
    "estimated_friction": 48500.0,
    "estimated_review_cost": 130.0,
    "net_utility": -130.0,
    "assumptions": ["Non-monetary execution guarantee"],
    "confidence": 0.95,
    "simulation_version": "sim-v2",
    "status_tag": "SIMULATED"
  }
  ```

### 12. Outcome Verification API
`GET /risk/cases/{case_id}/outcome`

- **Response 200 OK:** `OutcomeResultResponse`

### 13. Case Audit Trail API
`GET /risk/cases/{case_id}/audit`

- **Response 200 OK:** List of `AuditEventContract` items.

### 14. Analyst Feedback API
`POST /risk/cases/{case_id}/feedback`

- **Request Body:** `AnalystFeedbackRequest` (`adjudication`: `TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`, `EVIDENCE_INSUFFICIENT`)
- **Response 200 OK:** `AnalystFeedbackResponse`
