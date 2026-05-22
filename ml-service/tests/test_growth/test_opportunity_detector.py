import pytest
from unittest.mock import AsyncMock, MagicMock
from app.growth.opportunity_detector import OpportunityDetector, Opportunity


@pytest.fixture
def mock_decision_integrator():
    di = MagicMock()
    di.recommend_actions = AsyncMock(return_value=[
        {"action_type": "fix_title", "confidence": 0.85, "reason": "policy_recommended"},
        {"action_type": "add_schema", "confidence": 0.72, "reason": "policy_recommended"},
    ])
    di.score_action = AsyncMock(side_effect=lambda s, a: {
        "fix_title": 0.85, "add_schema": 0.72, "optimize_content": 0.45,
    }.get(a.get("action_type"), 0.5))
    return di


@pytest.fixture
def mock_cross_site():
    cs = MagicMock()
    cs.get_insights_for_site = AsyncMock(return_value=[
        MagicMock(pattern_id="p1", name="fix_title_pattern", description="Fixing titles helps", avg_improvement=0.3, site_count=5, action_sequence=["fix_title"]),
    ])
    return cs


@pytest.fixture
def detector(mock_decision_integrator, mock_cross_site):
    return OpportunityDetector(
        decision_integrator=mock_decision_integrator,
        cross_site_analyzer=mock_cross_site,
    )


class TestOpportunityDetector:
    @pytest.mark.asyncio
    async def test_detect_opportunities(self, detector):
        state = {"score": 55, "issues": 5, "features": [0.5] * 128}
        opps = await detector.detect_opportunities("site-1", state)
        assert len(opps) > 0
        assert all(isinstance(o, Opportunity) for o in opps)

    @pytest.mark.asyncio
    async def test_opportunity_has_required_fields(self, detector):
        state = {"score": 55, "issues": 5}
        opps = await detector.detect_opportunities("site-1", state)
        for opp in opps:
            assert opp.action_type
            assert isinstance(opp.expected_reward, float)
            assert opp.confidence in ("high", "medium", "low")
            assert opp.source in ("policy", "cross_site", "heuristic")
            assert opp.effort in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_high_confidence_policy_actions_sorted_first(self, detector):
        state = {"score": 30, "issues": 10}
        opps = await detector.detect_opportunities("site-1", state)
        confidences = [o.expected_reward for o in opps]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_low_score_adds_heuristic_actions(self, detector):
        state = {"score": 25, "issues": 12}
        opps = await detector.detect_opportunities("site-1", state)
        sources = [o.source for o in opps]
        assert "heuristic" in sources

    @pytest.mark.asyncio
    async def test_no_integrator_falls_back(self):
        detector = OpportunityDetector()
        state = {"score": 25, "issues": 10}
        opps = await detector.detect_opportunities("site-1", state)
        assert len(opps) >= 2
        assert all(o.source == "heuristic" for o in opps)

    @pytest.mark.asyncio
    async def test_cross_site_patterns_appear(self, detector):
        state = {"score": 70, "issues": 3}
        opps = await detector.detect_opportunities("site-1", state)
        sources = [o.source for o in opps]
        assert "cross_site" in sources or "policy" in sources

    @pytest.mark.asyncio
    async def test_predict_growth_called(self, detector, mock_decision_integrator):
        state = {"score": 50, "issues": 5}
        _ = await detector.detect_opportunities("site-1", state)
        mock_decision_integrator.recommend_actions.assert_called_once()
