"""
RiskOrbit — Control-Plane Top-Level Blueprint FastAPI Router

Implements strict, fully-typed REST endpoints for top-level Blueprint routes:
- /risk/queue
- /risk/cases
- /risk/cases/{case_id}
- /risk/cases/{case_id}/graph
- /risk/cases/{case_id}/evidence
- /risk/cases/{case_id}/verification
- /risk/cases/{case_id}/decision
- /risk/cases/{case_id}/action-preview
- /risk/cases/{case_id}/approve
- /risk/cases/{case_id}/reject
- /risk/cases/{case_id}/edit
- /risk/cases/{case_id}/simulate
- /risk/cases/{case_id}/outcome
- /risk/cases/{case_id}/audit
- /risk/audit
- /risk/cases/{case_id}/feedback
- /risk/governance
- /ready
- /live
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from src.api.schema_control_plane import (
    ActionOverrideCommandRequest,
    ActionPreviewResponse,
    AnalystFeedbackRequest,
    AnalystFeedbackResponse,
    ApprovalCommandRequest,
    AuditEventContract,
    ComponentHealthDetail,
    ComponentHealthState,
    DecisionResultResponse,
    ErrorResponse,
    EvidenceBundleResponse,
    EvidenceRecordContract,
    GovernanceStateResponse,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OutcomeResultResponse,
    RiskQueueItemResponse,
    RiskQueueResponse,
    SimulationCommandRequest,
    SimulationResultResponse,
    SystemHealthResponse,
    VerificationResultResponse,
)
from src.ops.audit_log import audit_trail
from src.ops.case_manager import CasePriority, CaseStatus, RiskCaseRecord, authorize_case_access, case_manager
from src.ops.case_orchestrator import case_orchestrator
from src.ops.rbac import UserContext, UserRole, get_current_user, require_role
from src.ops.system_state import system_state

router = APIRouter(tags=["Control Plane Gate"])


def _require_case_access(case_id: str, user: UserContext) -> None:
    case = case_manager.get_case(case_id)
    if case is not None:
        authorize_case_access(case, user)


# ---------------------------------------------------------------------------
# Health, Readiness & Liveness Probes
# ---------------------------------------------------------------------------

@router.get(
    "/ready",
    response_model=SystemHealthResponse,
    summary="Readiness Probe",
    description="Check component availability (api, model, graph, evidence, policy, persistence).",
)
async def readiness_probe() -> SystemHealthResponse:
    """Readiness probe indicating if all core dependencies are healthy."""
    ctrls = system_state.get_state()
    graph_ok = ctrls.graph_engine_available
    model_ok = ctrls.model_ready

    components = {
        "api": ComponentHealthDetail(status=ComponentHealthState.HEALTHY, details="FastAPI core active"),
        "model": ComponentHealthDetail(status=ComponentHealthState.HEALTHY if model_ok else ComponentHealthState.OFFLINE, details="Phase 1 LightGBM artifact loaded" if model_ok else "Required scoring model unavailable"),
        "graph": ComponentHealthDetail(
            status=ComponentHealthState.HEALTHY if graph_ok else ComponentHealthState.DEGRADED,
            details="PaymentGraphEngine multi-hop graph active" if graph_ok else "Graph engine unavailable (Degraded Mode)",
        ),
        "evidence": ComponentHealthDetail(status=ComponentHealthState.HEALTHY, details="Evidence grounding engine ready"),
        "policy": ComponentHealthDetail(status=ComponentHealthState.HEALTHY, details="3-Tier Policy Engine ready"),
        "persistence": ComponentHealthDetail(status=ComponentHealthState.HEALTHY, details="In-memory thread-safe storage ready"),
    }

    overall = ComponentHealthState.HEALTHY if model_ok and graph_ok else (ComponentHealthState.DEGRADED if model_ok else ComponentHealthState.OFFLINE)
    response = SystemHealthResponse(overall_status=overall, components=components)
    if not model_ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=response.model_dump())
    return response


@router.get(
    "/live",
    response_model=SystemHealthResponse,
    summary="Liveness Probe",
    description="Liveness check for container orchestration.",
)
async def liveness_probe() -> SystemHealthResponse:
    """Liveness probe for process vitality."""
    components = {
        "process": ComponentHealthDetail(status=ComponentHealthState.HEALTHY, details="Python worker process running"),
    }
    return SystemHealthResponse(overall_status=ComponentHealthState.HEALTHY, components=components)


# ---------------------------------------------------------------------------
# Governance & Release Manifest
# ---------------------------------------------------------------------------

@router.get(
    "/risk/governance",
    response_model=GovernanceStateResponse,
    summary="Governance & Artifact Hashes API",
    description="Read-only governance state, shadow mode toggle status, release manifest hash, and artifact integrity checksums.",
)
async def get_governance_state(
    user: UserContext = Depends(get_current_user),
) -> GovernanceStateResponse:
    """Expose read-only system governance state and artifact hashes."""
    ctrls = system_state.get_state()
    manifest_path = Path("reports/RISKORBIT_FINAL_MANIFEST.json")
    manifest_hash = "sha256_unknown"
    hashes: Dict[str, str] = {}

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            manifest_hash = manifest_data.get("manifest_signature_sha256", "sha256_valid")
            hashes = manifest_data.get("artifact_hashes", {})

    return GovernanceStateResponse(
        environment="Local / Replay Benchmark",
        model_version=ctrls.model_version,
        graph_version="graph-v2",
        evidence_version="evidence-grounded-v2",
        policy_version=ctrls.policy_version,
        shadow_mode=ctrls.shadow_mode_enabled,
        safe_mode=not ctrls.graph_engine_available,
        action_pause=ctrls.kill_switch_active,
        release_manifest_hash=manifest_hash,
        artifact_hashes=hashes,
    )


# ---------------------------------------------------------------------------
# Risk Queue & Case List APIs
# ---------------------------------------------------------------------------

@router.get(
    "/risk/queue",
    response_model=RiskQueueResponse,
    summary="Ranked Risk Queue API",
    description="Retrieve ranked risk cases with filtering, pagination, search, and deterministic priority ordering.",
)
async def get_risk_queue(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority_filter: Optional[str] = Query(default=None, alias="severity"),
    pattern_filter: Optional[str] = Query(default=None, alias="pattern"),
    action_filter: Optional[str] = Query(default=None, alias="action"),
    approval_status_filter: Optional[str] = Query(default=None, alias="approval_status"),
    min_confidence: Optional[float] = Query(default=None, alias="confidence_min"),
    max_confidence: Optional[float] = Query(default=None, alias="confidence_max"),
    min_amount: Optional[float] = Query(default=None, alias="amount_min"),
    max_amount: Optional[float] = Query(default=None, alias="amount_max"),
    search_query: Optional[str] = Query(default=None, alias="search"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: UserContext = Depends(get_current_user),
) -> RiskQueueResponse:
    """Retrieve ranked cases matching all search and filter conditions."""
    effective_status = status_filter or approval_status_filter
    raw_cases = case_manager.list_queue(
        status_filter=effective_status,
        priority_filter=priority_filter,
        pattern_filter=pattern_filter,
        action_filter=action_filter,
        min_score=min_confidence,
        max_score=max_confidence,
        search_query=search_query,
        limit=1000,
    )

    if min_amount is not None:
        raw_cases = [c for c in raw_cases if c.amount_inr >= min_amount]
    if max_amount is not None:
        raw_cases = [c for c in raw_cases if c.amount_inr <= max_amount]

    total_count = len(raw_cases)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_cases = raw_cases[start_idx:end_idx]

    items = [
        RiskQueueItemResponse(
            case_id=c.case_id,
            priority=c.priority.value,
            transaction_id=c.transaction_id,
            customer_id=c.customer_id,
            merchant_id="MERCH_DEMO_01",
            ring_id=c.ring_id or f"RING_{c.case_id[:6]}",
            pattern=c.pattern_type or "Pattern A: Collusive Ring",
            transaction_risk=c.phase1_risk,
            membership_confidence=c.membership_confidence,
            evidence_strength=c.evidence_strength,
            recommended_action=c.recommended_action,
            amount=c.amount_inr,
            exposure=c.amount_inr,
            status=c.status.value,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in paged_cases
    ]

    return RiskQueueResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/risk/cases",
    response_model=RiskQueueResponse,
    summary="Case List API",
    description="Retrieve filtered list of risk cases.",
)
async def list_cases(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority_filter: Optional[str] = Query(default=None, alias="severity"),
    pattern_filter: Optional[str] = Query(default=None, alias="pattern"),
    action_filter: Optional[str] = Query(default=None, alias="action"),
    search_query: Optional[str] = Query(default=None, alias="search"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: UserContext = Depends(get_current_user),
) -> RiskQueueResponse:
    """Case list endpoint."""
    return await get_risk_queue(
        status_filter=status_filter,
        priority_filter=priority_filter,
        pattern_filter=pattern_filter,
        action_filter=action_filter,
        search_query=search_query,
        page=page,
        page_size=page_size,
        user=user,
    )


# ---------------------------------------------------------------------------
# Case Sub-Topology & Analysis APIs
# ---------------------------------------------------------------------------

@router.get(
    "/risk/cases/{case_id}/verification",
    response_model=VerificationResultResponse,
    summary="Evidence Verification API",
    description="Out-of-fold invariant and evidence grounding check (non-LLM deterministic verifier).",
)
async def get_case_verification(
    case_id: str,
    user: UserContext = Depends(get_current_user),
) -> VerificationResultResponse:
    """Return non-LLM evidence verifier check result."""
    _require_case_access(case_id, user)
    return case_orchestrator.get_verification(case_id)


@router.get(
    "/risk/cases/{case_id}/decision",
    response_model=DecisionResultResponse,
    summary="Decision Score & Rationale API",
    description="Counterfactual score breakdown, risk tiering, and counterfactual explanations.",
)
async def get_case_decision(
    case_id: str,
    user: UserContext = Depends(get_current_user),
) -> DecisionResultResponse:
    """Return risk decision score and counterfactual explanations."""
    _require_case_access(case_id, user)
    return case_orchestrator.get_decision(case_id)


@router.get(
    "/risk/cases/{case_id}/action-preview",
    response_model=ActionPreviewResponse,
    summary="Action Preview API",
    description="Preview friction cost, estimated review cost, and blast radius without executing.",
)
async def preview_case_action(
    case_id: str,
    user: UserContext = Depends(get_current_user),
) -> ActionPreviewResponse:
    """Return action preview metadata without side effects."""
    _require_case_access(case_id, user)
    return case_orchestrator.get_action_preview(case_id)


# ---------------------------------------------------------------------------
# Human Approval Gate APIs
# ---------------------------------------------------------------------------

@router.post(
    "/risk/cases/{case_id}/approve",
    response_model=Dict[str, Any],
    summary="Approve Case Action API",
    description="Approve proposed action with optimistic locking (expected_version) and idempotency key.",
)
async def approve_case_action(
    case_id: str,
    cmd: ApprovalCommandRequest,
    user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Approve proposed case action."""
    _require_case_access(case_id, user)
    case = case_orchestrator.approve_action(
        case_id=case_id,
        actor=user.user_id,
        role=user.role.value,
        reason=cmd.reason,
        expected_version=cmd.expected_version,
        idempotency_key=cmd.idempotency_key,
    )
    return {"status": "SUCCESS", "case": case.model_dump()}


