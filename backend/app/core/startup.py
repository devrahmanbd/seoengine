import logging
import os
from typing import Any

from app.core.config import settings
from app.services.atropos.base_env import Registry
from app.services.atropos.environments import (
    TechnicalSEOEnv,
    ContentSEOEnv,
    KeywordResearchEnv,
    BacklinkEnv,
    CWVEnv,
    SchemaEnv,
)

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
]


def _check_env_vars() -> list[str]:
    warnings: list[str] = []
    for var in _REQUIRED_ENV_VARS:
        val = os.getenv(var) or getattr(settings, var.lower(), None)
        if not val:
            warnings.append(f"Required env var {var} is not set")
    return warnings


def _register_environments() -> list[str]:
    warnings: list[str] = []
    try:
        Registry.register("technical_seo", TechnicalSEOEnv)
        Registry.register("content_seo", ContentSEOEnv)
        Registry.register("keyword_research", KeywordResearchEnv)
        Registry.register("backlink", BacklinkEnv)
        Registry.register("cwv", CWVEnv)
        Registry.register("schema", SchemaEnv)
        logger.info("Registered %d environments: %s", len(Registry.list()), Registry.list())
    except Exception as e:
        warnings.append(f"Failed to register environments: {e}")
    return warnings


async def verify_system(app_state: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    # 1. DB connection ping
    db_ok = False
    try:
        from app.core.database import engine
        conn = engine.connect()
        conn.close()
        db_ok = True
    except Exception as e:
        warnings.append(f"Database connection check failed: {e}")

    if db_ok:
        logger.info("Database connection: OK")

    # 2. Model file exists
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "ppo_model.pt"
    )
    if os.path.exists(model_path):
        logger.info("PPO model file found at %s", model_path)
    else:
        warnings.append(f"PPO model file not found at {model_path}")

    # 3. All environments registered
    registered = Registry.list()
    expected = {"technical_seo", "content_seo", "keyword_research", "backlink", "cwv", "schema"}
    missing = expected - set(registered)
    if missing:
        warnings.append(f"Environments not registered: {missing}")
    else:
        logger.info("All %d expected environments are registered", len(registered))

    # 4. Required env vars
    env_warnings = _check_env_vars()
    warnings.extend(env_warnings)

    if not warnings:
        logger.info("System verification: ALL CHECKS PASSED")
    else:
        logger.warning("System verification completed with %d warnings", len(warnings))
        for w in warnings:
            logger.warning("  - %s", w)

    return warnings
