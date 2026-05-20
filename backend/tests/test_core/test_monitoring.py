import pytest
import asyncio

from app.core.monitoring import MetricsCollector


@pytest.fixture
def collector():
    return MetricsCollector()


class TestRecordTraining:
    @pytest.mark.asyncio
    async def test_records_single_training_run(self, collector):
        await collector.record_training({"avg_reward": 0.85})
        assert collector.metrics["training"]["count"] == 1
        assert collector.metrics["training"]["total_reward"] == 0.85
        assert collector.metrics["training"]["avg_reward"] == 0.85

    @pytest.mark.asyncio
    async def test_multiple_training_runs_averages_correctly(self, collector):
        await collector.record_training({"avg_reward": 0.8})
        await collector.record_training({"avg_reward": 0.9})
        assert collector.metrics["training"]["count"] == 2
        assert collector.metrics["training"]["total_reward"] == pytest.approx(1.7)
        assert collector.metrics["training"]["avg_reward"] == pytest.approx(0.85)


class TestRecordExecution:
    @pytest.mark.asyncio
    async def test_records_successful_execution(self, collector):
        await collector.record_execution("fix_title", True, 1.0, 100)
        assert collector.metrics["executions"]["count"] == 1
        assert collector.metrics["executions"]["successes"] == 1
        assert collector.metrics["executions"]["failures"] == 0
        assert collector.metrics["executions"]["total_reward"] == 1.0

    @pytest.mark.asyncio
    async def test_records_failed_execution(self, collector):
        await collector.record_execution("fix_title", False, 0.0, 50)
        assert collector.metrics["executions"]["failures"] == 1
        assert collector.metrics["executions"]["successes"] == 0

    @pytest.mark.asyncio
    async def test_avg_duration_across_executions(self, collector):
        await collector.record_execution("fix_title", True, 1.0, 100)
        await collector.record_execution("optimize_content", True, 1.0, 200)
        assert collector.metrics["executions"]["avg_duration_ms"] == 150.0


class TestGetAllMetrics:
    @pytest.mark.asyncio
    async def test_returns_all_metric_categories(self, collector):
        await collector.record_training({"avg_reward": 0.5})
        await collector.record_execution("fix_title", True, 1.0, 100)

        metrics = await collector.get_all_metrics()
        assert "training" in metrics
        assert "executions" in metrics
        assert "api_calls" in metrics
        assert "uptime_seconds" in metrics
        assert metrics["training"]["count"] == 1
        assert metrics["executions"]["count"] == 1

    @pytest.mark.asyncio
    async def test_uptime_increases_over_time(self, collector):
        m1 = await collector.get_all_metrics()
        await asyncio.sleep(0.01)
        m2 = await collector.get_all_metrics()
        assert m2["uptime_seconds"] > m1["uptime_seconds"]


class TestGetHealthStatus:
    @pytest.mark.asyncio
    async def test_empty_collector_returns_ok(self, collector):
        health = await collector.get_health_status()
        assert health["status"] == "ok"
        assert health["training_runs"] == 0
        assert health["executions"] == 0
        assert health["execution_success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_with_executions_returns_correct_success_rate(self, collector):
        await collector.record_execution("a", True, 1.0, 100)
        await collector.record_execution("b", False, 0.0, 50)
        health = await collector.get_health_status()
        assert health["executions"] == 2
        assert health["execution_success_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_uptime_and_training(self, collector):
        await collector.record_training({"avg_reward": 0.7})
        health = await collector.get_health_status()
        assert health["training_runs"] == 1
        assert health["uptime_seconds"] > 0
