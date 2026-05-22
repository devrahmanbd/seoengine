import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

DANGEROUS_ACTIONS: dict[str, str] = {
    "mass_redirect": "Redirecting many URLs at once can break existing traffic",
    "mass_delete": "Deleting pages or content permanently",
    "domain_change": "Changing domain or URL structure",
    "bulk_301": "Bulk 301 redirects can propagate incorrectly",
    "build_backlinks": "Building backlinks requires manual oversight to avoid penalties",
}


class SafetyMonitor:
    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self._rate_limits: dict[str, list[float]] = defaultdict(list)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._circuit_open_until: dict[str, float] = {}
        self._circuit_breaker_threshold = config.get("circuit_breaker_threshold", 5)
        self._circuit_breaker_timeout = config.get("circuit_breaker_timeout", 300)
        self._max_actions_per_minute = config.get("max_actions_per_minute", 10)
        self._max_actions_per_hour = config.get("max_actions_per_hour", 100)
        self._total_executions = 0
        self._total_blocks = 0

    async def check_rate_limit(self, site_id: str) -> bool:
        now = time.time()
        timestamps = self._rate_limits[site_id]
        self._rate_limits[site_id] = [t for t in timestamps if t > now - 3600]

        last_minute = [t for t in self._rate_limits[site_id] if t > now - 60]
        if len(last_minute) >= self._max_actions_per_minute:
            logger.warning("Rate limit per-minute exceeded for %s (%d/%d)", site_id, len(last_minute), self._max_actions_per_minute)
            return False

        if len(self._rate_limits[site_id]) >= self._max_actions_per_hour:
            logger.warning("Rate limit per-hour exceeded for %s (%d/%d)", site_id, len(self._rate_limits[site_id]), self._max_actions_per_hour)
            return False

        return True

    async def check_circuit_breaker(self, site_id: str) -> bool:
        if site_id in self._circuit_open_until:
            if time.time() < self._circuit_open_until[site_id]:
                remaining = int(self._circuit_open_until[site_id] - time.time())
                logger.warning("Circuit breaker open for %s (%ds remaining)", site_id, remaining)
                return False
            del self._circuit_open_until[site_id]
            logger.info("Circuit breaker reset for %s", site_id)
        return True

    async def record_execution(self, site_id: str, success: bool, error: str | None = None) -> None:
        self._total_executions += 1
        now = time.time()
        self._rate_limits[site_id].append(now)

        if not success:
            self._error_counts[site_id] += 1
            logger.warning("Execution failed for %s (error #%d): %s", site_id, self._error_counts[site_id], error)
            if self._error_counts[site_id] >= self._circuit_breaker_threshold:
                self._circuit_open_until[site_id] = now + self._circuit_breaker_timeout
                self._total_blocks += 1
                logger.warning(
                    "Circuit breaker TRIPPED for %s until %s",
                    site_id,
                    self._circuit_open_until[site_id],
                )
        else:
            self._error_counts[site_id] = max(0, self._error_counts[site_id] - 1)

    async def requires_confirmation(self, action_type: str) -> bool:
        return action_type in DANGEROUS_ACTIONS

    def get_confirmation_message(self, action_type: str) -> str:
        return DANGEROUS_ACTIONS.get(action_type, "Unknown dangerous action")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_executions": self._total_executions,
            "total_blocks": self._total_blocks,
            "active_circuit_breakers": list(self._circuit_open_until.keys()),
            "tracked_sites": list(self._rate_limits.keys()),
        }
