from __future__ import annotations

import asyncio
from typing import Any

import pytest


@pytest.fixture
def load_test_config() -> dict[str, Any]:
    return {
        "concurrent_users": [10, 100, 500, 1000],
        "concurrent_projects": [10, 50, 100],
        "concurrent_exports": [10, 50],
        "latency_threshold_ms": 2000,
        "failure_rate_threshold": 0.05,
        "throughput_threshold_rps": 10,
    }


@pytest.fixture
def concurrent_requests():
    async def _execute(tasks: list, limit: int = 10):
        semaphore = asyncio.Semaphore(limit)
        async def _task(coro):
            async with semaphore:
                return await coro
        return await asyncio.gather(*(_task(t) for t in tasks), return_exceptions=True)
    return _execute
