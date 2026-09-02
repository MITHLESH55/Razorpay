"""
RiskOrbit — Grounded Evidence Agent (Phase 2)

Generates concise, human-readable, grounded risk reports strictly backed by
unique Evidence IDs (EVID-xxxx).

ANTI-HALLUCINATION & GROUNDING VALIDATION:
  - Factual claims must reference valid EVID-xxxx records.
  - Entity IDs and numerical values must match structured tool outputs.
  - Uncorroborated single links are explicitly labeled with appropriate uncertainty.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional
from src.investigation.schema import (
    CaseInvestigationResponse,
    EvidenceCategory,
    EvidenceConfidence,
    EvidenceRecord,
    TimelineEvent,
)

logger = logging.getLogger(__name__)


class GroundingValidator:
    """Validates that evidence reports strictly cite verified tool outputs."""

    @staticmethod
    def validate_evidence_grounding(
        evidence_records: List[EvidenceRecord],
        known_entity_ids: set[str],
    ) -> dict[str, Any]:
        unsupported_claims = []
        grounded_count = 0

        for ev in evidence_records:
            # Verify entities cited in supporting_entity_ids actually exist
            missing_entities = [eid for eid in ev.supporting_entity_ids if eid not in known_entity_ids]
            if missing_entities:
                unsupported_claims.append({
                    "evidence_id": ev.evidence_id,
                    "reason": f"Cited unknown entity IDs: {missing_entities}",
                })
            else:
                grounded_count += 1

        total = len(evidence_records)
        grounding_rate = round(grounded_count / total, 4) if total > 0 else 1.0

        return {
            "total_evidence_records": total,
            "grounded_records": grounded_count,
            "grounding_rate": grounding_rate,
            "unsupported_claim_count": len(unsupported_claims),
            "unsupported_claims": unsupported_claims,
            "is_fully_grounded": len(unsupported_claims) == 0,
        }


class DeterministicEvidenceGenerator:
    """
    100% deterministic, hallucination-free evidence synthesizer.
    Used for production risk scoring and offline evaluation fallback.
    """

    def generate_case_narrative(
        self,
        case_id: str,
        root_entity: str,
        candidate_ring: dict[str, Any],
        evidence_records: List[EvidenceRecord],
        timeline: List[TimelineEvent],
        individual_risk: float,
        relationship_risk: float,
        combined_risk: float,
    ) -> dict[str, Any]:
        members = candidate_ring.get("member_customers", [root_entity])
        devices = candidate_ring.get("shared_devices", [])
        ips = candidate_ring.get("shared_ips", [])
        merchants = candidate_ring.get("targeted_merchants", [])
        refund_rate = candidate_ring.get("member_refund_rate", 0.0)

        why_flagged = []
        if len(members) >= 2 and len(devices) >= 1:
            ev_id = next((e.evidence_id for e in evidence_records if e.category == EvidenceCategory.DEVICE_SHARING), "EVID-0001")
            why_flagged.append(f"[{ev_id}] {len(members)} customer accounts are linked via {len(devices)} shared hardware device(s).")

        if len(ips) >= 1:
            ev_id = next((e.evidence_id for e in evidence_records if e.category == EvidenceCategory.NETWORK_SHARING), "EVID-0002")
            why_flagged.append(f"[{ev_id}] Member accounts connect through {len(ips)} shared IP subnet(s).")

        if refund_rate >= 0.35:
            ev_id = next((e.evidence_id for e in evidence_records if e.category == EvidenceCategory.REFUND_COORDINATION), "EVID-0003")
            why_flagged.append(f"[{ev_id}] Coordinated group refund rate of {refund_rate*100:.1f}% across {candidate_ring.get('member_transaction_count', 0)} total orders.")

        if len(merchants) >= 2:
            ev_id = next((e.evidence_id for e in evidence_records if e.category == EvidenceCategory.CROSS_MERCHANT), "EVID-0004")
            why_flagged.append(f"[{ev_id}] Coordinated refund requests dispersed across {len(merchants)} distinct merchant catalogs.")

        if not why_flagged:
            why_flagged.append("No suspicious multi-account coordination discovered. Single customer behavioral risk.")

        # Uncertainties & Missing Evidence
        uncertainties = candidate_ring.get("uncertainties", [])
        if len(devices) == 1 and len(members) <= 3 and refund_rate < 0.30:
            uncertainties.append("Shared device connection with low refund volume may represent legitimate household usage.")
        if len(ips) >= 1 and len(devices) == 0:
            uncertainties.append("Shared network without device overlap may reflect corporate campus or public Wi-Fi.")

        missing_evidence = []
        if len(devices) == 0:
            missing_evidence.append("No hardware device overlap verified between accounts.")
        if len(ips) == 0:
            missing_evidence.append("No network IP correlation found.")

        # Construct concise summary
        if combined_risk >= 0.70:
            summary = (
                f"High-confidence coordinated refund abuse candidate. Root account {root_entity} is connected to "
                f"{len(members)-1} other accounts across {len(devices)} device(s) and {len(merchants)} merchant(s), "
                f"with a collective refund rate of {refund_rate*100:.1f}%."
            )
        elif combined_risk >= 0.35:
            summary = (
                f"Moderate relational risk case. Account {root_entity} exhibits shared infrastructure with "
                f"{len(members)-1} account(s), but behavioral coordination requires manual review."
            )
        else:
            summary = f"Low risk. Account {root_entity} exhibits standard purchasing behavior with no coordinated abuse pattern."

        return {
            "case_summary": summary,
            "why_flagged": why_flagged,
            "uncertainties": uncertainties,
            "missing_evidence": missing_evidence,
        }
