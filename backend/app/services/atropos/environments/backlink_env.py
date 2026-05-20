import asyncio
import math
import random
import time

from app.services.atropos.base_env import SEOEnvironment, SEOAction, State


MOCK_BACKLINK_DATA: dict = {
    "backlink_count": 127,
    "referring_domains": 34,
    "domain_authority": 28.5,
    "anchor_text_diversity": 0.45,
    "toxic_links": 8,
    "competitor_backlinks_avg": 420,
    "broken_outbound_links": 12,
    "anchor_text_distribution": {
        "branded": 0.35,
        "exact_match": 0.30,
        "partial_match": 0.20,
        "generic": 0.10,
        "naked_url": 0.05,
    },
}


class BacklinkEnv(SEOEnvironment):
    def __init__(self, site_id: str = "default"):
        self.site_id = site_id
        self._step_count = 0
        self.max_steps = 20
        self.data: dict = {}

    async def reset(self) -> State:
        self._step_count = 0
        self.data = {k: v for k, v in MOCK_BACKLINK_DATA.items()}
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

        if action.action_type == "earn_backlink":
            quality = action.params.get("quality", "medium")
            quality_map = {"high": (0.3, 3), "medium": (0.2, 1), "low": (0.05, 0)}
            auth_delta, domain_delta = quality_map.get(quality, (0.1, 1))
            self.data["domain_authority"] = min(
                100.0, self.data["domain_authority"] + auth_delta
            )
            self.data["referring_domains"] += domain_delta
            self.data["backlink_count"] += domain_delta * random.randint(2, 5)
            reward = min(0.4, domain_delta * 0.15 + auth_delta * 0.5)
            info["quality"] = quality
            info["new_domains"] = domain_delta

        elif action.action_type == "fix_broken_links":
            fix_count = action.params.get("count", self.data.get("broken_outbound_links", 0))
            actual_fix = min(fix_count, self.data.get("broken_outbound_links", 0))
            self.data["broken_outbound_links"] -= actual_fix
            self.data["domain_authority"] = min(
                100.0, self.data["domain_authority"] + actual_fix * 0.1
            )
            reward = min(0.3, actual_fix * 0.03)
            info["fixed"] = actual_fix

        elif action.action_type == "diversify_anchors":
            dist = self.data.get("anchor_text_distribution", {})
            if dist.get("exact_match", 0) > 0.25:
                over = dist["exact_match"] - 0.20
                dist["exact_match"] = 0.20
                dist["branded"] = dist.get("branded", 0.35) + over * 0.5
                dist["generic"] = dist.get("generic", 0.10) + over * 0.3
                dist["naked_url"] = dist.get("naked_url", 0.05) + over * 0.2
            self.data["anchor_text_diversity"] = min(
                1.0, self.data.get("anchor_text_diversity", 0.45) + 0.05
            )
            entropy = self._anchor_entropy(dist)
            reward = min(0.4, entropy * 0.4)
            info["entropy"] = entropy

        elif action.action_type == "disavow_toxic":
            disavow_count = action.params.get("count", self.data.get("toxic_links", 0))
            actual_disavow = min(disavow_count, self.data.get("toxic_links", 0))
            self.data["toxic_links"] -= actual_disavow
            self.data["domain_authority"] = min(
                100.0, self.data["domain_authority"] + actual_disavow * 0.2
            )
            reward = min(0.4, actual_disavow * 0.05)
            info["disavowed"] = actual_disavow

        done = self._step_count >= self.max_steps
        if not done and self.data.get("domain_authority", 0) >= 70.0:
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
            "backlink_count": self.data.get("backlink_count", 0),
            "referring_domains": self.data.get("referring_domains", 0),
            "domain_authority": self.data.get("domain_authority", 0),
            "anchor_text_diversity": self.data.get("anchor_text_diversity", 0),
            "toxic_links": self.data.get("toxic_links", 0),
            "competitor_backlinks_avg": self.data.get("competitor_backlinks_avg", 0),
            "broken_outbound_links": self.data.get("broken_outbound_links", 0),
            "anchor_text_distribution": self.data.get("anchor_text_distribution", {}),
        }

    def _compute_backlink_score(self, metrics: dict) -> float:
        da = metrics.get("domain_authority", 0)
        da_score = da / 100.0
        diversity = metrics.get("anchor_text_diversity", 0)
        ref_domains = metrics.get("referring_domains", 0)
        domain_score = min(1.0, ref_domains / 100)
        toxic = metrics.get("toxic_links", 0)
        toxic_penalty = max(0.0, 1.0 - toxic / 20)
        competitive = metrics.get("competitive_ratio", 1.0)
        return round(
            0.35 * da_score
            + 0.20 * diversity
            + 0.20 * domain_score
            + 0.10 * toxic_penalty
            + 0.15 * competitive,
            4,
        )

    def _collect_metrics(self) -> dict:
        comp_avg = self.data.get("competitor_backlinks_avg", 1)
        own_count = self.data.get("backlink_count", 0)
        competitive_ratio = min(1.0, own_count / comp_avg) if comp_avg > 0 else 0.0
        return {
            "backlink_count": self.data.get("backlink_count", 0),
            "referring_domains": self.data.get("referring_domains", 0),
            "domain_authority": self.data.get("domain_authority", 0),
            "anchor_text_diversity": self.data.get("anchor_text_diversity", 0),
            "toxic_links": self.data.get("toxic_links", 0),
            "competitor_backlinks_avg": self.data.get("competitor_backlinks_avg", 0),
            "broken_outbound_links": self.data.get("broken_outbound_links", 0),
            "competitive_ratio": competitive_ratio,
        }

    def _compute_features(self, metrics: dict) -> list[float]:
        return [
            metrics.get("domain_authority", 0) / 100.0,
            metrics.get("anchor_text_diversity", 0),
            min(1.0, metrics.get("referring_domains", 0) / 100),
            min(1.0, metrics.get("backlink_count", 0) / 1000),
            max(0.0, 1.0 - metrics.get("toxic_links", 0) / 20),
            metrics.get("competitive_ratio", 0.0),
        ]

    def _anchor_entropy(self, dist: dict) -> float:
        total = sum(dist.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for v in dist.values():
            p = v / total
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(len(dist))
        return entropy / max_entropy if max_entropy > 0 else 1.0
