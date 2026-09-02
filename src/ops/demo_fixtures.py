"""
RiskOrbit — Golden Cases & Interactive Demo Fixtures

Provides pre-seeded, high-fidelity risk cases, subgraphs, verified evidence artifacts,
and simulation scenarios for the Risk Operations Console.
"""
from __future__ import annotations

from typing import Any, Dict, List
from src.ops.audit_log import AuditEventType, audit_trail
from src.ops.case_manager import CasePriority, CaseStatus, RiskCaseRecord, case_manager
from src.ops.drift_detector import drift_detector
from src.ops.monitoring import operational_monitor


# Detailed Subgraph & Evidence Data for Golden Cases
GOLDEN_CASE_DETAILS: dict[str, dict[str, Any]] = {
    "CASE-RING-A-01": {
        "case_id": "CASE-RING-A-01",
        "pattern_name": "Pattern A: Device Farm Collusion & Rapid Fan-Out",
        "narrative": "A network of 32 synthetic accounts routing rapid micropayments through a shared rooted emulator cluster.",
        "nodes": [
            {"id": "CUST-FARMA-101", "type": "customer", "label": "CUST-FARMA-101 (Primary)", "role": "Primary Target", "tier": "PRIMARY", "risk_score": 0.88},
            {"id": "CUST-FARMA-102", "type": "customer", "label": "CUST-FARMA-102", "role": "Ring Member", "tier": "SECONDARY", "risk_score": 0.72},
            {"id": "CUST-FARMA-103", "type": "customer", "label": "CUST-FARMA-103", "role": "Ring Member", "tier": "SECONDARY", "risk_score": 0.69},
            {"id": "DEV-FARM-991", "type": "device", "label": "DEV-FARM-991 (Rooted Android)", "role": "Shared Device", "tier": "INFRASTRUCTURE", "risk_score": 0.95},
            {"id": "IP-103-45-88-12", "type": "ip", "label": "103.45.88.12 (VPN Proxy)", "role": "Shared IP", "tier": "INFRASTRUCTURE", "risk_score": 0.82},
            {"id": "MERCH-GATEWAY-11", "type": "merchant", "label": "MERCH-GATEWAY-11", "role": "Target Merchant", "tier": "MERCHANT", "risk_score": 0.15},
        ],
        "edges": [
            {"id": "e1", "source": "CUST-FARMA-101", "target": "DEV-FARM-991", "label": "SHARED_DEVICE", "weight": 0.95},
            {"id": "e2", "source": "CUST-FARMA-102", "target": "DEV-FARM-991", "label": "SHARED_DEVICE", "weight": 0.95},
            {"id": "e3", "source": "CUST-FARMA-103", "target": "DEV-FARM-991", "label": "SHARED_DEVICE", "weight": 0.95},
            {"id": "e4", "source": "CUST-FARMA-101", "target": "IP-103-45-88-12", "label": "SHARED_IP", "weight": 0.80},
            {"id": "e5", "source": "CUST-FARMA-102", "target": "IP-103-45-88-12", "label": "SHARED_IP", "weight": 0.80},
            {"id": "e6", "source": "CUST-FARMA-101", "target": "MERCH-GATEWAY-11", "label": "TRANSACTS_INR_48.5K", "weight": 0.88},
        ],
        "evidence_items": [
            {
                "evidence_id": "EVID-DEV-001",
                "category": "DEVICE_COLLUSION",
                "title": "Cluster Device Fingerprint Collision",
                "strength": 0.94,
                "verified": True,
                "hash_sha256": "8f3b61a9c4021dd982f1b40283c74911d9f82613ba814e8201ac6110f019bf83",
                "description": "Device DEV-FARM-991 matched across 32 active customer wallets within a 3-hour sliding window. Canvas fingerprint and WebGL vendor ID confirm headless Linux emulator.",
                "features": {"shared_accounts": 32, "os_family": "Android / Rooted", "emulator_flag": True},
            },
            {
                "evidence_id": "EVID-VEL-002",
                "category": "VELOCITY_ANOMALY",
                "title": "Sub-Minute Burst Velocity",
                "strength": 0.89,
                "verified": True,
                "hash_sha256": "4a18ceb9f1d0a87612c751249b109e9927cf8a1e345b10da7762a5b281f69201",
                "description": "48 distinct UPI push intent requests generated in 90 seconds. 18.5x deviation above customer baseline velocity.",
                "features": {"txns_in_window": 48, "window_seconds": 90, "z_score": 5.42},
            },
            {
                "evidence_id": "EVID-GEO-003",
                "category": "GEO_IMPOSSIBILITY",
                "title": "Impossible Geographic Flight Speed",
                "strength": 0.85,
                "verified": True,
                "hash_sha256": "b71694fca2980182ec88371900192eab9c83210987fa28189cbb610192837411",
                "description": "Simultaneous authentication events detected from Bangalore (IP 103.45.88.12) and Frankfurt (IP 185.220.101.5) within 4 seconds.",
                "features": {"distance_km": 7450, "delta_seconds": 4, "calculated_speed_kmh": 6705000},
            },
        ],
        "decision_trace": {
            "p1_raw_score": 0.88,
            "sigma_membership_confidence": 0.94,
            "rho_evidence_strength": 0.92,
            "tier_multiplier": 1.0,
            "final_decision_score": 0.895,
            "policy_rule_matched": "RULE_PRIMARY_BLOCK_P1_HIGH_EVID_CRITICAL",
            "friction_cost_estimate_inr": 48500.0,
            "bounded_intervention": "BLOCK_TRANSACTION",
        },
    },
    "CASE-RING-B-02": {
        "case_id": "CASE-RING-B-02",
        "pattern_name": "Pattern B: Circular Layering & Rapid Flow Retention",
        "narrative": "A 4-hop circular UPI fund layering chain designed to obfuscate illicit merchant cash-out with 98.5% volume retention.",
        "nodes": [
            {"id": "CUST-CYCLE-201", "type": "customer", "label": "CUST-CYCLE-201 (Origin)", "role": "Originator", "tier": "PRIMARY", "risk_score": 0.92},
            {"id": "CUST-CYCLE-202", "type": "customer", "label": "CUST-CYCLE-202 (Layer 1)", "role": "Primary Target", "tier": "PRIMARY", "risk_score": 0.94},
            {"id": "CUST-CYCLE-203", "type": "customer", "label": "CUST-CYCLE-203 (Layer 2)", "role": "Mule Node", "tier": "SECONDARY", "risk_score": 0.84},
            {"id": "CUST-CYCLE-204", "type": "customer", "label": "CUST-CYCLE-204 (Sink)", "role": "Cash-Out Sink", "tier": "PRIMARY", "risk_score": 0.91},
        ],
        "edges": [
            {"id": "e201", "source": "CUST-CYCLE-201", "target": "CUST-CYCLE-202", "label": "HOP_1_INR_98K", "weight": 0.98},
            {"id": "e202", "source": "CUST-CYCLE-202", "target": "CUST-CYCLE-203", "label": "HOP_2_INR_96.5K", "weight": 0.97},
            {"id": "e203", "source": "CUST-CYCLE-203", "target": "CUST-CYCLE-204", "label": "HOP_3_INR_95.2K", "weight": 0.96},
            {"id": "e204", "source": "CUST-CYCLE-204", "target": "CUST-CYCLE-201", "label": "CYCLE_INR_95.0K", "weight": 0.95},
        ],
        "evidence_items": [
            {
                "evidence_id": "EVID-CYC-001",
                "category": "CIRCULAR_TOPOLOGY",
                "title": "Closed Directed Cycle Detected",
                "strength": 0.98,
                "verified": True,
                "hash_sha256": "3c91d84e551029ba88102fca12093817ab9018471629471bb901928374162981",
                "description": "Deterministic 4-node cycle discovered: CUST-201 -> CUST-202 -> CUST-203 -> CUST-204 -> CUST-201. Volume retention = 96.9% across 4 hops.",
                "features": {"cycle_length": 4, "volume_retention_pct": 96.9, "total_cycle_amount_inr": 384700.0},
            },
            {
                "evidence_id": "EVID-TIM-002",
                "category": "SETTLEMENT_VELOCITY",
                "title": "Sub-Second In-Out Pass-Through",
                "strength": 0.95,
                "verified": True,
                "hash_sha256": "7a91bc820194817a5b0182746190283719028371629481726591029384756192",
                "description": "Mean time between fund arrival and onward dispatch across all ring nodes is 8.4 seconds, characteristic of automated relay mules.",
                "features": {"avg_holding_time_sec": 8.4, "min_holding_time_sec": 2.1},
            },
        ],
        "decision_trace": {
            "p1_raw_score": 0.92,
            "sigma_membership_confidence": 0.98,
            "rho_evidence_strength": 0.96,
            "tier_multiplier": 1.0,
            "final_decision_score": 0.942,
            "policy_rule_matched": "RULE_RING_FREEZE_CIRCULAR_CONFIRMED",
            "friction_cost_estimate_inr": 95000.0,
            "bounded_intervention": "FREEZE_RING",
        },
    },
    "CASE-HARDNEG-04": {
        "case_id": "CASE-HARDNEG-04",
        "pattern_name": "Hard Negative: Festive High-Value Legitimate Spike",
        "narrative": "Legitimate enterprise corporate buyer purchasing high-value electronics during festive season. High single-transaction amount, but zero graph ring collusion.",
        "nodes": [
            {"id": "CUST-VIP-404", "type": "customer", "label": "CUST-VIP-404 (Corporate VIP)", "role": "Verified Customer", "tier": "ISOLATED", "risk_score": 0.28},
            {"id": "DEV-MAC-404", "type": "device", "label": "DEV-MAC-404 (MacBook Pro)", "role": "Trusted Device (4 yrs)", "tier": "INFRASTRUCTURE", "risk_score": 0.05},
            {"id": "IP-CORP-404", "type": "ip", "label": "IP-CORP-404 (Tata Telecom Static)", "role": "Clean ISP", "tier": "INFRASTRUCTURE", "risk_score": 0.02},
            {"id": "MERCH-CROMA-88", "type": "merchant", "label": "MERCH-CROMA-88", "role": "Authorized Merchant", "tier": "MERCHANT", "risk_score": 0.05},
        ],
        "edges": [
            {"id": "en1", "source": "CUST-VIP-404", "target": "DEV-MAC-404", "label": "AUTH_DEVICE_KYC_VERIFIED", "weight": 0.05},
            {"id": "en2", "source": "CUST-VIP-404", "target": "IP-CORP-404", "label": "STATIC_CORP_IP", "weight": 0.02},
            {"id": "en3", "source": "CUST-VIP-404", "target": "MERCH-CROMA-88", "label": "TRANSACTS_INR_89K", "weight": 0.28},
        ],
        "evidence_items": [
            {
                "evidence_id": "EVID-NEG-001",
                "category": "HARD_NEGATIVE_VERIFICATION",
                "title": "Grounded Hard Negative — No Collusion Graph",
                "strength": 0.12,
                "verified": True,
                "hash_sha256": "1e91283746190283746190283746190283746190283746190283746190283746",
                "description": "Graph traversal reveals 0 shared devices, 0 shared IPs, 0 circular cycles. Account KYC age = 48 months. Point model p1 was elevated solely due to large amount (₹89,000).",
                "features": {"shared_devices": 0, "shared_ips": 0, "kyc_age_months": 48, "tier": "ISOLATED"},
            },
        ],
        "decision_trace": {
            "p1_raw_score": 0.62,
            "sigma_membership_confidence": 0.05,
            "rho_evidence_strength": 0.12,
            "tier_multiplier": 0.35,
            "final_decision_score": 0.284,
            "policy_rule_matched": "RULE_ISOLATED_STEP_UP_2FA_PROPORTIONAL",
            "friction_cost_estimate_inr": 25.0,
            "bounded_intervention": "STEP_UP_2FA",
        },
    },
}


