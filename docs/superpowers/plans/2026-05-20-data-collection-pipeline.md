# Data Collection Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform historical DB records (SEOResults, Tasks, AgentLogs) into (state, action, reward, next_state) RL trajectories for PPO training.

**Architecture:** Two new service classes — `DataCollector` queries DB records and builds trajectory tuples; `RewardCalculator` computes reward signals from score deltas, issue reductions, and task outcomes. Both are async, use SQLAlchemy 2.0 style queries, and log collection stats.

**Tech Stack:** Python, SQLAlchemy 2.0, asyncio, pytest-asyncio

---

### Task 1: Create `backend/app/services/learning/__init__.py`

**Files:**
- Create: `backend/app/services/learning/__init__.py`

- [ ] **Write the file**

```python
from .reward_calculator import RewardCalculator
from .data_collector import DataCollector

__all__ = [
    "RewardCalculator",
    "DataCollector",
]
```

---

### Task 2: Create `backend/app/services/learning/reward_calculator.py`

**Files:**
- Create: `backend/app/services/learning/reward_calculator.py`

- [ ] **Write the file**

```python
"""
Reward Calculator — Computes reward signals from data deltas.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RewardCalculator:
    """
    Computes reward signals from score deltas, issue reductions,
    and other measurable improvements.

    Reward sources:
    - SEO score delta: (new_score - old_score) / 100 -> [-1, 1]
    - Issue reduction: (old_count - new_count) / max(old_count, 1) -> [0, 1]
    - Task completion: success(1.0), failure(-0.5), timeout(-0.3)
    - CWV improvement: threshold pass rate delta
    - Ranking improvement: position improvement normalized
    """

    @staticmethod
    def from_seo_results(before: dict, after: dict) -> float:
        score_before = before.get("score") or 0
        score_after = after.get("score") or 0
        reward = max(-1.0, min(1.0, (score_after - score_before) / 100.0))
        logger.debug("from_seo_results: %d -> %d, reward=%.4f", score_before, score_after, reward)
        return reward

    @staticmethod
    def from_task_result(task: dict) -> float:
        status = task.get("status", "")
        if status == "completed":
            result = task.get("result_data") or {}
            score = result.get("score")
            if score is not None:
                return max(0.0, min(1.0, score / 100.0))
            return 1.0
        if status == "failed":
            return -0.5
        return -0.3

    @staticmethod
    def from_issues(before: list, after: list) -> float:
        if not isinstance(before, list) or not isinstance(after, list):
            return 0.0
        old_count = len(before)
        new_count = len(after)
        if old_count == 0:
            return 0.0 if new_count == 0 else -min(1.0, new_count / 10.0)
        reduction = (old_count - new_count) / max(old_count, 1)
        return max(-1.0, min(1.0, reduction))

    @staticmethod
    def combined(
        before_score: int | float | None,
        after_score: int | float | None,
        before_issues: list | None,
        after_issues: list | None,
        task_success: bool = False,
    ) -> float:
        b_score = before_score or 0
        a_score = after_score or 0
        score_reward = max(-1.0, min(1.0, (a_score - b_score) / 100.0))

        b_issues = before_issues or []
        a_issues = after_issues or []
        n_before = len(b_issues)
        n_after = len(a_issues)
        issue_reward = 0.0
        if n_before > 0:
            issue_reward = min(1.0, (n_before - n_after) / max(n_before, 1))

        task_bonus = 1.0 if task_success else 0.0

        combined = 0.5 * score_reward + 0.3 * issue_reward + 0.2 * task_bonus
        return max(-1.0, min(1.0, combined))
```

---

### Task 3: Create `backend/app/services/learning/data_collector.py`

**Files:**
- Create: `backend/app/services/learning/data_collector.py`

- [ ] **Write the file**

