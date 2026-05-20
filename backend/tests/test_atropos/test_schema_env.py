import pytest
from app.services.atropos.environments.schema_env import SchemaEnv
from app.services.atropos.base_env import SEOAction


@pytest.fixture
def env():
    return SchemaEnv(site_id="test-site")


@pytest.mark.asyncio
async def test_reset_initializes_state(env):
    state = await env.reset()
    assert state.site_id == "test-site"
    assert "organization_schema" in state.metrics["current_schema_types"]
    assert len(state.metrics["schema_errors"]) == 2
    assert state.metrics["validation_pass_rate"] == 0.65
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_generate_article_schema(env):
    await env.reset()
    action = SEOAction(action_type="generate_article_schema", params={})
    state, reward, done, info = await env.step(action)
    assert "article_schema" in state.metrics["current_schema_types"]
    assert reward > 0


@pytest.mark.asyncio
async def test_generate_faq_schema(env):
    await env.reset()
    action = SEOAction(action_type="generate_faq_schema", params={})
    state, reward, done, info = await env.step(action)
    assert "faq_schema" in state.metrics["current_schema_types"]


@pytest.mark.asyncio
async def test_generate_breadcrumb(env):
    await env.reset()
    action = SEOAction(action_type="generate_breadcrumb", params={})
    state, reward, done, info = await env.step(action)
    assert "breadcrumb_schema" in state.metrics["current_schema_types"]


@pytest.mark.asyncio
async def test_generate_organization(env):
    await env.reset()
    action = SEOAction(action_type="generate_organization", params={})
    state, reward, done, info = await env.step(action)
    assert reward >= 0


@pytest.mark.asyncio
async def test_generate_local_business(env):
    await env.reset()
    action = SEOAction(action_type="generate_local_business", params={})
    state, reward, done, info = await env.step(action)
    assert "local_business_schema" in state.metrics["current_schema_types"]


@pytest.mark.asyncio
async def test_fix_schema_errors(env):
    await env.reset()
    action = SEOAction(action_type="fix_schema_errors", params={})
    state, reward, done, info = await env.step(action)
    assert len(state.metrics["schema_errors"]) == 0
    assert reward > 0


@pytest.mark.asyncio
async def test_episode_ends_at_max_steps(env):
    await env.reset()
    for i in range(env.max_steps):
        action = SEOAction(action_type="generate_article_schema", params={})
        state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_episode_ends_when_all_schemas_added_and_no_errors(env):
    await env.reset()
    env.data["current_schema_types"] = [
        "article_schema", "faq_schema", "breadcrumb_schema",
        "organization_schema", "local_business_schema",
    ]
    env.data["missing_types"] = []
    env.data["schema_errors"] = []
    env.data["schema_count"] = 5
    action = SEOAction(action_type="generate_article_schema", params={})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render(env):
    await env.reset()
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert rendered["site_id"] == "test-site"
    assert "coverage" in rendered
    assert "current_schema_types" in rendered
