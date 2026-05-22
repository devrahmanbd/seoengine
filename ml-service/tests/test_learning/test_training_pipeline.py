import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.learning.training_pipeline import TrainingPipeline
from app.learning.data_collector import TrajectoryData
from app.atropos.scored_data_api import ScoredData, ScoredDataBuffer


@pytest.fixture
def mock_collector():
    c = MagicMock()
    c.collect_website_trajectories = AsyncMock()
    c.collect_all_trajectories = AsyncMock()
    return c


@pytest.fixture
def mock_trainer():
    t = MagicMock()
    t.update_policy = AsyncMock(return_value={
        "policy_loss": 0.1, "value_loss": 0.2, "entropy": 0.5, "kl": 0.01, "clip_fraction": 0.05,
    })
    return t


@pytest.fixture
def pipeline(mock_collector, mock_trainer):
    return TrainingPipeline(collector=mock_collector, trainer=mock_trainer)


class TestTransformToScoredData:
    def test_single_trajectory(self, pipeline):
        trajs = [
            TrajectoryData(
                states=[{"s": 1}, {"s": 2}],
                actions=[{"a": "fix"}],
                rewards=[1.0],
            ),
        ]
        scored = pipeline._transform_to_scored_data(trajs)
        assert len(scored) == 1
        assert scored[0].reward == 1.0
        assert scored[0].state == {"s": 1}
        assert scored[0].next_state == {"s": 2}
        assert scored[0].done is True

    def test_multi_step(self, pipeline):
        trajs = [
            TrajectoryData(
                states=[{"s": 1}, {"s": 2}, {"s": 3}],
                actions=[{"a": "fix1"}, {"a": "fix2"}],
                rewards=[1.0, 0.5],
            ),
        ]
        scored = pipeline._transform_to_scored_data(trajs)
        assert len(scored) == 2
        assert scored[0].reward == 1.0
        assert scored[1].reward == 0.5
        assert scored[1].done is True

    def test_empty_trajectories(self, pipeline):
        scored = pipeline._transform_to_scored_data([])
        assert scored == []

    def test_single_state_trajectory(self, pipeline):
        trajs = [
            TrajectoryData(
                states=[{"s": 1}],
                actions=[{"a": "fix"}],
                rewards=[1.0],
            ),
        ]
        scored = pipeline._transform_to_scored_data(trajs)
        assert len(scored) == 1
        assert scored[0].done is True

    def test_multiple_trajectories(self, pipeline):
        trajs = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
            TrajectoryData(states=[{"s": 3}, {"s": 4}], actions=[{"a": "opt"}], rewards=[0.5]),
        ]
        scored = pipeline._transform_to_scored_data(trajs)
        assert len(scored) == 2


class TestCollectAndTrain:
    @pytest.mark.asyncio
    async def test_successful_training(self, pipeline, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
        ]
        result = await pipeline.collect_and_train("site-1")
        assert result["status"] == "success"
        assert result["website_id"] == "site-1"
        assert result["trajectories"] == 1
        assert "training_stats" in result

    @pytest.mark.asyncio
    async def test_no_collector(self):
        pipeline = TrainingPipeline()
        result = await pipeline.collect_and_train("site-1")
        assert result["status"] == "no_collector"

    @pytest.mark.asyncio
    async def test_no_data(self, pipeline, mock_collector):
        mock_collector.collect_website_trajectories.return_value = []
        result = await pipeline.collect_and_train("site-1")
        assert result["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_buffer_populated(self, pipeline, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
        ]
        initial_len = len(pipeline._buffer)
        await pipeline.collect_and_train("site-1")
        assert len(pipeline._buffer) > initial_len

    @pytest.mark.asyncio
    async def test_trainer_error_handled(self, pipeline, mock_collector, mock_trainer):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
        ]
        mock_trainer.update_policy = AsyncMock(side_effect=Exception("trainer_error"))
        result = await pipeline.collect_and_train("site-1")
        assert result["status"] == "success"
        assert result["training_stats"] == {}


class TestCollectFromAllSites:
    @pytest.mark.asyncio
    async def test_successful(self, pipeline, mock_collector):
        mock_collector.collect_all_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
        ]
        result = await pipeline.collect_from_all_sites()
        assert result["status"] == "success"
        assert result["sites_trained"] == 1

    @pytest.mark.asyncio
    async def test_no_collector(self):
        pipeline = TrainingPipeline()
        result = await pipeline.collect_from_all_sites()
        assert result["status"] == "no_collector"

    @pytest.mark.asyncio
    async def test_no_data(self, pipeline, mock_collector):
        mock_collector.collect_all_trajectories.return_value = []
        result = await pipeline.collect_from_all_sites()
        assert result["status"] == "no_data"


class TestTrainingStats:
    def test_initial_stats(self, pipeline):
        stats = pipeline.get_training_stats()
        assert stats["total_training_runs"] == 0
        assert stats["total_trajectories_collected"] == 0
        assert stats["total_reward"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_after_training(self, pipeline, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}, {"s": 2}], actions=[{"a": "fix"}], rewards=[1.0]),
        ]
        await pipeline.collect_and_train("site-1")
        stats = pipeline.get_training_stats()
        assert stats["total_training_runs"] == 1
        assert stats["total_trajectories_collected"] == 1
        assert "last_training_stats" in stats


class TestAutoTrain:
    @pytest.mark.asyncio
    async def test_start_stop(self, pipeline, mock_collector):
        mock_collector.collect_all_trajectories.return_value = []
        await pipeline.start_auto_train(interval=1)
        assert pipeline._auto_train_task is not None
        await pipeline.stop_auto_train()
        assert pipeline._auto_train_task is None

    @pytest.mark.asyncio
    async def test_start_twice(self, pipeline):
        await pipeline.start_auto_train(interval=3600)
        task1 = pipeline._auto_train_task
        await pipeline.start_auto_train(interval=3600)
        task2 = pipeline._auto_train_task
        assert task1 is task2
        await pipeline.stop_auto_train()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, pipeline):
        await pipeline.stop_auto_train()
        assert pipeline._auto_train_task is None