```python
"""
Data Collection Pipeline — Transforms DB records into RL trajectories.
Collects historical SEO results, tasks, and agent logs to build
(state, action, reward, next_state) tuples for PPO training.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_models import SEOResult, Task, AgentLog, Website
from app.services.learning.reward_calculator import RewardCalculator

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects and transforms historical data into RL trajectories.

    Data flow:
    1. Query SEOResults for a website (ordered by time)
    2. Query Tasks that ran between consecutive scans
    3. Compute reward from score delta between scans
    4. Build (state, action, reward, next_state) tuples
    """

    def __init__(self, db_session_factory=None) -> None:
        self._session_factory = db_session_factory
        self._reward_calc = RewardCalculator()

    async def _get_session(self) -> AsyncIterator[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("DataCollector requires a db_session_factory")
        async with self._session_factory() as session:
            yield session

    # ------------------------------------------------------------------
    # Website-level trajectory collection
    # ------------------------------------------------------------------

    async def collect_website_trajectories(
        self, website_id: str, limit: int = 100
    ) -> list[dict]:
        """
        Collect all trajectories for a single website.
        Returns list of {state, action, reward, next_state, done} dicts.
        """
        async with self._session_factory() as session:
            stmt = (
                select(SEOResult)
                .where(SEOResult.website_id == website_id)
                .order_by(SEOResult.scanned_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            seo_results = result.scalars().all()

        if len(seo_results) < 2:
            logger.info("Website %s: %d results (<2), skipping", website_id, len(seo_results))
            return []

        trajectories: list[dict] = []
        for i in range(len(seo_results) - 1):
            before = seo_results[i]
            after = seo_results[i + 1]

            tasks = await self._get_tasks_between(session, website_id, before.scanned_at, after.scanned_at)

            if not tasks:
                continue

            state = {
                "score": before.score,
                "data": before.data or {},
                "issues": before.issues or [],
                "result_type": before.result_type,
                "scanned_at": before.scanned_at.isoformat() if before.scanned_at else None,
            }
            next_state = {
                "score": after.score,
                "data": after.data or {},
                "issues": after.issues or [],
                "result_type": after.result_type,
                "scanned_at": after.scanned_at.isoformat() if after.scanned_at else None,
            }

            action = {
                "tasks": [
                    {
                        "task_type": t.task_type,
                        "status": t.status,
                        "input_data": t.input_data or {},
                        "result_data": t.result_data or {},
                    }
                    for t in tasks
                ],
                "count": len(tasks),
            }

            reward = self._reward_calc.from_seo_results(
                {"score": before.score or 0},
                {"score": after.score or 0},
            )

            done = i == len(seo_results) - 2

            trajectories.append({
                "state": state,
                "action": action,
                "reward": round(reward, 4),
                "next_state": next_state,
                "done": done,
            })

        logger.info(
            "Website %s: built %d trajectories from %d results",
            website_id, len(trajectories), len(seo_results),
        )
        return trajectories

    async def _get_tasks_between(
        self,
        session: AsyncSession,
        website_id: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[Task]:
        if start is None or end is None:
            return []
        stmt = (
            select(Task)
            .where(Task.website_id == website_id)
            .where(Task.created_at >= start)
            .where(Task.created_at <= end)
            .order_by(Task.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Cross-website collection
    # ------------------------------------------------------------------

    async def collect_all_trajectories(
        self, max_websites: int = 50, max_per_website: int = 20
    ) -> list[dict]:
        """
        Collect trajectories across all websites.
        Returns combined list of trajectories from all sites.
        """
        async with self._session_factory() as session:
            stmt = select(Website.id).limit(max_websites)
            result = await session.execute(stmt)
            website_ids = [row[0] for row in result.all()]

        all_trajectories: list[dict] = []
        for wid in website_ids:
            trajs = await self.collect_website_trajectories(wid, limit=max_per_website)
            all_trajectories.extend(trajs)

        logger.info(
            "Collected %d total trajectories from %d websites",
            len(all_trajectories), len(website_ids),
        )
        return all_trajectories

    # ------------------------------------------------------------------
    # Agent-level trajectory collection
    # ------------------------------------------------------------------

    async def collect_agent_trajectories(
        self, agent_type: str, limit: int = 200
    ) -> list[dict]:
        """
        Collect trajectories from AgentLogs for a specific agent type.
        """
        async with self._session_factory() as session:
            stmt = (
                select(AgentLog)
                .where(AgentLog.agent_type == agent_type)
                .order_by(AgentLog.created_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()

        if len(logs) < 2:
            logger.info("Agent %s: %d logs (<2), skipping", agent_type, len(logs))
            return []

        trajectories: list[dict] = []
        for i in range(len(logs) - 1):
            before = logs[i]
            after = logs[i + 1]

            reward = self._reward_calc.from_task_result({
                "status": before.status,
                "result_data": before.output_data or {},
            })

            done = i == len(logs) - 2

            trajectories.append({
                "state": before.input_data or {},
                "action": {
                    "agent_type": before.agent_type,
                    "status": before.status,
                    "execution_time_ms": before.execution_time_ms,
                },
                "reward": round(reward, 4),
                "next_state": after.input_data or {},
                "done": done,
            })

        logger.info(
            "Agent %s: built %d trajectories from %d logs",
            agent_type, len(trajectories), len(logs),
        )
        return trajectories

    # ------------------------------------------------------------------
    # Training batch sampling
    # ------------------------------------------------------------------

    async def get_training_batch(
        self, batch_size: int = 32
    ) -> list[dict]:
        """
        Get a random batch of trajectories for training.
        Samples from all collected trajectories across all websites.
        """
        all_trajs = await self.collect_all_trajectories(max_websites=50, max_per_website=20)
        if not all_trajs:
            return []
        actual = min(batch_size, len(all_trajs))
        sampled = random.sample(all_trajs, actual)
        logger.info("Sampled %d trajectories for training batch", len(sampled))
        return sampled

    # ------------------------------------------------------------------
    # Growth metrics
    # ------------------------------------------------------------------

    async def get_website_growth_metrics(self, website_id: str) -> dict:
        """
        Get growth trajectory for a website.
        Returns score progression, issue reduction rate, action efficiency.
        """
        async with self._session_factory() as session:
            stmt = (
                select(SEOResult)
                .where(SEOResult.website_id == website_id)
                .order_by(SEOResult.scanned_at.asc())
                .limit(100)
            )
            result = await session.execute(stmt)
            seo_results = result.scalars().all()

        if not seo_results:
            return {
                "website_id": website_id,
                "trajectory_count": 0,
                "score_progression": [],
                "issue_reduction_rate": 0.0,
                "action_efficiency": 0.0,
                "avg_reward": 0.0,
            }

        scores = [r.score or 0 for r in seo_results]
        issues = [len(r.issues or []) for r in seo_results]

        score_deltas: list[int] = []
        issue_deltas: list[int] = []
        for i in range(1, len(scores)):
            score_deltas.append(scores[i] - scores[i - 1])
            issue_deltas.append(issues[i - 1] - issues[i])

        avg_score_delta = sum(score_deltas) / max(len(score_deltas), 1) if score_deltas else 0
        total_issue_reduction = sum(max(d, 0) for d in issue_deltas)
        total_initial_issues = max(issues[0], 1)
        issue_reduction_rate = min(1.0, total_issue_reduction / total_initial_issues)

        rewards = [max(-1.0, min(1.0, d / 100.0)) for d in score_deltas]
        avg_reward = sum(rewards) / max(len(rewards), 1) if rewards else 0.0

        return {
            "website_id": website_id,
            "trajectory_count": len(seo_results),
            "score_progression": scores,
            "issue_reduction_rate": round(issue_reduction_rate, 4),
            "action_efficiency": round(avg_score_delta / 100.0, 4),
            "avg_reward": round(avg_reward, 4),
        }
```

