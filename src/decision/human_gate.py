"""
RiskOrbit — Phase 3.2: Human Approval Gate & Audit System

Manages the human-in-the-loop review workflow for high-blast-radius actions,
high-value transactions, and policy escalations with complete auditability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid

from src.decision.actions import ActionType


class ApprovalStatus(str, Enum):
    """Lifecycle status of an approval request."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT_FALLBACK = "TIMEOUT_FALLBACK"


@dataclass
class ApprovalAuditRecord:
    """Immutable audit record for human review decisions."""
    request_id: str
    transaction_id: str
    customer_id: str
    proposed_action: ActionType
    final_action: ActionType
    status: ApprovalStatus
    amount: float
    tier: str
    risk_score: float
    escalation_reason: str
    created_at: str
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "request_id": self.request_id,
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "proposed_action": self.proposed_action.value,
            "final_action": self.final_action.value,
            "status": self.status.value,
            "amount": self.amount,
            "tier": self.tier,
            "risk_score": self.risk_score,
            "escalation_reason": self.escalation_reason,
            "created_at": self.created_at,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "review_notes": self.review_notes,
            "metadata": self.metadata,
        }


class HumanApprovalGate:
    """
    Orchestrates approval queues and audit logging for sensitive risk actions.
    """

    def __init__(self, fallback_action: ActionType = ActionType.DELAY_SETTLEMENT):
        self.fallback_action = fallback_action
        self._pending_queue: dict[str, ApprovalAuditRecord] = {}
        self._audit_history: list[ApprovalAuditRecord] = []

    def submit_request(
        self,
        transaction_id: str,
        customer_id: str,
        proposed_action: ActionType,
        amount: float,
        tier: str,
        risk_score: float,
        escalation_reason: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ApprovalAuditRecord:
        """Submit an action recommendation to the human approval queue."""
        request_id = f"REQ_{uuid.uuid4().hex[:12].upper()}"
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()

        record = ApprovalAuditRecord(
            request_id=request_id,
            transaction_id=transaction_id,
            customer_id=customer_id,
            proposed_action=proposed_action,
            final_action=proposed_action,
            status=ApprovalStatus.PENDING,
            amount=amount,
            tier=tier,
            risk_score=risk_score,
            escalation_reason=escalation_reason,
            created_at=ts,
            metadata=metadata or {},
        )
        self._pending_queue[request_id] = record
        return record

    def approve(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str = "Approved by fraud operations",
        timestamp: Optional[datetime] = None,
    ) -> ApprovalAuditRecord:
        """Approve proposed risk action."""
        if request_id not in self._pending_queue:
            raise KeyError(f"No pending request found with ID: {request_id}")

        record = self._pending_queue.pop(request_id)
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()

        record.status = ApprovalStatus.APPROVED
        record.reviewer_id = reviewer_id
        record.reviewed_at = ts
        record.review_notes = notes
        record.final_action = record.proposed_action

        self._audit_history.append(record)
        return record

    def reject(
        self,
        request_id: str,
        reviewer_id: str,
        override_action: ActionType = ActionType.ALLOW,
        notes: str = "Rejected by fraud operations - false alarm",
        timestamp: Optional[datetime] = None,
    ) -> ApprovalAuditRecord:
        """Reject proposed action and apply safe override."""
        if request_id not in self._pending_queue:
            raise KeyError(f"No pending request found with ID: {request_id}")

        record = self._pending_queue.pop(request_id)
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()

        record.status = ApprovalStatus.REJECTED
        record.reviewer_id = reviewer_id
        record.reviewed_at = ts
        record.review_notes = notes
        record.final_action = override_action

        self._audit_history.append(record)
        return record

    def handle_timeout(
        self,
        request_id: str,
        timestamp: Optional[datetime] = None,
    ) -> ApprovalAuditRecord:
        """Apply safe fallback policy when approval times out."""
        if request_id not in self._pending_queue:
            raise KeyError(f"No pending request found with ID: {request_id}")

        record = self._pending_queue.pop(request_id)
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()

        record.status = ApprovalStatus.TIMEOUT_FALLBACK
        record.reviewed_at = ts
        record.review_notes = f"Review timed out. Auto-downgraded to safe fallback: {self.fallback_action.value}"
        record.final_action = self.fallback_action

        self._audit_history.append(record)
        return record

    def get_pending(self) -> list[ApprovalAuditRecord]:
        """Return all pending requests."""
        return list(self._pending_queue.values())

    def get_audit_history(self) -> list[ApprovalAuditRecord]:
        """Return complete immutable history of resolved approvals."""
        return list(self._audit_history)
