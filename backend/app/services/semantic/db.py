import json
from collections import defaultdict

from app.services.semantic.embeddings import cosine_similarity as _cosine_similarity, embed_text as _embed_text
from app.services.semantic.models import EntityGraph, EntityNode, EntityEdge


class SemanticDB:
    def __init__(self, dimension: int = 32):
        self.dimension = dimension  # informational; actual dimension determined by embedding function
        self._graphs: dict[str, EntityGraph] = {}
        self._topic_vectors: dict[str, list[float]] = {}
        self._documents: dict[str, dict[str, str]] = defaultdict(dict)

    async def store_entity_graph(self, site_id: str, graph: EntityGraph) -> None:
        self._graphs[site_id] = graph
        topic_texts = []
        for node in graph.nodes:
            topic_texts.append(f"{node.label} {node.type} {json.dumps(node.properties)}")
        combined = " ".join(topic_texts)
        self._topic_vectors[site_id] = _embed_text(combined)

    async def get_entity_graph(self, site_id: str) -> EntityGraph | None:
        return self._graphs.get(site_id)

    async def get_graph(self, site_id: str) -> EntityGraph | None:
        return await self.get_entity_graph(site_id)

    async def store_document(self, site_id: str, doc_id: str, content: str) -> None:
        self._documents[site_id][doc_id] = content

    async def search_similar(
        self, embedding: list[float], limit: int = 10,
    ) -> list[dict]:
        results = []
        for site_id, graph in self._graphs.items():
            for node in graph.nodes:
                if node.embedding:
                    score = _cosine_similarity(embedding, node.embedding)
                    results.append({
                        "site_id": site_id,
                        "node_id": node.id,
                        "label": node.label,
                        "score": round(score, 4),
                    })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    async def find_related_sites(
        self, site_id: str, max_results: int = 10,
    ) -> list[dict]:
        graph = await self.get_entity_graph(site_id)
        if not graph:
            return []
        related: dict[str, dict] = {}
        for node in graph.nodes:
            if node.embedding:
                similar = await self.search_similar(node.embedding, limit=5)
                for item in similar:
                    sid = item["site_id"]
                    if sid != site_id:
                        if sid not in related:
                            related[sid] = {"site_id": sid, "score": 0.0, "overlap": 0}
                        related[sid]["score"] = max(related[sid]["score"], item["score"])
                        related[sid]["overlap"] += 1
        return sorted(related.values(), key=lambda x: x["score"], reverse=True)[:max_results]

    async def find_similar_sites(self, site_id: str, limit: int = 5) -> list[tuple[str, float]]:
        if site_id not in self._topic_vectors:
            return []
        query_vec = self._topic_vectors[site_id]
        scored = []
        for sid, vec in self._topic_vectors.items():
            if sid == site_id:
                continue
            score = _cosine_similarity(query_vec, vec)
            scored.append((sid, round(score, 4)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    async def get_all_site_ids(self) -> list[str]:
        return list(self._graphs.keys())

    async def get_topic_vector(self, site_id: str) -> list[float] | None:
        return self._topic_vectors.get(site_id)

    async def get_graph_context(self, site_id: str, query: str) -> dict:
        graph = await self.get_entity_graph(site_id)
        if not graph:
            return {"site_id": site_id, "entities": [], "edges": [], "documents": []}
        query_vec = _embed_text(query)
        scored_nodes = []
        for node in graph.nodes:
            node_text = f"{node.label} {node.type}"
            node_vec = _embed_text(node_text)
            score = _cosine_similarity(query_vec, node_vec)
            scored_nodes.append((node, score))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        top_nodes = scored_nodes[:10]
        top_ids = {n.id for n, _ in top_nodes}
        relevant_edges = [
            e for e in graph.edges if e.source in top_ids or e.target in top_ids
        ]
        return {
            "site_id": site_id,
            "query": query,
            "entities": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type,
                    "properties": n.properties,
                    "relevance": round(s, 4),
                }
                for n, s in top_nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for e in relevant_edges
            ],
        }

    async def health(self) -> dict:
        import time
        start = time.monotonic()
        site_count = len(self._graphs)
        _ = self._topic_vectors.get
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "site_count": site_count,
        }

    async def close(self) -> None:
        self._graphs.clear()
        self._topic_vectors.clear()
        self._documents.clear()
