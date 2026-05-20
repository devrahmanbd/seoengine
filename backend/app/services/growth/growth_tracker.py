import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class GrowthState:
    website_id: str
    growth_score: float
    trend: Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]
    trajectory_count: int
    avg_reward: float
    score_history: list[float] = field(default_factory=list)
    action_effectiveness: dict[str, dict] = field(default_factory=dict)


INTERVENTION_THRESHOLD = 0.2


class GrowthTracker:
    def __init__(self, growth_scorer: Any = None, data_collector: Any = None):
        self._growth_scorer = growth_scorer
        self._data_collector = data_collector

    async def get_growth_state(self, website_id: str) -> GrowthState:
        if self._growth_scorer is None:
            return GrowthState(
                website_id=website_id, growth_score=0.0,
                trend="unknown", trajectory_count=0, avg_reward=0.0,
            )

        score_data = await self._growth_scorer.score_growth(website_id)

        trend: Literal["accelerating", "decelerating", "plateauing", "declining", "unknown"]
        raw_trend = score_data.get("trend", "unknown")
        if raw_trend == "stable":
            trend = "plateauing"
        elif raw_trend in ("accelerating", "declining", "unknown"):
            trend = raw_trend
        else:
            trend = "unknown"

        score_history: list[float] = []
        if self._data_collector is not None:
            score_history = await self._data_collector.get_score_progression(website_id) or []

        action_effectiveness: dict[str, dict] = {}
        if self._growth_scorer is not None:
            ae = await self._growth_scorer.get_action_effectiveness(website_id)
            for k, v in ae.items():
                action_effectiveness[k] = {
                    "count": v.get("count", 0),
                    "avg_reward": v.get("avg_reward", 0.0),
                }

        return GrowthState(
            website_id=website_id,
            growth_score=score_data.get("growth_score", 0.0),
            trend=trend,
            trajectory_count=score_data.get("trajectories_count", 0),
            avg_reward=score_data.get("avg_reward", 0.0),
            score_history=score_history,
            action_effectiveness=action_effectiveness,
        )

    async def compare_websites(self, website_ids: list[str]) -> list[GrowthState]:
        states: list[GrowthState] = []
        for wid in website_ids:
            state = await self.get_growth_state(wid)
            states.append(state)
        states.sort(key=lambda s: s.growth_score, reverse=True)
        return states

    async def needs_intervention(self, website_id: str) -> bool:
        state = await self.get_growth_state(website_id)
        if state.trend == "declining":
            return True
        if state.trend == "plateauing" and state.growth_score < INTERVENTION_THRESHOLD:
            return True
        return False

    async def get_effective_actions(
        self, website_id: str, min_occurrences: int = 2
    ) -> dict[str, dict]:
        if self._growth_scorer is None:
            return {}
        eff = await self._growth_scorer.get_action_effectiveness(website_id)
        return {
            k: v for k, v in eff.items()
            if v.get("count", 0) >= min_occurrences
        }
