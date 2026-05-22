import pytest
from unittest.mock import AsyncMock, patch
from app.atropos.environments.content_seo_env import ContentSEOEnv
from app.atropos.base_env import SEOAction


CONTENT_HTML = """<!DOCTYPE html>
<html>
<head><title>Content Test</title></head>
<body>
<h1>Main Topic Overview</h1>
<p>This is a comprehensive guide about search engine optimization and content marketing strategies for modern websites.</p>
<h2>Why SEO Matters</h2>
<p>Search engine optimization is crucial for driving organic traffic to your website. Studies show that 75% of users never scroll past the first page of search results.</p>
<h2>Content Strategy</h2>
<p>Developing a solid content strategy involves keyword research, competitor analysis, and understanding user intent for maximum impact.</p>
<h3>Keyword Research Methods</h3>
<p>There are several proven methods for keyword research including competitor analysis, search volume evaluation, and long-tail keyword discovery.</p>
<script type="application/ld+json">{"@context": "https://schema.org"}</script>
</body>
</html>"""


@pytest.fixture
def env():
    return ContentSEOEnv(site_id="https://example.com/page", max_steps=5)


@pytest.mark.asyncio
async def test_reset_sets_initial_state(env):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = CONTENT_HTML

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        state = await env.reset()

    assert state.site_id == "https://example.com/page"
    assert state.metrics["word_count"] > 0
    assert state.metrics["readability_score"] > 0
    assert state.metrics["entity_count"] > 0
    assert state.metrics["heading_structure_score"] > 0
    assert state.metrics["has_schema"] is True
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_reset_handles_fetch_error(env):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        state = await env.reset()

    assert state.metrics["word_count"] == 0
    assert state.metrics["readability_score"] == 0.0


@pytest.mark.asyncio
async def test_optimize_content_action(env):
    await _setup_env(env)
    old_wc = env.metrics["word_count"]
    action = SEOAction(action_type="optimize_content", params={"target_word_count": 2000})
    state, reward, done, info = await env.step(action)
    assert state.metrics["word_count"] >= old_wc
    assert info["action_result"]["applied"] is True


@pytest.mark.asyncio
async def test_add_entities_action(env):
    await _setup_env(env)
    old_entity_count = env.metrics["entity_count"]
    action = SEOAction(action_type="add_entities", params={"entities": ["Google", "Ahrefs", "Semrush"]})
    state, reward, done, info = await env.step(action)
    assert state.metrics["entity_count"] >= old_entity_count + 3


@pytest.mark.asyncio
async def test_add_entities_without_list(env):
    await _setup_env(env)
    old_entity_count = env.metrics["entity_count"]
    action = SEOAction(action_type="add_entities", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["entity_count"] == old_entity_count + 3


@pytest.mark.asyncio
async def test_improve_readability_action(env):
    await _setup_env(env)
    old_rd = env.metrics["readability_score"]
    action = SEOAction(action_type="improve_readability", params={"target_readability": 80.0})
    state, reward, done, info = await env.step(action)
    if old_rd < 80.0:
        assert state.metrics["readability_score"] > old_rd


@pytest.mark.asyncio
async def test_add_faq_schema_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="add_faq_schema", params={"faq_count": 5})
    state, reward, done, info = await env.step(action)
    assert state.metrics["has_faq"] is True


@pytest.mark.asyncio
async def test_restructure_headings_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="restructure_headings", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["heading_structure_score"] > 0


@pytest.mark.asyncio
async def test_step_done_when_score_high(env):
    env.current_step = 0
    env.metrics = {
        "word_count": 2000,
        "readability_score": 85.0,
        "keyword_density": 1.5,
        "target_keyword": "seo",
        "entity_count": 25,
        "heading_structure_score": 1.0,
        "has_faq": True,
        "has_schema": True,
        "content_score": 0.85,
    }
    action = SEOAction(action_type="optimize_content", params={"target_word_count": 2000})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render_returns_metrics(env):
    await _setup_env(env)
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert "word_count" in rendered
    assert "content_score" in rendered


async def _setup_env(env):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = CONTENT_HTML

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await env.reset()