def seed_demo_cases() -> None:
    """Initialize case manager with rich golden demonstration cases and synthetic queue."""
    # 1. Flagship Pattern A Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-RING-A-01",
            transaction_id="TXN-DEMO-A9901",
            customer_id="CUST-FARMA-101",
            amount_inr=48500.0,
            timestamp="2026-09-01T09:15:00Z",
            phase1_risk=0.88,
            membership_confidence=0.94,
            evidence_strength=0.92,
            decision_score=0.895,
            tier="PRIMARY",
            recommended_action="BLOCK_TRANSACTION",
            final_action="BLOCK_TRANSACTION",
            requires_human_approval=True,
            escalation_reason="Critical High-Risk: Primary Ring node with 32 shared device collusions.",
            action_reason="Pattern A Device Farm: Multi-device collision with impossible geo-velocity.",
            expected_friction_cost_inr=48500.0,
            ring_id="RING_A_001",
            pattern_type="PATTERN_A_DEVICE_FARM",
            is_hard_negative=False,
            status=CaseStatus.RECOMMENDED,
            priority=CasePriority.CRITICAL,
            member_count=32,
            shared_devices=["DEV-FARM-991", "DEV-EMU-882"],
            shared_ips=["103.45.88.12", "185.220.101.5"],
        )
    )

    # 2. Flagship Pattern B Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-RING-B-02",
            transaction_id="TXN-DEMO-B4402",
            customer_id="CUST-CYCLE-202",
            amount_inr=95000.0,
            timestamp="2026-09-01T09:18:22Z",
            phase1_risk=0.92,
            membership_confidence=0.98,
            evidence_strength=0.96,
            decision_score=0.942,
            tier="PRIMARY",
            recommended_action="FREEZE_RING",
            final_action="FREEZE_RING",
            requires_human_approval=True,
            escalation_reason="Severe Collusion: 4-hop circular UPI layering ring with 96.9% volume retention.",
            action_reason="Pattern B Circular Layering: Immediate ring freeze mandated by governance policy.",
            expected_friction_cost_inr=95000.0,
            ring_id="RING_B_004",
            pattern_type="PATTERN_B_CIRCULAR_LAYERING",
            is_hard_negative=False,
            status=CaseStatus.PENDING_APPROVAL,
            priority=CasePriority.CRITICAL,
            member_count=4,
            shared_devices=["DEV-RELAY-11", "DEV-RELAY-12"],
            shared_ips=["45.134.22.8", "194.26.29.112"],
        )
    )

    # 3. Flagship Pattern C Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-RING-C-03",
            transaction_id="TXN-DEMO-C7703",
            customer_id="CUST-SYNTH-303",
            amount_inr=125000.0,
            timestamp="2026-09-01T09:22:45Z",
            phase1_risk=0.79,
            membership_confidence=0.86,
            evidence_strength=0.82,
            decision_score=0.815,
            tier="PRIMARY",
            recommended_action="RESTRICT_ACCOUNT",
            final_action="RESTRICT_ACCOUNT",
            requires_human_approval=True,
            escalation_reason="Merchant Bust-Out: Dormant 180-day account suddenly transacting ₹1.25L.",
            action_reason="Pattern C Synthetic Bust-Out: Instant account restriction pending merchant verification.",
            expected_friction_cost_inr=125000.0,
            ring_id="RING_C_009",
            pattern_type="PATTERN_C_SYNTHETIC_VELOCITY",
            is_hard_negative=False,
            status=CaseStatus.RECOMMENDED,
            priority=CasePriority.CRITICAL,
            member_count=6,
            shared_devices=["DEV-SYNTH-01"],
            shared_ips=["185.191.171.12"],
        )
    )

    # 4. Hard Negative Festive Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-HARDNEG-04",
            transaction_id="TXN-LEGIT-D104",
            customer_id="CUST-VIP-404",
            amount_inr=89000.0,
            timestamp="2026-09-01T09:25:10Z",
            phase1_risk=0.62,
            membership_confidence=0.05,
            evidence_strength=0.12,
            decision_score=0.284,
            tier="ISOLATED",
            recommended_action="STEP_UP_2FA",
            final_action="STEP_UP_2FA",
            requires_human_approval=False,
            action_reason="High value single txn with clean graph profile. Proportional 2FA friction applied (0.04% Hard-Block FPR invariant).",
            expected_friction_cost_inr=25.0,
            ring_id=None,
            pattern_type="HARD_NEGATIVE_FESTIVE_SPIKE",
            is_hard_negative=True,
            hard_negative_type="FESTIVE_ELECTRONICS_PURCHASE",
            status=CaseStatus.APPROVED,
            priority=CasePriority.MEDIUM,
            member_count=1,
            shared_devices=[],
            shared_ips=[],
            reviewed_by="analyst_01",
            reviewed_at="2026-09-01T09:26:00Z",
            reviewer_notes="Verified legitimate festive corporate bulk purchase. 2FA challenge completed successfully.",
        )
    )

    # 5. Hard Negative Shared WiFi Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-HARDNEG-05",
            transaction_id="TXN-LEGIT-E505",
            customer_id="CUST-FAM-505",
            amount_inr=14200.0,
            timestamp="2026-09-01T09:30:14Z",
            phase1_risk=0.38,
            membership_confidence=0.15,
            evidence_strength=0.08,
            decision_score=0.210,
            tier="ISOLATED",
            recommended_action="ALLOW",
            final_action="ALLOW",
            requires_human_approval=False,
            action_reason="Shared residential router subnet with legitimate multi-account family usage. Zero collusion markers.",
            expected_friction_cost_inr=0.0,
            ring_id=None,
            pattern_type="HARD_NEGATIVE_SHARED_WIFI",
            is_hard_negative=True,
            hard_negative_type="RESIDENTIAL_SHARED_IP",
            status=CaseStatus.RECOMMENDED,
            priority=CasePriority.LOW,
            member_count=1,
            shared_devices=[],
            shared_ips=["122.161.44.19"],
        )
    )

    # 6. Secondary Member Settlement Delay Case
    case_manager.register_case(
        RiskCaseRecord(
            case_id="CASE-DELAY-06",
            transaction_id="TXN-SEC-F606",
            customer_id="CUST-SEC-606",
            amount_inr=32000.0,
            timestamp="2026-09-01T09:35:50Z",
            phase1_risk=0.55,
            membership_confidence=0.62,
            evidence_strength=0.48,
            decision_score=0.535,
            tier="SECONDARY",
            recommended_action="DELAY_SETTLEMENT",
            final_action="DELAY_SETTLEMENT",
            requires_human_approval=False,
            action_reason="Secondary ring node with moderate confidence. Settlement held for 4-hour review window.",
            expected_friction_cost_inr=150.0,
            ring_id="RING_A_001",
            pattern_type="PATTERN_A_DEVICE_FARM",
            is_hard_negative=False,
            status=CaseStatus.RECOMMENDED,
            priority=CasePriority.HIGH,
            member_count=32,
            shared_devices=["DEV-FARM-991"],
            shared_ips=[],
        )
    )

    # 7. Additional cases for rich dashboard display
    for i in range(7, 26):
        score = 0.15 + (i * 0.03) % 0.70
        is_high = score > 0.45
        act = "BLOCK_TRANSACTION" if score > 0.65 else ("STEP_UP_2FA" if is_high else "ALLOW")
        tier = "PRIMARY" if score > 0.65 else ("SECONDARY" if is_high else "ISOLATED")
        prio = CasePriority.CRITICAL if score > 0.65 else (CasePriority.HIGH if is_high else CasePriority.LOW)

        rec = RiskCaseRecord(
            case_id=f"CASE-SYNTH-{i:02d}",
            transaction_id=f"TXN-SYNTH-{i*100+42}",
            customer_id=f"CUST-USER-{1000+i}",
            amount_inr=round(1500.0 + (i * 3750.5), 2),
            timestamp=f"2026-09-01T09:{i+10:02d}:00Z",
            phase1_risk=round(score * 0.95, 3),
            membership_confidence=round(score * 0.9, 3) if is_high else 0.05,
            evidence_strength=round(score * 0.85, 3) if is_high else 0.08,
            decision_score=round(score, 3),
            tier=tier,
            recommended_action=act,
            final_action=act,
            requires_human_approval=is_high,
            escalation_reason=f"Automated risk evaluation score {round(score, 3)}" if is_high else None,
            action_reason=f"Policy threshold matched for score {round(score, 3)}.",
            expected_friction_cost_inr=round(1500.0 + (i * 3750.5), 2) if act.startswith("BLOCK") else 20.0,
            ring_id=f"RING_A_{(i%4)+1:03d}" if is_high else None,
            pattern_type="PATTERN_A_DEVICE_FARM" if is_high else None,
            status=CaseStatus.PENDING_APPROVAL if is_high else CaseStatus.RECOMMENDED,
            priority=prio,
            member_count=4 if is_high else 1,
        )
        case_manager.register_case(rec)

        # Feed initial observations to monitor & drift detector
        drift_detector.record_observation(
            amount_inr=rec.amount_inr,
            decision_score=rec.decision_score,
            evidence_strength=rec.evidence_strength,
            member_count=rec.member_count,
        )
        operational_monitor.record_request(
            endpoint="/api/v2/investigate",
            latency_ms=4.5 + (i * 0.8),
            status_code=200,
            action=rec.recommended_action,
            tier=rec.tier,
            priority=rec.priority.value,
            is_investigation=True,
        )

    # Initial Audit Trail log entries
    audit_trail.record(
        case_id="CASE-RING-A-01",
        actor_id="risk_engine",
        actor_role="SYSTEM",
        event_type=AuditEventType.CASE_CREATED,
        previous_state=None,
        new_state=CaseStatus.RECOMMENDED.value,
        details={"pattern": "Pattern A", "decision_score": 0.895},
    )
    audit_trail.record(
        case_id="CASE-RING-B-02",
        actor_id="risk_engine",
        actor_role="SYSTEM",
        event_type=AuditEventType.APPROVAL_REQUESTED,
        previous_state=CaseStatus.RECOMMENDED.value,
        new_state=CaseStatus.PENDING_APPROVAL.value,
        details={"action": "FREEZE_RING", "reason": "High-impact Ring Collusion"},
    )
    audit_trail.record(
        case_id="CASE-HARDNEG-04",
        actor_id="analyst_01",
        actor_role="ANALYST",
        event_type=AuditEventType.ACTION_APPROVED,
        previous_state=CaseStatus.RECOMMENDED.value,
        new_state=CaseStatus.APPROVED.value,
        details={"action": "STEP_UP_2FA", "notes": "Approved 2FA challenge for festive high-value order"},
    )


# Automatically seed cases on module import
seed_demo_cases()
