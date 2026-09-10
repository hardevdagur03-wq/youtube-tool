"""Concurrency Framework — parallel AI calls, batch operations, and task pooling.

Enables independent AI operations (SEO, KG, entities, etc.) to execute
concurrently, dramatically reducing pipeline latency.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ConcurrentResult:
    name: str = ""
    success: bool = False
    data: Any = None
    duration_ms: float = 0.0
    error: str = ""


class ConcurrencyEngine:
    """Executes independent tasks concurrently with configurable limits."""

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_all(
        self, tasks: dict[str, Callable]
    ) -> list[ConcurrentResult]:
        results = []

        async def run_task(name: str, func: Callable) -> ConcurrentResult:
            start = time.time()
            async with self._semaphore:
                try:
                    result = await func()
                    elapsed = (time.time() - start) * 1000
                    return ConcurrentResult(
                        name=name,
                        success=True,
                        data=result,
                        duration_ms=round(elapsed, 1),
                    )
                except Exception as e:
                    elapsed = (time.time() - start) * 1000
                    logger.error("Task %s failed: %s", name, e)
                    return ConcurrentResult(
                        name=name,
                        success=False,
                        duration_ms=round(elapsed, 1),
                        error=str(e),
                    )

        coros = [run_task(name, func) for name, func in tasks.items()]
        for coro in asyncio.as_completed(coros):
            result = await coro
            results.append(result)

        return results

    async def execute_batch(
        self,
        items: list[Any],
        processor: Callable,
        batch_size: int = 10,
    ) -> list[ConcurrentResult]:
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            tasks = {f"item_{j}": lambda b=batch: processor(b) for j in range(len(batch))}
            batch_results = await self.execute_all(tasks)
            results.extend(batch_results)
        return results


class TaskGroup:
    """Group related concurrent tasks for coordinated execution."""

    def __init__(self):
        self._tasks: dict[str, Callable] = {}

    def add(self, name: str, func: Callable) -> None:
        self._tasks[name] = func

    async def run(
        self, max_concurrent: int = 5
    ) -> dict[str, ConcurrentResult]:
        engine = ConcurrencyEngine(max_concurrent=max_concurrent)
        results = await engine.execute_all(self._tasks)
        return {r.name: r for r in results}


class AIConcurrencyManager:
    """Manages concurrent AI calls with provider-aware limits."""

    def __init__(self, max_concurrent: int = 3):
        self._engine = ConcurrencyEngine(max_concurrent=max_concurrent)

    async def run_ai_tasks(
        self, tasks: dict[str, Callable]
    ) -> dict[str, ConcurrentResult]:
        results = await self._engine.execute_all(tasks)
        return {r.name: r for r in results}

    def summary(self, results: dict[str, ConcurrentResult]) -> dict[str, Any]:
        succeeded = sum(1 for r in results.values() if r.success)
        failed = sum(1 for r in results.values() if not r.success)
        total_ms = sum(r.duration_ms for r in results.values())
        sequential_estimate = total_ms
        parallel_improvement = sequential_estimate - max(
            r.duration_ms for r in results.values()
        ) if results else 0

        return {
            "total_tasks": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "total_duration_ms": round(total_ms, 1),
            "parallel_estimate_ms": round(
                max(r.duration_ms for r in results.values()), 1
            ) if results else 0,
            "sequential_estimate_ms": round(sequential_estimate, 1),
            "time_saved_ms": round(
                sequential_estimate
                - max(r.duration_ms for r in results.values()),
                1,
            ) if results else 0,
            "speedup": round(
                sequential_estimate
                / max(r.duration_ms for r in results.values()),
                1,
            ) if results and max(r.duration_ms for r in results.values()) > 0 else 1.0,
        }
