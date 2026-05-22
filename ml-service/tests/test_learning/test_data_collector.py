import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.learning.data_collector import DataCollector, TrajectoryData


def make_scan(id, score, issues_count=0, scanned_at=None):
    return {
        "id": id,
        "website_id": "site-1",
        "score": score,
        "issues": [{"i": n} for n in range(issues_count)] if issues_count > 0 else [],
        "data": {},
        "result_type": "technical",
        "scanned_at": scanned_at or datetime.now(timezone.utc),
    }


def make_task(task_type, status):
    return {"task_type": task_type, "status": status}


class TestTrajectoryData:
    def test_defaults(self):
        td = TrajectoryData(states=[], actions=[], rewards=[])
        assert td.metadata is None

    def test_all_fields(self):
        td = TrajectoryData(
            states=[{"s": 1}],
            actions=[{"a": 1}],
            rewards=[0.5],
            metadata={"key": "val"},
        )
        assert td.metadata == {"key": "val"}
        assert td.states == [{"s": 1}]


class TestDataCollectorNoDB:
    @pytest.mark.asyncio
    async def test_collect_website_trajectories(self):
        c = DataCollector()
        result = await c.collect_website_trajectories("site-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_all_trajectories(self):
        c = DataCollector()
        result = await c.collect_all_trajectories()
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_agent_trajectories(self):
        c = DataCollector()
        result = await c.collect_agent_trajectories("technical_auditor")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_website_scans(self):
        c = DataCollector()
        result = await c.get_website_scans("site-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_website_not_found(self):
        c = DataCollector()
        metrics = await c.get_website_growth_metrics("nonexistent")
        assert metrics["total_trajectories"] == 0
        assert metrics["score_trend"] == "unknown"


@pytest.fixture
def collector():
    return DataCollector()


class TestDataCollector:
    @pytest.mark.asyncio
    async def test_collect_website_trajectories_no_scans(self):
        c = DataCollector()
        c.get_website_scans = AsyncMock(return_value=[])
        result = await c.collect_website_trajectories("site-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_single_scan(self):
        c = DataCollector()
        c.get_website_scans = AsyncMock(return_value=[make_scan("s1", 50)])
        result = await c.collect_website_trajectories("site-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_with_tasks(self):
        c = DataCollector()
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 2, 1, tzinfo=timezone.utc)

        c.get_website_scans = AsyncMock(return_value=[
            make_scan("s1", 50, issues_count=3, scanned_at=t1),
            make_scan("s2", 75, issues_count=0, scanned_at=t2),
        ])
        c._get_tasks_between_scans = AsyncMock(return_value=[
            make_task("fix_title", "completed"),
        ])

        result = await c.collect_website_trajectories("site-1")
        assert len(result) == 1
        assert len(result[0].states) == 2
        assert len(result[0].actions) == 1
        assert result[0].rewards[0] > 0
        assert result[0].actions[0]["task_type"] == "fix_title"

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_score_decrease(self):
        c = DataCollector()
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 2, 1, tzinfo=timezone.utc)

        c.get_website_scans = AsyncMock(return_value=[
            make_scan("s1", 80, scanned_at=t1),
            make_scan("s2", 60, scanned_at=t2),
        ])
        c._get_tasks_between_scans = AsyncMock(return_value=[
            make_task("fix_title", "completed"),
        ])

        result = await c.collect_website_trajectories("site-1")
        assert len(result) == 1
        assert result[0].rewards[0] < 0

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_no_tasks_between_scans(self):
        c = DataCollector()
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 2, 1, tzinfo=timezone.utc)

        c.get_website_scans = AsyncMock(return_value=[
            make_scan("s1", 50, scanned_at=t1),
            make_scan("s2", 75, scanned_at=t2),
        ])
        c._get_tasks_between_scans = AsyncMock(return_value=[])

        result = await c.collect_website_trajectories("site-1")
        assert len(result) == 1
        assert result[0].actions[0]["action_type"] == "scan_complete"

    @pytest.mark.asyncio
    async def test_collect_website_trajectories_multiple_gaps(self):
        c = DataCollector()
        c.get_website_scans = AsyncMock(return_value=[
            make_scan("s1", 50, scanned_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
            make_scan("s2", 55, scanned_at=datetime(2024, 2, 1, tzinfo=timezone.utc)),
            make_scan("s3", 70, scanned_at=datetime(2024, 3, 1, tzinfo=timezone.utc)),
        ])
        c._get_tasks_between_scans = AsyncMock(side_effect=[
            [make_task("fix_meta", "completed")],
            [make_task("fix_title", "completed")],
        ])

        result = await c.collect_website_trajectories("site-1")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_collect_all_trajectories(self):
        c = DataCollector()
        mock_traj = TrajectoryData(states=[{"s": 1}], actions=[{"a": "fix"}], rewards=[1.0])
        c.collect_website_trajectories = AsyncMock(return_value=[mock_traj])

        mock_session = AsyncMock()
        mock_execute = MagicMock()
        mock_execute.all.return_value = [("site-1",)]
        mock_session.execute.return_value = mock_execute

        factory_cm = AsyncMock()
        factory_cm.__aenter__.return_value = mock_session
        factory_cm.__aexit__.return_value = None

        with patch.object(c, "_session_factory", return_value=factory_cm):
            with patch.object(c, "_get_all_website_ids", new=AsyncMock(return_value=["site-1"])):
                result = await c.collect_all_trajectories(max_websites=5, max_per_website=10)

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_collect_all_trajectories_multiple_websites(self):
        c = DataCollector()
        c.collect_website_trajectories = AsyncMock(side_effect=[
            [TrajectoryData(states=[{"s": 1}], actions=[{"a": "fix"}], rewards=[1.0])],
            [TrajectoryData(states=[{"s": 2}], actions=[{"a": "opt"}], rewards=[0.5])],
        ])

        mock_session = AsyncMock()
        mock_execute = MagicMock()
        mock_execute.all.return_value = [("site-1",), ("site-2",)]
        mock_session.execute.return_value = mock_execute

        factory_cm = AsyncMock()
        factory_cm.__aenter__.return_value = mock_session
        factory_cm.__aexit__.return_value = None

        with patch.object(c, "_session_factory", return_value=factory_cm):
            with patch.object(c, "_get_all_website_ids", new=AsyncMock(return_value=["site-1", "site-2"])):
                result = await c.collect_all_trajectories()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_collect_agent_trajectories_with_logs(self):
        c = DataCollector()
        log1 = MagicMock()
        log1.id = "l1"
        log1.agent_type = "technical_auditor"
        log1.status = "completed"
        log1.input_data = {"url": "https://example.com"}
        log1.execution_time_ms = 1500
        log1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        log2 = MagicMock()
        log2.id = "l2"
        log2.agent_type = "technical_auditor"
        log2.status = "completed"
        log2.input_data = {"url": "https://example.com/page2"}
        log2.execution_time_ms = 2000
        log2.created_at = datetime(2024, 2, 1, tzinfo=timezone.utc)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [log1, log2]
        mock_session.execute.return_value = mock_result

        factory_cm = AsyncMock()
        factory_cm.__aenter__.return_value = mock_session
        factory_cm.__aexit__.return_value = None

        with patch.object(c, "_session_factory", return_value=factory_cm):
            result = await c.collect_agent_trajectories("technical_auditor")

        assert len(result) == 1
        assert result[0].states[0]["url"] == "https://example.com"
        assert result[0].states[1]["url"] == "https://example.com/page2"

    @pytest.mark.asyncio
    async def test_collect_agent_trajectories_single_log(self):
        c = DataCollector()
        log1 = MagicMock()
        log1.id = "l1"
        log1.agent_type = "technical_auditor"
        log1.status = "completed"
        log1.input_data = {}
        log1.execution_time_ms = 1000
        log1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [log1]
        mock_session.execute.return_value = mock_result

        factory_cm = AsyncMock()
        factory_cm.__aenter__.return_value = mock_session
        factory_cm.__aexit__.return_value = None

        with patch.object(c, "_session_factory", return_value=factory_cm):
            result = await c.collect_agent_trajectories("technical_auditor")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_training_batch(self):
        c = DataCollector()
        c.collect_all_trajectories = AsyncMock(return_value=[
            TrajectoryData(states=[{"s": i}], actions=[{"a": "fix"}], rewards=[1.0])
            for i in range(10)
        ])
        with patch("random.sample", side_effect=lambda items, k: items[:k]):
            batch = await c.get_training_batch(batch_size=5)
        assert len(batch) == 5

    @pytest.mark.asyncio
    async def test_get_training_batch_empty(self):
        c = DataCollector()
        c.collect_all_trajectories = AsyncMock(return_value=[])
        batch = await c.get_training_batch(batch_size=5)
        assert batch == []

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics(self):
        c = DataCollector()
        c.collect_website_trajectories = AsyncMock(return_value=[
            TrajectoryData(
                states=[{"score": 50}, {"score": 75}],
                actions=[{"action_type": "fix_title"}],
                rewards=[1.0],
                metadata={"score_delta": 25, "issue_delta": -3},
            ),
        ])
        metrics = await c.get_website_growth_metrics("site-1")
        assert metrics["website_id"] == "site-1"
        assert metrics["total_trajectories"] == 1

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics_no_data(self):
        c = DataCollector()
        c.collect_website_trajectories = AsyncMock(return_value=[])
        metrics = await c.get_website_growth_metrics("site-1")
        assert metrics["total_trajectories"] == 0
        assert metrics["score_trend"] == "unknown"

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics_improving_trend(self):
        c = DataCollector()
        c.collect_website_trajectories = AsyncMock(return_value=[
            TrajectoryData(states=[{"score": 50}, {"score": 60}], actions=[{"a": "fix"}], rewards=[0.5],
                           metadata={"score_delta": 10}),
            TrajectoryData(states=[{"score": 60}, {"score": 70}], actions=[{"a": "fix"}], rewards=[0.5],
                           metadata={"score_delta": 10}),
            TrajectoryData(states=[{"score": 70}, {"score": 80}], actions=[{"a": "fix"}], rewards=[0.5],
                           metadata={"score_delta": 10}),
        ])
        metrics = await c.get_website_growth_metrics("site-1")
        assert metrics["score_trend"] == "improving"

    @pytest.mark.asyncio
    async def test_get_website_growth_metrics_declining_trend(self):
        c = DataCollector()
        c.collect_website_trajectories = AsyncMock(return_value=[
            TrajectoryData(states=[{"score": 80}, {"score": 70}], actions=[{"a": "fix"}], rewards=[-0.5],
                           metadata={"score_delta": -10}),
            TrajectoryData(states=[{"score": 70}, {"score": 60}], actions=[{"a": "fix"}], rewards=[-0.5],
                           metadata={"score_delta": -10}),
            TrajectoryData(states=[{"score": 60}, {"score": 50}], actions=[{"a": "fix"}], rewards=[-0.5],
                           metadata={"score_delta": -10}),
        ])
        metrics = await c.get_website_growth_metrics("site-1")
        assert metrics["score_trend"] == "declining"
