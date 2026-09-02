"""
RiskOrbit — Control-Plane API Contracts & Domain Schemas

Provides strict, validated Pydantic models for:
- Queue & Case list queries
- GraphSnapshot
- Grounded Evidence Bundle
- Non-LLM Outcome Verification
- Counterfactual Decision & Action Preview
- Human Approval, Rejection, & Override
- Counterfactual Simulation & Outcome Verification
- Chronological Append-Only Audit Trail
- Analyst Feedback
- System Health, Readiness, Liveness
- Governance State
- Unified Standardized Error Responses
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums & Common Types
# ---------------------------------------------------------------------------

class CaseStateMachineState(str, Enum):
    CREATED = "CREATED"
    INVESTIGATING = "INVESTIGATING"
    EVIDENCE_READY = "EVIDENCE_READY"
    VERIFIED = "VERIFIED"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"
    SIMULATED = "SIMULATED"
    VERIFIED_OUTCOME = "VERIFIED_OUTCOME"
    CLOSED = "CLOSED"


class ComponentHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


# ---------------------------------------------------------------------------
# Standard Error Contract
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    code: str = Field(..., example="STATE_CONFLICT")
    message: str = Field(..., example="Conflict: Case version 1 does not match expected version 2.")
    request_id: str = Field(..., example="req_abc123")
    case_id: Optional[str] = Field(None, example="CASE_20260901_001")
    retryable: bool = Field(False)


# ---------------------------------------------------------------------------
# Queue & Case List Schemas
# ---------------------------------------------------------------------------

class RiskQueueItemResponse(BaseModel):
    case_id: str
    priority: str
    transaction_id: str
    customer_id: str
    merchant_id: str
    ring_id: Optional[str] = None
    pattern: Optional[str] = None
    transaction_risk: float
    membership_confidence: float
    evidence_strength: float
    recommended_action: str
    amount: float
    exposure: float
    status: str
    created_at: str
    updated_at: str


class RiskQueueResponse(BaseModel):
    items: List[RiskQueueItemResponse]
    total_count: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Graph Snapshot Schema
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship_type: str
    strength: float = 1.0
    timestamp: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class GraphSnapshot(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    graph_statistics: Dict[str, Any]
    as_of_timestamp: str
    max_hops: int
    graph_version: str = "graph-v2"


# ---------------------------------------------------------------------------
# Grounded Evidence Schema
# ---------------------------------------------------------------------------

class EvidenceRecordContract(BaseModel):
    evidence_id: str
    category: str
    confidence: str
    statement: str
    supporting_entity_ids: List[str] = Field(default_factory=list)
    supporting_event_ids: List[str] = Field(default_factory=list)
    metric_value: Optional[float] = None
    metric_description: Optional[str] = None
    timestamp: Optional[str] = None


class EvidenceBundleResponse(BaseModel):
    case_id: str
    evidence_records: List[EvidenceRecordContract]
    grounding_status: str = "VERIFIED_GROUNDED"
    provenance_status: str = "VALID_SHA256"
    evidence_version: str = "evidence-grounded-v2"


# ---------------------------------------------------------------------------
# Verification Schema
# ---------------------------------------------------------------------------

class VerificationResultResponse(BaseModel):
    case_id: str
    status: str = "PASSED"
    evidence_sufficient: bool = True
    contradiction_count: int = 0
    contradictions: List[str] = Field(default_factory=list)
    provenance_valid: bool = True
    pit_valid: bool = True
    policy_constraints_valid: bool = True
    safety_constraints_valid: bool = True
    verifier_version: str = "verifier-v2"
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Decision & Action Preview Schemas
# ---------------------------------------------------------------------------

class DecisionResultResponse(BaseModel):
    case_id: str
    transaction_risk: float
    membership_confidence: float
    evidence_strength: float
    relationship_strength: float
    temporal_relevance: float
    decision_score: float
    risk_tier: str
    recommended_action: str
    reason: str
    why_not_stronger: str
    why_not_weaker: str
    policy_version: str = "v3.2.0-frozen"


class ActionPreviewResponse(BaseModel):
    case_id: str
    action: str
    target: str
    scope: str
    rationale: str
    evidence_ids: List[str]
    policy_version: str = "v3.2.0-frozen"
    friction_cost: float
    estimated_review_cost: float
    approval_required: bool
    expiration: str
    blast_radius: str


# ---------------------------------------------------------------------------
# Human Approval Schemas
# ---------------------------------------------------------------------------

class ApprovalCommandRequest(BaseModel):
    actor: str = Field(..., example="analyst_01")
    role: str = Field("ANALYST", example="ANALYST")
    reason: str = Field(..., example="Verified device cluster match")
    expected_version: Optional[int] = Field(None, example=1)
    idempotency_key: Optional[str] = Field(None, example="key-approve-1001")


class ActionOverrideCommandRequest(BaseModel):
    actor: str = Field(..., example="senior_analyst_01")
    role: str = Field("SENIOR_ANALYST", example="SENIOR_ANALYST")
    new_action: str = Field(..., example="STEP_UP_2FA")
    reason: str = Field(..., example="Lower blast radius recommendation")
    expected_version: Optional[int] = Field(None, example=1)
    idempotency_key: Optional[str] = Field(None, example="key-edit-1001")


# ---------------------------------------------------------------------------
# Simulation Schema
# ---------------------------------------------------------------------------

class SimulationCommandRequest(BaseModel):
    policy_version: Optional[str] = Field("v3.2.0-frozen")
    optional_action_override: Optional[str] = None
    simulation_parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationResultResponse(BaseModel):
    case_id: str
    predicted_action: str
    estimated_protected_loss: float
    estimated_friction: float
    estimated_review_cost: float
    net_utility: float
    assumptions: List[str]
    confidence: float
    simulation_version: str = "sim-v2"
    status_tag: str = "SIMULATED"


# ---------------------------------------------------------------------------
# Outcome Verification Schema
# ---------------------------------------------------------------------------

class OutcomeResultResponse(BaseModel):
    case_id: str
    execution_status: str
    verification_status: str
    invariant_results: List[str]
    final_simulated_state: str
    cost: float
    timestamp: str


# ---------------------------------------------------------------------------
# Audit API Schemas
# ---------------------------------------------------------------------------

class AuditEventContract(BaseModel):
    event_id: str
    case_id: str
    actor_id: str
    actor_role: str
    event_type: str
    timestamp: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    model_version: str = "riskorbit-risk-v1"
    policy_version: str = "v3.2.0-frozen"
    evidence_version: str = "evidence-grounded-v2"
    reason: Optional[str] = None
    request_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Feedback Schema
# ---------------------------------------------------------------------------

class AnalystFeedbackRequest(BaseModel):
    analyst: str = Field(..., example="analyst_01")
    role: str = Field("ANALYST", example="ANALYST")
    adjudication: str = Field(..., example="TRUE_POSITIVE")
    reason: str = Field(..., example="Ground truth verified collusive ring")
    evidence_conflict: Optional[str] = None
    suggested_policy_tuning: Optional[str] = None


class AnalystFeedbackResponse(BaseModel):
    feedback_id: str
    case_id: str
    transaction_id: str
    adjudication: str
    analyst: str
    role: str
    reason: str
    timestamp: str


# ---------------------------------------------------------------------------
# System Health & Governance Schemas
# ---------------------------------------------------------------------------

class ComponentHealthDetail(BaseModel):
    status: ComponentHealthState
    details: Optional[str] = None


class SystemHealthResponse(BaseModel):
    overall_status: ComponentHealthState
    components: Dict[str, ComponentHealthDetail]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernanceStateResponse(BaseModel):
    environment: str = "Local / Replay Benchmark"
    model_version: str = "riskorbit-risk-v1"
    graph_version: str = "graph-v2"
    evidence_version: str = "evidence-grounded-v2"
    policy_version: str = "v3.2.0-frozen"
    shadow_mode: bool = False
    safe_mode: bool = False
    action_pause: bool = False
    release_manifest_hash: str
    artifact_hashes: Dict[str, str]
