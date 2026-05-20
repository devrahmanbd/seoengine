import pytest
from app.core.config_provider import AppConfig, LearningConfig, ExecutionConfig


class TestDefaultValues:
    def test_app_config_defaults(self):
        config = AppConfig()
        assert config.debug is False
        assert config.environment == "production"
        assert isinstance(config.learning, LearningConfig)
        assert isinstance(config.execution, ExecutionConfig)

    def test_learning_config_defaults(self):
        config = LearningConfig()
        assert config.batch_size == 32
        assert config.min_buffer_size == 100
        assert config.train_interval == 3600
        assert config.model_save_path == "/tmp/ppo_model.pt"

    def test_execution_config_defaults(self):
        config = ExecutionConfig()
        assert config.high_confidence_threshold == 0.7
        assert config.medium_confidence_threshold == 0.4
        assert config.max_concurrent == 3
        assert config.rate_limit_per_hour == 10


class TestEnvVarOverrides:
    def test_learning_env_vars_override(self, monkeypatch):
        monkeypatch.setenv("LEARNING_BATCH_SIZE", "64")
        monkeypatch.setenv("LEARNING_MIN_BUFFER_SIZE", "200")
        monkeypatch.setenv("LEARNING_TRAIN_INTERVAL", "7200")
        monkeypatch.setenv("LEARNING_MODEL_SAVE_PATH", "/models/test.pt")

        from app.core.config_provider import load_config
        config = load_config()
        assert config.learning.batch_size == 64
        assert config.learning.min_buffer_size == 200
        assert config.learning.train_interval == 7200
        assert config.learning.model_save_path == "/models/test.pt"

    def test_execution_env_vars_override(self, monkeypatch):
        monkeypatch.setenv("EXECUTION_HIGH_CONFIDENCE", "0.8")
        monkeypatch.setenv("EXECUTION_MEDIUM_CONFIDENCE", "0.5")
        monkeypatch.setenv("EXECUTION_MAX_CONCURRENT", "5")
        monkeypatch.setenv("EXECUTION_RATE_LIMIT", "20")

        from app.core.config_provider import load_config
        config = load_config()
        assert config.execution.high_confidence_threshold == 0.8
        assert config.execution.medium_confidence_threshold == 0.5
        assert config.execution.max_concurrent == 5
        assert config.execution.rate_limit_per_hour == 20

    def test_debug_env_var(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "true")
        from app.core.config_provider import load_config
        config = load_config()
        assert config.debug is True

    def test_environment_env_var(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        from app.core.config_provider import load_config
        config = load_config()
        assert config.environment == "development"
        assert config.debug is False


class TestNestedConfigAccess:
    def test_nested_attributes_accessible(self):
        config = AppConfig()
        assert config.learning.batch_size == 32
        assert config.execution.high_confidence_threshold == 0.7
        assert config.execution.max_concurrent == 3

    def test_pydantic_dump(self):
        config = AppConfig()
        dumped = config.model_dump()
        assert "learning" in dumped
        assert "execution" in dumped
        assert "debug" in dumped
        assert "environment" in dumped
