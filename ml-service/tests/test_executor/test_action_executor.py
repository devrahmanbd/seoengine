import pytest
from unittest.mock import AsyncMock, MagicMock

from app.executor.action_executor import ActionExecutor, ACTION_ENV_MAP
from app.atropos.base_env import Registry


@pytest.fixture
def mock_env():
    env = AsyncMock()
    env.step = AsyncMock(return_value=(
        MagicMock(), 1.0, False, {"details": "ok"},
    ))
    env.close = AsyncMock()
    return env


@pytest.fixture
def registry(mock_env):
    reg = MagicMock(spec=Registry)
    reg.create.return_value = mock_env
    return reg


@pytest.fixture
def executor(registry):
    return ActionExecutor(registry)


class TestExecute:
    @pytest.mark.asyncio
    async def test_known_action_type_returns_success(self, executor, mock_env, registry):
        result = await executor.execute("site_1", "fix_title", {"key": "value"})

        assert result["status"] == "success"
        registry.create.assert_called_once_with("technical_seo", site_id="site_1")
        mock_env.step.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_action_type_returns_error(self, executor):
        result = await executor.execute("site_1", "nonexistent_action")
        assert result["status"] == "error"
        assert "No environment mapped" in result["error"]

    @pytest.mark.asyncio
    async def test_unregistered_environment_returns_error(self, executor, registry):
        registry.create.side_effect = ValueError("not registered")
        result = await executor.execute("site_1", "fix_title")
        assert result["status"] == "error"
        assert "not registered" in result["error"]

    @pytest.mark.asyncio
    async def test_env_step_exception_returns_error(self, executor, mock_env):
        mock_env.step.side_effect = Exception("step failed")
        result = await executor.execute("site_1", "fix_title")
        assert result["status"] == "error"
        assert "step failed" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_reward_and_info(self, executor):
        result = await executor.execute("site_1", "fix_title")
        assert "reward" in result
        assert "info" in result
        assert "done" in result

    @pytest.mark.asyncio
    async def test_closes_env_after_execution(self, executor, mock_env):
        await executor.execute("site_1", "fix_title")
        mock_env.close.assert_awaited_once()


class TestExecuteBatch:
    @pytest.mark.asyncio
    async def test_executes_multiple_actions(self, executor):
        actions = [
            {"action_type": "fix_title", "params": {}},
            {"action_type": "fix_meta", "params": {}},
        ]
        results = await executor.execute_batch("site_1", actions)
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty_list(self, executor):
        results = await executor.execute_batch("site_1", [])
        assert results == []


class TestActionEnvMap:
    def test_contains_all_known_actions(self):
        assert "fix_title" in ACTION_ENV_MAP
        assert "generate_article_schema" in ACTION_ENV_MAP
        assert "optimize_content" in ACTION_ENV_MAP
        assert "target_keyword" in ACTION_ENV_MAP
        assert "optimize_images" in ACTION_ENV_MAP
        assert "earn_backlink" in ACTION_ENV_MAP

    def test_includes_all_environment_categories(self):
        envs = set(ACTION_ENV_MAP.values())
        assert "technical_seo" in envs
        assert "schema" in envs
        assert "content_seo" in envs
        assert "keyword_research" in envs
        assert "cwv" in envs
        assert "backlink" in envs

    def test_returns_all_actions(self):
        assert len(ACTION_ENV_MAP) >= 30
