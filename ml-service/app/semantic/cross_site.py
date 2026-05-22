from dataclasses import dataclass, field
from uuid import uuid4

from app.semantic.db import SemanticDB


@dataclass
class Pattern:
    pattern_id: str
    name: str
    description: str
    site_count: int
    avg_improvement: float
    entities_involved: list[str] = field(default_factory=list)
    action_sequence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "site_count": self.site_count,
            "avg_improvement": round(self.avg_improvement, 4),
            "entities_involved": self.entities_involved,
            "action_sequence": self.action_sequence,
        }


class CrossSiteAnalyzer:
    def __init__(self, semantic_db: SemanticDB, min_sites: int = 2):
        self.db = semantic_db
        self.min_sites = min_sites
        self._cached_patterns: list[Pattern] = []

    async def find_patterns(self, limit: int = 10) -> list[Pattern]:
        site_ids = await self.db.get_all_site_ids()
        if len(site_ids) < self.min_sites:
            return []

        clusters = await self._cluster_sites(site_ids)
        all_patterns: list[Pattern] = []

        for cluster in clusters:
            if len(cluster) < self.min_sites:
                continue
            patterns = await self._extract_cluster_patterns(cluster)
            all_patterns.extend(patterns)

        all_patterns.sort(key=lambda p: p.avg_improvement, reverse=True)
        self._cached_patterns = all_patterns[:limit]
        return self._cached_patterns

    async def get_site_cluster(self, site_id: str) -> list[str]:
        all_ids = await self.db.get_all_site_ids()
        similar = await self.db.find_similar_sites(site_id, limit=10)
        cluster = [site_id]
        cluster.extend(sid for sid, _ in similar)
        return cluster

    async def detect_action_patterns(
        self, trajectories: list[list[dict]]
    ) -> list[Pattern]:
        if not trajectories:
            return []

        fingerprints: dict[str, dict] = {}
        for traj in trajectories:
            seq = tuple(t["action"] for t in traj)
            fp = hash(seq)
            rewards = [t.get("reward", 0.0) for t in traj]
            avg_r = sum(rewards) / len(rewards) if rewards else 0.0
            if fp not in fingerprints:
                fingerprints[fp] = {
                    "action_sequence": list(seq),
                    "rewards": [],
                    "count": 0,
                }
            fingerprints[fp]["rewards"].append(avg_r)
            fingerprints[fp]["count"] += 1

        patterns = []
        for fp, data in fingerprints.items():
            if data["count"] < self.min_sites:
                continue
            avg_imp = sum(data["rewards"]) / len(data["rewards"])
            patterns.append(
                Pattern(
                    pattern_id=str(uuid4()),
                    name=f"pattern_{len(patterns)+1}",
                    description=f"Action sequence repeated across {data['count']} trajectories",
                    site_count=data["count"],
                    avg_improvement=avg_imp,
                    action_sequence=data["action_sequence"],
                )
            )

        patterns.sort(key=lambda p: p.avg_improvement, reverse=True)
        return patterns

    async def get_insights_for_site(self, site_id: str) -> list[Pattern]:
        cluster = await self.get_site_cluster(site_id)
        if len(cluster) < self.min_sites:
            return []

        all_patterns = self._cached_patterns
        if not all_patterns:
            all_patterns = await self.find_patterns(limit=50)

        site_patterns = []
        for p in all_patterns:
            overlap = [e for e in p.entities_involved if e in cluster]
            if overlap:
                site_patterns.append(p)

        site_patterns.sort(key=lambda p: p.avg_improvement, reverse=True)
        return site_patterns[:10]

    async def _cluster_sites(self, site_ids: list[str]) -> list[list[str]]:
        if len(site_ids) < 2:
            return []

        vectors = []
        valid_ids = []
        for sid in site_ids:
            vec = await self.db.get_topic_vector(sid)
            if vec is not None:
                vectors.append(vec)
                valid_ids.append(sid)

        if len(valid_ids) < 2:
            return []

        import numpy as np
        from sklearn.cluster import DBSCAN

        matrix = np.array(vectors, dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix_normed = matrix / norms
        sim_matrix = matrix_normed @ matrix_normed.T
        sim_matrix = np.clip(sim_matrix, 0.0, 1.0)
        dist_matrix = 1.0 - sim_matrix

        clustering = DBSCAN(eps=0.3, min_samples=2, metric="precomputed").fit(dist_matrix)

        cluster_map: dict[int, list[str]] = {}
        for idx, label in enumerate(clustering.labels_):
            if label == -1:
                continue
            cluster_map.setdefault(label, []).append(valid_ids[idx])

        result = list(cluster_map.values())
        result.sort(key=len, reverse=True)
        return result

    async def _extract_cluster_patterns(
        self, cluster: list[str]
    ) -> list[Pattern]:
        if len(cluster) < 2:
            return []

        import numpy as np

        site_entities: dict[str, list[tuple[str, str, list[float]]]] = {}
        for sid in cluster:
            graph = await self.db.get_graph(sid)
            if not graph:
                continue
            entries = []
            for node in graph.nodes:
                if node.embedding is not None:
                    entries.append((node.id, node.label, node.embedding))
            if entries:
                site_entities[sid] = entries

        if len(site_entities) < 2:
            return []

        seen_sets: set[frozenset] = set()
        patterns = []
        sids = list(site_entities.keys())

        for i in range(len(sids)):
            for j in range(i + 1, len(sids)):
                ents_i = site_entities[sids[i]]
                ents_j = site_entities[sids[j]]

                vecs_i = np.array([e[2] for e in ents_i], dtype=np.float64)
                vecs_j = np.array([e[2] for e in ents_j], dtype=np.float64)

                norms_i = np.linalg.norm(vecs_i, axis=1, keepdims=True)
                norms_j = np.linalg.norm(vecs_j, axis=1, keepdims=True)
                norms_i[norms_i == 0] = 1.0
                norms_j[norms_j == 0] = 1.0

                normed_i = vecs_i / norms_i
                normed_j = vecs_j / norms_j

                sim_matrix = normed_i @ normed_j.T
                sim_matrix = np.clip(sim_matrix, 0.0, 1.0)

                shared: set[str] = set()
                for ei_idx in range(len(ents_i)):
                    for ej_idx in range(len(ents_j)):
                        if sim_matrix[ei_idx, ej_idx] >= 0.75:
                            shared.add(ents_i[ei_idx][1])
                            shared.add(ents_j[ej_idx][1])

                if shared:
                    key = frozenset(shared)
                    if key not in seen_sets:
                        seen_sets.add(key)
                        patterns.append(
                            Pattern(
                                pattern_id=str(uuid4()),
                                name=f"shared_topic_{len(patterns)+1}",
                                description=f"Shared entities across {len(cluster)} sites",
                                site_count=len(cluster),
                                avg_improvement=0.0,
                                entities_involved=sorted(shared),
                                action_sequence=[],
                            )
                        )

        patterns.sort(key=lambda p: p.site_count, reverse=True)
        return patterns
