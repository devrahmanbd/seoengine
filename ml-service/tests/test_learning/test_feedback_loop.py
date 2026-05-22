import pytest
from unittest.mock import AsyncMock, MagicMock

from app.learning.feedback_loop import FeedbackLoop
from app.learning.reward_calculator import RewardCalculator
from app.learning.data_collector import TrajectoryData


@pytest.fixture
def mock_collector():
    c = MagicMock()
    c.get_website_scans = AsyncMock()
    c.collect_website_trajectories = AsyncMock()
    c.get_website_growth_metrics = AsyncMock()
    return c


@pytest.fixture
def mock_pipeline():
    p = MagicMock()
    p._transform_to_scored_data = MagicMock(return_value=[])
    p._buffer = MagicMock()
    p._buffer.extend = MagicMock()
    return p


@pytest.fixture
def feedback_loop(mock_collector, mock_pipeline):
    return FeedbackLoop(
        collector=mock_collector,
        calculator=RewardCalculator(),
        pipeline=mock_pipeline,
    )


class TestOnScanComplete:
    @pytest.mark.asyncio
    async def test_triggers_trajectory_creation(self, feedback_loop, mock_collector):
        mock_collector.get_website_scans.return_value = [
            {"id": "s1", "website_id": "site-1", "score": 50, "issues": [{"i": 1}], "result_type": "technical"},
            {"id": "s2", "website_id": "site-1", "score": 75, "issues": [], "result_type": "technical"},
        ]
        result = await feedback_loop.on_scan_complete("site-1", {"score": 75})
        assert result["status"] == "success"
        assert result["trajectory_created"] is True
        assert isinstance(result["reward"], float)

    @pytest.mark.asyncio
    async def test_no_previous_scan(self, feedback_loop, mock_collector):
        mock_collector.get_website_scans.return_value = [
            {"id": "s1", "website_id": "site-1", "score": 50, "issues": [], "result_type": "technical"},
        ]
        result = await feedback_loop.on_scan_complete("site-1", {"score": 75})
        assert result["status"] == "insufficient_data"
        assert result["trajectory_created"] is False

    @pytest.mark.asyncio
    async def test_no_scans_at_all(self, feedback_loop, mock_collector):
        mock_collector.get_website_scans.return_value = []
        result = await feedback_loop.on_scan_complete("site-1", {"score": 75})
        assert result["status"] == "insufficient_data"


class TestOnTaskComplete:
    @pytest.mark.asyncio
    async def test_completed_task(self, feedback_loop):
        result = await feedback_loop.on_task_complete("task-1", {
            "website_id": "site-1",
            "status": "completed",
            "task_type": "fix_title",
        })
        assert result["status"] == "success"
        assert result["trajectory_created"] is True
        assert result["reward"] > 0

    @pytest.mark.asyncio
    async def test_failed_task(self, feedback_loop):
        result = await feedback_loop.on_task_complete("task-1", {
            "website_id": "site-1",
            "status": "failed",
            "task_type": "fix_title",
        })
        assert result["reward"] < 0

    @pytest.mark.asyncio
    async def test_no_website_id(self, feedback_loop):
        result = await feedback_loop.on_task_complete("task-1", {
            "status": "completed",
            "task_type": "fix_title",
        })
        assert result["status"] == "error"
        assert "no_website_id" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout_task(self, feedback_loop):
        result = await feedback_loop.on_task_complete("task-1", {
            "website_id": "site-1",
            "status": "timeout",
            "task_type": "fix_title",
        })
        assert result["reward"] < 0


class TestOnWebsiteUpdate:
    @pytest.mark.asyncio
    async def test_captures_growth_signal(self, feedback_loop, mock_collector):
        mock_collector.get_website_growth_metrics.return_value = {
            "website_id": "site-1",
            "total_trajectories": 3,
            "avg_reward": 0.5,
            "score_trend": "improving",
            "total_actions": 5,
        }
        result = await feedback_loop.on_website_update("site-1")
        assert result["status"] == "success"
        assert result["trajectory_created"] is True
        assert result["metrics"]["score_trend"] == "improving"

    @pytest.mark.asyncio
    async def test_no_collector(self):
        loop = FeedbackLoop()
        result = await loop.on_website_update("site-1")
        assert result["status"] == "no_collector"


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_calls(self, feedback_loop, mock_collector):
        mock_collector.get_website_scans.return_value = [
            {"id": "s1", "website_id": "site-1", "score": 50, "issues": [], "result_type": "technical"},
            {"id": "s2", "website_id": "site-1", "score": 75, "issues": [], "result_type": "technical"},
        ]
        import asyncio
        results = await asyncio.gather(
            feedback_loop.on_scan_complete("site-1", {}),
            feedback_loop.on_scan_complete("site-1", {}),
        )
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
