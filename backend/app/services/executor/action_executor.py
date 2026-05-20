import logging
from typing import Any

from app.services.atropos.base_env import Registry, SEOAction

logger = logging.getLogger(__name__)

ACTION_ENV_MAP: dict[str, str] = {
    "fix_title": "technical_seo",
    "fix_meta": "technical_seo",
    "add_schema": "technical_seo",
    "fix_headings": "technical_seo",
    "fix_images": "technical_seo",
    "improve_cwv": "technical_seo",
    "generate_article_schema": "schema",
    "generate_faq_schema": "schema",
    "generate_breadcrumb": "schema",
    "generate_organization": "schema",
    "generate_local_business": "schema",
    "fix_schema_errors": "schema",
    "optimize_content": "content_seo",
    "add_entities": "content_seo",
    "improve_readability": "content_seo",
    "add_faq_schema": "content_seo",
    "restructure_headings": "content_seo",
    "target_keyword": "keyword_research",
    "expand_cluster": "keyword_research",
    "fill_content_gap": "keyword_research",
    "optimize_for_intent": "keyword_research",
    "optimize_images": "cwv",
    "lazy_load": "cwv",
    "reduce_js": "cwv",
    "optimize_fonts": "cwv",
    "improve_server_response": "cwv",
    "earn_backlink": "backlink",
    "fix_broken_links": "backlink",
    "diversify_anchors": "backlink",
    "disavow_toxic": "backlink",
    "run_technical_audit": "technical_seo",
}


class ActionExecutor:
    def __init__(self, env_registry: Registry) -> None:
        self._registry = env_registry

    async def execute(self, website_id: str, action_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        env_name = ACTION_ENV_MAP.get(action_type)

        if not env_name:
            return {
                "status": "error",
                "action_type": action_type,
                "error": f"No environment mapped for action type '{action_type}'",
            }

        try:
            env = self._registry.create(env_name, site_id=website_id)
        except ValueError as e:
            return {
                "status": "error",
                "action_type": action_type,
                "error": f"Environment '{env_name}' not registered: {e}",
            }

        try:
            seo_action = SEOAction(action_type=action_type, params=params)
            state, reward, done, info = await env.step(seo_action)
            return {
                "status": "success",
                "action_type": action_type,
                "reward": reward,
                "done": done,
                "info": info,
                "state_metrics": dict(state.metrics) if hasattr(state, "metrics") else {},
            }
        except Exception as e:
            logger.exception("Failed to execute action '%s' for %s via %s", action_type, website_id, env_name)
            return {
                "status": "error",
                "action_type": action_type,
                "error": str(e),
            }
        finally:
            try:
                await env.close()
            except Exception:
                pass

    async def execute_batch(self, website_id: str, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for action in actions:
            result = await self.execute(
                website_id=website_id,
                action_type=action.get("action_type", ""),
                params=action.get("params"),
            )
            results.append(result)
        return results
