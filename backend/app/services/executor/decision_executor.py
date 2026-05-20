import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.services.executor.action_executor import ActionExecutor
from app.services.executor.safety_monitor import SafetyMonitor

if TYPE_CHECKING:
    from app.services.learning.decision_integrator import DecisionIntegrator
    from app.services.growth.action_scheduler import ActionScheduler, ScheduledAction
    from app.services.atropos.base_env import Registry
    from app.services.learning.feedback_loop import FeedbackLoop

logger = logging.getLogger(__name__)

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MEDIUM = 0.4


class DecisionExecutor:
    def __init__(
        self,
        integrator: "DecisionIntegrator",
        scheduler: "ActionScheduler",
        env_registry: "Registry",
        feedback_loop: "FeedbackLoop",
        config: dict[str, Any] | None = None,
    ) -> None:
        self._integrator = integrator
        self._scheduler = scheduler
        self._registry = env_registry
        self._feedback = feedback_loop
        self._config = config or {}
        self._action_executor = ActionExecutor(env_registry)
        self._safety = SafetyMonitor(self._config.get("safety"))
        self._scheduled_actions: list[tuple[str, "ScheduledAction"]] = []
        self._execution_history: list[dict[str, Any]] = []

    async def execute_decision(
        self,
        website_id: str,
        decision: dict[str, Any],
        urgent: bool = False,
    ) -> dict[str, Any]:
        action_type = decision.get("action_type", "unknown")
        confidence = float(decision.get("confidence", 0.0))

        gate = self._check_confidence_gate(action_type, confidence, urgent)
        if gate["action"] == "block":
            return {
                "status": "blocked",
                "action_type": action_type,
                "confidence": confidence,
                "gate": gate,
            }

        if not await self._safety.check_rate_limit(website_id):
            return {
                "status": "rate_limited",
                "action_type": action_type,
                "confidence": confidence,
                "gate": gate,
            }

        if not await self._safety.check_circuit_breaker(website_id):
            return {
                "status": "circuit_open",
                "action_type": action_type,
                "confidence": confidence,
                "gate": gate,
            }

        if await self._safety.requires_confirmation(action_type):
            return {
                "status": "needs_confirmation",
                "action_type": action_type,
                "confidence": confidence,
                "gate": gate,
                "message": self._safety.get_confirmation_message(action_type),
            }

        params = decision.get("params", {})
        result = await self._action_executor.execute(website_id, action_type, params)

        success = result.get("status") == "success"
        await self._safety.record_execution(website_id, success, result.get("error"))

        if success:
            try:
                task_result: dict[str, Any] = {
                    "website_id": website_id,
                    "task_type": action_type,
                    "status": "completed",
                    "reward": result.get("reward", 0.0),
                    "info": result.get("info", {}),
                }
                task_id = f"{website_id}_{action_type}_{uuid.uuid4().hex[:8]}"
                await self._feedback.on_task_complete(task_id, task_result)
            except Exception as e:
                logger.warning("Failed to record feedback for %s/%s: %s", website_id, action_type, e)

        execution: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "website_id": website_id,
            "action_type": action_type,
            "confidence": confidence,
            "gate": gate,
            "result": result,
        }
        self._execution_history.append(execution)

        return execution

    async def execute_top_actions(
        self,
        website_id: str,
        state: dict[str, Any],
        top_k: int = 3,
    ) -> dict[str, Any]:
        recommendations = await self._integrator.recommend_actions(state, top_k)

        results: list[dict[str, Any]] = []
        for rec in recommendations:
            decision = {
                "action_type": rec["action_type"],
                "confidence": rec["confidence"],
                "params": {},
            }
            result = await self.execute_decision(website_id, decision)
            results.append(result)

        return {
            "website_id": website_id,
            "total_requested": len(recommendations),
            "executed": len(results),
            "results": results,
        }

    async def execute_scheduled_actions(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        due: list[tuple[int, tuple[str, "ScheduledAction"]]] = []
        remaining: list[tuple[str, "ScheduledAction"]] = []

        for idx, (site_id, action) in enumerate(self._scheduled_actions):
            if action.status == "pending" and action.scheduled_at and action.scheduled_at <= now:
                due.append((idx, (site_id, action)))
            else:
                remaining.append((site_id, action))

        self._scheduled_actions = remaining

        results: list[dict[str, Any]] = []
        for idx, (site_id, action) in due:
            result = await self.execute_decision(
                site_id,
                {
                    "action_type": action.opportunity.action_type,
                    "confidence": action.priority_score,
                    "params": {},
                },
                urgent=True,
            )
            results.append(result)

        logger.info("Executed %d scheduled actions", len(results))
        return results

    def add_scheduled_actions(self, website_id: str, actions: list["ScheduledAction"]) -> None:
        for action in actions:
            self._scheduled_actions.append((website_id, action))
        logger.info("Added %d scheduled actions for %s", len(actions), website_id)

    def _check_confidence_gate(
        self,
        action_type: str,
        confidence: float,
        urgent: bool = False,
    ) -> dict[str, Any]:
        if confidence >= CONFIDENCE_HIGH:
            return {
                "action": "execute",
                "level": "high",
                "confidence": confidence,
                "reason": "High confidence - executing immediately",
            }
        elif confidence >= CONFIDENCE_MEDIUM:
            return {
                "action": "execute_monitored",
                "level": "medium",
                "confidence": confidence,
                "reason": "Medium confidence - executing with monitoring",
            }
        elif urgent:
            return {
                "action": "execute_monitored",
                "level": "low",
                "confidence": confidence,
                "reason": "Low confidence but urgent - executing with monitoring",
            }
        else:
            return {
                "action": "block",
                "level": "low",
                "confidence": confidence,
                "reason": "Low confidence - queued for review",
            }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_executions": len(self._execution_history),
            "scheduled_actions_pending": len(self._scheduled_actions),
            "safety": self._safety.get_stats(),
            "recent_executions": self._execution_history[-10:],
        }
