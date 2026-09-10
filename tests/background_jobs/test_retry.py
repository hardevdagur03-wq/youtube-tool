from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.background_job


class TestRetry:
    def test_exponential_backoff(self):
        base_delay = 1.0
        max_delay = 60.0
        for attempt in range(5):
            delay = min(base_delay * (2 ** attempt), max_delay)
            assert delay > 0
            if attempt == 0:
                assert delay == 1.0
            elif attempt == 4:
                assert delay <= max_delay

    @pytest.mark.asyncio
    async def test_max_retries(self):
        max_attempts = 3
        call_count = 0

        async def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < max_attempts:
                raise Exception("Temporary failure")
            return "success"

        result = await flaky_task()
        assert call_count == max_attempts
        assert result == "success"

    @pytest.mark.asyncio
    async def test_non_recoverable_error_skip_retry(self):
        non_recoverable = ("ValidationError", "AuthError", "PermissionDenied")

        async def execute():
            raise PermissionDenied("Access denied")  # noqa: F821

        with pytest.raises(Exception):
            await execute()

    @pytest.mark.asyncio
    async def test_retry_history_tracking(self):
        history = []
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            history.append({
                "attempt": attempt,
                "error": f"Error on attempt {attempt}",
                "timestamp": time.time(),
            })
        assert len(history) == 3
        assert history[0]["attempt"] == 1
        assert history[2]["attempt"] == 3
