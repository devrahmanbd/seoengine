import unittest.mock

import pytest

from app.services.atropos.base_env import SEOAction, State, Registry
from app.services.atropos.environments.technical_seo_env import TechnicalSEOEnv
from app.services.atropos.environments.content_seo_env import ContentSEOEnv
from app.services.atropos.environments.keyword_env import KeywordResearchEnv
from app.services.atropos.environments.backlink_env import BacklinkEnv
from app.services.atropos.environments.cwv_env import CWVEnv
from app.services.atropos.environments.schema_env import SchemaEnv


class TestRegistration:
    def setup_method(self):
        Registry._environments = {}

    def test_all_six_environments_registered(self):
        envs = {
            "technical": TechnicalSEOEnv,
            "content": ContentSEOEnv,
            "keyword": KeywordResearchEnv,
            "backlink": BacklinkEnv,
            "cwv": CWVEnv,
            "schema": SchemaEnv,
        }
        for name, cls in envs.items():
            Registry.register(name, cls)
        names = Registry.list()
        assert len(names) == 6
        for name in envs:
            assert name in names

    def test_each_environment_creatable(self):
        envs = {
            "technical": (TechnicalSEOEnv, {"site_id": "https://example.com"}),
            "content": (ContentSEOEnv, {"site_id": "https://example.com"}),
            "keyword": (KeywordResearchEnv, {"site_id": "test_site"}),
            "backlink": (BacklinkEnv, {"site_id": "test_site"}),
            "cwv": (CWVEnv, {"site_id": "test_site"}),
            "schema": (SchemaEnv, {"site_id": "test_site"}),
        }
        for name, (cls, kwargs) in envs.items():
            Registry.register(name, cls)
            env = Registry.create(name, **kwargs)
            assert isinstance(env, cls)


@pytest.mark.asyncio
class TestTechnicalSEOEnv:
    async def _setup_with_mock_fetch(self, env):
        async def _mock_fetch():
            env.metrics["status_code"] = 200
            env.metrics["title_length"] = 55
            env.metrics["meta_description_length"] = 155
            env.metrics["h1_count"] = 1
            env.metrics["schema_count"] = 1
            env.metrics["has_canonical"] = True
            env.metrics["has_viewport"] = True
            env.metrics["response_time_ms"] = 100.0
            env.metrics["internal_links"] = 10
            env.metrics["external_links"] = 5
            env.metrics["images_total"] = 5
            env.metrics["images_missing_alt"] = 0
            env.metrics["og_title"] = True
            env.metrics["og_description"] = True
            env.metrics["og_image"] = True

        with unittest.mock.patch.object(env, "_fetch_and_parse", _mock_fetch):
            return await env.reset()

    async def test_reset_returns_state_with_expected_keys(self):
        env = TechnicalSEOEnv(site_id="https://example.com", max_steps=10)
        state = await self._setup_with_mock_fetch(env)
        assert isinstance(state, State)
        assert "title_length" in state.metrics
        assert "meta_description_length" in state.metrics
        assert "h1_count" in state.metrics
        assert "technical_score" in state.metrics
        assert "status_code" in state.metrics

    async def test_step_fix_title_returns_tuple(self):
        env = TechnicalSEOEnv(site_id="https://example.com", max_steps=10)
        await self._setup_with_mock_fetch(env)

        action = SEOAction(
            action_type="fix_title",
            params={"title": "Optimal Title Length Here!"},
        )
        result = await env.step(action)
        assert isinstance(result, tuple)
        assert len(result) == 4
        state, reward, done, info = result
        assert isinstance(state, State)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    async def test_score_computation_between_0_and_1(self):
        env = TechnicalSEOEnv(site_id="https://example.com", max_steps=10)
        score = env._compute_score({
            "status_code": 200,
            "title_length": 55,
            "meta_description_length": 155,
            "h1_count": 1,
            "schema_count": 1,
            "has_canonical": True,
            "has_viewport": True,
            "response_time_ms": 100.0,
            "internal_links": 10,
            "external_links": 5,
            "images_total": 5,
            "images_missing_alt": 0,
            "og_title": True,
            "og_description": True,
            "og_image": True,
        })
        assert 0.0 <= score <= 1.0

    async def test_score_computation_low_end(self):
        env = TechnicalSEOEnv(site_id="https://example.com", max_steps=10)
        score = env._compute_score({
            "status_code": 404,
            "title_length": 0,
            "meta_description_length": 0,
            "h1_count": 0,
            "schema_count": 0,
            "has_canonical": False,
            "has_viewport": False,
            "response_time_ms": 99999.0,
            "internal_links": 0,
            "external_links": 0,
            "images_total": 0,
            "images_missing_alt": 0,
            "og_title": False,
            "og_description": False,
            "og_image": False,
        })
        assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
