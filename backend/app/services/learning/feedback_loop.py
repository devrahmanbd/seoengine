import asyncio
from datetime import datetime, timezone
from typing import Any

from app.services.learning.reward_calculator import RewardCalculator
from app.services.learning.data_collector import TrajectoryData


class FeedbackLoop:
    def __init__(self, collector: Any = None, calculator: RewardCalculator | None = None, pipeline: Any = None):
        self._collector = collector
        self._calculator = calculator or RewardCalculator()
        self._pipeline = pipeline
        self._lock = asyncio.Lock()

    async def on_scan_complete(self, website_id: str, scan_result: dict) -> dict:
        previous_scans = []
        if self._collector is not None:
            previous_scans = await self._collector.get_website_scans(website_id)

        if len(previous_scans) < 2:
            return {"status": "insufficient_data", "website_id": website_id, "trajectory_created": False}

        prev = previous_scans[-2]
        curr = previous_scans[-1]

        score_reward = self._calculator.from_seo_results(
            prev.get("score") or 0,
            curr.get("score") or 0,
        )
        issues_reward = self._calculator.from_issues(
            len(prev.get("issues") or []),
            len(curr.get("issues") or []),
        )
        combined = self._calculator.combined(score_reward, issues_reward)

        trajectory = TrajectoryData(
            states=[{"score": prev.get("score"), "issues": len(prev.get("issues") or [])}],
            actions=[{"action_type": "scan_complete"}],
            rewards=[combined.value],
            metadata={"website_id": website_id, "source": "scan_complete", "prev_scan_id": prev.get("id")},
        )

        result = {
            "status": "success",
            "website_id": website_id,
            "trajectory_created": True,
            "reward": combined.value,
        }

        async with self._lock:
            if self._pipeline is not None:
                scored = self._pipeline._transform_to_scored_data([trajectory])
                self._pipeline.add_to_buffer(scored)
                result["scored_data_added"] = len(scored)

        return result

    async def on_task_complete(self, task_id: str, task_result: dict) -> dict:
        website_id = task_result.get("website_id")
        if not website_id:
            return {"status": "error", "error": "no_website_id", "task_id": task_id}

        task_status = task_result.get("status", "unknown")
        task_type = task_result.get("task_type", "unknown")

        task_reward = self._calculator.from_task_result(task_status, task_type)

        trajectory = TrajectoryData(
            states=[{"website_id": website_id, "task_id": task_id}],
            actions=[{"action_type": task_type, "task_id": task_id}],
            rewards=[task_reward.value],
            metadata={"source": "task_complete", "task_id": task_id},
        )

        result = {
            "status": "success",
            "task_id": task_id,
            "website_id": website_id,
            "reward": task_reward.value,
            "trajectory_created": True,
        }

        async with self._lock:
            if self._pipeline is not None:
                scored = self._pipeline._transform_to_scored_data([trajectory])
                self._pipeline.add_to_buffer(scored)
                result["scored_data_added"] = len(scored)

        return result

    async def on_website_update(self, website_id: str) -> dict:
        if self._collector is None:
            return {"status": "no_collector", "website_id": website_id}

        metrics = await self._collector.get_website_growth_metrics(website_id)
        trajectory = TrajectoryData(
            states=[{"website_id": website_id, "metrics": metrics}],
            actions=[{"action_type": "growth_signal"}],
            rewards=[metrics.get("avg_reward", 0.0)],
            metadata={"source": "website_update", "website_id": website_id, "metrics": metrics},
        )

        result = {
            "status": "success",
            "website_id": website_id,
            "trajectory_created": True,
            "metrics": metrics,
        }

        async with self._lock:
            if self._pipeline is not None:
                scored = self._pipeline._transform_to_scored_data([trajectory])
                self._pipeline._buffer.extend(scored)
                result["scored_data_added"] = len(scored)

        return result
