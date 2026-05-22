import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.atropos.environments.technical_seo_env import TechnicalSEOEnv
from app.atropos.base_env import SEOAction


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Test Page Title</title>
<meta name="description" content="A meta description for testing that is long enough to be valid.">
<meta name="viewport" content="width=device-width">
<meta property="og:title" content="Test OG">
<meta property="og:description" content="OG desc">
<meta property="og:image" content="https://example.com/image.jpg">
<link rel="canonical" href="https://example.com/">
</head>
<body>
<h1>Main Heading</h1>
<p>Some content.</p>
<a href="/internal-link">Internal</a>
<a href="https://external.com">External</a>
<img src="test.jpg" alt="Has alt">
<img src="noalt.jpg" alt="">
<script type="application/ld+json">{"@context": "https://schema.org"}</script>
</body>
</html>"""


@pytest.fixture
def env():
    return TechnicalSEOEnv(site_id="https://example.com", max_steps=5)


@pytest.mark.asyncio
async def test_reset_sets_initial_state(env):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_HTML

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        state = await env.reset()

    assert state.site_id == "https://example.com"
    assert state.metrics["status_code"] == 200
    assert state.metrics["title"] == "Test Page Title"
    assert state.metrics["h1_count"] == 1
    assert state.metrics["schema_count"] == 1
    assert state.metrics["has_canonical"] is True
    assert state.metrics["has_viewport"] is True
    assert state.metrics["og_title"] is True
    assert state.metrics["og_description"] is True
    assert state.metrics["og_image"] is True
    assert state.metrics["internal_links"] == 1
    assert state.metrics["external_links"] == 1
    assert state.metrics["images_total"] == 2
    assert state.metrics["images_missing_alt"] == 1
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_reset_handles_fetch_error(env):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        state = await env.reset()

    assert state.metrics["status_code"] == 0
    assert state.metrics["response_time_ms"] == 99999.0


@pytest.mark.asyncio
async def test_fix_title_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="fix_title", params={"title": "New Optimized Title"})
    state, reward, done, info = await env.step(action)
    assert state.metrics["title"] == "New Optimized Title"
    assert state.metrics["title_length"] == len("New Optimized Title")


@pytest.mark.asyncio
async def test_fix_meta_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="fix_meta", params={"description": "A brand new meta description for the page that is sufficiently long to pass validation."})
    state, reward, done, info = await env.step(action)
    assert state.metrics["meta_description"] == action.params["description"]


@pytest.mark.asyncio
async def test_add_schema_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="add_schema", params={"schema_type": "FAQPage"})
    state, reward, done, info = await env.step(action)
    assert state.metrics["schema_count"] >= 1


@pytest.mark.asyncio
async def test_fix_headings_action(env):
    await _setup_env(env)
    action = SEOAction(action_type="fix_headings", params={"h1_count": 1})
    state, reward, done, info = await env.step(action)
    assert state.metrics["h1_count"] == 1


@pytest.mark.asyncio
async def test_fix_images_action_fixes_missing_alt(env):
    await _setup_env(env)
    assert env.metrics["images_missing_alt"] > 0
    action = SEOAction(action_type="fix_images", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["images_missing_alt"] == 0


@pytest.mark.asyncio
async def test_improve_cwv_action(env):
    await _setup_env(env)
    env.metrics["response_time_ms"] = 500.0
    old_rt = env.metrics["response_time_ms"]
    action = SEOAction(action_type="improve_cwv", params={"suggestions": ["compress", "cache"]})
    state, reward, done, info = await env.step(action)
    assert state.metrics["response_time_ms"] < old_rt
    assert state.metrics["response_time_ms"] >= 50.0


@pytest.mark.asyncio
async def test_step_done_when_score_high(env):
    await _setup_env(env)
    env.metrics["status_code"] = 200
    env.metrics["title_length"] = 55
    env.metrics["meta_description_length"] = 155
    env.metrics["h1_count"] = 1
    env.metrics["schema_count"] = 1
    env.metrics["images_total"] = 0
    env.metrics["has_canonical"] = True
    env.metrics["og_title"] = True
    env.metrics["og_description"] = True
    env.metrics["og_image"] = True
    env.metrics["has_viewport"] = True
    env.metrics["response_time_ms"] = 100
    env.metrics["internal_links"] = 10
    env.metrics["external_links"] = 5
    env.metrics["technical_score"] = 0.9
    action = SEOAction(action_type="fix_title", params={"title": "x"})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render_returns_metrics(env):
    await _setup_env(env)
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert "title" in rendered
    assert "technical_score" in rendered


async def _setup_env(env):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_HTML

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await env.reset()


@pytest.mark.asyncio
async def test_max_steps_ends_episode(env):
    await _setup_env(env)
    for i in range(5):
        action = SEOAction(action_type="fix_title", params={"title": f"Title {i}"})
        state, reward, done, info = await env.step(action)
    assert done is True
