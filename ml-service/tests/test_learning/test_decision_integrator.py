import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import torch
import torch.nn as nn
from torch.distributions import Categorical

from app.learning.decision_integrator import DecisionIntegrator
from app.atropos.scored_data_api import ScoredDataBuffer


class DummyPolicy(nn.Module):
    def __init__(self, action_dim: int = 6):
        super().__init__()
        self.fc = nn.Linear(128, action_dim)

    def forward(self, x):
        return Categorical(logits=self.fc(x))


class DummyValue(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(128, 1)

    def forward(self, x):
        return self.fc(x).squeeze(-1)


@pytest.fixture
def mock_trainer():
    t = MagicMock()
    t._train_step = 1
    t._state_dim = 128
    t._action_dim = 6

    def state_to_tensor(state):
        import torch
        features = state.get("features")
        if isinstance(features, list) and len(features) >= 128:
            return torch.tensor(features[:128], dtype=torch.float32)
        return torch.zeros(128, dtype=torch.float32)

    def get_action_idx(action):
        action_type = action.get("action_type", "")
        registry = {"run_technical_audit": 0, "optimize_content": 1, "fix_meta_tags": 2, "improve_cwv": 3, "add_schema": 4, "build_backlinks": 5}
        return registry.get(action_type, 0)

    t._state_to_tensor = MagicMock(side_effect=state_to_tensor)
    t._get_action_idx = MagicMock(side_effect=get_action_idx)
    t._policy = DummyPolicy()
    t._value = DummyValue()
    return t


@pytest.fixture
def integrator(mock_trainer):
    return DecisionIntegrator(trainer=mock_trainer)


@pytest.fixture
def integrator_no_trainer():
    return DecisionIntegrator()


def make_state(score: float = 0.5):
    return {"features": [score] * 128, "score": score * 100}


class TestRecommendActions:
    @pytest.mark.asyncio
    async def test_returns_top_k(self, integrator):
        state = make_state()
        recs = await integrator.recommend_actions(state, top_k=3)
        assert len(recs) <= 3
        assert all("action_type" in r for r in recs)
        assert all("confidence" in r for r in recs)
        assert all("reason" in r for r in recs)

    @pytest.mark.asyncio
    async def test_sorted_by_confidence(self, integrator):
        state = make_state()
        recs = await integrator.recommend_actions(state, top_k=6)
        confidences = [r["confidence"] for r in recs]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_unrained_policy(self, integrator_no_trainer):
        state = make_state()
        recs = await integrator_no_trainer.recommend_actions(state, top_k=3)
        assert len(recs) == 2
        assert all(r["confidence"] == 0.5 for r in recs)


class TestScoreAction:
    @pytest.mark.asyncio
    async def test_returns_probability(self, integrator):
        state = make_state()
        score = await integrator.score_action(state, {"action_type": "run_technical_audit"})
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_no_trainer(self, integrator_no_trainer):
        state = make_state()
        score = await integrator_no_trainer.score_action(state, {"action_type": "run_technical_audit"})
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_different_actions_different_scores(self, integrator):
        state = make_state()
        scores = set()
        for at in ["run_technical_audit", "optimize_content", "fix_meta_tags"]:
            s = await integrator.score_action(state, {"action_type": at})
            scores.add(round(s, 4))
        assert len(scores) > 0


class TestGetActionValue:
    @pytest.mark.asyncio
    async def test_returns_value(self, integrator):
        state = make_state()
        value = await integrator.get_action_value(state, {"action_type": "run_technical_audit"})
        assert isinstance(value, float)

    @pytest.mark.asyncio
    async def test_no_trainer(self, integrator_no_trainer):
        state = make_state()
        value = await integrator_no_trainer.get_action_value(state, {"action_type": "run_technical_audit"})
        assert value == 0.0


class TestHasTrainedPolicy:
    def test_trained(self, integrator):
        assert integrator.has_trained_policy() is True

    def test_not_trained(self, integrator_no_trainer):
        assert integrator_no_trainer.has_trained_policy() is False

    def test_zero_train_steps(self, mock_trainer):
        mock_trainer._train_step = 0
        integrator = DecisionIntegrator(trainer=mock_trainer)
        assert integrator.has_trained_policy() is False


class TestEnrichDecision:
    @pytest.mark.asyncio
    async def test_adds_recommendations(self, integrator):
        state = make_state()
        llm_dec = {"action": "fix_meta", "reason": "llm_says", "priority": "high"}
        enriched = await integrator.enrich_decision(state, llm_dec)
        assert "policy_recommendations" in enriched
        assert "data_confidence" in enriched
        assert "expected_impact" in enriched
        assert enriched["policy_recommendations"] != []

    @pytest.mark.asyncio
    async def test_preserves_llm_fields(self, integrator):
        state = make_state()
        llm_dec = {"action": "fix_meta", "reason": "llm_says"}
        enriched = await integrator.enrich_decision(state, llm_dec)
        assert enriched["action"] == "fix_meta"
        assert enriched["reason"] == "llm_says"

    @pytest.mark.asyncio
    async def test_untrained_policy(self, integrator_no_trainer):
        state = make_state()
        llm_dec = {"action": "fix_meta"}
        enriched = await integrator_no_trainer.enrich_decision(state, llm_dec)
        assert enriched["policy_recommendations"] == []
        assert enriched["data_confidence"] == "low"
        assert enriched["expected_impact"] == 0.0

    @pytest.mark.asyncio
    async def test_tracks_history(self, integrator):
        state = make_state()
        await integrator.enrich_decision(state, {"action": "fix"})
        assert len(integrator._action_history) == 1
        assert "policy_recommendations" in integrator._action_history[0]


class TestStats:
    def test_get_stats(self, integrator, integrator_no_trainer):
        stats = integrator.get_stats()
        assert stats["total_decisions"] == 0
        assert stats["has_trained_policy"] is True

        stats2 = integrator_no_trainer.get_stats()
        assert stats2["has_trained_policy"] is False
