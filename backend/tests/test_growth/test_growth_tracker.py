import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.services.growth.growth_tracker import GrowthTracker


@pytest.fixture
def mock_growth_scorer():
    gs = MagicMock()
    gs.score_growth = AsyncMock(return_value={
        "website_id": "site-1", "growth_score": 0.65, "trend": "accelerating",
        "trajectories_count": 5, "avg_reward": 0.65,
    })
    gs.get_action_effectiveness = AsyncMock(return_value={
        "fix_title": {"count": 3, "total_reward": 2.4, "avg_reward": 0.8},
        "optimize_content": {"count": 2, "total_reward": 1.0, "avg_reward": 0.5},
    })
    gs.predict_growth = AsyncMock(return_value={
        "website_id": "site-1", "predicted_growth": 0.75,
        "confidence": "high", "similar_actions_found": 5, "action_type": "fix_title",
    })
    return gs


@pytest.fixture
def mock_data_collector():
    dc = MagicMock()
    dc.get_score_progression = AsyncMock(return_value=[50, 60, 70, 75, 80])
    return dc


@pytest.fixture
def tracker(mock_growth_scorer, mock_data_collector):
    return GrowthTracker(
        growth_scorer=mock_growth_scorer,
        data_collector=mock_data_collector,
    )


class TestGrowthTracker:
    @pytest.mark.asyncio
    async def test_get_growth_state(self, tracker):
        state = await tracker.get_growth_state("site-1")
        assert state.website_id == "site-1"
        assert state.growth_score == 0.65
        assert state.trend == "accelerating"
        assert state.trajectory_count == 5
        assert isinstance(state.score_history, list)

    @pytest.mark.asyncio
    async def test_get_growth_state_detects_plateau(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "stable"
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "plateauing"

    @pytest.mark.asyncio
    async def test_get_growth_state_declining(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "declining"
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "declining"

    @pytest.mark.asyncio
    async def test_get_growth_state_no_data(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value = {
            "website_id": "site-1", "growth_score": 0.0,
            "trend": "unknown", "trajectories_count": 0, "avg_reward": 0.0,
        }
        state = await tracker.get_growth_state("site-1")
        assert state.trend == "unknown"
        assert state.trajectory_count == 0

    @pytest.mark.asyncio
    async def test_get_growth_state_no_collector(self):
        gs = MagicMock()
        gs.score_growth = AsyncMock(return_value={
            "website_id": "site-1", "growth_score": 0.65, "trend": "accelerating",
            "trajectories_count": 5, "avg_reward": 0.65,
        })
        gs.get_action_effectiveness = AsyncMock(return_value={})
        tracker = GrowthTracker(growth_scorer=gs)
        state = await tracker.get_growth_state("site-1")
        assert state.score_history == []

    @pytest.mark.asyncio
    async def test_compare_websites(self, tracker):
        mock_gs = tracker._growth_scorer
        mock_gs.score_growth = AsyncMock(side_effect=[
            {"website_id": "site-1", "growth_score": 0.8, "trend": "accelerating", "trajectories_count": 5, "avg_reward": 0.8},
            {"website_id": "site-2", "growth_score": 0.3, "trend": "declining", "trajectories_count": 3, "avg_reward": 0.3},
        ])
        results = await tracker.compare_websites(["site-1", "site-2"])
        assert len(results) == 2
        assert results[0].website_id == "site-1"
        assert results[0].growth_score > results[1].growth_score

    @pytest.mark.asyncio
    async def test_needs_intervention_accelerating(self, tracker):
        needs = await tracker.needs_intervention("site-1")
        assert needs is False

    @pytest.mark.asyncio
    async def test_needs_intervention_declining(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "declining"
        mock_growth_scorer.score_growth.return_value["growth_score"] = -0.3
        needs = await tracker.needs_intervention("site-1")
        assert needs is True

    @pytest.mark.asyncio
    async def test_needs_intervention_plateau(self, tracker, mock_growth_scorer):
        mock_growth_scorer.score_growth.return_value["trend"] = "stable"
        mock_growth_scorer.score_growth.return_value["growth_score"] = 0.15
        needs = await tracker.needs_intervention("site-1")
        assert needs is True

    @pytest.mark.asyncio
    async def test_get_effective_actions(self, tracker):
        actions = await tracker.get_effective_actions("site-1", min_occurrences=2)
        assert "fix_title" in actions
        assert "optimize_content" in actions
        assert actions["fix_title"]["avg_reward"] == 0.8

    @pytest.mark.asyncio
    async def test_get_effective_actions_filters_by_count(self, tracker):
        actions = await tracker.get_effective_actions("site-1", min_occurrences=3)
        assert "fix_title" in actions
        assert "optimize_content" not in actions
