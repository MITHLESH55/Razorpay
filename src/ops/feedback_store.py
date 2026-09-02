"""
RiskOrbit — Analyst Feedback & Adjudication Store

Captures human analyst domain ground-truth adjudications and feedback
without modifying frozen model weights or triggering automated retraining loops.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class AdjudicationOutcome(str, Enum):
    """Analyst adjudication classifications."""
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


class FeedbackRecord(BaseModel):
    """Structured analyst adjudication record."""
    feedback_id: str = Field(default_factory=lambda: f"FDBK-{uuid.uuid4().hex[:8].upper()}")
    case_id: str
    transaction_id: str
    adjudication: AdjudicationOutcome
    actor_id: str
    actor_role: str
    notes: Optional[str] = None
    evidence_conflict_notes: Optional[str] = None
    suggested_policy_tuning: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_version: str = "riskorbit-risk-v1"
    policy_version: str = "phase3_final_policy"
    status_notice: str = "Feedback captured — model remains frozen."


class FeedbackStore:
    """Thread-safe store for analyst adjudication records."""

    def __init__(self, persistence_path: Optional[Path] = None):
        self._lock = threading.Lock()
        self._records: list[FeedbackRecord] = []
        self._persistence_path = persistence_path or Path("data/processed/analyst_feedback.jsonl")

    def submit_feedback(
        self,
        case_id: str,
        transaction_id: str,
        adjudication: AdjudicationOutcome,
        actor_id: str,
        actor_role: str,
        notes: Optional[str] = None,
        evidence_conflict_notes: Optional[str] = None,
        suggested_policy_tuning: Optional[str] = None,
    ) -> FeedbackRecord:
        """Record an analyst adjudication decision."""
        record = FeedbackRecord(
            case_id=case_id,
            transaction_id=transaction_id,
            adjudication=adjudication,
            actor_id=actor_id,
            actor_role=actor_role,
            notes=notes,
            evidence_conflict_notes=evidence_conflict_notes,
            suggested_policy_tuning=suggested_policy_tuning,
        )

        with self._lock:
            self._records.append(record)
            self._persist_record(record)

        return record

    def _persist_record(self, record: FeedbackRecord) -> None:
        """Save feedback entry to disk."""
        try:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")
        except Exception:
            pass

    def get_feedback_for_case(self, case_id: str) -> list[FeedbackRecord]:
        """Retrieve feedback records for a specific case."""
        with self._lock:
            return [r for r in self._records if r.case_id == case_id]

    def list_all(self, limit: int = 100) -> list[FeedbackRecord]:
        """Retrieve all recorded feedback."""
        with self._lock:
            return list(reversed(self._records[-limit:]))


# Global singleton instance
feedback_store = FeedbackStore()
