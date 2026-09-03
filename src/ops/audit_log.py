"""
RiskOrbit — Immutable Append-Only Audit Trail Module

Maintains a secure, append-only chronological log of all operational events,
investigations, human approvals, overrides, simulations, and feedback submissions.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Lifecycle audit event categories."""
    CASE_CREATED = "CASE_CREATED"
    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    ACTION_EDITED = "ACTION_EDITED"
    ACTION_APPROVED = "ACTION_APPROVED"
    ACTION_REJECTED = "ACTION_REJECTED"
    SIMULATION_EXECUTED = "SIMULATION_EXECUTED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    FEEDBACK_RECORDED = "FEEDBACK_RECORDED"
    SYSTEM_MODE_CHANGED = "SYSTEM_MODE_CHANGED"


class AuditRecord(BaseModel):
    """Immutable audit record schema."""
    event_id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:10].upper()}")
    case_id: str
    actor_id: str
    actor_role: str
    event_type: AuditEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_version: str = "riskorbit-risk-v1"
    policy_version: str = "phase3_final_policy"
    evidence_version: str = "evidence-grounded-v2"
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class AuditTrailManager:
    """
    Thread-safe, append-only manager for operational audit records.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        self._lock = threading.Lock()
        self._records: list[AuditRecord] = []
        self._persistence_path = persistence_path or Path("data/processed/audit_trail.jsonl")

    def record(
        self,
        case_id: str,
        actor_id: str,
        actor_role: str,
        event_type: AuditEventType,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        model_version: str = "riskorbit-risk-v1",
        policy_version: str = "phase3_final_policy",
        evidence_version: str = "evidence-grounded-v2",
    ) -> AuditRecord:
        """Append an immutable audit entry."""
        entry = AuditRecord(
            case_id=case_id,
            actor_id=actor_id,
            actor_role=actor_role,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            details=details or {},
            model_version=model_version,
            policy_version=policy_version,
            evidence_version=evidence_version,
        )

        with self._lock:
            self._persist_entry(entry)
            self._records.append(entry)

        return entry

    def _persist_entry(self, entry: AuditRecord) -> None:
        """Persist entry to disk in JSONL format."""
        try:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as exc:
            logger.error("Audit persistence failed for %s: %s", entry.event_id, exc)
            raise RuntimeError("Audit persistence failed; mutation was not recorded") from exc

    def get_case_audit(self, case_id: str) -> list[AuditRecord]:
        """Retrieve chronological audit entries for a specific case."""
        with self._lock:
            return [r for r in self._records if r.case_id == case_id]

    def get_recent_audit(self, limit: int = 100) -> list[AuditRecord]:
        """Retrieve recent global audit events."""
        with self._lock:
            return list(reversed(self._records[-limit:]))

    def count(self) -> int:
        """Return total audit records count."""
        with self._lock:
            return len(self._records)


# Global singleton instance
audit_trail = AuditTrailManager()
