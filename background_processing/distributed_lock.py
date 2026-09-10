"""Distributed Lock — Redis-based distributed locking to prevent duplicate execution."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired within the configured retry limit."""


class DistributedLock:
    """Redis-based distributed mutex.

    Uses SET NX EX for atomic lock acquisition with TTL.
    Supports blocking (retry until acquired) and non-blocking (try once) modes.

    Thread-safe: each lock acquires a unique token for safe release.
    """

    LOCK_SCRIPT = """
    if redis.call("SET", KEYS[1], ARGV[1], "NX", "EX", ARGV[2]) then
        return 1
    end
    return 0
    """

    UNLOCK_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    end
    return 0
    """

    RENEW_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("EXPIRE", KEYS[1], ARGV[2])
    end
    return 0
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._redis = redis_client

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.redis_url,
                socket_timeout=self._config.redis_socket_timeout,
                socket_connect_timeout=self._config.redis_socket_connect_timeout,
                retry_on_timeout=self._config.redis_retry_on_timeout,
                health_check_interval=self._config.redis_health_check_interval,
                decode_responses=True,
            )
        return self._redis

    async def acquire(
        self,
        lock_key: str,
        ttl: int | None = None,
        block: bool = True,
        token: str | None = None,
    ) -> tuple[bool, str]:
        """Attempt to acquire a distributed lock.

        Args:
            lock_key: Unique key for the resource being locked.
            ttl: Time-to-live in seconds (default: config.lock_ttl).
            block: If True, retry until acquired (up to config.lock_max_retries).
            token: Unique token for safe release (auto-generated if None).

        Returns:
            Tuple of (acquired: bool, token: str).
        """
        redis = await self._get_redis()
        ttl = ttl or self._config.lock_ttl
        token = token or str(uuid.uuid4())
        max_retries = self._config.lock_max_retries if block else 1

        for attempt in range(max_retries):
            acquired = await redis.set(lock_key, token, nx=True, ex=ttl)
            if acquired:
                logger.debug("Lock acquired: %s (token=%s, ttl=%ds)", lock_key, token[:8], ttl)
                return True, token

            if not block:
                return False, token

            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(self._config.lock_retry_interval)

        logger.warning("Lock failed after %d retries: %s", max_retries, lock_key)
        return False, token

    async def release(self, lock_key: str, token: str) -> bool:
        """Release the lock only if the token matches (safe unlock)."""
        redis = await self._get_redis()
        result = await redis.eval(self.UNLOCK_SCRIPT, 1, lock_key, token)
        if result:
            logger.debug("Lock released: %s (token=%s)", lock_key, token[:8])
        else:
            logger.warning("Lock release failed (wrong token or expired): %s", lock_key)
        return bool(result)

    async def renew(self, lock_key: str, token: str, ttl: int | None = None) -> bool:
        """Extend the lock TTL if the token matches."""
        redis = await self._get_redis()
        ttl = ttl or self._config.lock_ttl
        result = await redis.eval(self.RENEW_SCRIPT, 1, lock_key, token, str(ttl))
        return bool(result)

    async def locked(self, lock_key: str) -> bool:
        """Check if a lock exists (without acquiring)."""
        redis = await self._get_redis()
        return await redis.exists(lock_key) > 0

    async def get_token(self, lock_key: str) -> str | None:
        """Get the current lock token (for inspection)."""
        redis = await self._get_redis()
        return await redis.get(lock_key)

    async def clear(self, lock_key: str) -> bool:
        """Force-clear a lock (use with caution, bypasses token check)."""
        redis = await self._get_redis()
        return bool(await redis.delete(lock_key))

    @asynccontextmanager
    async def lock(
        self,
        lock_key: str,
        ttl: int | None = None,
        block: bool = True,
        token: str | None = None,
    ) -> AsyncIterator[str]:
        """Context manager for distributed locking.

        Example:
            lock = DistributedLock()
            async with lock.lock("project:123:export"):
                # exclusive access
                ...
        """
        acquired, token_val = await self.acquire(lock_key, ttl=ttl, block=block, token=token)
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire lock: {lock_key}")
        try:
            yield token_val
        finally:
            await self.release(lock_key, token_val)


class AutoRenewLock:
    """Distributed lock with automatic TTL renewal.

    Periodically renews the lock TTL while the context is active,
    preventing premature expiry during long-running operations.
    """

    def __init__(
        self,
        lock: DistributedLock,
        lock_key: str,
        ttl: int = 300,
        renew_interval: int = 60,
        token: str | None = None,
    ) -> None:
        self._lock = lock
        self._lock_key = lock_key
        self._ttl = ttl
        self._renew_interval = min(renew_interval, ttl // 2)
        self._token = token or str(uuid.uuid4())
        self._renew_task: Any = None

    async def __aenter__(self) -> str:
        acquired, token = await self._lock.acquire(self._lock_key, ttl=self._ttl, token=self._token)
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire auto-renew lock: {self._lock_key}")
        self._token = token
        self._start_renew()
        return token

    async def __aexit__(self, *args: Any) -> None:
        self._stop_renew()
        await self._lock.release(self._lock_key, self._token)

    def _start_renew(self) -> None:
        import asyncio
        self._renew_task = asyncio.ensure_future(self._renew_loop())

    def _stop_renew(self) -> None:
        if self._renew_task:
            self._renew_task.cancel()
            self._renew_task = None

    async def _renew_loop(self) -> None:
        import asyncio
        while True:
            await asyncio.sleep(self._renew_interval)
            try:
                await self._lock.renew(self._lock_key, self._token, ttl=self._ttl)
            except Exception:
                logger.warning("Lock renew failed: %s", self._lock_key, exc_info=True)
                break


# Global lock instance
_distributed_lock: DistributedLock | None = None


def get_lock(redis_client: Redis | None = None) -> DistributedLock:
    global _distributed_lock
    if _distributed_lock is None:
        _distributed_lock = DistributedLock(redis_client=redis_client)
    return _distributed_lock
