import logging
from typing import Any

from app.services.atropos.scored_data_api import ScoredDataBuffer

logger = logging.getLogger(__name__)


class DecisionIntegrator:
    def __init__(self, trainer: Any = None, buffer: ScoredDataBuffer | None = None):
        self._trainer = trainer
        self._buffer = buffer
        self._action_history: list[dict] = []
        self._total_decisions = 0
        self._total_policy_hits = 0

    async def recommend_actions(self, state: dict, top_k: int = 3) -> list[dict]:
        logger.info("Recommending top-%d actions for state (has_trained=%s)", top_k, self.has_trained_policy())
        if not self.has_trained_policy():
            return [
                {"action_type": "run_technical_audit", "confidence": 0.5, "reason": "default"},
                {"action_type": "optimize_content", "confidence": 0.5, "reason": "default"},
            ]

        recommendations: list[dict] = []
        action_types = ["run_technical_audit", "optimize_content", "fix_meta_tags", "improve_cwv", "add_schema", "build_backlinks"]
        for at in action_types:
            score = await self.score_action(state, {"action_type": at})
            recommendations.append({
                "action_type": at,
                "confidence": float(score),
                "reason": "policy_recommended" if score > 0.5 else "policy_discouraged",
            })

        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        return recommendations[:top_k]

    async def score_action(self, state: dict, action: dict) -> float:
        if self._trainer is None:
            return 0.5

        try:
            tensor = self._trainer._state_to_tensor(state)
            action_idx = self._trainer._get_action_idx(action)
            import torch
            with torch.no_grad():
                dist = self._trainer._policy(tensor.unsqueeze(0))
                prob = dist.probs[0, action_idx].item()
            return float(prob)
        except Exception as e:
            logger.warning("Failed to score action: %s", e)
            return 0.5

    async def get_action_value(self, state: dict, action: dict) -> float:
        if self._trainer is None:
            return 0.0

        try:
            tensor = self._trainer._state_to_tensor(state)
            import torch
            with torch.no_grad():
                value = self._trainer._value(tensor.unsqueeze(0))
            return float(value.item())
        except Exception as e:
            logger.warning("Failed to get action value: %s", e)
            return 0.0

    def has_trained_policy(self) -> bool:
        if self._trainer is None:
            return False
        return self._trainer._train_step > 0

    async def enrich_decision(self, state: dict, llm_decision: dict) -> dict:
        self._total_decisions += 1

        if not self.has_trained_policy():
            enriched = dict(llm_decision)
            enriched["policy_recommendations"] = []
            enriched["data_confidence"] = "low"
            enriched["expected_impact"] = 0.0
            return enriched

        recommendations = await self.recommend_actions(state, top_k=3)
        best_action = recommendations[0] if recommendations else {}
        expected_impact = await self.get_action_value(state, best_action) if best_action else 0.0

        if expected_impact > 0:
            self._total_policy_hits += 1

        enriched = dict(llm_decision)
        enriched["policy_recommendations"] = recommendations
        enriched["data_confidence"] = "medium" if expected_impact > 0 else "low"
        enriched["expected_impact"] = expected_impact

        self._action_history.append({
            "state": state,
            "llm_decision": llm_decision,
            "policy_recommendations": recommendations,
            "expected_impact": expected_impact,
        })

        logger.info("Enriched decision #%d (confidence=%s, impact=%.4f)", self._total_decisions, enriched["data_confidence"], expected_impact)
        return enriched

    def get_stats(self) -> dict:
        return {
            "total_decisions": self._total_decisions,
            "total_policy_hits": self._total_policy_hits,
            "history_size": len(self._action_history),
            "has_trained_policy": self.has_trained_policy(),
        }
