"""
Data Collection Pipeline — Transforms DB records into RL trajectories.
Collects historical SEO results, tasks, and agent logs to build
(state, action, reward, next_state) tuples for PPO training.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from app.core.db_models import SEOResult, Task, Website, AgentLog

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryData:
    states: list[dict]
    actions: list[dict]
    rewards: list[float]
    metadata: dict | None = None


class DataCollector:
    """
    Collects and transforms historical data into RL trajectories.

    Data flow:
    1. Query SEOResults for a website (ordered by time)
    2. Query Tasks that ran between consecutive scans
    3. Compute reward from score delta between scans
    4. Build (state, action, reward, next_state) tuples as TrajectoryData
    """

    def __init__(self, db_session_factory=None) -> None:
        self._session_factory = db_session_factory

    async def get_website_scans(self, website_id: str, limit: int = 100) -> list[dict]:
        """
        Get SEO scan results for a website, ordered by time.
        Public hook used by FeedbackLoop and internally by collect_website_trajectories.
        """
        if self._session_factory is None:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(SEOResult)
                .where(SEOResult.website_id == website_id)
                .order_by(SEOResult.scanned_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "website_id": r.website_id,
                    "score": r.score,
                    "issues": r.issues or [],
                    "data": r.data or {},
                    "result_type": r.result_type,
                    "scanned_at": r.scanned_at,
                }
                for r in rows
            ]

    async def collect_website_trajectories(
        self, website_id: str, limit: int = 100
    ) -> list[TrajectoryData]:
        """
        Collect all trajectories for a single website.
        Returns list of TrajectoryData objects.

        Uses get_website_scans() internally so tests can mock scan retrieval.
        If a DB session factory is available, also fetches tasks between scans.
        """
        from app.learning.reward_calculator import RewardCalculator

        scans = await self.get_website_scans(website_id, limit)

        if len(scans) < 2:
            logger.info(
                "Website %s: %d scan(s) (<2), no trajectories",
                website_id, len(scans),
            )
            return []

        calculator = RewardCalculator()
        trajectories: list[TrajectoryData] = []

        for i in range(len(scans) - 1):
            before = scans[i]
            after = scans[i + 1]

            tasks = await self._get_tasks_between_scans(
                website_id, before, after,
            )

            b_score = before.get("score") or 0
            a_score = after.get("score") or 0
            b_issues = before.get("issues") or []
            a_issues = after.get("issues") or []

            if not tasks:
                actions = [{
                    "action_type": "scan_complete",
                    "result_type": before.get("result_type"),
                }]
            else:
                actions = [
                    {
                        "task_type": t.get("task_type") if isinstance(t, dict) else t.task_type,
                        "status": t.get("status") if isinstance(t, dict) else t.status,
                    }
                    for t in tasks
                ]

            reward = calculator.from_seo_results(b_score, a_score)
            issue_reward = calculator.from_issues(len(b_issues), len(a_issues))
            combined = calculator.combined(reward, issue_reward, weights=[0.6, 0.4])

            state = {
                "score": b_score,
                "data": before.get("data") or {},
                "issues": b_issues,
                "result_type": before.get("result_type"),
                "scanned_at": self._fmt_ts(before.get("scanned_at")),
            }
            next_state = {
                "score": a_score,
                "data": after.get("data") or {},
                "issues": a_issues,
                "result_type": after.get("result_type"),
                "scanned_at": self._fmt_ts(after.get("scanned_at")),
            }

            t = TrajectoryData(
                states=[state, next_state],
                actions=actions,
                rewards=[round(combined.value, 4)],
                metadata={
                    "website_id": website_id,
                    "before_scan": before.get("id"),
                    "after_scan": after.get("id"),
                    "score_delta": a_score - b_score,
                    "issue_delta": len(b_issues) - len(a_issues),
                    "task_count": len(tasks),
                },
            )
            trajectories.append(t)

        logger.info(
            "Website %s: built %d trajectories from %d scans",
            website_id, len(trajectories), len(scans),
        )
        return trajectories

    def _fmt_ts(self, ts) -> str | None:
        if ts is None:
            return None
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
        return str(ts)

    async def _get_tasks_between_scans(
        self, website_id: str, before: dict, after: dict,
    ) -> list:
        if self._session_factory is None:
            return []

        b_ts = before.get("scanned_at")
        a_ts = after.get("scanned_at")
        if b_ts is None or a_ts is None:
            return []
        if isinstance(b_ts, str):
            b_ts = datetime.fromisoformat(b_ts)
        if isinstance(a_ts, str):
            a_ts = datetime.fromisoformat(a_ts)

        async with self._session_factory() as session:
            stmt = (
                select(Task)
                .where(Task.website_id == website_id)
                .where(Task.created_at >= b_ts)
                .where(Task.created_at <= a_ts)
                .order_by(Task.created_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _get_all_website_ids(self, max_websites: int) -> list:
        if self._session_factory is None:
            return []

        async with self._session_factory() as session:
            stmt = select(Website.id).limit(max_websites)
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def collect_all_trajectories(
        self, max_websites: int = 50, max_per_website: int = 20
    ) -> list[TrajectoryData]:
        """
        Collect trajectories across all websites.
        Returns combined list of TrajectoryData from all sites.
        """
        website_ids = await self._get_all_website_ids(max_websites)
        if not website_ids:
            return []

        all_trajectories: list[TrajectoryData] = []
        for wid in website_ids:
            trajs = await self.collect_website_trajectories(wid, limit=max_per_website)
            all_trajectories.extend(trajs)

        logger.info(
            "Collected %d total trajectories from %d websites",
            len(all_trajectories), len(website_ids),
        )
        return all_trajectories

    async def collect_agent_trajectories(
        self, agent_type: str, limit: int = 200
    ) -> list[TrajectoryData]:
        """
        Collect trajectories from AgentLogs for a specific agent type.
        """
        logs = await self._get_agent_logs(agent_type, limit)

        if len(logs) < 2:
            logger.info("Agent %s: %d log(s) (<2), no trajectories", agent_type, len(logs))
            return []

        from app.learning.reward_calculator import RewardCalculator
        calculator = RewardCalculator()
        trajectories: list[TrajectoryData] = []

        for i in range(len(logs) - 1):
            before = logs[i]
            after = logs[i + 1]

            b_input = before.input_data if hasattr(before, "input_data") else before.get("input_data", {})
            a_input = after.input_data if hasattr(after, "input_data") else after.get("input_data", {})
            b_status = before.status if hasattr(before, "status") else before.get("status", "")
            b_agent = before.agent_type if hasattr(before, "agent_type") else before.get("agent_type", "")
            b_exec = before.execution_time_ms if hasattr(before, "execution_time_ms") else before.get("execution_time_ms")
            b_id = before.id if hasattr(before, "id") else before.get("id", "")
            a_id = after.id if hasattr(after, "id") else after.get("id", "")

            reward = calculator.from_task_result(b_status)

            trajectories.append(TrajectoryData(
                states=[b_input, a_input],
                actions=[{
                    "agent_type": b_agent,
                    "status": b_status,
                    "execution_time_ms": b_exec,
                }],
                rewards=[round(reward.value, 4)],
                metadata={
                    "agent_type": agent_type,
                    "before_log": b_id,
                    "after_log": a_id,
                },
            ))

        logger.info(
            "Agent %s: built %d trajectories from %d logs",
            agent_type, len(trajectories), len(logs),
        )
        return trajectories

    async def _get_agent_logs(self, agent_type: str, limit: int) -> list:
        if self._session_factory is None:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(AgentLog)
                .where(AgentLog.agent_type == agent_type)
                .order_by(AgentLog.created_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_training_batch(
        self, batch_size: int = 32
    ) -> list[TrajectoryData]:
        """
        Get a random batch of trajectories for training.
        Samples from all collected trajectories across all websites.
        """
        all_trajs = await self.collect_all_trajectories(
            max_websites=50, max_per_website=20,
        )
        if not all_trajs:
            return []
        actual = min(batch_size, len(all_trajs))
        sampled = random.sample(all_trajs, actual)
        logger.info("Sampled %d trajectories for training batch", len(sampled))
        return sampled

    async def get_website_growth_metrics(self, website_id: str) -> dict:
        """
        Get growth trajectory for a website.
        Returns score progression, issue reduction rate, action efficiency.
        """
        trajectories = await self.collect_website_trajectories(website_id)
        if not trajectories:
            return {
                "website_id": website_id,
                "total_trajectories": 0,
                "score_trend": "unknown",
                "avg_reward": 0.0,
                "total_actions": 0,
            }

        all_rewards = [r for t in trajectories for r in t.rewards]
        avg_reward = sum(all_rewards) / max(len(all_rewards), 1) if all_rewards else 0.0

        score_deltas = [
            t.metadata.get("score_delta", 0)
            for t in trajectories
            if t.metadata
        ]
        if len(score_deltas) >= 3:
            recent = score_deltas[-3:]
            if all(d > 0 for d in recent):
                trend = "improving"
            elif all(d < 0 for d in recent):
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        total_actions = sum(len(t.actions) for t in trajectories)

        return {
            "website_id": website_id,
            "total_trajectories": len(trajectories),
            "score_trend": trend,
            "avg_reward": round(avg_reward, 4),
            "total_actions": total_actions,
        }

    async def get_score_progression(self, website_id: str) -> list[float]:
        trajectories = await self.collect_website_trajectories(website_id)
        if not trajectories:
            return []
        scores = []
        for t in trajectories:
            if t.states:
                scores.append(t.states[0].get("score", 0))
        if trajectories and trajectories[-1].states:
            scores.append(trajectories[-1].states[-1].get("score", 0))
        return scores
