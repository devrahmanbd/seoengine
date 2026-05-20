import asyncio
import math
import time

from app.services.atropos.base_env import SEOEnvironment, SEOAction, State


MOCK_KEYWORD_DATA: dict = {
    "current_rankings": {
        "seo tools": 12,
        "content marketing": 8,
        "keyword research": 15,
        "link building": 22,
        "site audit": 9,
    },
    "keyword_difficulty": {
        "seo tools": 45,
        "content marketing": 30,
        "keyword research": 55,
        "link building": 60,
        "site audit": 35,
    },
    "search_volume": {
        "seo tools": 5400,
        "content marketing": 8900,
        "keyword research": 4200,
        "link building": 3200,
        "site audit": 2800,
    },
    "competitor_coverage": [
        {"keyword": "seo tools", "competitors": ["ahrefs", "semrush", "moz"]},
        {"keyword": "content marketing", "competitors": ["hubspot", "neilpatel"]},
        {"keyword": "keyword research", "competitors": ["ahrefs", "semrush"]},
    ],
    "content_gaps": [
        {"keyword": "seo tools", "gap": "comparative_guide", "priority": "high"},
        {"keyword": "keyword research", "gap": "beginner_tutorial", "priority": "high"},
        {"keyword": "link building", "gap": "case_study", "priority": "medium"},
        {"keyword": "site audit", "gap": "checklist", "priority": "low"},
    ],
    "target_keywords": [],
}


