import pytest
from app.services.atropos.environments.backlink_env import BacklinkEnv
from app.services.atropos.base_env import SEOAction


@pytest.fixture
def env():
    return BacklinkEnv(site_id="test-site")


@pytest.mark.asyncio
async def test_reset_initializes_state(env):
    state = await env.reset()
    assert state.site_id == "test-site"
    assert state.metrics["backlink_count"] == 127
    assert state.metrics["referring_domains"] == 34
    assert state.metrics["domain_authority"] == 28.5
    assert state.metrics["anchor_text_diversity"] == 0.45
    assert state.metrics["toxic_links"] == 8
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_earn_backlink_improves_metrics(env):
    await env.reset()
    old_da = env.data["domain_authority"]
    action = SEOAction(action_type="earn_backlink", params={"quality": "high"}, confidence=0.9)
    state, reward, done, info = await env.step(action)
    assert state.metrics["domain_authority"] > old_da
    assert reward > 0
    assert info["quality"] == "high"


@pytest.mark.asyncio
async def test_earn_backlink_low_quality(env):
    await env.reset()
    action = SEOAction(action_type="earn_backlink", params={"quality": "low"})
    state, reward, done, info = await env.step(action)
    assert reward > 0


@pytest.mark.asyncio
async def test_fix_broken_links(env):
    await env.reset()
    old_broken = env.data["broken_outbound_links"]
    action = SEOAction(action_type="fix_broken_links", params={"count": 5})
    state, reward, done, info = await env.step(action)
    assert state.metrics["broken_outbound_links"] < old_broken
    assert reward > 0


@pytest.mark.asyncio
async def test_diversify_anchors(env):
    await env.reset()
    old_diversity = env.data["anchor_text_diversity"]
    action = SEOAction(action_type="diversify_anchors", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["anchor_text_diversity"] >= old_diversity


@pytest.mark.asyncio
async def test_disavow_toxic(env):
    await env.reset()
    old_toxic = env.data["toxic_links"]
    action = SEOAction(action_type="disavow_toxic", params={"count": 3})
    state, reward, done, info = await env.step(action)
    assert state.metrics["toxic_links"] < old_toxic
    assert reward > 0


@pytest.mark.asyncio
async def test_episode_ends_at_max_steps(env):
    await env.reset()
    for i in range(env.max_steps):
        action = SEOAction(action_type="earn_backlink", params={"quality": "medium"})
        state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_episode_ends_when_da_high(env):
    await env.reset()
    env.data["domain_authority"] = 70.0
    action = SEOAction(action_type="earn_backlink", params={"quality": "high"})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render(env):
    await env.reset()
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert rendered["site_id"] == "test-site"
    assert rendered["domain_authority"] == 28.5