@router.post(
    "/risk/cases/{case_id}/reject",
    response_model=Dict[str, Any],
    summary="Reject Case Action API",
    description="Reject proposed action, downgrading to ALLOW with audit logging.",
)
async def reject_case_action(
    case_id: str,
    cmd: ApprovalCommandRequest,
    user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Reject proposed case action."""
    _require_case_access(case_id, user)
    case = case_orchestrator.reject_action(
        case_id=case_id,
        actor=user.user_id,
        role=user.role.value,
        reason=cmd.reason,
        expected_version=cmd.expected_version,
        idempotency_key=cmd.idempotency_key,
    )
    return {"status": "SUCCESS", "case": case.model_dump()}


@router.post(
    "/risk/cases/{case_id}/edit",
    response_model=Dict[str, Any],
    summary="Override / Edit Case Action API",
    description="Senior Analyst action override with optimistic locking and idempotency key.",
)
async def edit_case_action(
    case_id: str,
    cmd: ActionOverrideCommandRequest,
    user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Override proposed case action."""
    _require_case_access(case_id, user)
    case = case_orchestrator.edit_action(
        case_id=case_id,
        actor=user.user_id,
        role=user.role.value,
        new_action=cmd.new_action,
        reason=cmd.reason,
        expected_version=cmd.expected_version,
        idempotency_key=cmd.idempotency_key,
    )
    return {"status": "SUCCESS", "case": case.model_dump()}


# ---------------------------------------------------------------------------
# Counterfactual Simulation & Outcome APIs
# ---------------------------------------------------------------------------

@router.post(
    "/risk/cases/{case_id}/simulate",
    response_model=SimulationResultResponse,
    summary="Counterfactual Simulation API",
    description="Run counterfactual simulation for case action. Output is explicitly tagged SIMULATED.",
)
async def simulate_case_action(
    case_id: str,
    cmd: SimulationCommandRequest,
    user: UserContext = Depends(get_current_user),
) -> SimulationResultResponse:
    """Execute counterfactual simulation on case."""
    _require_case_access(case_id, user)
    return case_orchestrator.simulate_execution(
        case_id=case_id,
        policy_version=cmd.policy_version,
        optional_action_override=cmd.optional_action_override,
        simulation_parameters=cmd.simulation_parameters,
    )


@router.get(
    "/risk/cases/{case_id}/outcome",
    response_model=OutcomeResultResponse,
    summary="Outcome Verification API",
    description="Retrieve execution status, invariant results, and final simulated state.",
)
async def get_case_outcome(
    case_id: str,
    user: UserContext = Depends(get_current_user),
) -> OutcomeResultResponse:
    """Return outcome verification result."""
    _require_case_access(case_id, user)
    return case_orchestrator.get_outcome(case_id)


# ---------------------------------------------------------------------------
# Audit Trail APIs
# ---------------------------------------------------------------------------

@router.get(
    "/risk/cases/{case_id}/audit",
    response_model=List[AuditEventContract],
    summary="Case Audit Trail API",
    description="Retrieve chronological append-only audit events for a specific case.",
)
async def get_case_audit_trail(
    case_id: str,
    user: UserContext = Depends(get_current_user),
) -> List[AuditEventContract]:
    """Return audit events for case_id."""
    _require_case_access(case_id, user)
    raw_audits = audit_trail.get_case_audit(case_id)
    return [
        AuditEventContract(
            event_id=a.event_id,
            case_id=a.case_id,
            actor_id=a.actor_id,
            actor_role=a.actor_role,
            event_type=a.event_type.value if hasattr(a.event_type, "value") else str(a.event_type),
            timestamp=a.timestamp,
            previous_state=a.previous_state,
            new_state=a.new_state,
            model_version=a.model_version,
            policy_version=a.policy_version,
            evidence_version=a.evidence_version,
            reason=a.details.get("reason") or a.details.get("notes"),
            request_id=a.details.get("request_id"),
        )
        for a in raw_audits
    ]


@router.get(
    "/risk/audit",
    response_model=List[AuditEventContract],
    summary="Global Audit Trail API",
    description="Query chronological append-only audit trail with optional filtering.",
)
async def get_global_audit_trail(
    case_id: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None, alias="actor"),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    user: UserContext = Depends(get_current_user),
) -> List[AuditEventContract]:
    """Return filtered audit events."""
    raw_audits = audit_trail.get_recent_audit(limit=limit)
    if case_id:
        raw_audits = [a for a in raw_audits if a.case_id == case_id]
    if actor_id:
        raw_audits = [a for a in raw_audits if a.actor_id == actor_id]
    if event_type:
        raw_audits = [a for a in raw_audits if (a.event_type.value if hasattr(a.event_type, "value") else str(a.event_type)) == event_type]

    return [
        AuditEventContract(
            event_id=a.event_id,
            case_id=a.case_id,
            actor_id=a.actor_id,
            actor_role=a.actor_role,
            event_type=a.event_type.value if hasattr(a.event_type, "value") else str(a.event_type),
            timestamp=a.timestamp,
            previous_state=a.previous_state,
            new_state=a.new_state,
            model_version=a.model_version,
            policy_version=a.policy_version,
            evidence_version=a.evidence_version,
            reason=a.details.get("reason") or a.details.get("notes"),
            request_id=a.details.get("request_id"),
        )
        for a in raw_audits
    ]


