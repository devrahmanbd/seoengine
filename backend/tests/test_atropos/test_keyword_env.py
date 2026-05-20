import pytest
from app.services.atropos.environments.keyword_env import KeywordResearchEnv
from app.services.atropos.base_env import SEOAction


@pytest.fixture
def env():
    return KeywordResearchEnv(site_id="test-site")


@pytest.mark.asyncio
async def test_reset_initializes_state(env):
    state = await env.reset()
    assert state.site_id == "test-site"
    assert "seo tools" in state.metrics["current_rankings"]
    assert len(state.metrics["target_keywords"]) == 0
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_target_keyword_adds_and_improves_rank(env):
    await env.reset()
    old_rank = env.data["current_rankings"]["seo tools"]
    action = SEOAction(action_type="target_keyword", params={"keyword": "seo tools"}, confidence=0.8)
    state, reward, done, info = await env.step(action)
    assert "seo tools" in state.metrics["target_keywords"]
    assert state.metrics["current_rankings"]["seo tools"] <= old_rank
    assert reward > 0


@pytest.mark.asyncio
async def test_target_keyword_new_term(env):
    await env.reset()
    action = SEOAction(action_type="target_keyword", params={"keyword": "new keyword"})
    state, reward, done, info = await env.step(action)
    assert "new keyword" in state.metrics["target_keywords"]
    assert reward > 0


@pytest.mark.asyncio
async def test_expand_cluster(env):
    await env.reset()
    action = SEOAction(action_type="expand_cluster", params={"cluster": "seo", "terms": ["on-page seo", "technical seo"]})
    state, reward, done, info = await env.step(action)
    assert "on-page seo" in state.metrics["current_rankings"]
    assert "technical seo" in state.metrics["current_rankings"]
    assert reward > 0


@pytest.mark.asyncio
async def test_fill_content_gap(env):
    await env.reset()
    action = SEOAction(action_type="fill_content_gap", params={"keyword": "seo tools"})
    state, reward, done, info = await env.step(action)
    filled = [g for g in env.data["content_gaps"] if g["keyword"] == "seo tools"]
    assert filled
    assert filled[0].get("priority") == "filled"
    assert reward > 0


@pytest.mark.asyncio
async def test_optimize_for_intent(env):
    await env.reset()
    old_rank = env.data["current_rankings"]["seo tools"]
    action = SEOAction(action_type="optimize_for_intent", params={"keyword": "seo tools", "intent": "informational"})
    state, reward, done, info = await env.step(action)
    assert state.metrics["current_rankings"]["seo tools"] < old_rank
    assert reward > 0


@pytest.mark.asyncio
async def test_episode_ends_at_max_steps(env):
    await env.reset()
    for i in range(env.max_steps):
        action = SEOAction(action_type="target_keyword", params={"keyword": f"kw{i}"})
        state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_episode_ends_when_gaps_filled(env):
    await env.reset()
    env.data["content_gaps"][0]["priority"] = "filled"
    env.data["content_gaps"][1]["priority"] = "filled"
    remaining = [g for g in env.data["content_gaps"] if g.get("priority") == "high"]
    assert len(remaining) == 0
    action = SEOAction(action_type="fill_content_gap", params={"keyword": "link building"})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render(env):
    await env.reset()
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert rendered["site_id"] == "test-site"
    assert "current_rankings" in rendered
