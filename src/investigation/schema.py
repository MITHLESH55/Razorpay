"""
RiskOrbit — Investigation & Evidence Schema (Phase 2)

Pydantic contracts for:
  - Investigation Requests & Responses
  - Structured Evidence Records with Unique Evidence IDs (EVID-xxxx)
  - Chronological Timeline Events
  - Case Audit Trail
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class EvidenceConfidence(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class EvidenceCategory(str, Enum):
    DEVICE_SHARING = "DEVICE_SHARING"
    NETWORK_SHARING = "NETWORK_SHARING"
    INSTRUMENT_LINK = "INSTRUMENT_LINK"
    REFUND_COORDINATION = "REFUND_COORDINATION"
    CROSS_MERCHANT = "CROSS_MERCHANT"
    TEMPORAL_BURST = "TEMPORAL_BURST"
    BENIGN_CONFUSER = "BENIGN_CONFUSER"


class EvidenceRecord(BaseModel):
    evidence_id: str = Field(..., description="Unique evidence ID e.g. EVID-0001")
    category: EvidenceCategory
    confidence: EvidenceConfidence
    statement: str = Field(..., description="Factual evidence claim directly derived from data")
    supporting_entity_ids: List[str] = Field(default_factory=list)
    supporting_event_ids: List[str] = Field(default_factory=list)
    metric_value: Optional[float] = None
    metric_description: Optional[str] = None


class TimelineEvent(BaseModel):
    event_timestamp: str
    event_type: str
    entity_id: str
    description: str
    supporting_event_id: Optional[str] = None


class CaseInvestigationRequest(BaseModel):
    candidate_id: str = Field(..., description="Customer ID or Transaction ID to investigate")
    as_of_timestamp: Optional[str] = Field(None, description="ISO timestamp for point-in-time scoring")
    max_hops: int = Field(default=2, ge=1, le=3)


class CaseAuditTrail(BaseModel):
    case_id: str
    candidate_id: str
    scoring_timestamp: str
    phase1_model_version: str = "riskorbit-risk-v1"
    graph_version: str = "graph-v2"
    investigation_version: str = "investigation-v2"
    evidence_version: str = "evidence-grounded-v2"
    created_at: str


class CaseInvestigationResponse(BaseModel):
    case_id: str
    root_entity: str
    candidate_ring_type: str = "coordinated_refund_abuse"
    individual_risk_score: float = Field(..., ge=0.0, le=1.0)
    relationship_risk_score: float = Field(..., ge=0.0, le=1.0)
    combined_risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str = Field(..., description="low | medium | high | critical")
    is_candidate_ring: bool
    member_accounts: List[str] = Field(default_factory=list)
    shared_devices: List[str] = Field(default_factory=list)
    shared_ips: List[str] = Field(default_factory=list)
    targeted_merchants: List[str] = Field(default_factory=list)
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    case_summary: str
    why_flagged: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    graph_statistics: dict[str, Any] = Field(default_factory=dict)
    audit_trail: CaseAuditTrail
