"""
RiskOrbit — Case Queue & Lifecycle State Machine

Manages active analyst cases, deterministic priority ranking, state transitions,
idempotent approvals, edit overrides, and concurrency protection.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from src.ops.audit_log import AuditEventType, audit_trail
from src.ops.rbac import UserContext, UserRole, validate_action_permission


class CaseStatus(str, Enum):
    """Case workflow status."""
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"
    EXECUTED_SIMULATION = "EXECUTED_SIMULATION"
    VERIFIED = "VERIFIED"


class CasePriority(str, Enum):
    """Deterministic priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskCaseRecord(BaseModel):
    """Comprehensive risk case representation."""
    case_id: str
    transaction_id: str
    customer_id: str
    amount_inr: float
    timestamp: str

    # Scores
    phase1_risk: float
    membership_confidence: float
    evidence_strength: float
    decision_score: float
    tier: str

    # Policy & Action
    recommended_action: str
    final_action: str
    requires_human_approval: bool
    escalation_reason: Optional[str] = None
    action_reason: str
    expected_friction_cost_inr: float = 0.0

    # Ring & Pattern
    ring_id: Optional[str] = None
    pattern_type: Optional[str] = None
    is_hard_negative: bool = False
    hard_negative_type: Optional[str] = None

    # Status & Workflow
    status: CaseStatus = CaseStatus.RECOMMENDED
    priority: CasePriority = CasePriority.MEDIUM
    version: int = 1
    idempotency_keys: list[str] = Field(default_factory=list)

    # Review details
    assigned_reviewer: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None
    original_action: Optional[str] = None

    # Audit & Entities
    member_count: int = 1
    shared_devices: list[str] = Field(default_factory=list)
    shared_ips: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def compute_priority(
    decision_score: float,
    amount_inr: float,
    requires_human_approval: bool,
    tier: str,
) -> CasePriority:
    """Compute deterministic case priority."""
    if requires_human_approval or amount_inr >= 50000.0 or decision_score >= 0.70 or tier == "PRIMARY":
        return CasePriority.CRITICAL
    elif decision_score >= 0.40 or tier == "SECONDARY":
        return CasePriority.HIGH
    elif decision_score >= 0.20:
        return CasePriority.MEDIUM
    return CasePriority.LOW


