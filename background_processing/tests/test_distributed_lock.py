"""Tests for DistributedLock and AutoRenewLock — Redis-based distributed locking."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from background_processing.distributed_lock import (
    AutoRenewLock, DistributedLock, LockAcquisitionError,
)


class TestDistributedLock:
    async def test_acquire_success(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=True)
        acquired, token = await lock.acquire("test:lock", ttl=30)
        assert acquired is True
        assert token is not None

    async def test_acquire_failure(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=None)
        acquired, token = await lock.acquire("test:lock", ttl=30, block=False)
        assert acquired is False

    async def test_release_success(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.eval = AsyncMock(return_value=1)
        result = await lock.release("test:lock", "token-123")
        assert result is True

    async def test_release_wrong_token(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.eval = AsyncMock(return_value=0)
        result = await lock.release("test:lock", "wrong-token")
        assert result is False

    async def test_renew_success(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.eval = AsyncMock(return_value=1)
        result = await lock.renew("test:lock", "token-123", ttl=60)
        assert result is True

    async def test_renew_failure(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.eval = AsyncMock(return_value=0)
        result = await lock.renew("test:lock", "wrong-token", ttl=60)
        assert result is False

    async def test_locked(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.exists = AsyncMock(return_value=1)
        assert await lock.locked("test:lock") is True

    async def test_not_locked(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.exists = AsyncMock(return_value=0)
        assert await lock.locked("test:lock") is False

    async def test_get_token(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.get = AsyncMock(return_value="token-xyz")
        token = await lock.get_token("test:lock")
        assert token == "token-xyz"

    async def test_clear(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.delete = AsyncMock(return_value=1)
        result = await lock.clear("test:lock")
        assert result is True

    async def test_context_manager(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.eval = AsyncMock(return_value=1)
        async with lock.lock("test:lock", ttl=30) as token:
            assert token is not None

    async def test_context_manager_failure(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=None)
        with pytest.raises(LockAcquisitionError):
            async with lock.lock("test:lock", ttl=30, block=False):
                pass


class TestAutoRenewLock:
    async def test_acquire_and_release(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.eval = AsyncMock(return_value=1)

        auto = AutoRenewLock(lock, "test:lock", ttl=300, renew_interval=60)
        token = await auto.__aenter__()
        assert token is not None
        await auto.__aexit__(None, None, None)

    async def test_acquire_failure(self, mock_redis):
        lock = DistributedLock(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=None)

        auto = AutoRenewLock(lock, "test:lock", ttl=300, renew_interval=60)
        with pytest.raises(LockAcquisitionError):
            await auto.__aenter__()
