"""
RiskOrbit — FastAPI Risk Scoring & Investigation API (Phase 1 + Phase 2)

Serves:
  Phase 1: POST /risk/score (transaction-level tabular risk scoring, preserved)
  Phase 2: POST /risk/investigate (bounded relationship investigation)
  Phase 2: GET  /risk/cases/{case_id} (stored case retrieval)
  Phase 2: GET  /risk/cases/{case_id}/graph (case graph statistics)
  Phase 2: GET  /risk/cases/{case_id}/evidence (grounded evidence bundle)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException

from src.api.schema import HealthResponse, ScoreRequest, ScoreResponse
from src.graph.graph_engine import PaymentGraphEngine
from src.investigation.case_cache import CaseStorage
from src.investigation.investigation_agent import InvestigationAgent
from src.investigation.schema import CaseInvestigationRequest, CaseInvestigationResponse
from src.models.main_model import get_top_signals, load_artifact

logger = logging.getLogger("riskorbit.api")

_pipeline_v1 = None
_threshold_v1: float = 0.35
_feature_names_v1: list[str] = []
_model_version_v1 = "riskorbit-risk-v1"

_graph_engine: Optional[PaymentGraphEngine] = None
_investigation_agent: Optional[InvestigationAgent] = None
_case_storage = CaseStorage()

_transactions: pd.DataFrame = pd.DataFrame()
_orders: pd.DataFrame = pd.DataFrame()
_refunds: pd.DataFrame = pd.DataFrame()
_customers: pd.DataFrame = pd.DataFrame()
_merchants: pd.DataFrame = pd.DataFrame()
_devices: pd.DataFrame = pd.DataFrame()
_ip_entities: pd.DataFrame = pd.DataFrame()
_instruments: pd.DataFrame = pd.DataFrame()
_train_split: pd.DataFrame = pd.DataFrame()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler for startup/shutdown (replaces deprecated on_event)."""
    global _pipeline_v1, _threshold_v1, _feature_names_v1
    global _transactions, _orders, _refunds, _customers, _merchants
    global _devices, _ip_entities, _instruments, _train_split
    global _graph_engine, _investigation_agent

    artifact_dir = Path(os.environ.get("ARTIFACT_DIR", "artifacts/riskorbit-risk-v1"))
    if artifact_dir.exists():
        _pipeline_v1, _threshold_v1, _feature_names_v1 = load_artifact(artifact_dir)
        logger.info("Loaded Phase 1 model from %s (threshold=%.4f)", artifact_dir, _threshold_v1)

    data_dir = Path(os.environ.get("DATA_DIR", "data/raw"))
    splits_dir = Path(os.environ.get("SPLITS_DIR", "data/splits"))

    if (data_dir / "transactions.csv").exists():
        _transactions = pd.read_csv(data_dir / "transactions.csv", low_memory=False)
        _orders = pd.read_csv(data_dir / "orders.csv", low_memory=False)
        _refunds = pd.read_csv(data_dir / "refunds.csv", low_memory=False)
        _customers = pd.read_csv(data_dir / "customers.csv", low_memory=False)
        _merchants = pd.read_csv(data_dir / "merchants.csv", low_memory=False)
        _devices = pd.read_csv(data_dir / "devices.csv", low_memory=False)
        _ip_entities = pd.read_csv(data_dir / "ip_entities.csv", low_memory=False)
        _instruments = pd.read_csv(data_dir / "instruments.csv", low_memory=False)
        for df, col in [(_transactions, "timestamp"), (_orders, "created_at")]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="mixed")

        if (splits_dir / "train.csv").exists():
            _train_split = pd.read_csv(splits_dir / "train.csv", low_memory=False)
            _train_split["timestamp"] = pd.to_datetime(_train_split["timestamp"], format="mixed")

        try:
            _graph_engine = PaymentGraphEngine(
                transactions=_train_split if len(_train_split) > 0 else _transactions,
                orders=_orders,
                refunds=_refunds,
                customers=_customers,
                merchants=_merchants,
                devices=_devices,
                ip_entities=_ip_entities,
                instruments=_instruments,
            )
            _investigation_agent = InvestigationAgent(
                graph_engine=_graph_engine,
                phase1_pipeline=_pipeline_v1,
                phase1_threshold=_threshold_v1,
            )
            logger.info("Phase 2 relationship engine and investigation agent initialized.")
        except Exception as e:
            logger.warning("Graph engine initialization failed: %s", e)

        logger.info("Reference datasets successfully loaded.")

    yield  # Application runs here
    # Shutdown: nothing to clean up


