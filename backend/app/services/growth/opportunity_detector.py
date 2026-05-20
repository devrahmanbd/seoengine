import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    action_type: str
    expected_reward: float
    confidence: Literal["high", "medium", "low"]
    source: Literal["policy", "cross_site", "heuristic"]
    effort: Literal["low", "medium", "high"]
    description: str
    evidence: list[str] = field(default_factory=list)


EFFORT_MAP: dict[str, Literal["low", "medium", "high"]] = {
    "fix_title": "low",
    "fix_meta": "low",
    "fix_images": "low",
    "optimize_content": "medium",
    "improve_cwv": "medium",
    "add_schema": "medium",
    "build_backlinks": "high",
    "fix_headings": "low",
    "run_technical_audit": "low",
    "run_full_audit": "medium",
}


class OpportunityDetector:
    def __init__(
        self,
        decision_integrator: Any = None,
        cross_site_analyzer: Any = None,
    ):
        self._integrator = decision_integrator
        self._cross_site = cross_site_analyzer

    async def detect_opportunities(
        self, website_id: str, state: dict, top_k: int = 5
    ) -> list[Opportunity]:
        opportunities: list[Opportunity] = []

        if self._integrator is not None:
            policy_recs = await self._integrator.recommend_actions(state, top_k=top_k)
            for rec in policy_recs:
                reward = rec.get("confidence", 0.5)
                opportunities.append(Opportunity(
                    action_type=rec.get("action_type", "unknown"),
                    expected_reward=reward,
                    confidence="high" if reward > 0.7 else ("medium" if reward > 0.4 else "low"),
                    source="policy",
                    effort=EFFORT_MAP.get(rec.get("action_type", ""), "medium"),
                    description=f"Policy recommends: {rec.get('reason', 'policy_recommended')}",
                    evidence=[f"Policy confidence: {reward:.2f}"],
                ))

        if self._cross_site is not None:
            try:
                patterns = await self._cross_site.get_insights_for_site(website_id)
                for pattern in patterns[:3]:
                    for action in pattern.action_sequence:
                        opportunities.append(Opportunity(
                            action_type=action,
                            expected_reward=pattern.avg_improvement,
                            confidence="medium" if pattern.site_count > 3 else "low",
                            source="cross_site",
                            effort=EFFORT_MAP.get(action, "medium"),
                            description=pattern.description[:120],
                            evidence=[
                                f"Pattern: {pattern.name}",
                                f"Sites: {pattern.site_count}",
                                f"Avg improvement: {pattern.avg_improvement:.2f}",
                            ],
                        ))
            except Exception as e:
                logger.warning("Cross-site analysis failed for %s: %s", website_id, e)

        score = state.get("score", 50)
        issues = state.get("issues", 0)
        if score < 40:
            opportunities.append(Opportunity(
                action_type="run_full_audit",
                expected_reward=0.3,
                confidence="medium",
                source="heuristic",
                effort="medium",
                description=f"Low score ({score}) triggers full audit",
                evidence=[f"Score {score} below 40 threshold"],
            ))
        if issues > 5:
            opportunities.append(Opportunity(
                action_type="fix_meta_tags",
                expected_reward=0.25,
                confidence="medium",
                source="heuristic",
                effort="low",
                description=f"High issue count ({issues}) suggests meta fixes",
                evidence=[f"{issues} issues detected"],
            ))

        opportunities.sort(key=lambda o: o.expected_reward, reverse=True)
        logger.info("Detected %d opportunities for site %s", len(opportunities), website_id)
        return opportunities[:top_k]
