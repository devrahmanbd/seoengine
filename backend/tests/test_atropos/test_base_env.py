import pytest
from app.services.atropos.base_env import SEOAction, State, SEOEnvironment, Registry
from app.services.atropos.environments.technical_seo_env import TechnicalSEOEnv


class TestSEOAction:
    def test_creation_and_defaults(self):
        action = SEOAction(action_type="fix_title", params={"title": "Test"})
        assert action.action_type == "fix_title"
        assert action.params == {"title": "Test"}
        assert action.confidence == 0.0

    def test_with_confidence(self):
        action = SEOAction(action_type="test", params={}, confidence=0.8)
        assert action.confidence == 0.8


class TestState:
    def test_creation(self):
        state = State(
            site_id="test_site",
            metrics={"score": 0.5},
            timestamp=123.0,
        )
        assert state.site_id == "test_site"
        assert state.metrics == {"score": 0.5}
        assert state.timestamp == 123.0
        assert state.features is None

    def test_with_features(self):
        state = State(site_id="s", metrics={}, timestamp=1.0, features=[0.1, 0.2])
        assert state.features == [0.1, 0.2]


class TestSEOEnvironment:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            SEOEnvironment()


class TestRegistry:
    def setup_method(self):
        Registry._environments = {}

    def test_register_and_create(self):
        Registry.register("technical", TechnicalSEOEnv)
        env = Registry.create("technical", site_id="https://example.com")
        assert isinstance(env, TechnicalSEOEnv)

    def test_list(self):
        Registry.register("technical", TechnicalSEOEnv)
        names = Registry.list()
        assert "technical" in names

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            Registry.create("unknown")

    def test_created_env_has_reset_and_step(self):
        Registry.register("technical", TechnicalSEOEnv)
        env = Registry.create("technical", site_id="https://example.com")
        assert hasattr(env, "reset")
        assert callable(env.reset)
        assert hasattr(env, "step")
        assert callable(env.step)
