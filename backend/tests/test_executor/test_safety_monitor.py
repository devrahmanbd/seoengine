import pytest
import time
from unittest.mock import patch

from app.services.executor.safety_monitor import SafetyMonitor, DANGEROUS_ACTIONS


@pytest.fixture
def monitor():
    return SafetyMonitor()


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_allows_below_threshold(self, monitor):
        assert await monitor.check_rate_limit("site_1") is True

    @pytest.mark.asyncio
    async def test_blocks_after_minute_threshold(self, monitor):
        monitor._max_actions_per_minute = 3
        now = time.time()
        monitor._rate_limits["site_1"] = [now - 10, now - 20, now - 30]
        assert await monitor.check_rate_limit("site_1") is False

    @pytest.mark.asyncio
    async def test_blocks_after_hour_threshold(self, monitor):
        monitor._max_actions_per_minute = 100
        monitor._max_actions_per_hour = 3
        now = time.time()
        monitor._rate_limits["site_1"] = [now - 120, now - 180, now - 240]
        assert await monitor.check_rate_limit("site_1") is False

    @pytest.mark.asyncio
    async def test_cleans_old_timestamps(self, monitor):
        old = time.time() - 4000
        monitor._rate_limits["site_1"] = [old]
        await monitor.check_rate_limit("site_1")
        assert len(monitor._rate_limits["site_1"]) == 0


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_allows_when_closed(self, monitor):
        assert await monitor.check_circuit_breaker("site_1") is True

    @pytest.mark.asyncio
    async def test_trips_after_threshold_failures(self, monitor):
        monitor._circuit_breaker_threshold = 3
        now = time.time()
        with patch("time.time", return_value=now):
            for _ in range(3):
                await monitor.record_execution("site_1", False, "error")
        assert "site_1" in monitor._circuit_open_until
        assert monitor._total_blocks == 1

    @pytest.mark.asyncio
    async def test_blocks_when_open(self, monitor):
        monitor._circuit_open_until["site_1"] = time.time() + 300
        assert await monitor.check_circuit_breaker("site_1") is False

    @pytest.mark.asyncio
    async def test_resets_after_timeout(self, monitor):
        now = time.time()
        with patch("time.time", return_value=now):
            monitor._circuit_open_until["site_1"] = now - 1
            result = await monitor.check_circuit_breaker("site_1")
        assert result is True
        assert "site_1" not in monitor._circuit_open_until

    @pytest.mark.asyncio
    async def test_decrements_error_count_on_success(self, monitor):
        monitor._error_counts["site_1"] = 3
        await monitor.record_execution("site_1", True)
        assert monitor._error_counts["site_1"] == 2

    @pytest.mark.asyncio
    async def test_tracks_error_count_across_failures(self, monitor):
        await monitor.record_execution("site_1", False, "err")
        assert monitor._error_counts["site_1"] == 1
        assert monitor._total_executions == 1


class TestRequiresConfirmation:
    @pytest.mark.asyncio
    async def test_returns_true_for_dangerous_actions(self, monitor):
        assert await monitor.requires_confirmation("mass_redirect") is True
        assert await monitor.requires_confirmation("mass_delete") is True
        assert await monitor.requires_confirmation("domain_change") is True
        assert await monitor.requires_confirmation("bulk_301") is True
        assert await monitor.requires_confirmation("build_backlinks") is True

    @pytest.mark.asyncio
    async def test_returns_false_for_safe_actions(self, monitor):
        assert await monitor.requires_confirmation("fix_title") is False
        assert await monitor.requires_confirmation("optimize_content") is False
        assert await monitor.requires_confirmation("run_technical_audit") is False

    def test_dangerous_actions_dict_has_messages(self):
        for action, msg in DANGEROUS_ACTIONS.items():
            assert len(msg) > 0

    def test_get_confirmation_message_returns_message(self, monitor):
        msg = monitor.get_confirmation_message("mass_redirect")
        assert "traffic" in msg

    def test_get_confirmation_message_for_unknown(self, monitor):
        msg = monitor.get_confirmation_message("unknown")
        assert msg == "Unknown dangerous action"


class TestGetStats:
    def test_returns_all_stats(self, monitor):
        stats = monitor.get_stats()
        assert stats["total_executions"] == 0
        assert stats["total_blocks"] == 0
        assert stats["active_circuit_breakers"] == []
        assert stats["tracked_sites"] == []

    def test_after_some_activity(self, monitor):
        monitor._total_executions = 5
        monitor._total_blocks = 1
        monitor._circuit_open_until["site_1"] = time.time() + 100
        monitor._rate_limits["site_2"].append(time.time())

        stats = monitor.get_stats()
        assert stats["total_executions"] == 5
        assert stats["total_blocks"] == 1
        assert "site_1" in stats["active_circuit_breakers"]
        assert "site_2" in stats["tracked_sites"]