app = FastAPI(
    title="RiskOrbit Sentinel API",
    description=(
        "RiskOrbit — Agentic Coordinated Refund-Abuse Sentinel. "
        "Phase 1: Tabular risk scoring via LightGBM. "
        "Phase 2: Bounded graph intelligence & grounded investigation agent."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Phase 1 Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok" if _pipeline_v1 is not None else "model_not_loaded",
        model_version=_model_version_v1,
        threshold=_threshold_v1 if _threshold_v1 is not None else -1.0,
    )


@app.post("/risk/score", response_model=ScoreResponse)
async def score_transaction(request: ScoreRequest) -> ScoreResponse:
    """
    Score a transaction for coordinated refund abuse risk (Phase 1).
    """
    if _pipeline_v1 is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if len(_transactions) > 0:
        txn_row = _transactions[_transactions["transaction_id"] == request.transaction_id]
        if len(txn_row) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {request.transaction_id} not found in reference data"
            )
    else:
        txn_row = pd.DataFrame([{
            "transaction_id": request.transaction_id,
            "customer_id": request.customer_id,
            "merchant_id": "MER_UNKNOWN",
            "device_id": None,
            "ip_id": None,
            "instrument_id": None,
            "timestamp": pd.Timestamp.utcnow(),
            "amount": 0.0,
            "payment_method": "unknown",
            "payment_status": "unknown",
        }])

    from src.features.pipeline import build_features
    try:
        features = build_features(
            transactions=txn_row,
            orders=_orders,
            refunds=_refunds,
            customers=_customers,
            merchants=_merchants,
            devices=_devices,
            ip_entities=_ip_entities,
            instruments=_instruments,
            reference_transactions=_transactions,
        )
    except Exception as e:
        logger.error("Feature computation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Feature computation error: {e}")

    for col in _feature_names_v1:
        if col not in features.columns:
            features[col] = 0.0
    features = features[_feature_names_v1]

    imputer = _pipeline_v1.named_steps["imputer"]
    X_imp = imputer.transform(features)
    prob = _pipeline_v1.named_steps["lgbm"].predict_proba(X_imp)[0][1]

    try:
        top_signals = get_top_signals(_pipeline_v1, features, _feature_names_v1, top_n=5)
    except Exception as e:
        logger.warning("SHAP computation failed: %s", e)
        top_signals = []

    return ScoreResponse.from_score(
        transaction_id=request.transaction_id,
        customer_id=request.customer_id,
        risk_score=float(prob),
        threshold=_threshold_v1,
        model_version=_model_version_v1,
        top_signals=top_signals,
    )


# ---------------------------------------------------------------------------
# Phase 2 Endpoints
# ---------------------------------------------------------------------------

@app.post("/risk/investigate", response_model=CaseInvestigationResponse)
async def investigate_candidate(request: CaseInvestigationRequest) -> CaseInvestigationResponse:
    """
    Phase 2: Bounded graph relationship investigation.
    """
    if _investigation_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Investigation agent not initialized."
        )

    as_of_ts: Optional[datetime] = None
    if request.as_of_timestamp:
        try:
            as_of_ts = datetime.fromisoformat(request.as_of_timestamp)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid as_of_timestamp format. Use ISO 8601.")

    try:
        case = _investigation_agent.investigate_candidate(
            candidate_id=request.candidate_id,
            as_of_time=as_of_ts,
            max_hops=request.max_hops,
        )
        _case_storage.save_case(case)
        return case
    except Exception as e:
        logger.error("Investigation failed for %s: %s", request.candidate_id, e)
        raise HTTPException(status_code=500, detail=f"Investigation error: {e}")


@app.get("/risk/cases/{case_id}", response_model=CaseInvestigationResponse)
async def get_case(case_id: str) -> CaseInvestigationResponse:
    """Retrieve stored investigation case."""
    case = _case_storage.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return case


@app.get("/risk/cases/{case_id}/graph")
async def get_case_graph(case_id: str) -> dict[str, Any]:
    """Retrieve case graph statistics."""
    case = _case_storage.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return {
        "case_id": case.case_id,
        "root_entity": case.root_entity,
        "member_accounts": case.member_accounts,
        "shared_devices": case.shared_devices,
        "shared_ips": case.shared_ips,
        "targeted_merchants": case.targeted_merchants,
        "graph_statistics": case.graph_statistics,
    }


@app.get("/risk/cases/{case_id}/evidence")
async def get_case_evidence(case_id: str) -> dict[str, Any]:
    """Retrieve grounded evidence records and timeline."""
    case = _case_storage.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return {
        "case_id": case.case_id,
        "case_summary": case.case_summary,
        "why_flagged": case.why_flagged,
        "evidence_records": [e.model_dump() for e in case.evidence_records],
        "timeline": [t.model_dump() for t in case.timeline],
        "uncertainties": case.uncertainties,
        "missing_evidence": case.missing_evidence,
    }


if __name__ == "__main__":
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)
