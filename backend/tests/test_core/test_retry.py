import pytest
from unittest.mock import AsyncMock

from app.core.retry import retry_with_backoff


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_returns_on_first_success(self):
        func = AsyncMock(return_value="success")
        result = await retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = await retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_max_retries_and_raises(self):
        func = AsyncMock(side_effect=ValueError("always fail"))

        with pytest.raises(ValueError, match="always fail"):
            await retry_with_backoff(func, max_retries=2, base_delay=0.01)

        assert func.call_count == 3

    @pytest.mark.asyncio
    async def test_zero_max_retries_does_not_retry(self):
        func = AsyncMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError, match="fail"):
            await retry_with_backoff(func, max_retries=0, base_delay=0.01)

        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_preserves_return_value(self):
        func = AsyncMock(return_value=42)
        result = await retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == 42
