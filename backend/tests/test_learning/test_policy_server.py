import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.learning.policy_server import PolicyServer


@pytest.fixture
def mock_trainer():
    trainer = MagicMock()
    trainer._train_step = 5
    trainer._action_registry = {"fix_title": 0, "fix_meta": 1}
    return trainer


@pytest.fixture
def mock_integrator():
    integrator = MagicMock()
    integrator.recommend_actions = AsyncMock(return_value=[
        {"action_type": "fix_title", "confidence": 0.9, "reason": "test"},
        {"action_type": "fix_meta", "confidence": 0.7, "reason": "test"},
    ])
    return integrator


class TestGetRecommendations:
    @pytest.mark.asyncio
    async def test_with_integrator_returns_recommendations(self, mock_trainer, mock_integrator):
        server = PolicyServer(trainer=mock_trainer, integrator=mock_integrator)
        state = {"features": [0.5] * 128}
        recs = await server.get_recommendations(state, top_k=2)
        assert len(recs) == 2
        assert all("action_type" in r for r in recs)
        assert all("confidence" in r for r in recs)

    @pytest.mark.asyncio
    async def test_no_integrator_returns_empty_list(self):
        server = PolicyServer(trainer=None, integrator=None)
        state = {"features": [0.5] * 128}
        recs = await server.get_recommendations(state, top_k=2)
        assert recs == []

    @pytest.mark.asyncio
    async def test_passes_top_k_to_integrator(self, mock_trainer, mock_integrator):
        server = PolicyServer(trainer=mock_trainer, integrator=mock_integrator)
        await server.get_recommendations({}, top_k=5)
        mock_integrator.recommend_actions.assert_awaited_once_with({}, top_k=5)


class TestGetPolicyInfo:
    @pytest.mark.asyncio
    async def test_with_trained_model_returns_stats(self, mock_trainer, mock_integrator):
        server = PolicyServer(trainer=mock_trainer, integrator=mock_integrator)
        info = await server.get_policy_info()
        assert info["model_loaded"] is True
        assert info["training_steps"] == 5
        assert info["action_registry_size"] == 2

    @pytest.mark.asyncio
    async def test_untrained_model_returns_defaults(self):
        server = PolicyServer(trainer=None, integrator=None)
        info = await server.get_policy_info()
        assert info["model_loaded"] is False
        assert info["training_steps"] == 0
        assert info["action_registry_size"] == 0

    @pytest.mark.asyncio
    async def test_empty_registry(self):
        trainer = MagicMock()
        trainer._train_step = 0
        trainer._action_registry = {}
        server = PolicyServer(trainer=trainer)
        info = await server.get_policy_info()
        assert info["model_loaded"] is True
        assert info["training_steps"] == 0
        assert info["action_registry_size"] == 0


class TestReloadPolicy:
    @pytest.mark.asyncio
    async def test_no_trainer_returns_false(self):
        server = PolicyServer(trainer=None)
        result = await server.reload_policy()
        assert result is False

    @pytest.mark.asyncio
    async def test_no_model_file_returns_false(self, mock_trainer, mock_integrator):
        server = PolicyServer(trainer=mock_trainer, integrator=mock_integrator)
        result = await server.reload_policy()
        assert result is False
