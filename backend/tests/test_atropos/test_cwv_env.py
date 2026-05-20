import pytest
from app.services.atropos.environments.cwv_env import CWVEnv
from app.services.atropos.base_env import SEOAction


@pytest.fixture
def env():
    return CWVEnv(site_id="test-site")


@pytest.mark.asyncio
async def test_reset_initializes_state(env):
    state = await env.reset()
    assert state.site_id == "test-site"
    assert state.metrics["lcp_score"] == 0.45
    assert state.metrics["inp_score"] == 0.50
    assert state.metrics["cls_score"] == 0.35
    assert state.metrics["fcp_score"] == 0.55
    assert state.metrics["tbt_score"] == 0.40
    assert state.metrics["mobile_score"] == 52
    assert state.metrics["desktop_score"] == 68
    assert isinstance(state.features, list)
    assert state.timestamp > 0


@pytest.mark.asyncio
async def test_optimize_images(env):
    await env.reset()
    old_lcp = env.data["lcp_score"]
    action = SEOAction(action_type="optimize_images", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["lcp_score"] > old_lcp
    assert reward > 0


@pytest.mark.asyncio
async def test_lazy_load(env):
    await env.reset()
    old_cls = env.data["cls_score"]
    action = SEOAction(action_type="lazy_load", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["cls_score"] > old_cls
    assert reward > 0


@pytest.mark.asyncio
async def test_reduce_js(env):
    await env.reset()
    old_tbt = env.data["tbt_score"]
    action = SEOAction(action_type="reduce_js", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["tbt_score"] > old_tbt
    assert reward > 0


@pytest.mark.asyncio
async def test_optimize_fonts(env):
    await env.reset()
    old_fcp = env.data["fcp_score"]
    action = SEOAction(action_type="optimize_fonts", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["fcp_score"] > old_fcp
    assert reward > 0


@pytest.mark.asyncio
async def test_improve_server_response(env):
    await env.reset()
    old_fcp = env.data["fcp_score"]
    action = SEOAction(action_type="improve_server_response", params={})
    state, reward, done, info = await env.step(action)
    assert state.metrics["fcp_score"] > old_fcp
    assert reward > 0


@pytest.mark.asyncio
async def test_pass_rate_increases(env):
    await env.reset()
    state = await env.reset()
    initial_pass = env._compute_pass_rate()
    for action_type in ["optimize_images", "lazy_load", "reduce_js", "optimize_fonts", "improve_server_response"]:
        action = SEOAction(action_type=action_type, params={})
        state, reward, done, info = await env.step(action)
    final_pass = env._compute_pass_rate()
    assert final_pass >= initial_pass


@pytest.mark.asyncio
async def test_episode_ends_at_max_steps(env):
    await env.reset()
    for i in range(env.max_steps):
        action = SEOAction(action_type="optimize_images", params={})
        state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_episode_ends_when_all_pass(env):
    await env.reset()
    for metric in ["lcp_score", "inp_score", "cls_score", "fcp_score", "tbt_score"]:
        env.data[metric] = 1.0
    action = SEOAction(action_type="optimize_images", params={})
    state, reward, done, info = await env.step(action)
    assert done is True


@pytest.mark.asyncio
async def test_render(env):
    await env.reset()
    rendered = await env.render()
    assert isinstance(rendered, dict)
    assert rendered["site_id"] == "test-site"
    assert "lcp_score" in rendered
    assert "mobile_score" in rendered
