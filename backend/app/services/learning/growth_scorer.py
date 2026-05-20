import logging
from typing import Any

logger = logging.getLogger(__name__)


class GrowthScorer:
    def __init__(self, collector: Any = None):
        self._collector = collector

    async def score_growth(self, website_id: str) -> dict:
        if self._collector is None:
            return {"website_id": website_id, "growth_score": 0.0, "trend": "unknown"}

        trajectories = await self._collector.collect_website_trajectories(website_id)
        if not trajectories:
            return {"website_id": website_id, "growth_score": 0.0, "trend": "unknown", "trajectories_count": 0}

        rewards = [sum(t.rewards) for t in trajectories]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0

        growth_score = max(-1.0, min(1.0, avg_reward))

        if len(rewards) >= 3:
            recent = rewards[-3:]
            if all(r > 0 for r in recent):
                trend = "accelerating"
            elif all(r < 0 for r in recent):
                trend = "declining"
            else:
                trend = "mixed"
        elif len(rewards) >= 1:
            trend = "stable"
        else:
            trend = "unknown"

        logger.info("Growth score for %s: %.4f (trend=%s, trajs=%d)", website_id, growth_score, trend, len(trajectories))

        return {
            "website_id": website_id,
            "growth_score": growth_score,
            "trend": trend,
            "trajectories_count": len(trajectories),
            "avg_reward": avg_reward,
        }

    async def get_action_effectiveness(self, website_id: str) -> dict:
        if self._collector is None:
            return {}

        trajectories = await self._collector.collect_website_trajectories(website_id)
        action_stats: dict[str, dict] = {}

        for traj in trajectories:
            for action, reward in zip(traj.actions, traj.rewards):
                at = action.get("action_type", "unknown")
                if at not in action_stats:
                    action_stats[at] = {"count": 0, "total_reward": 0.0, "avg_reward": 0.0}
                action_stats[at]["count"] += 1
                action_stats[at]["total_reward"] += reward

        for stats in action_stats.values():
            stats["avg_reward"] = stats["total_reward"] / stats["count"] if stats["count"] > 0 else 0.0

        return action_stats

    async def predict_growth(self, website_id: str, action: dict) -> dict:
        if self._collector is None:
            return {"website_id": website_id, "predicted_growth": 0.0, "confidence": "low"}

        trajectories = await self._collector.collect_website_trajectories(website_id)
        if not trajectories:
            return {"website_id": website_id, "predicted_growth": 0.0, "confidence": "low", "trajectories_count": 0}

        action_type = action.get("action_type", "unknown")
        similar: list[float] = []
        for traj in trajectories:
            for t_action, t_reward in zip(traj.actions, traj.rewards):
                if t_action.get("action_type") == action_type:
                    similar.append(t_reward)

        if similar:
            predicted = round(sum(similar) / len(similar), 4)
            confidence = "high" if len(similar) >= 5 else ("medium" if len(similar) >= 2 else "low")
        else:
            predicted = 0.0
            confidence = "low"

        logger.info("Predicted growth for %s/%s: %.4f (confidence=%s, samples=%d)", website_id, action_type, predicted, confidence, len(similar))

        return {
            "website_id": website_id,
            "predicted_growth": predicted,
            "confidence": confidence,
            "similar_actions_found": len(similar),
            "action_type": action_type,
        }
