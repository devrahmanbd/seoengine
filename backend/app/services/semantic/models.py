from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EntityNode:
    id: str
    label: str
    type: str
    properties: dict = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class EntityEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


@dataclass
class EntityGraph:
    site_id: str
    nodes: list[EntityNode] = field(default_factory=list)
    edges: list[EntityEdge] = field(default_factory=list)

    def add_node(self, node: EntityNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: EntityEdge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> EntityNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def to_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type,
                    "properties": n.properties,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for e in self.edges
            ],
        }


@dataclass
class LoRAContext:
    adapter_id: str
    site_id: str
    query: str
    adapted_embedding: list[float]
    confidence: float
    metadata: dict = field(default_factory=dict)
    top_entities: list[EntityNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "adapter_id": self.adapter_id,
            "site_id": self.site_id,
            "query": self.query,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "top_entities": [
                {"id": e.id, "label": e.label, "type": e.type}
                for e in self.top_entities
            ],
        }