class TestContentSEOEnv:
    async def _setup_with_mock_fetch(self, env):
        async def _mock_fetch():
            env._text = "This is a sample article with enough words for testing purposes only. " * 40
            env._headings = ["h1", "h2", "h2", "h3"]
            env.metrics["word_count"] = len(env._text.split())
            env.metrics["readability_score"] = 60.0
            env.metrics["heading_structure_score"] = 0.8
            env.metrics["entity_count"] = 10
            env.metrics["has_faq"] = False
            env.metrics["has_schema"] = True

        with unittest.mock.patch.object(env, "_fetch_and_parse", _mock_fetch):
            return await env.reset()

    async def test_reset_returns_state(self):
        env = ContentSEOEnv(site_id="https://example.com", max_steps=10)
        state = await self._setup_with_mock_fetch(env)
        assert isinstance(state, State)
        assert "word_count" in state.metrics
        assert "content_score" in state.metrics

    async def test_step_optimize_content(self):
        env = ContentSEOEnv(site_id="https://example.com", max_steps=10)
        await self._setup_with_mock_fetch(env)

        action = SEOAction(
            action_type="optimize_content",
            params={"target_word_count": 2000},
        )
        result = await env.step(action)
        assert isinstance(result, tuple)
        assert len(result) == 4
        state, reward, done, info = result
        assert isinstance(state, State)
        assert isinstance(reward, float)

    async def test_step_add_faq_schema(self):
        env = ContentSEOEnv(site_id="https://example.com", max_steps=10)
        await self._setup_with_mock_fetch(env)

        action = SEOAction(
            action_type="add_faq_schema",
            params={"faq_count": 3},
        )
        _, reward, done, info = await env.step(action)
        assert env.metrics["has_faq"] is True

    async def test_max_steps_termination(self):
        env = ContentSEOEnv(site_id="https://example.com", max_steps=5)
        await self._setup_with_mock_fetch(env)

        action = SEOAction(action_type="optimize_content", params={"target_word_count": 2000})
        done = False
        for _ in range(10):
            if done:
                break
            _, _, done, _ = await env.step(action)
        assert done is True


@pytest.mark.asyncio
class TestKeywordResearchEnv:
    async def test_reset_and_step_target_keyword(self):
        env = KeywordResearchEnv(site_id="test_site")
        state = await env.reset()
        assert isinstance(state, State)
        assert "current_rankings" in state.metrics

        action = SEOAction(
            action_type="target_keyword",
            params={"keyword": "seo tools"},
        )
        next_state, reward, done, info = await env.step(action)
        assert isinstance(next_state, State)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert info["action"] == "target_keyword"


@pytest.mark.asyncio
class TestBacklinkEnv:
    async def test_reset_and_step(self):
        env = BacklinkEnv(site_id="test_site")
        state = await env.reset()
        assert isinstance(state, State)
        assert "backlink_count" in state.metrics

        action = SEOAction(
            action_type="earn_backlink",
            params={"quality": "high"},
        )
        next_state, reward, done, info = await env.step(action)
        assert isinstance(next_state, State)
        assert reward > 0


@pytest.mark.asyncio
class TestCWVEnv:
    async def test_reset_and_step(self):
        env = CWVEnv(site_id="test_site")
        state = await env.reset()
        assert isinstance(state, State)
        assert "lcp_score" in state.metrics

        action = SEOAction(action_type="optimize_images", params={})
        next_state, reward, done, info = await env.step(action)
        assert isinstance(next_state, State)
        assert isinstance(reward, float)


@pytest.mark.asyncio
class TestSchemaEnv:
    async def test_reset_and_step_generate_article_schema(self):
        env = SchemaEnv(site_id="test_site")
        state = await env.reset()
        assert isinstance(state, State)
        assert "current_schema_types" in state.metrics

        action = SEOAction(action_type="generate_article_schema", params={})
        next_state, reward, done, info = await env.step(action)
        assert isinstance(next_state, State)
        assert reward > 0
        assert info["schema_type_added"] == "article_schema"
