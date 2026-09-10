"""Async Executor — wraps synchronous service calls as non-blocking async operations.

Converts every blocking service call (TranscriptService, YouTube API, AI providers)
into non-blocking async using ThreadPoolExecutor.
Target: zero blocking operations in request handling.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncExecutor:
    """Converts synchronous service calls to non-blocking async.

    Uses a ThreadPoolExecutor to offload blocking I/O to worker threads,
    allowing the asyncio event loop to handle other requests concurrently.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._executor = ThreadPoolExecutor(
            max_workers=self._config.async_max_workers,
            thread_name_prefix="perf-async",
        )
        self._enabled = self._config.async_enabled
        self._total_tasks = 0
        self._total_time_ms = 0.0

    async def run(
        self,
        func: Callable[..., T],
        *args: Any,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute a synchronous function in a non-blocking manner."""
        if not self._enabled:
            return func(*args, **kwargs)
        timeout = timeout or self._config.async_executor_timeout
        loop = asyncio.get_running_loop()
        start = time.time()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor, functools.partial(func, *args, **kwargs)
                ),
                timeout=timeout,
            )
            elapsed = (time.time() - start) * 1000
            self._total_tasks += 1
            self._total_time_ms += elapsed
            return result
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            logger.warning(
                "Async executor timed out after %.0fms: %s",
                elapsed, func.__name__ if hasattr(func, '__name__') else '?',
            )
            raise

    async def run_coro(self, coro: Any, timeout: int | None = None) -> Any:
        """Execute an async callable with timeout."""
        timeout = timeout or self._config.async_executor_timeout
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Async coroutine timed out after %ds", timeout)
            raise

    def get_stats(self) -> dict[str, Any]:
        total = self._total_tasks
        return {
            "total_tasks": total,
            "total_time_ms": round(self._total_time_ms, 1),
            "avg_time_ms": round(self._total_time_ms / max(total, 1), 1),
            "max_workers": self._executor._max_workers,
            "enabled": self._enabled,
        }

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
        logger.info("Async executor shut down")
