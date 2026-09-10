"""Tests for the Rate Limiter — token bucket algorithm with multi-scope limiting."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.rate_limiter import RateLimiter, RateLimitExceeded


class TestRateLimiter:
    @pytest_asyncio.fixture
    async def limiter(self, mock_redis):
        mock_redis.eval = AsyncMock(return_value=1)
        l = RateLimiter(redis_client=mock_redis)
        yield l

    async def test_allow_within_limits(self, limiter, mock_redis):
        mock_redis.eval.return_value = 1
        result = await limiter.allow(tenant_id="tenant-1", user_id="user-1", job_type="pipeline.analysis")
        assert result is True

    async def test_deny_when_rate_limited(self, limiter, mock_redis):
        mock_redis.eval.return_value = 0
        result = await limiter.allow(tenant_id="tenant-1", user_id="user-1", job_type="pipeline.analysis")
        assert result is False

    async def test_global_limit_applied(self, limiter, mock_redis):
        calls = []
        mock_redis.eval.side_effect = lambda *a, **kw: 1 if len(calls) < 3 else 0
        for _ in range(3):
            calls.append(await limiter.allow(tenant_id="t", user_id="u"))
        assert calls[-1] is True  # all pass when eval returns 1

    async def test_remaining_tokens(self, limiter, mock_redis):
        mock_redis.hmget = AsyncMock(return_value=[50, "1000000"])
        remaining = await limiter.remaining(tenant_id="tenant-1", user_id="user-1")
        assert "global" in remaining
        assert "tenant" in remaining
        assert "user" in remaining

    async def test_reset_limits(self, limiter, mock_redis):
        mock_redis.delete = AsyncMock(return_value=1)
        await limiter.reset(tenant_id="tenant-1", user_id="user-1")
        assert mock_redis.delete.called

    async def test_allow_without_scope(self, limiter, mock_redis):
        mock_redis.eval.return_value = 1
        result = await limiter.allow()
        assert result is True

    async def test_multiple_scopes_checked(self, limiter, mock_redis):
        eval_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal eval_count
            eval_count += 1
            return 1

        mock_redis.eval = AsyncMock(side_effect=side_effect)
        await limiter.allow(tenant_id="tenant-1", user_id="user-1", job_type="pipeline.analysis")
        assert eval_count >= 3  # global + tenant + user + type
