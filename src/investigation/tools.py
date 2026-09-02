"""
RiskOrbit — Structured Investigation Tools (Phase 2)

Deterministic, typed, point-in-time tools for graph and behavioral investigation.
SECURITY:
  - Unrestricted shell or raw SQL is strictly prevented.
  - Hidden ground-truth labels (abuse_label, ring_id, abuse_pattern_type) are strictly inaccessible.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, List, Optional
import networkx as nx
import numpy as np
import pandas as pd

from src.graph.graph_engine import PaymentGraphEngine
from src.graph.traversal import extract_local_case_subgraph
from src.graph.strength import compute_edge_strength


class InvestigationToolKit:
    def __init__(self, graph_engine: PaymentGraphEngine):
        self.engine = graph_engine

    def get_customer_profile(self, customer_id: str, as_of_time: datetime) -> dict[str, Any]:
        """Fetch historical customer statistics strictly prior to as_of_time."""
        txn_sub, _, ref_sub = self.engine.get_events_as_of(as_of_time)
        cust_txns = txn_sub[txn_sub["customer_id"] == customer_id]

        if len(cust_txns) == 0:
            return {"customer_id": customer_id, "status": "no_transactions_found"}

        txn_ids = cust_txns["transaction_id"].values
        cust_refs = ref_sub[ref_sub["transaction_id"].isin(txn_ids)] if len(ref_sub) > 0 and "transaction_id" in ref_sub.columns else pd.DataFrame()

        return {
            "customer_id": customer_id,
            "first_transaction_at": str(cust_txns["timestamp"].min()),
            "last_transaction_at": str(cust_txns["timestamp"].max()),
            "total_transactions": len(cust_txns),
            "total_spend": round(float(cust_txns["amount"].sum()), 2),
            "avg_transaction_amount": round(float(cust_txns["amount"].mean()), 2),
            "total_refunds": len(cust_refs),
            "refund_rate": round(float(len(cust_refs) / len(cust_txns)), 4),
            "unique_devices": int(cust_txns["device_id"].dropna().nunique()),
            "unique_ips": int(cust_txns["ip_id"].dropna().nunique()),
            "unique_merchants": int(cust_txns["merchant_id"].dropna().nunique()),
        }

    def get_device_connections(self, customer_id: str, as_of_time: datetime) -> list[dict[str, Any]]:
        """Get all devices used by customer and other accounts using those devices."""
        txn_sub, _, _ = self.engine.get_events_as_of(as_of_time)
        cust_txns = txn_sub[txn_sub["customer_id"] == customer_id]
        devices = cust_txns["device_id"].dropna().unique()

        connections = []
        for did in devices:
            dev_txns = txn_sub[txn_sub["device_id"] == did]
            sharing_custs = dev_txns["customer_id"].unique().tolist()
            connections.append({
                "device_id": did,
                "n_sharing_accounts": len(sharing_custs),
                "sharing_account_ids": sharing_custs,
                "total_device_txns": len(dev_txns),
                "first_seen": str(dev_txns["timestamp"].min()),
                "last_seen": str(dev_txns["timestamp"].max()),
            })
        return connections

    def get_ip_connections(self, customer_id: str, as_of_time: datetime) -> list[dict[str, Any]]:
        """Get all IP subnets connected to customer and other accounts using those IPs."""
        txn_sub, _, _ = self.engine.get_events_as_of(as_of_time)
        cust_txns = txn_sub[txn_sub["customer_id"] == customer_id]
        ips = cust_txns["ip_id"].dropna().unique()

        connections = []
        for ipid in ips:
            ip_txns = txn_sub[txn_sub["ip_id"] == ipid]
            sharing_custs = ip_txns["customer_id"].unique().tolist()
            connections.append({
                "ip_id": ipid,
                "n_sharing_accounts": len(sharing_custs),
                "sharing_account_ids": sharing_custs[:20],  # bounded output
                "total_ip_txns": len(ip_txns),
                "first_seen": str(ip_txns["timestamp"].min()),
                "last_seen": str(ip_txns["timestamp"].max()),
            })
        return connections

    def get_related_customers(self, customer_id: str, as_of_time: datetime, max_hops: int = 2) -> dict[str, Any]:
        """Fetch 2-hop connected customer accounts and linking infrastructure."""
        G = self.engine.build_networkx_graph_as_of(as_of_time, min_edge_strength=0.05)
        case_sub = extract_local_case_subgraph(G, customer_id, max_hops=max_hops)

        connected_custs = [n["node_id"] for n in case_sub["nodes"] if n["node_type"] == "CUSTOMER" and n["node_id"] != customer_id]
        shared_devices = [n["node_id"] for n in case_sub["nodes"] if n["node_type"] == "DEVICE"]
        shared_ips = [n["node_id"] for n in case_sub["nodes"] if n["node_type"] == "IP"]
        shared_ins = [n["node_id"] for n in case_sub["nodes"] if n["node_type"] == "INSTRUMENT"]

        return {
            "root_customer_id": customer_id,
            "connected_customer_count": len(connected_custs),
            "connected_customer_ids": connected_custs,
            "shared_devices": shared_devices,
            "shared_ips": shared_ips,
            "shared_instruments": shared_ins,
            "subgraph_statistics": case_sub["statistics"],
        }

    def calculate_temporal_overlap(self, customer_ids: list[str], as_of_time: datetime) -> dict[str, Any]:
        """Calculate temporal coordination density among a set of customer IDs."""
        txn_sub, _, _ = self.engine.get_events_as_of(as_of_time)
        sub = txn_sub[txn_sub["customer_id"].isin(customer_ids)]

        if len(sub) < 2:
            return {"coordination_score": 0.0, "time_span_hours": 0.0, "burst_detected": False}

        ts = sub["timestamp"].sort_values()
        span_hours = max(0.1, (ts.max() - ts.min()).total_seconds() / 3600.0)
        txn_rate_per_hour = len(sub) / span_hours
        burst_detected = txn_rate_per_hour >= 0.20  # >= 5 txns/day

        return {
            "coordination_score": round(min(1.0, txn_rate_per_hour / 0.50), 4),
            "time_span_hours": round(span_hours, 2),
            "total_transactions": len(sub),
            "burst_detected": burst_detected,
        }

    def calculate_refund_similarity(self, customer_ids: list[str], as_of_time: datetime) -> dict[str, Any]:
        """Compute refund rate consistency across member accounts."""
        txn_sub, _, ref_sub = self.engine.get_events_as_of(as_of_time)
        sub_txn = txn_sub[txn_sub["customer_id"].isin(customer_ids)]

        if len(sub_txn) == 0:
            return {"mean_refund_rate": 0.0, "refund_similarity_score": 0.0}

        rates = []
        for cid in customer_ids:
            c_txns = sub_txn[sub_txn["customer_id"] == cid]
            if len(c_txns) > 0:
                t_ids = c_txns["transaction_id"].values
                c_refs = ref_sub[ref_sub["transaction_id"].isin(t_ids)] if len(ref_sub) > 0 else pd.DataFrame()
                rates.append(len(c_refs) / len(c_txns))

        mean_rate = float(np.mean(rates)) if rates else 0.0
        std_rate = float(np.std(rates)) if len(rates) > 1 else 0.0
        # High similarity = high mean rate + low standard deviation
        similarity_score = round(max(0.0, mean_rate * (1.0 - min(1.0, std_rate))), 4)

        return {
            "mean_refund_rate": round(mean_rate, 4),
            "std_refund_rate": round(std_rate, 4),
            "refund_similarity_score": similarity_score,
            "individual_rates": [round(r, 4) for r in rates],
        }