class KeywordResearchEnv(SEOEnvironment):
    def __init__(self, site_id: str = "default"):
        self.site_id = site_id
        self._step_count = 0
        self.max_steps = 20
        self.data: dict = {}

    async def reset(self) -> State:
        self._step_count = 0
        self.data = {
            "current_rankings": dict(MOCK_KEYWORD_DATA["current_rankings"]),
            "keyword_difficulty": dict(MOCK_KEYWORD_DATA["keyword_difficulty"]),
            "search_volume": dict(MOCK_KEYWORD_DATA["search_volume"]),
            "competitor_coverage": [
                {**c} for c in MOCK_KEYWORD_DATA["competitor_coverage"]
            ],
            "content_gaps": [
                {**g} for g in MOCK_KEYWORD_DATA["content_gaps"]
            ],
            "target_keywords": [],
        }
        metrics = self._collect_metrics()
        features = self._compute_features(metrics)
        return State(
            site_id=self.site_id,
            metrics=metrics,
            timestamp=time.time(),
            features=features,
        )

    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        self._step_count += 1
        await asyncio.sleep(0)

        reward = 0.0
        info = {"action": action.action_type, "params": action.params}

        if action.action_type == "target_keyword":
            keyword = action.params.get("keyword", "")
            if keyword and keyword not in self.data["target_keywords"]:
                self.data["target_keywords"].append(keyword)
                improvement = min(0.5, len(self.data["target_keywords"]) * 0.08)
                if keyword in self.data["current_rankings"]:
                    old_rank = self.data["current_rankings"][keyword]
                    new_rank = max(1, old_rank - max(1, int(improvement * 10)))
                    self.data["current_rankings"][keyword] = new_rank
                    improvement += (old_rank - new_rank) / old_rank * 0.3
                reward = min(0.5, improvement)
                info["keyword_added"] = keyword

        elif action.action_type == "expand_cluster":
            cluster = action.params.get("cluster", "")
            related_terms = action.params.get("terms", [])
            added = 0
            for term in related_terms:
                if term not in self.data["current_rankings"]:
                    self.data["current_rankings"][term] = max(
                        1, int(30 + hash(term) % 20)
                    )
                    added += 1
            reward = min(0.5, added * 0.1)
            info["cluster"] = cluster
            info["terms_added"] = added

        elif action.action_type == "fill_content_gap":
            gap_keyword = action.params.get("keyword", "")
            gaps = self.data["content_gaps"]
            matched = [g for g in gaps if g["keyword"] == gap_keyword and g.get("priority")]
            if matched:
                original_priority = matched[0].get("priority", "medium")
                matched[0]["priority"] = "filled"
                priority_map = {"high": 0.3, "medium": 0.2, "low": 0.1}
                base = priority_map.get(original_priority, 0.15)
                reward = min(0.3, base + 0.05)
                info["gap_filled"] = gap_keyword
            else:
                reward = 0.0

        elif action.action_type == "optimize_for_intent":
            keyword = action.params.get("keyword", "")
            intent = action.params.get("intent", "informational")
            if keyword in self.data["current_rankings"]:
                old_rank = self.data["current_rankings"][keyword]
                boost = {"informational": 3, "commercial": 2, "navigational": 1, "transactional": 2}
                bump = boost.get(intent, 1)
                self.data["current_rankings"][keyword] = max(1, old_rank - bump)
                reward = min(0.5, bump * 0.1)
                info["intent"] = intent
                info["rank_change"] = -bump

        done = self._step_count >= self.max_steps
        if not done:
            remaining_gaps = [g for g in self.data["content_gaps"] if g.get("priority") == "high"]
            if not remaining_gaps:
                done = True

        metrics = self._collect_metrics()
        features = self._compute_features(metrics)
        next_state = State(
            site_id=self.site_id,
            metrics=metrics,
            timestamp=time.time(),
            features=features,
        )
        return next_state, reward, done, info

    async def render(self) -> dict:
        return {
            "site_id": self.site_id,
            "step": self._step_count,
            "max_steps": self.max_steps,
            "current_rankings": self.data.get("current_rankings", {}),
            "keyword_difficulty": self.data.get("keyword_difficulty", {}),
            "search_volume": self.data.get("search_volume", {}),
            "competitor_coverage": self.data.get("competitor_coverage", []),
            "content_gaps": self.data.get("content_gaps", []),
            "target_keywords": self.data.get("target_keywords", []),
        }

    def _compute_keyword_score(self, metrics: dict) -> float:
        rankings = metrics.get("current_rankings", {})
        if not rankings:
            return 0.0
        avg_rank = sum(rankings.values()) / len(rankings)
        rank_score = max(0.0, 1.0 - (avg_rank - 1) / 30)
        gap_closure = metrics.get("gap_closure_rate", 0.0)
        coverage = metrics.get("competitor_coverage_ratio", 0.0)
        return round(0.5 * rank_score + 0.3 * gap_closure + 0.2 * coverage, 4)

    def _collect_metrics(self) -> dict:
        rankings = self.data.get("current_rankings", {})
        gaps = self.data.get("content_gaps", [])
        total_gaps = len(gaps)
        filled = sum(1 for g in gaps if g.get("priority") == "filled")
        gap_closure_rate = filled / total_gaps if total_gaps > 0 else 0.0
        coverage = self.data.get("competitor_coverage", [])
        covered = sum(
            1 for kw in rankings if any(c["keyword"] == kw for c in coverage)
        )
        coverage_ratio = covered / len(rankings) if rankings else 0.0
        return {
            "current_rankings": rankings,
            "keyword_difficulty": self.data.get("keyword_difficulty", {}),
            "search_volume": self.data.get("search_volume", {}),
            "target_keywords": self.data.get("target_keywords", []),
            "gap_closure_rate": gap_closure_rate,
            "competitor_coverage_ratio": coverage_ratio,
            "total_gaps": total_gaps,
            "filled_gaps": filled,
        }

    def _compute_features(self, metrics: dict) -> list[float]:
        rankings = metrics.get("current_rankings", {})
        avg_rank = sum(rankings.values()) / len(rankings) if rankings else 30.0
        difficulties = metrics.get("keyword_difficulty", {})
        avg_difficulty = sum(difficulties.values()) / len(difficulties) if difficulties else 50.0
        volumes = metrics.get("search_volume", {})
        avg_volume = sum(volumes.values()) / len(volumes) if volumes else 0.0
        norm_volume = min(1.0, avg_volume / 10000.0)
        return [
            avg_rank / 30.0,
            avg_difficulty / 100.0,
            norm_volume,
            metrics.get("gap_closure_rate", 0.0),
            metrics.get("competitor_coverage_ratio", 0.0),
            len(metrics.get("target_keywords", [])) / 20.0,
        ]
