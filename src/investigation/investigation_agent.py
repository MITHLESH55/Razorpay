"""
RiskOrbit — Investigation Agent (Phase 2)

Orchestrates multi-hop relationship investigation, candidate ring discovery,
evidence bundling, and case construction.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.ring_detector import detect_candidate_ring
from src.investigation.evidence_agent import (
    DeterministicEvidenceGenerator,
    GroundingValidator,
)
from src.investigation.schema import (
    CaseAuditTrail,
    CaseInvestigationResponse,
    EvidenceCategory,
    EvidenceConfidence,
    EvidenceRecord,
    TimelineEvent,
)
from src.investigation.tools import InvestigationToolKit

logger = logging.getLogger(__name__)


class InvestigationAgent:
    """
    Main investigation agent coordinating bounded point-in-time relationship analysis.
    """

    def __init__(
        self,
        graph_engine: PaymentGraphEngine,
        phase1_pipeline: Optional[Any] = None,
        phase1_threshold: float = 0.35,
    ):
        self.engine = graph_engine
        self.toolkit = InvestigationToolKit(graph_engine)
        self.evidence_gen = DeterministicEvidenceGenerator()
        self.phase1_pipeline = phase1_pipeline
        self.phase1_threshold = phase1_threshold

    def investigate_candidate(
        self,
        candidate_id: str,
        as_of_time: Optional[datetime] = None,
        max_hops: int = 2,
        individual_risk: Optional[float] = None,
        G: Optional[Any] = None,
    ) -> CaseInvestigationResponse:
        """
        Execute bounded multi-hop investigation around candidate_id (customer_id or transaction_id).
        """
        # Resolve customer ID if a transaction ID was passed
        if as_of_time is not None:
            scoring_time = pd.to_datetime(as_of_time)
            if scoring_time.tzinfo is not None:
                scoring_time = scoring_time.tz_localize(None)
        else:
            scoring_time = None

        if candidate_id.startswith("TXN_"):
            txn_row = self.engine.txn[self.engine.txn["transaction_id"] == candidate_id]
            if len(txn_row) > 0:
                root_customer_id = str(txn_row.iloc[0]["customer_id"])
                if scoring_time is None:
                    scoring_time = txn_row.iloc[0]["timestamp"]
            else:
                root_customer_id = candidate_id
                if scoring_time is None:
                    scoring_time = self.engine.txn["timestamp"].max() if len(self.engine.txn) > 0 else pd.Timestamp.now()
        else:
            root_customer_id = candidate_id
            cust_txns = self.engine.txn[self.engine.txn["customer_id"] == candidate_id]
            if scoring_time is None:
                scoring_time = cust_txns["timestamp"].max() if len(cust_txns) > 0 else (self.engine.txn["timestamp"].max() if len(self.engine.txn) > 0 else pd.Timestamp.now())

        if scoring_time.tzinfo is not None:
            scoring_time = scoring_time.tz_localize(None)

        # 1. Build NetworkX graph as of scoring timestamp
        if G is None:
            G = self.engine.build_networkx_graph_as_of(scoring_time, min_edge_strength=0.05)
        txn_sub, ord_sub, ref_sub = self.engine.get_events_as_of(scoring_time)

        # 2. Extract candidate ring
        ring_result = detect_candidate_ring(
            G=G,
            root_customer_id=root_customer_id,
            as_of_time=scoring_time,
            transactions=txn_sub,
            refunds=ref_sub,
            max_hops=max_hops,
        )

        member_custs = ring_result["member_customers"]
        shared_devs = ring_result["shared_devices"]
        shared_ips = ring_result["shared_ips"]
        targeted_merchants = ring_result["targeted_merchants"]
        rel_score = float(ring_result["ring_risk_score"])

        # 3. Individual Risk from Phase 1 Baseline
        if individual_risk is not None:
            indiv_score = float(individual_risk)
        else:
            indiv_score = 0.0
            cust_txns_prior = txn_sub[txn_sub["customer_id"] == root_customer_id]
            if self.phase1_pipeline is not None and len(cust_txns_prior) > 0:
                try:
                    from src.features.pipeline import build_features, FEATURE_COLUMNS
                    X_feat = build_features(
                        transactions=cust_txns_prior.tail(1),
                        orders=ord_sub,
                        refunds=ref_sub,
                        customers=self.engine.customers if self.engine.customers is not None else pd.DataFrame(),
                        merchants=self.engine.merchants if self.engine.merchants is not None else pd.DataFrame(),
                        devices=self.engine.devices if self.engine.devices is not None else pd.DataFrame(),
                        ip_entities=self.engine.ip_entities if self.engine.ip_entities is not None else pd.DataFrame(),
                        instruments=self.engine.instruments if self.engine.instruments is not None else pd.DataFrame(),
                        reference_transactions=txn_sub,
                    )
                    imp = self.phase1_pipeline.named_steps["imputer"]
                    indiv_score = float(self.phase1_pipeline.named_steps["lgbm"].predict_proba(imp.transform(X_feat[FEATURE_COLUMNS]))[0][1])
                except Exception as e:
                    logger.warning("Phase 1 baseline scoring failed: %s — using heuristic fallback", e)
                    indiv_score = 0.10
            else:
                # Fallback heuristic based on individual refund rate
                if len(cust_txns_prior) > 0:
                    t_ids = cust_txns_prior["transaction_id"].values
                    c_refs = ref_sub[ref_sub["transaction_id"].isin(t_ids)] if len(ref_sub) > 0 else pd.DataFrame()
                    indiv_score = round(min(1.0, len(c_refs) / max(1, len(cust_txns_prior))), 4)

        # 4. Combined Risk Formula (Phase 1 individual + Phase 2 relational risk)
        # Relational risk provides massive boost when multi-account sharing exists
        combined_score = round(min(1.0, max(0.0, 0.35 * indiv_score + 0.65 * rel_score)), 4)

        if combined_score >= 0.70:
            risk_tier = "critical" if combined_score >= 0.85 else "high"
        elif combined_score >= 0.35:
            risk_tier = "medium"
        else:
            risk_tier = "low"

        # 5. Build Structured Evidence Records (EVID-xxxx)
        evidence_records = []
        ev_idx = 1

        if len(shared_devs) > 0 and len(member_custs) >= 2:
            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"EVID-{ev_idx:04d}",
                    category=EvidenceCategory.DEVICE_SHARING,
                    confidence=EvidenceConfidence.STRONG,
                    statement=f"{len(member_custs)} distinct customer accounts transacted using {len(shared_devs)} shared hardware device(s).",
                    supporting_entity_ids=member_custs + shared_devs,
                    metric_value=float(len(shared_devs)),
                    metric_description="shared_device_count",
                )
            )
            ev_idx += 1

        if len(shared_ips) > 0 and len(member_custs) >= 2:
            conf = EvidenceConfidence.STRONG if len(shared_devs) > 0 else EvidenceConfidence.MODERATE
            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"EVID-{ev_idx:04d}",
                    category=EvidenceCategory.NETWORK_SHARING,
                    confidence=conf,
                    statement=f"{len(member_custs)} customer accounts connect through {len(shared_ips)} shared IP network(s).",
                    supporting_entity_ids=member_custs + shared_ips,
                    metric_value=float(len(shared_ips)),
                    metric_description="shared_ip_count",
                )
            )
            ev_idx += 1

        if ring_result["member_refund_rate"] >= 0.30:
            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"EVID-{ev_idx:04d}",
                    category=EvidenceCategory.REFUND_COORDINATION,
                    confidence=EvidenceConfidence.STRONG,
                    statement=f"Coordinated group refund rate of {ring_result['member_refund_rate']*100:.1f}% across {ring_result['member_transaction_count']} member orders.",
                    supporting_entity_ids=member_custs,
                    metric_value=float(ring_result["member_refund_rate"]),
                    metric_description="member_refund_rate",
                )
            )
            ev_idx += 1

        if len(targeted_merchants) >= 2:
            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"EVID-{ev_idx:04d}",
                    category=EvidenceCategory.CROSS_MERCHANT,
                    confidence=EvidenceConfidence.MODERATE,
                    statement=f"Ring transactions span {len(targeted_merchants)} distinct merchant catalogs with coordinated timing.",
                    supporting_entity_ids=member_custs + targeted_merchants,
                    metric_value=float(len(targeted_merchants)),
                    metric_description="targeted_merchant_count",
                )
            )
            ev_idx += 1

        # 6. Chronological Event Timeline
        timeline = []
        member_txns = txn_sub[txn_sub["customer_id"].isin(member_custs)].sort_values("timestamp")

        for _, r in member_txns.head(15).iterrows():
            tid = r["transaction_id"]
            cid = r["customer_id"]
            did = r.get("device_id", "N/A")
            amt = r.get("amount", 0.0)
            timeline.append(
                TimelineEvent(
                    event_timestamp=str(r["timestamp"]),
                    event_type="TRANSACTION",
                    entity_id=cid,
                    description=f"Customer {cid} placed order ({tid}) for ₹{amt:,.2f} on device {did}",
                    supporting_event_id=tid,
                )
            )
            # Check for refund
            ref_match = ref_sub[ref_sub["transaction_id"] == tid] if len(ref_sub) > 0 else pd.DataFrame()
            if len(ref_match) > 0:
                ref_row = ref_match.iloc[0]
                timeline.append(
                    TimelineEvent(
                        event_timestamp=str(ref_row["refund_requested_at"]),
                        event_type="REFUND_REQUEST",
                        entity_id=cid,
                        description=f"Customer {cid} requested refund of ₹{ref_row['refund_amount']:,.2f} on transaction {tid}",
                        supporting_event_id=ref_row["refund_id"] if "refund_id" in ref_row else tid,
                    )
                )

        # 7. Generate Grounded Narrative
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        narrative = self.evidence_gen.generate_case_narrative(
            case_id=case_id,
            root_entity=root_customer_id,
            candidate_ring=ring_result,
            evidence_records=evidence_records,
            timeline=timeline,
            individual_risk=indiv_score,
            relationship_risk=rel_score,
            combined_risk=combined_score,
        )

        # 8. Assemble Case Response
        audit_trail = CaseAuditTrail(
            case_id=case_id,
            candidate_id=candidate_id,
            scoring_timestamp=str(scoring_time),
            phase1_model_version="riskorbit-risk-v1",
            graph_version="graph-v2",
            investigation_version="investigation-v2",
            evidence_version="evidence-grounded-v2",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return CaseInvestigationResponse(
            case_id=case_id,
            root_entity=root_customer_id,
            candidate_ring_type="coordinated_refund_abuse",
            individual_risk_score=round(indiv_score, 4),
            relationship_risk_score=round(rel_score, 4),
            combined_risk_score=round(combined_score, 4),
            risk_tier=risk_tier,
            is_candidate_ring=ring_result["is_ring_candidate"],
            member_accounts=member_custs,
            shared_devices=shared_devs,
            shared_ips=shared_ips,
            targeted_merchants=targeted_merchants,
            evidence_records=evidence_records,
            timeline=timeline,
            case_summary=narrative["case_summary"],
            why_flagged=narrative["why_flagged"],
            uncertainties=narrative["uncertainties"],
            missing_evidence=narrative["missing_evidence"],
            graph_statistics=ring_result["case_subgraph"]["statistics"],
            audit_trail=audit_trail,
        )
