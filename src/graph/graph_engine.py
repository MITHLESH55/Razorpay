"""
RiskOrbit — Point-in-Time Graph Engine (Phase 2)

Builds and queries the multi-entity payment relationship graph strictly enforcing
point-in-time causal availability (events <= as_of_timestamp).

SECURITY & LEAKAGE GUARD:
  - Hidden labels (abuse_label, ring_id, abuse_pattern_type) are strictly forbidden.
  - Graph edges are constructed solely from observable transaction logs, orders, and refund requests.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd

from src.graph.schema import GraphEdge, GraphNode, NodeType, RelationshipType
from src.graph.strength import compute_edge_strength

logger = logging.getLogger(__name__)


class PaymentGraphEngine:
    """
    In-memory point-in-time relationship graph engine backed by NetworkX and lookup indices.
    """

    def __init__(
        self,
        transactions: pd.DataFrame,
        orders: pd.DataFrame,
        refunds: pd.DataFrame,
        customers: Optional[pd.DataFrame] = None,
        merchants: Optional[pd.DataFrame] = None,
        devices: Optional[pd.DataFrame] = None,
        ip_entities: Optional[pd.DataFrame] = None,
        instruments: Optional[pd.DataFrame] = None,
    ):
        # Prepare DataFrames with sanitized timestamps
        self.txn = transactions.copy()
        self.txn["timestamp"] = pd.to_datetime(self.txn["timestamp"], format="mixed", errors="coerce")
        self.txn = self.txn.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        self.orders = orders.copy()
        if "created_at" in self.orders.columns:
            self.orders["created_at"] = pd.to_datetime(self.orders["created_at"], format="mixed", errors="coerce")

        self.refunds = refunds.copy()
        if len(self.refunds) > 0 and "refund_requested_at" in self.refunds.columns:
            self.refunds["refund_requested_at"] = pd.to_datetime(self.refunds["refund_requested_at"], format="mixed", errors="coerce")

        self.customers = customers
        self.merchants = merchants
        self.devices = devices
        self.ip_entities = ip_entities
        self.instruments = instruments

        # Index maps for fast lookups
        self._cust_txns = self.txn.groupby("customer_id")
        self._dev_txns = self.txn[self.txn["device_id"].notna()].groupby("device_id")
        self._ip_txns = self.txn[self.txn["ip_id"].notna()].groupby("ip_id")
        self._ins_txns = self.txn[self.txn["instrument_id"].notna()].groupby("instrument_id")

    @classmethod
    def from_data_dir(cls, raw_dir: Path | str = "data/raw") -> PaymentGraphEngine:
        p = Path(raw_dir)
        txns = pd.read_csv(p / "transactions.csv", low_memory=False)
        orders = pd.read_csv(p / "orders.csv", low_memory=False)
        refunds = pd.read_csv(p / "refunds.csv", low_memory=False)
        customers = pd.read_csv(p / "customers.csv", low_memory=False) if (p / "customers.csv").exists() else None
        merchants = pd.read_csv(p / "merchants.csv", low_memory=False) if (p / "merchants.csv").exists() else None
        devices = pd.read_csv(p / "devices.csv", low_memory=False) if (p / "devices.csv").exists() else None
        ip_entities = pd.read_csv(p / "ip_entities.csv", low_memory=False) if (p / "ip_entities.csv").exists() else None
        instruments = pd.read_csv(p / "instruments.csv", low_memory=False) if (p / "instruments.csv").exists() else None

        return cls(
            transactions=txns,
            orders=orders,
            refunds=refunds,
            customers=customers,
            merchants=merchants,
            devices=devices,
            ip_entities=ip_entities,
            instruments=instruments,
        )

    def get_events_as_of(self, as_of_timestamp: datetime) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Filter transaction, order, and refund logs strictly <= as_of_timestamp."""
        txn_sub = self.txn[self.txn["timestamp"] <= as_of_timestamp]
        ord_sub = self.orders[self.orders["created_at"] <= as_of_timestamp] if "created_at" in self.orders.columns else self.orders
        ref_sub = self.refunds[self.refunds["refund_requested_at"] <= as_of_timestamp] if len(self.refunds) > 0 and "refund_requested_at" in self.refunds.columns else self.refunds
        return txn_sub, ord_sub, ref_sub

    def build_networkx_graph_as_of(
        self,
        as_of_timestamp: datetime,
        min_edge_strength: float = 0.0,
    ) -> nx.Graph:
        """
        Build full point-in-time NetworkX graph representing observable payment interactions.
        """
        if not hasattr(self, "_graph_cache"):
            self._graph_cache = {}
        cache_key = (str(as_of_timestamp), min_edge_strength)
        if cache_key in self._graph_cache:
            return self._graph_cache[cache_key]

        txn_sub, _, ref_sub = self.get_events_as_of(as_of_timestamp)
        G = nx.Graph()

        if len(txn_sub) == 0:
            return G

        # Count entity degrees for hubness normalization
        dev_cust_counts = txn_sub[txn_sub["device_id"].notna()].groupby("device_id")["customer_id"].nunique().to_dict()
        ip_cust_counts = txn_sub[txn_sub["ip_id"].notna()].groupby("ip_id")["customer_id"].nunique().to_dict()
        ins_cust_counts = txn_sub[txn_sub["instrument_id"].notna()].groupby("instrument_id")["customer_id"].nunique().to_dict()
        merch_cust_counts = txn_sub.groupby("merchant_id")["customer_id"].nunique().to_dict()

        # 1. Customer <-> Device edges
        dev_pairs = txn_sub[txn_sub["device_id"].notna()].groupby(["customer_id", "device_id"]).agg(
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
            event_count=("transaction_id", "count"),
        ).reset_index()

        for r in dev_pairs.itertuples(index=False):
            cid, did = r.customer_id, r.device_id
            n_acc = dev_cust_counts.get(did, 1)
            st_info = compute_edge_strength(
                event_count=r.event_count,
                first_seen=r.first_seen,
                last_seen=r.last_seen,
                as_of_time=as_of_timestamp,
                n_connected_accounts=n_acc,
                target_entity_type="DEVICE",
            )
            if st_info["strength"] >= min_edge_strength:
                G.add_node(cid, node_type=NodeType.CUSTOMER.value)
                G.add_node(did, node_type=NodeType.DEVICE.value, n_connected_accounts=n_acc)
                G.add_edge(
                    cid, did,
                    relationship_type=RelationshipType.CUSTOMER_USED_DEVICE.value,
                    strength=st_info["strength"],
                    event_count=r.event_count,
                    first_seen=r.first_seen.isoformat(),
                    last_seen=r.last_seen.isoformat(),
                    strength_components=st_info,
                )

        # 2. Customer <-> IP edges
        ip_pairs = txn_sub[txn_sub["ip_id"].notna()].groupby(["customer_id", "ip_id"]).agg(
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
            event_count=("transaction_id", "count"),
        ).reset_index()

        for r in ip_pairs.itertuples(index=False):
            cid, ipid = r.customer_id, r.ip_id
            n_acc = ip_cust_counts.get(ipid, 1)
            st_info = compute_edge_strength(
                event_count=r.event_count,
                first_seen=r.first_seen,
                last_seen=r.last_seen,
                as_of_time=as_of_timestamp,
                n_connected_accounts=n_acc,
                target_entity_type="IP",
            )
            if st_info["strength"] >= min_edge_strength:
                G.add_node(cid, node_type=NodeType.CUSTOMER.value)
                G.add_node(ipid, node_type=NodeType.IP.value, n_connected_accounts=n_acc)
                G.add_edge(
                    cid, ipid,
                    relationship_type=RelationshipType.CUSTOMER_CONNECTED_IP.value,
                    strength=st_info["strength"],
                    event_count=r.event_count,
                    first_seen=r.first_seen.isoformat(),
                    last_seen=r.last_seen.isoformat(),
                    strength_components=st_info,
                )

        # 3. Customer <-> Instrument edges
        ins_pairs = txn_sub[txn_sub["instrument_id"].notna()].groupby(["customer_id", "instrument_id"]).agg(
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
            event_count=("transaction_id", "count"),
        ).reset_index()

        for r in ins_pairs.itertuples(index=False):
            cid, insid = r.customer_id, r.instrument_id
            n_acc = ins_cust_counts.get(insid, 1)
            st_info = compute_edge_strength(
                event_count=r.event_count,
                first_seen=r.first_seen,
                last_seen=r.last_seen,
                as_of_time=as_of_timestamp,
                n_connected_accounts=n_acc,
                target_entity_type="INSTRUMENT",
            )
            if st_info["strength"] >= min_edge_strength:
                G.add_node(cid, node_type=NodeType.CUSTOMER.value)
                G.add_node(insid, node_type=NodeType.INSTRUMENT.value, n_connected_accounts=n_acc)
                G.add_edge(
                    cid, insid,
                    relationship_type=RelationshipType.CUSTOMER_USED_INSTRUMENT.value,
                    strength=st_info["strength"],
                    event_count=r.event_count,
                    first_seen=r.first_seen.isoformat(),
                    last_seen=r.last_seen.isoformat(),
                    strength_components=st_info,
                )

        # 4. Customer <-> Merchant edges
        merch_pairs = txn_sub.groupby(["customer_id", "merchant_id"]).agg(
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
            event_count=("transaction_id", "count"),
        ).reset_index()

        for r in merch_pairs.itertuples(index=False):
            cid, mid = r.customer_id, r.merchant_id
            n_acc = merch_cust_counts.get(mid, 1)
            st_info = compute_edge_strength(
                event_count=r.event_count,
                first_seen=r.first_seen,
                last_seen=r.last_seen,
                as_of_time=as_of_timestamp,
                n_connected_accounts=n_acc,
                target_entity_type="MERCHANT",
            )
            G.add_node(cid, node_type=NodeType.CUSTOMER.value)
            G.add_node(mid, node_type=NodeType.MERCHANT.value, n_connected_accounts=n_acc)
            G.add_edge(
                cid, mid,
                relationship_type=RelationshipType.CUSTOMER_PLACED_ORDER.value,
                strength=st_info["strength"],
                event_count=r.event_count,
                first_seen=r.first_seen.isoformat(),
                last_seen=r.last_seen.isoformat(),
                strength_components=st_info,
            )

        self._graph_cache[cache_key] = G
        return G
