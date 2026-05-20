import os
from pydantic import BaseModel, Field


class LearningConfig(BaseModel):
    batch_size: int = 32
    min_buffer_size: int = 100
    train_interval: int = 3600
    model_save_path: str = "/tmp/ppo_model.pt"


class ExecutionConfig(BaseModel):
    high_confidence_threshold: float = 0.7
    medium_confidence_threshold: float = 0.4
    max_concurrent: int = 3
    rate_limit_per_hour: int = 10


class AppConfig(BaseModel):
    learning: LearningConfig = Field(default_factory=LearningConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    debug: bool = False
    environment: str = "production"


def load_config() -> AppConfig:
    return AppConfig(
        learning=LearningConfig(
            batch_size=int(os.getenv("LEARNING_BATCH_SIZE", "32")),
            min_buffer_size=int(os.getenv("LEARNING_MIN_BUFFER_SIZE", "100")),
            train_interval=int(os.getenv("LEARNING_TRAIN_INTERVAL", "3600")),
            model_save_path=os.getenv("LEARNING_MODEL_SAVE_PATH", "/tmp/ppo_model.pt"),
        ),
        execution=ExecutionConfig(
            high_confidence_threshold=float(os.getenv("EXECUTION_HIGH_CONFIDENCE", "0.7")),
            medium_confidence_threshold=float(os.getenv("EXECUTION_MEDIUM_CONFIDENCE", "0.4")),
            max_concurrent=int(os.getenv("EXECUTION_MAX_CONCURRENT", "3")),
            rate_limit_per_hour=int(os.getenv("EXECUTION_RATE_LIMIT", "10")),
        ),
        debug=os.getenv("DEBUG", "").lower() in ("true", "1", "yes"),
        environment=os.getenv("ENVIRONMENT", "production"),
    )
