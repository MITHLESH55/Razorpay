"""
RiskOrbit — Risk Scoring API Contract (Pydantic schemas)

These schemas define the stable contract between Phase 1 and Phase 2.
Phase 2 graph/investigation/decision layers MUST consume this contract
without modifying it. Phase 1 is responsible for the risk_score and top_signals.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    """Input to POST /risk/score"""
    customer_id: str = Field(..., description="Synthetic customer identifier")
    transaction_id: str = Field(..., description="Transaction to score")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class SignalDetail(BaseModel):
    """One contributing signal in the risk explanation."""
    feature: str = Field(..., description="Feature name from the canonical feature list")
    value: float = Field(..., description="Feature value for this transaction")
    importance: float = Field(
        ..., ge=0.0, le=1.0,
        description="Normalized SHAP importance (0-1) for this feature"
    )


class ScoreResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    """
    Output of POST /risk/score

    This is the Phase 1 → Phase 2 contract.
    Phase 2 must not require changes to this schema.

    Fields:
      transaction_id: the scored transaction
      customer_id: the customer
      risk_score: continuous score in [0, 1]
      risk_label: categorical label (low / medium / high)
      threshold: the operating threshold used for risk_label
      model_version: versioned model identifier
      top_signals: up to 5 contributing SHAP explanations
      scored_at: UTC timestamp of scoring
    """

    transaction_id: str
    customer_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: str = Field(..., description="low | medium | high")
    threshold: float
    model_version: str
    top_signals: list[SignalDetail] = Field(default_factory=list)
    scored_at: str

    @classmethod
    def from_score(
        cls,
        transaction_id: str,
        customer_id: str,
        risk_score: float,
        threshold: float,
        model_version: str,
        top_signals: list[dict],
    ) -> "ScoreResponse":
        """Construct a ScoreResponse with derived risk_label."""
        if risk_score >= threshold:
            label = "high"
        elif risk_score >= threshold * 0.6:
            label = "medium"
        else:
            label = "low"

        return cls(
            transaction_id=transaction_id,
            customer_id=customer_id,
            risk_score=round(risk_score, 4),
            risk_label=label,
            threshold=round(threshold, 4),
            model_version=model_version,
            top_signals=[SignalDetail(**s) for s in top_signals],
            scored_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    status: str
    model_version: str
    threshold: float
