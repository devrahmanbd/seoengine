import asyncio
import time
from typing import Any


class MetricsCollector:
    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "training": {"count": 0, "total_reward": 0.0, "avg_reward": 0.0},
            "executions": {"count": 0, "successes": 0, "failures": 0, "total_reward": 0.0, "avg_duration_ms": 0.0},
            "api_calls": {"count": 0, "errors": 0, "total_duration_ms": 0.0},
            "started_at": time.time(),
        }
        self._lock = asyncio.Lock()

    async def record_training(self, stats: dict) -> None:
        async with self._lock:
            self.metrics["training"]["count"] += 1
            reward = stats.get("avg_reward", 0.0)
            self.metrics["training"]["total_reward"] += reward
            total = self.metrics["training"]["count"]
            self.metrics["training"]["avg_reward"] = (
                self.metrics["training"]["total_reward"] / total if total else 0.0
            )

    async def record_execution(self, action_type: str, success: bool, reward: float, duration_ms: int) -> None:
        async with self._lock:
            self.metrics["executions"]["count"] += 1
            if success:
                self.metrics["executions"]["successes"] += 1
            else:
                self.metrics["executions"]["failures"] += 1
            self.metrics["executions"]["total_reward"] += reward
            total = self.metrics["executions"]["count"]
            self.metrics["executions"]["avg_duration_ms"] = (
                (self.metrics["executions"]["avg_duration_ms"] * (total - 1) + duration_ms) / total
            )

    async def get_all_metrics(self) -> dict:
        async with self._lock:
            result = dict(self.metrics)
            result["uptime_seconds"] = time.time() - self.metrics["started_at"]
            return result

    async def get_health_status(self) -> dict:
        async with self._lock:
            return {
                "status": "ok",
                "uptime_seconds": time.time() - self.metrics["started_at"],
                "training_runs": self.metrics["training"]["count"],
                "executions": self.metrics["executions"]["count"],
                "execution_success_rate": (
                    self.metrics["executions"]["successes"] / self.metrics["executions"]["count"]
                    if self.metrics["executions"]["count"] > 0
                    else 1.0
                ),
            }