---

### Task 4: Create `backend/tests/test_learning/__init__.py`

**Files:**
- Create: `backend/tests/test_learning/__init__.py`

- [ ] **Write the file**

```python
```

---

### Task 5: Create `backend/tests/test_learning/test_reward_calculator.py`

**Files:**
- Create: `backend/tests/test_learning/test_reward_calculator.py`

- [ ] **Write the file**

```python
import pytest
from app.services.learning.reward_calculator import RewardCalculator


class TestRewardCalculator:
    def test_from_seo_results_positive_delta(self):
        before = {"score": 30}
        after = {"score": 80}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == pytest.approx(0.5)

    def test_from_seo_results_negative_delta(self):
        before = {"score": 80}
        after = {"score": 30}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == pytest.approx(-0.5)

    def test_from_seo_results_no_change(self):
        before = {"score": 50}
        after = {"score": 50}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == pytest.approx(0.0)

    def test_from_seo_results_clamps_positive(self):
        before = {"score": 0}
        after = {"score": 200}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == 1.0

    def test_from_seo_results_clamps_negative(self):
        before = {"score": 100}
        after = {"score": -100}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == -1.0

    def test_from_seo_results_missing_score(self):
        before = {}
        after = {}
        reward = RewardCalculator.from_seo_results(before, after)
        assert reward == 0.0

    def test_from_task_result_completed(self):
        task = {"status": "completed", "result_data": {"score": 80}}
        reward = RewardCalculator.from_task_result(task)
        assert reward == 0.8

    def test_from_task_result_completed_no_score(self):
        task = {"status": "completed"}
        reward = RewardCalculator.from_task_result(task)
        assert reward == 1.0

    def test_from_task_result_failed(self):
        task = {"status": "failed"}
        reward = RewardCalculator.from_task_result(task)
        assert reward == -0.5

    def test_from_task_result_timeout(self):
        task = {"status": "timeout"}
        reward = RewardCalculator.from_task_result(task)
        assert reward == -0.3

    def test_from_issues_reduction(self):
        before = [{"type": "error"}, {"type": "warning"}]
        after = [{"type": "warning"}]
        reward = RewardCalculator.from_issues(before, after)
        assert reward == pytest.approx(0.5)

    def test_from_issues_increase(self):
        before = [{"type": "error"}]
        after = [{"type": "error"}, {"type": "warning"}, {"type": "info"}]
        reward = RewardCalculator.from_issues(before, after)
        assert reward <= 0.0

    def test_from_issues_no_before_issues(self):
        reward = RewardCalculator.from_issues([], [{"type": "error"}])
        assert reward < 0.0

    def test_from_issues_no_issues(self):
        reward = RewardCalculator.from_issues([], [])
        assert reward == 0.0

    def test_from_issues_non_list(self):
        reward = RewardCalculator.from_issues("bad", "data")
        assert reward == 0.0

    def test_combined_defaults(self):
        reward = RewardCalculator.combined(50, 60, [], [], False)
        assert isinstance(reward, float)

    def test_combined_with_success(self):
        reward = RewardCalculator.combined(50, 80, [], [], True)
        assert reward > 0

    def test_combined_missing_values(self):
        reward = RewardCalculator.combined(None, None, None, None, False)
        assert reward == 0.0
```

