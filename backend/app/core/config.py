from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import field_validator
import logging
import os


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://rahman@localhost:5432/zenseo"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Security
    secret_key: str = "your-secret-key-change-in-production"

    # Environment
    environment: str = "production"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in ("your-secret-key-change-in-production", "zenseo-secret-key-change-in-production"):
            logger.warning(
                "SECRET_KEY is using a default/dev value. Set SECRET_KEY env var "
                "to a secure random value for production."
            )
        return v

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
