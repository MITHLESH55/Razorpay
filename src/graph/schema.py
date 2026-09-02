"""
RiskOrbit — Graph Entities and Relationships Schema (Phase 2)

Defines explicit node and relationship schemas for the payment graph.
All nodes and edges carry temporal provenance and structured attributes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class NodeType(str, Enum):
    CUSTOMER = "CUSTOMER"
    DEVICE = "DEVICE"
    IP = "IP"
    MERCHANT = "MERCHANT"
    ORDER = "ORDER"
    REFUND = "REFUND"
    INSTRUMENT = "INSTRUMENT"


class RelationshipType(str, Enum):
    CUSTOMER_USED_DEVICE = "CUSTOMER_USED_DEVICE"
    CUSTOMER_CONNECTED_IP = "CUSTOMER_CONNECTED_IP"
    CUSTOMER_USED_INSTRUMENT = "CUSTOMER_USED_INSTRUMENT"
    CUSTOMER_PLACED_ORDER = "CUSTOMER_PLACED_ORDER"
    ORDER_BELONGS_TO_MERCHANT = "ORDER_BELONGS_TO_MERCHANT"
    ORDER_GENERATED_REFUND = "ORDER_GENERATED_REFUND"


@dataclass
class GraphNode:
    node_id: str
    node_type: NodeType
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "attributes": self.attributes,
        }


@dataclass
class GraphEdge:
    source_id: str
    source_type: NodeType
    relationship_type: RelationshipType
    target_id: str
    target_type: NodeType
    first_seen: datetime
    last_seen: datetime
    event_count: int = 1
    strength: float = 1.0
    supporting_event_ids: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "relationship_type": self.relationship_type.value,
            "target_id": self.target_id,
            "target_type": self.target_type.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "event_count": self.event_count,
            "strength": round(float(self.strength), 4),
            "supporting_event_ids": self.supporting_event_ids,
            "attributes": self.attributes,
        }
