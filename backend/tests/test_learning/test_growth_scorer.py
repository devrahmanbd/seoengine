import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.learning.growth_scorer import GrowthScorer
from app.services.learning.data_collector import TrajectoryData


@pytest.fixture
def mock_collector():
    c = MagicMock()
    c.collect_website_trajectories = AsyncMock()
    return c


@pytest.fixture
def scorer(mock_collector):
    return GrowthScorer(collector=mock_collector)


def make_trajs(rewards: list[float], action_types: list[str] | None = None):
    if action_types is None:
        action_types = ["fix_title"]
    return [
        TrajectoryData(
            states=[{"score": 50}, {"score": 50}],
            actions=[{"action_type": at} for at in action_types],
            rewards=[r],
        )
        for r in rewards
    ]


class TestScoreGrowth:
    @pytest.mark.asyncio
    async def test_increasing_trajectory(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([1.0, 0.8, 0.6])
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] > 0
        assert result["trajectories_count"] == 3

    @pytest.mark.asyncio
    async def test_decreasing_trajectory(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([-0.5, -0.3, -0.8])
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] < 0

    @pytest.mark.asyncio
    async def test_flat_trajectory(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([0.0, 0.0, 0.0])
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_history(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = []
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] == 0.0
        assert result["trajectories_count"] == 0
        assert result["trend"] == "unknown"

    @pytest.mark.asyncio
    async def test_single_data_point(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([0.5])
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] == 0.5
        assert result["trajectories_count"] == 1
        assert result["trend"] == "stable"

    @pytest.mark.asyncio
    async def test_accelerating_trend(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([0.1, 0.3, 0.5])
        result = await scorer.score_growth("site-1")
        assert result["trend"] == "accelerating"

    @pytest.mark.asyncio
    async def test_declining_trend(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([-0.1, -0.3, -0.5])
        result = await scorer.score_growth("site-1")
        assert result["trend"] == "declining"

    @pytest.mark.asyncio
    async def test_no_collector(self):
        scorer = GrowthScorer()
        result = await scorer.score_growth("site-1")
        assert result["growth_score"] == 0.0
        assert result["trend"] == "unknown"


class TestGetActionEffectiveness:
    @pytest.mark.asyncio
    async def test_multiple_action_types(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}], actions=[{"action_type": "fix_title"}], rewards=[1.0]),
            TrajectoryData(states=[{"s": 2}], actions=[{"action_type": "optimize_content"}], rewards=[0.5]),
            TrajectoryData(states=[{"s": 3}], actions=[{"action_type": "fix_title"}], rewards=[0.8]),
        ]
        result = await scorer.get_action_effectiveness("site-1")
        assert "fix_title" in result
        assert "optimize_content" in result
        assert result["fix_title"]["count"] == 2
        assert result["fix_title"]["avg_reward"] == 0.9

    @pytest.mark.asyncio
    async def test_empty_history(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = []
        result = await scorer.get_action_effectiveness("site-1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_actions(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}], actions=[{"action_type": "unknown"}], rewards=[0.0]),
        ]
        result = await scorer.get_action_effectiveness("site-1")
        assert "unknown" in result

    @pytest.mark.asyncio
    async def test_no_collector(self):
        scorer = GrowthScorer()
        result = await scorer.get_action_effectiveness("site-1")
        assert result == {}


class TestPredictGrowth:
    @pytest.mark.asyncio
    async def test_known_action_pattern(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = [
            TrajectoryData(states=[{"s": 1}], actions=[{"action_type": "fix_title"}], rewards=[1.0]),
            TrajectoryData(states=[{"s": 2}], actions=[{"action_type": "fix_title"}], rewards=[0.8]),
            TrajectoryData(states=[{"s": 3}], actions=[{"action_type": "fix_title"}], rewards=[0.6]),
        ]
        result = await scorer.predict_growth("site-1", {"action_type": "fix_title"})
        assert result["predicted_growth"] == pytest.approx(0.8)
        assert result["confidence"] == "medium"
        assert result["similar_actions_found"] == 3

    @pytest.mark.asyncio
    async def test_high_confidence(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs(
            [1.0] * 5, action_types=["fix_title"] * 5
        )
        result = await scorer.predict_growth("site-1", {"action_type": "fix_title"})
        assert result["confidence"] == "high"
        assert result["similar_actions_found"] == 5

    @pytest.mark.asyncio
    async def test_unknown_action(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = make_trajs([1.0], action_types=["fix_title"])
        result = await scorer.predict_growth("site-1", {"action_type": "unknown_action"})
        assert result["predicted_growth"] == 0.0
        assert result["confidence"] == "low"
        assert result["similar_actions_found"] == 0

    @pytest.mark.asyncio
    async def test_empty_history(self, scorer, mock_collector):
        mock_collector.collect_website_trajectories.return_value = []
        result = await scorer.predict_growth("site-1", {"action_type": "fix_title"})
        assert result["predicted_growth"] == 0.0
        assert result["confidence"] == "low"
        assert result["trajectories_count"] == 0

    @pytest.mark.asyncio
    async def test_no_collector(self):
        scorer = GrowthScorer()
        result = await scorer.predict_growth("site-1", {"action_type": "fix_title"})
        assert result["predicted_growth"] == 0.0
        assert result["confidence"] == "low"
