import logging
from typing import Any

logger = logging.getLogger(__name__)


class PolicyServer:
    def __init__(self, trainer: Any = None, integrator: Any = None):
        self._trainer = trainer
        self._integrator = integrator

    async def get_recommendations(self, site_state: dict, top_k: int = 3) -> list[dict]:
        if self._integrator is None:
            return []
        return await self._integrator.recommend_actions(site_state, top_k=top_k)

    async def get_policy_info(self) -> dict:
        info: dict[str, Any] = {
            "model_loaded": self._trainer is not None,
            "training_steps": 0,
            "action_registry_size": 0,
        }
        if self._trainer is not None:
            info["training_steps"] = self._trainer._train_step
            info["action_registry_size"] = len(self._trainer._action_registry)
        return info

    async def reload_policy(self) -> bool:
        if self._trainer is None:
            return False
        try:
            from app.core.config import settings
            import os
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "ppo_model.pt")
            if os.path.exists(model_path):
                self._trainer.load(model_path)
                logger.info("Policy model reloaded from %s", model_path)
                return True
            logger.warning("No model file found at %s", model_path)
            return False
        except Exception as e:
            logger.error("Failed to reload policy: %s", e)
            return False
