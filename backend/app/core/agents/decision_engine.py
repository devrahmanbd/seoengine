from typing import Any


class DecisionEngine:
    def __init__(self, integrator: Any = None):
        self._integrator = integrator

    async def decide(self, state: dict, context: dict | None = None) -> dict:
        base_decision = self._make_base_decision(state, context)

        if self._integrator is None:
            return {
                "decision": base_decision,
                "source": "heuristic",
            }

        enriched = await self._integrator.enrich_decision(state, base_decision)
        return {
            "decision": enriched,
            "source": "policy",
            "policy_recommendations": enriched.get("policy_recommendations", []),
            "data_confidence": enriched.get("data_confidence", "low"),
            "expected_impact": enriched.get("expected_impact", 0.0),
        }

    async def recommend(self, state: dict, top_k: int = 3) -> list[dict]:
        if self._integrator is not None:
            return await self._integrator.recommend_actions(state, top_k=top_k)
        return [
            {"action_type": "run_technical_audit", "confidence": 0.5, "reason": "default"},
            {"action_type": "optimize_content", "confidence": 0.5, "reason": "default"},
        ]

    async def get_enriched_decision(self, state: dict, llm_decision: dict) -> dict:
        if self._integrator is not None:
            return await self._integrator.enrich_decision(state, llm_decision)
        enriched = dict(llm_decision)
        enriched["policy_recommendations"] = []
        enriched["data_confidence"] = "low"
        enriched["expected_impact"] = 0.0
        return enriched

    def _make_base_decision(self, state: dict, context: dict | None = None) -> dict:
        score = state.get("score", 50)
        issues = state.get("issues", 0)

        if score < 30 or issues > 10:
            priority = "critical"
            recommended_action = "run_full_audit"
        elif score < 60 or issues > 5:
            priority = "high"
            recommended_action = "run_technical_audit"
        elif score < 80:
            priority = "medium"
            recommended_action = "optimize_content"
        else:
            priority = "low"
            recommended_action = "monitor"

        return {
            "score": score,
            "issues_count": issues,
            "priority": priority,
            "recommended_action": recommended_action,
            "context": context or {},
        }
