import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from app.executor.decision_executor import DecisionExecutor


@pytest.fixture
def mock_safety():
    safety = MagicMock()
    safety.check_rate_limit = AsyncMock(return_value=True)
    safety.check_circuit_breaker = AsyncMock(return_value=True)
    safety.requires_confirmation = AsyncMock(return_value=False)
    safety.record_execution = AsyncMock()
    safety.get_stats = MagicMock(return_value={
        "total_executions": 0, "total_blocks": 0,
        "active_circuit_breakers": [], "tracked_sites": [],
    })
    return safety


@pytest.fixture
def mock_action_executor():
    ae = MagicMock()
    ae.execute = AsyncMock(return_value={
        "status": "success", "reward": 1.0, "info": {},
        "action_type": "fix_title", "done": False, "state_metrics": {},
    })
    return ae


@pytest.fixture
def executor(mock_safety, mock_action_executor):
    integrator = MagicMock()
    scheduler = MagicMock()
    registry = MagicMock()
    feedback = MagicMock()
    feedback.on_task_complete = AsyncMock()

    de = DecisionExecutor(integrator, scheduler, registry, feedback)
    de._safety = mock_safety
    de._action_executor = mock_action_executor
    return de


class TestCheckConfidenceGate:
    def test_high_confidence_returns_execute(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.9)
        assert gate["action"] == "execute"
        assert gate["level"] == "high"

    def test_medium_confidence_returns_monitored(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.5)
        assert gate["action"] == "execute_monitored"
        assert gate["level"] == "medium"

    def test_low_confidence_blocked(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.3)
        assert gate["action"] == "block"
        assert gate["level"] == "low"

    def test_low_confidence_urgent_returns_monitored(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.3, urgent=True)
        assert gate["action"] == "execute_monitored"
        assert gate["level"] == "low"

    def test_zero_confidence_blocked(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.0)
        assert gate["action"] == "block"

    def test_high_confidence_boundary(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.7)
        assert gate["action"] == "execute"

    def test_medium_confidence_boundary(self, executor):
        gate = executor._check_confidence_gate("fix_title", 0.4)
        assert gate["action"] == "execute_monitored"


class TestExecuteDecision:
    @pytest.mark.asyncio
    async def test_high_confidence_executes_action(self, executor, mock_action_executor):
        decision = {"action_type": "fix_title", "confidence": 0.9, "params": {"key": "value"}}
        result = await executor.execute_decision("site_1", decision)

        mock_action_executor.execute.assert_awaited_once_with("site_1", "fix_title", {"key": "value"})
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_low_confidence_blocked(self, executor):
        decision = {"action_type": "fix_title", "confidence": 0.3}
        result = await executor.execute_decision("site_1", decision)
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_rate_limited(self, executor, mock_safety):
        mock_safety.check_rate_limit.return_value = False
        decision = {"action_type": "fix_title", "confidence": 0.9}
        result = await executor.execute_decision("site_1", decision)
        assert result["status"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_circuit_open(self, executor, mock_safety):
        mock_safety.check_circuit_breaker.return_value = False
        decision = {"action_type": "fix_title", "confidence": 0.9}
        result = await executor.execute_decision("site_1", decision)
        assert result["status"] == "circuit_open"

    @pytest.mark.asyncio
    async def test_needs_confirmation_for_dangerous_action(self, executor, mock_safety):
        mock_safety.requires_confirmation.return_value = True
        mock_safety.get_confirmation_message.return_value = "Manual review needed"
        decision = {"action_type": "mass_redirect", "confidence": 0.9}
        result = await executor.execute_decision("site_1", decision)
        assert result["status"] == "needs_confirmation"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_records_safety_and_feedback_on_success(self, executor, mock_safety):
        feedback = executor._feedback
        feedback.on_task_complete = AsyncMock()

        decision = {"action_type": "fix_title", "confidence": 0.9}
        result = await executor.execute_decision("site_1", decision)

        assert result["result"]["status"] == "success"
        mock_safety.record_execution.assert_awaited_once_with("site_1", True, None)
        feedback.on_task_complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tracks_execution_history(self, executor):
        decision = {"action_type": "fix_title", "confidence": 0.9}
        await executor.execute_decision("site_1", decision)
        assert len(executor._execution_history) == 1
        assert executor._execution_history[0]["website_id"] == "site_1"
        assert executor._execution_history[0]["action_type"] == "fix_title"

    @pytest.mark.asyncio
    async def test_medium_confidence_executes_with_monitoring(self, executor, mock_action_executor):
        decision = {"action_type": "optimize_content", "confidence": 0.5}
        result = await executor.execute_decision("site_1", decision)
        assert result["result"]["status"] == "success"
        assert result["gate"]["level"] == "medium"

    @pytest.mark.asyncio
    async def test_passes_params_to_action_executor(self, executor, mock_action_executor):
        decision = {"action_type": "fix_title", "confidence": 0.9, "params": {"target": "homepage"}}
        await executor.execute_decision("site_1", decision)
        mock_action_executor.execute.assert_awaited_once_with("site_1", "fix_title", {"target": "homepage"})

    @pytest.mark.asyncio
    async def test_empty_params_defaults_to_empty_dict(self, executor, mock_action_executor):
        decision = {"action_type": "fix_title", "confidence": 0.9}
        await executor.execute_decision("site_1", decision)
        mock_action_executor.execute.assert_awaited_once_with("site_1", "fix_title", {})


class TestExecuteScheduledActions:
    @pytest.mark.asyncio
    async def test_processes_due_pending_actions(self, executor):
        mock_opp = MagicMock()
        mock_opp.action_type = "fix_title"

        action = MagicMock()
        action.status = "pending"
        action.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        action.priority_score = 0.8
        action.opportunity = mock_opp

        executor._scheduled_actions = [("site_1", action)]

        results = await executor.execute_scheduled_actions()
        assert len(results) == 1
        assert len(executor._scheduled_actions) == 0

    @pytest.mark.asyncio
    async def test_empty_scheduled_actions_returns_empty(self, executor):
        results = await executor.execute_scheduled_actions()
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_non_pending_actions(self, executor):
        mock_opp = MagicMock()
        mock_opp.action_type = "fix_title"

        action = MagicMock()
        action.status = "completed"
        action.scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        action.priority_score = 0.8
        action.opportunity = mock_opp

        executor._scheduled_actions = [("site_1", action)]

        results = await executor.execute_scheduled_actions()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_keeps_future_actions(self, executor):
        mock_opp = MagicMock()
        mock_opp.action_type = "fix_title"

        action = MagicMock()
        action.status = "pending"
        action.scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
        action.priority_score = 0.8
        action.opportunity = mock_opp

        executor._scheduled_actions = [("site_1", action)]

        results = await executor.execute_scheduled_actions()
        assert len(results) == 0
        assert len(executor._scheduled_actions) == 1


class TestGetStats:
    def test_returns_execution_and_safety_stats(self, executor):
        executor._execution_history = [{"dummy": True}]
        stats = executor.get_stats()
        assert stats["total_executions"] == 1
        assert "safety" in stats
        assert "recent_executions" in stats
        assert len(stats["recent_executions"]) == 1