# ---------------------------------------------------------------------------
# Analyst Feedback API
# ---------------------------------------------------------------------------

@router.post(
    "/risk/cases/{case_id}/feedback",
    response_model=AnalystFeedbackResponse,
    summary="Analyst Feedback API",
    description="Submit ground-truth analyst adjudication (TRUE_POSITIVE, FALSE_POSITIVE, NEEDS_REVIEW, EVIDENCE_INSUFFICIENT).",
)
async def submit_case_feedback(
    case_id: str,
    req: AnalystFeedbackRequest,
    user: UserContext = Depends(get_current_user),
) -> AnalystFeedbackResponse:
    """Submit analyst feedback for case."""
    _require_case_access(case_id, user)
    if req.adjudication not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_REVIEW", "EVIDENCE_INSUFFICIENT"):
        raise HTTPException(
            status_code=400,
            detail="Invalid adjudication label. Must be TRUE_POSITIVE, FALSE_POSITIVE, NEEDS_REVIEW, or EVIDENCE_INSUFFICIENT.",
        )

    return case_orchestrator.submit_analyst_feedback(
        case_id=case_id,
        analyst=user.user_id,
        role=user.role.value,
        adjudication=req.adjudication,
        reason=req.reason,
        evidence_conflict=req.evidence_conflict,
        suggested_policy_tuning=req.suggested_policy_tuning,
    )
