"""
Reward Calculator — Computes reward signals from data deltas.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Reward:
    value: float
    components: dict = field(default_factory=dict)
    metadata: dict | None = None


class RewardCalculator:
    """
    Computes reward signals from score deltas, issue reductions,
    and other measurable improvements. All methods return Reward objects
    with the scalar value, breakdown components, and optional metadata.
    """

    @staticmethod
    def from_seo_results(previous_score: int | None, current_score: int | None) -> Reward:
        if previous_score is None or current_score is None:
            return Reward(value=0.0, components={"score_delta": 0.0})

        delta = current_score - previous_score
        value = max(-1.0, min(1.0, delta / 100.0))
        return Reward(
            value=value,
            components={"score_delta": delta},
            metadata={"previous_score": previous_score, "current_score": current_score},
        )

    @staticmethod
    def from_task_result(status: str, task_type: str | None = None) -> Reward:
        if status in ("completed", "success"):
            return Reward(
                value=1.0,
                components={"task_status": 1.0},
                metadata={"task_status": status, "task_type": task_type},
            )
        if status in ("failed", "error"):
            return Reward(
                value=-0.5,
                components={"task_status": -0.5},
                metadata={"task_status": status, "task_type": task_type},
            )
        if status == "timeout":
            return Reward(
                value=-0.5,
                components={"task_status": -0.5},
                metadata={"task_status": status, "task_type": task_type},
            )
        return Reward(
            value=0.0,
            components={"task_status": 0.0},
            metadata={"task_status": status, "task_type": task_type},
        )

    @staticmethod
    def from_issues(previous_count: int | None, current_count: int | None) -> Reward:
        if previous_count is None or current_count is None:
            return Reward(value=0.0, components={"issue_delta": 0.0})

        delta = previous_count - current_count
        if previous_count == 0:
            value = 0.0 if current_count == 0 else -min(1.0, current_count / 10.0)
        else:
            value = max(-1.0, min(1.0, delta / max(previous_count, 1)))

        return Reward(
            value=value,
            components={"issue_delta": delta},
            metadata={"previous_count": previous_count, "current_count": current_count},
        )

    @staticmethod
    def combined(*rewards: Reward, weights: list[float] | None = None) -> Reward:
        if not rewards:
            return Reward(value=0.0, components={})

        if weights is None:
            weights = [1.0 / len(rewards)] * len(rewards)

        merged_components: dict[str, float] = {}
        total_weight = sum(weights[:len(rewards)])
        if total_weight == 0.0:
            return Reward(value=0.0, components={})

        weighted_values = sum(
            r.value * w for r, w in zip(rewards, weights[:len(rewards)])
        )
        value = max(-1.0, min(1.0, weighted_values / total_weight))

        for r in rewards:
            merged_components.update(r.components or {})

        return Reward(value=value, components=merged_components)
