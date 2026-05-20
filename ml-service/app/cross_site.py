from dataclasses import dataclass, field
from uuid import uuid4


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
    def __init__(self, embed_fn=None, cosine_fn=None, min_sites: int = 2):
        self.min_sites = min_sites
        self._embed = embed_fn
        self._cosine = cosine_fn
        self._cached_patterns: list[Pattern] = []

    def cluster_vectors(self, vectors: list[list[float]], site_ids: list[str]) -> list[list[str]]:
        if len(vectors) < 2:
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
            cluster_map.setdefault(label, []).append(site_ids[idx])

        result = list(cluster_map.values())
        result.sort(key=len, reverse=True)
        return result

    def find_shared_entities(
        self, cluster: list[str], site_entities: dict[str, list[dict]]
    ) -> list[dict]:
        if len(cluster) < 2:
            return []

        import numpy as np

        seen_sets: set[frozenset] = set()
        patterns = []
        sids = list(site_entities.keys())

        for i in range(len(sids)):
            for j in range(i + 1, len(sids)):
                ents_i = site_entities[sids[i]]
                ents_j = site_entities[sids[j]]

                vecs_i = np.array([e["embedding"] for e in ents_i], dtype=np.float64) if ents_i else np.array([])
                vecs_j = np.array([e["embedding"] for e in ents_j], dtype=np.float64) if ents_j else np.array([])

                if vecs_i.size == 0 or vecs_j.size == 0:
                    continue

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
                            shared.add(ents_i[ei_idx]["label"])
                            shared.add(ents_j[ej_idx]["label"])

                if shared:
                    key = frozenset(shared)
                    if key not in seen_sets:
                        seen_sets.add(key)
                        patterns.append({
                            "pattern_id": str(uuid4()),
                            "name": f"shared_topic_{len(patterns)+1}",
                            "description": f"Shared entities across {len(cluster)} sites",
                            "site_count": len(cluster),
                            "avg_improvement": 0.0,
                            "entities_involved": sorted(shared),
                            "action_sequence": [],
                        })

        patterns.sort(key=lambda p: p["site_count"], reverse=True)
        return patterns

    def detect_action_patterns(self, trajectories: list[list[dict]]) -> list[Pattern]:
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