class CaseManager:
    """Thread-safe manager for risk queue and case transitions."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cases: dict[str, RiskCaseRecord] = {}
        self._txn_to_case: dict[str, str] = {}
        self._idempotency_map: dict[str, RiskCaseRecord] = {}

    def register_case(self, case: RiskCaseRecord) -> RiskCaseRecord:
        """Register or update a case in the queue."""
        with self._lock:
            self._cases[case.case_id] = case
            self._txn_to_case[case.transaction_id] = case.case_id
            return case

    def get_case(self, case_id: str) -> Optional[RiskCaseRecord]:
        """Fetch case by ID."""
        with self._lock:
            return self._cases.get(case_id)

    def get_case_by_transaction(self, transaction_id: str) -> Optional[RiskCaseRecord]:
        """Fetch case by transaction ID."""
        with self._lock:
            case_id = self._txn_to_case.get(transaction_id)
            return self._cases.get(case_id) if case_id else None

    def list_queue(
        self,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        pattern_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        search_query: Optional[str] = None,
        limit: int = 200,
    ) -> list[RiskCaseRecord]:
        """Query and filter risk cases with deterministic sort."""
        with self._lock:
            results = list(self._cases.values())

        if status_filter:
            results = [c for c in results if c.status.value == status_filter]
        if priority_filter:
            results = [c for c in results if c.priority.value == priority_filter]
        if pattern_filter:
            results = [c for c in results if c.pattern_type == pattern_filter]
        if action_filter:
            results = [c for c in results if c.final_action == action_filter or c.recommended_action == action_filter]
        if min_score is not None:
            results = [c for c in results if c.decision_score >= min_score]
        if max_score is not None:
            results = [c for c in results if c.decision_score <= max_score]
        if search_query:
            q = search_query.lower()
            results = [
                c for c in results
                if q in c.case_id.lower()
                or q in c.transaction_id.lower()
                or q in c.customer_id.lower()
                or (c.ring_id and q in c.ring_id.lower())
            ]

        # Sort: CRITICAL > HIGH > MEDIUM > LOW, then by decision score desc
        p_order = {CasePriority.CRITICAL: 0, CasePriority.HIGH: 1, CasePriority.MEDIUM: 2, CasePriority.LOW: 3}
        results.sort(key=lambda c: (p_order.get(c.priority, 4), -c.decision_score, -c.amount_inr))
        return results[:limit]

    def approve_case(
        self,
        case_id: str,
        user: UserContext,
        idempotency_key: Optional[str] = None,
        notes: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> RiskCaseRecord:
        """Approve proposed action on a case with concurrency and permission checks."""
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_map:
                return self._idempotency_map[idempotency_key]

            case = self._cases.get(case_id)
            if not case:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

            if expected_version is not None and case.version != expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Case version {case.version} does not match expected {expected_version}.",
                )

            # RBAC check for action MUST happen before status check
            validate_action_permission(user, case.recommended_action)

            if case.status in (CaseStatus.APPROVED, CaseStatus.VERIFIED, CaseStatus.EXECUTED_SIMULATION):
                return case  # Idempotent return

            prev_state = case.status.value
            case.status = CaseStatus.APPROVED
            case.final_action = case.recommended_action
            case.reviewed_by = user.user_id
            case.reviewed_at = datetime.now(timezone.utc).isoformat()
            case.reviewer_notes = notes
            case.version += 1
            case.updated_at = datetime.now(timezone.utc).isoformat()

            if idempotency_key:
                case.idempotency_keys.append(idempotency_key)
                self._idempotency_map[idempotency_key] = case

        audit_trail.record(
            case_id=case.case_id,
            actor_id=user.user_id,
            actor_role=user.role.value,
            event_type=AuditEventType.ACTION_APPROVED,
            previous_state=prev_state,
            new_state=case.status.value,
            details={"action": case.final_action, "notes": notes, "version": case.version},
        )
        return case

    def edit_case_action(
        self,
        case_id: str,
        new_action: str,
        user: UserContext,
        reason: str,
        idempotency_key: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> RiskCaseRecord:
        """Override / edit case action recommendation."""
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_map:
                return self._idempotency_map[idempotency_key]

            case = self._cases.get(case_id)
            if not case:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

            if expected_version is not None and case.version != expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Case version {case.version} does not match expected {expected_version}.",
                )

            # Editing/overriding requires at least SENIOR_ANALYST or ADMIN
            if user.role not in (UserRole.SENIOR_ANALYST, UserRole.ADMIN):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Action overrides require SENIOR_ANALYST or ADMIN role.",
                )

            validate_action_permission(user, new_action)

            prev_state = case.status.value
            prev_action = case.final_action
            case.original_action = case.recommended_action
            case.final_action = new_action
            case.status = CaseStatus.EDITED
            case.reviewed_by = user.user_id
            case.reviewed_at = datetime.now(timezone.utc).isoformat()
            case.reviewer_notes = f"Override reason: {reason}"
            case.version += 1
            case.updated_at = datetime.now(timezone.utc).isoformat()

            if idempotency_key:
                case.idempotency_keys.append(idempotency_key)
                self._idempotency_map[idempotency_key] = case

        audit_trail.record(
            case_id=case.case_id,
            actor_id=user.user_id,
            actor_role=user.role.value,
            event_type=AuditEventType.ACTION_EDITED,
            previous_state=prev_state,
            new_state=case.status.value,
            details={
                "original_action": prev_action,
                "new_action": new_action,
                "reason": reason,
                "version": case.version,
            },
        )
        return case

    def reject_case(
        self,
        case_id: str,
        user: UserContext,
        reason: str,
        idempotency_key: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> RiskCaseRecord:
        """Reject proposed intervention, falling back to ALLOW with audit."""
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_map:
                return self._idempotency_map[idempotency_key]

            case = self._cases.get(case_id)
            if not case:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

            if expected_version is not None and case.version != expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Case version {case.version} does not match expected {expected_version}.",
                )

            if user.role == UserRole.VIEWER:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VIEWER cannot reject actions.")

            prev_state = case.status.value
            prev_action = case.final_action
            case.original_action = case.recommended_action
            case.final_action = "ALLOW"
            case.status = CaseStatus.REJECTED
            case.reviewed_by = user.user_id
            case.reviewed_at = datetime.now(timezone.utc).isoformat()
            case.reviewer_notes = f"Rejection reason: {reason}"
            case.version += 1
            case.updated_at = datetime.now(timezone.utc).isoformat()

            if idempotency_key:
                case.idempotency_keys.append(idempotency_key)
                self._idempotency_map[idempotency_key] = case

        audit_trail.record(
            case_id=case.case_id,
            actor_id=user.user_id,
            actor_role=user.role.value,
            event_type=AuditEventType.ACTION_REJECTED,
            previous_state=prev_state,
            new_state=case.status.value,
            details={"original_action": prev_action, "final_action": "ALLOW", "reason": reason},
        )
        return case

    def simulate_execution(self, case_id: str, actor_id: str = "simulator") -> RiskCaseRecord:
        """Advance case to EXECUTED_SIMULATION and VERIFIED."""
        with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

            prev_state = case.status.value
            case.status = CaseStatus.EXECUTED_SIMULATION
            case.version += 1
            case.updated_at = datetime.now(timezone.utc).isoformat()

        audit_trail.record(
            case_id=case.case_id,
            actor_id=actor_id,
            actor_role="SIMULATOR",
            event_type=AuditEventType.SIMULATION_EXECUTED,
            previous_state=prev_state,
            new_state=case.status.value,
            details={"executed_action": case.final_action, "simulated": True},
        )

        with self._lock:
            case.status = CaseStatus.VERIFIED
            case.updated_at = datetime.now(timezone.utc).isoformat()

        audit_trail.record(
            case_id=case.case_id,
            actor_id=actor_id,
            actor_role="VERIFIER",
            event_type=AuditEventType.OUTCOME_VERIFIED,
            previous_state=CaseStatus.EXECUTED_SIMULATION.value,
            new_state=case.status.value,
            details={"verification_status": "PASSED", "idempotent": True},
        )
        return case


# Global singleton instance
case_manager = CaseManager()