---

### Task 6: Create `backend/tests/test_learning/test_data_collector.py`

**Files:**
- Create: `backend/tests/test_learning/test_data_collector.py`

- [ ] **Write the file**

```python
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.learning.data_collector import DataCollector
from app.core.db_models import SEOResult, Task, AgentLog, Website


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_factory(mock_session):
    factory = MagicMock()
    factory.return_value = mock_session
    return factory


@pytest.fixture
def collector(mock_factory):
    return DataCollector(db_session_factory=mock_factory)


def _make_seo_result(id: str, score: int, scanned_at: datetime, issues: list | None = None):
    return SEOResult(
        id=id,
        website_id="w1",
        result_type="technical",
        score=score,
        data={"key": f"value_{score}"},
        issues=issues or [],
        scanned_at=scanned_at,
    )


def _make_task(id: str, task_type: str, status: str, created_at: datetime):
    return Task(
        id=id,
        website_id="w1",
        task_type=task_type,
        status=status,
        input_data={"action": task_type},
        result_data={"score": 85},
        created_at=created_at,
    )


def _make_agent_log(id: str, agent_type: str, status: str, input_data: dict, output_data: dict, created_at: datetime):
    return AgentLog(
        id=id,
        agent_type=agent_type,
        status=status,
        input_data=input_data,
        output_data=output_data,
        execution_time_ms=100,
        created_at=created_at,
    )


class TestDataCollector:
    @pytest.mark.asyncio
    async def test_collect_website_trajectories_empty(self, collector, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await collector.collect_website_trajectories("w1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_single_result(self, collector, mock_session):
        now = datetime.utcnow()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_seo_result("r1", 50, now),
        ]
        mock_session.execute.return_value = mock_result

        result = await collector.collect_website_trajectories("w1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_with_tasks(self, collector, mock_session):
        now = datetime.utcnow()
        later = now + timedelta(hours=1)

        seo_results = [
            _make_seor_result("r1", 50, now),
            _make_seo_result("r2", 80, later),
        ]

        seo_mock = MagicMock()
        seo_mock.scalars.return_value.all.return_value = seo_results

        task_mock = MagicMock()
        task_mock.scalars.return_value.all.return_value = [
            _make_task("t1", "fix_meta", "completed", now + timedelta(minutes=30)),
        ]

        mock_session.execute = AsyncMock(side_effect=[seo_mock, task_mock])

        result = await collector.collect_website_trajectories("w1")
        assert len(result) == 1
        traj = result[0]
        assert traj["state"]["score"] == 50
        assert traj["next_state"]["score"] == 80
        assert traj["reward"] == 0.3
        assert traj["action"]["count"] == 1
        assert traj["done"] is True

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_skips_no_tasks(self, collector, mock_session):
        now = datetime.utcnow()
        later = now + timedelta(hours=1)

        seo_mock = MagicMock()
        seo_mock.scalars.return_value.all.return_value = [
            _make_seo_result("r1", 50, now),
            _make_seo_result("r2", 80, later),
        ]

        task_mock = MagicMock()
        task_mock.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[seo_mock, task_mock])

        result = await collector.collect_website_trajectories("w1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_agent_trajectories(self, collector, mock_session):
        now = datetime.utcnow()
        later = now + timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_agent_log(
                "l1", "technical_auditor", "completed",
                {"url": "https://example.com"},
                {"score": 70, "issues": []},
                now,
            ),
            _make_agent_log(
                "l2", "technical_auditor", "completed",
                {"url": "https://example.com/page2"},
                {"score": 85, "issues": []},
                later,
            ),
        ]
        mock_session.execute.return_value = mock_result

        result = await collector.collect_agent_trajectories("technical_auditor")
        assert len(result) == 1
        traj = result[0]
        assert traj["state"]["url"] == "https://example.com"
        assert traj["next_state"]["url"] == "https://example.com/page2"
        assert traj["action"]["agent_type"] == "technical_auditor"
        assert traj["done"] is True

    @pytest.mark.asyncio
    async def test_collect_agent_trajectories_empty(self, collector, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await collector.collect_agent_trajectories("technical_auditor")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics_empty(self, collector, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        metrics = await collector.get_website_growth_metrics("w1")
        assert metrics["trajectory_count"] == 0
        assert metrics["avg_reward"] == 0.0

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics_with_data(self, collector, mock_session):
        now = datetime.utcnow()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_seo_result("r1", 40, now, issues=[{"type": "error"}] * 5),
            _make_seo_result("r2", 60, now + timedelta(hours=1), issues=[{"type": "error"}] * 3),
            _make_seo_result("r3", 80, now + timedelta(hours=2), issues=[{"type": "error"}] * 1),
        ]
        mock_session.execute.return_value = mock_result

        metrics = await collector.get_website_growth_metrics("w1")
        assert metrics["trajectory_count"] == 3
        assert len(metrics["score_progression"]) == 3
        assert metrics["score_progression"] == [40, 60, 80]
        assert metrics["issue_reduction_rate"] == pytest.approx(0.8)
        assert metrics["avg_reward"] > 0

    @pytest.mark.asyncio
    async def test_collect_all_trajectories(self, collector, mock_session):
        now = datetime.utcnow()

        website_mock = MagicMock()
        website_mock.all.return_value = [("w1",), ("w2",)]

        seo_mock_1 = MagicMock()
        seo_mock_1.scalars.return_value.all.return_value = [
            _make_seo_result("r1", 50, now),
            _make_seo_result("r2", 80, now + timedelta(hours=1)),
        ]

        task_mock_1 = MagicMock()
        task_mock_1.scalars.return_value.all.return_value = [
            _make_task("t1", "fix_title", "completed", now + timedelta(minutes=30)),
        ]

        seo_mock_2 = MagicMock()
        seo_mock_2.scalars.return_value.all.return_value = [
            _make_seo_result("r3", 60, now),
        ]

        mock_session.execute = AsyncMock(side_effect=[
            website_mock, seo_mock_1, task_mock_1, seo_mock_2,
        ])

        result = await collector.collect_all_trajectories(max_websites=2, max_per_website=20)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_training_batch(self, collector, mock_session):
        now = datetime.utcnow()

        website_mock = MagicMock()
        website_mock.all.return_value = [("w1",)]

        seo_mock = MagicMock()
        seo_mock.scalars.return_value.all.return_value = [
            _make_seo_result("r1", 50, now),
            _make_seo_result("r2", 80, now + timedelta(hours=1)),
        ]

        task_mock = MagicMock()
        task_mock.scalars.return_value.all.return_value = [
            _make_task("t1", "fix_meta", "completed", now + timedelta(minutes=30)),
        ]

        mock_session.execute = AsyncMock(side_effect=[
            website_mock, seo_mock, task_mock,
        ])

        batch = await collector.get_training_batch(batch_size=5)
        assert len(batch) == 1
        assert batch[0]["state"]["score"] == 50
        assert batch[0]["next_state"]["score"] == 80

    @pytest.mark.asyncio
    async def test_no_factory_raises(self):
        collector = DataCollector()
        with pytest.raises(RuntimeError, match="requires a db_session_factory"):
            async for _ in collector._get_session():
                pass


# NOTE: Fix test helper function name typo
def _make_seor_result(id: str, score: int, scanned_at: datetime, issues: list | None = None):
    return _make_seo_result(id, score, scanned_at, issues)
```
