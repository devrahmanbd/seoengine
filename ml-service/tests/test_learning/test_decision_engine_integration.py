import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.agents.decision_engine import DecisionEngine
from app.learning.decision_integrator import DecisionIntegrator


@pytest.fixture
def mock_integrator():
    i = MagicMock(spec=DecisionIntegrator)
    i.enrich_decision = AsyncMock(return_value={
        "score": 50,
        "issues_count": 5,
        "priority": "high",
        "recommended_action": "run_technical_audit",
        "policy_recommendations": [
            {"action_type": "run_technical_audit", "confidence": 0.8, "reason": "policy_recommended"},
        ],
        "data_confidence": "medium",
        "expected_impact": 0.65,
    })
    i.recommend_actions = AsyncMock(return_value=[
        {"action_type": "run_technical_audit", "confidence": 0.8, "reason": "policy_recommended"},
        {"action_type": "optimize_content", "confidence": 0.6, "reason": "policy_recommended"},
    ])
    i.has_trained_policy = MagicMock(return_value=True)
    return i


@pytest.fixture
def engine_with_integrator(mock_integrator):
    return DecisionEngine(integrator=mock_integrator)


@pytest.fixture
def engine_without_integrator():
    return DecisionEngine()


def make_state(score=50, issues=5):
    return {"score": score, "issues": issues, "features": [0.5] * 128}


class TestDecisionEngineWithoutIntegrator:
    @pytest.mark.asyncio
    async def test_decide_returns_heuristic(self, engine_without_integrator):
        state = make_state()
        result = await engine_without_integrator.decide(state)
        assert result["source"] == "heuristic"
        assert "decision" in result

    @pytest.mark.asyncio
    async def test_decide_returns_base_fields(self, engine_without_integrator):
        state = make_state(score=45, issues=8)
        result = await engine_without_integrator.decide(state)
        dec = result["decision"]
        assert "score" in dec
        assert "priority" in dec
        assert "recommended_action" in dec

    @pytest.mark.asyncio
    async def test_critical_priority(self, engine_without_integrator):
        state = make_state(score=20, issues=15)
        result = await engine_without_integrator.decide(state)
        assert result["decision"]["priority"] == "critical"
        assert result["decision"]["recommended_action"] == "run_full_audit"

    @pytest.mark.asyncio
    async def test_low_priority(self, engine_without_integrator):
        state = make_state(score=85, issues=2)
        result = await engine_without_integrator.decide(state)
        assert result["decision"]["priority"] == "low"
        assert result["decision"]["recommended_action"] == "monitor"

    @pytest.mark.asyncio
    async def test_recommend_returns_defaults(self, engine_without_integrator):
        state = make_state()
        recs = await engine_without_integrator.recommend(state)
        assert len(recs) == 2
        assert all(r["confidence"] == 0.5 for r in recs)

    @pytest.mark.asyncio
    async def test_enriched_decision_returns_fallback(self, engine_without_integrator):
        state = make_state()
        llm_dec = {"action": "fix_title", "reason": "test"}
        enriched = await engine_without_integrator.get_enriched_decision(state, llm_dec)
        assert enriched["action"] == "fix_title"
        assert enriched["policy_recommendations"] == []
        assert enriched["data_confidence"] == "low"
        assert enriched["expected_impact"] == 0.0


class TestDecisionEngineWithIntegrator:
    @pytest.mark.asyncio
    async def test_decide_returns_policy_enriched(self, engine_with_integrator):
        state = make_state()
        result = await engine_with_integrator.decide(state)
        assert result["source"] == "policy"
        assert "policy_recommendations" in result
        assert "data_confidence" in result
        assert "expected_impact" in result

    @pytest.mark.asyncio
    async def test_decide_calls_integrator(self, engine_with_integrator, mock_integrator):
        state = make_state()
        await engine_with_integrator.decide(state)
        mock_integrator.enrich_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_uses_integrator(self, engine_with_integrator, mock_integrator):
        state = make_state()
        recs = await engine_with_integrator.recommend(state)
        mock_integrator.recommend_actions.assert_called_once_with(state, top_k=3)
        assert len(recs) == 2

    @pytest.mark.asyncio
    async def test_enriched_decision_uses_integrator(self, engine_with_integrator, mock_integrator):
        state = make_state()
        llm_dec = {"action": "fix_title"}
        enriched = await engine_with_integrator.get_enriched_decision(state, llm_dec)
        mock_integrator.enrich_decision.assert_called_once_with(state, llm_dec)
        assert "policy_recommendations" in enriched
        assert enriched["data_confidence"] == "medium"
        assert enriched["expected_impact"] == 0.65


class TestDecisionHeuristics:
    @pytest.mark.asyncio
    async def test_critical_score_low_many_issues(self, engine_without_integrator):
        result = await engine_without_integrator.decide(make_state(score=25, issues=12))
        assert result["decision"]["priority"] == "critical"

    @pytest.mark.asyncio
    async def test_high_medium_score_mid_issues(self, engine_without_integrator):
        result = await engine_without_integrator.decide(make_state(score=55, issues=6))
        assert result["decision"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_medium_good_score_few_issues(self, engine_without_integrator):
        result = await engine_without_integrator.decide(make_state(score=70, issues=3))
        assert result["decision"]["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_low_great_score_no_issues(self, engine_without_integrator):
        result = await engine_without_integrator.decide(make_state(score=90, issues=0))
        assert result["decision"]["priority"] == "low"

    @pytest.mark.asyncio
    async def test_context_preserved(self, engine_without_integrator):
        ctx = {"url": "https://example.com", "previous_action": "fix_meta"}
        result = await engine_without_integrator.decide(make_state(), context=ctx)
        assert result["decision"]["context"] == ctx
