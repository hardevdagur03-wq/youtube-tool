from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

import pytest


@pytest.fixture
def performance_config() -> dict[str, Any]:
    return {
        "pipeline_threshold_s": 30.0,
        "stage_threshold_s": 5.0,
        "api_threshold_ms": 500,
        "db_query_threshold_ms": 100,
        "cache_hit_threshold_ms": 5,
        "cache_miss_threshold_ms": 50,
        "export_threshold_s": 10.0,
        "bulk_insert_threshold_s": 2.0,
        "worker_throughput_jobs_per_sec": 50,
    }


@pytest.fixture
def timer() -> Any:
    @contextmanager
    def _timer():
        start = time.perf_counter()
        yield lambda: time.perf_counter() - start
    return _timer


@pytest.fixture
def metrics_collector() -> Any:
    class MetricsCollector:
        def __init__(self):
            self._metrics: dict[str, list[float]] = {}

        def record(self, name: str, value: float) -> None:
            self._metrics.setdefault(name, []).append(value)

        def get(self, name: str) -> list[float]:
            return self._metrics.get(name, [])

        def p50(self, name: str) -> float:
            vals = sorted(self._metrics.get(name, []))
            if not vals:
                return 0.0
            return vals[len(vals) // 2]

        def p95(self, name: str) -> float:
            vals = sorted(self._metrics.get(name, []))
            if not vals:
                return 0.0
            idx = max(0, int(len(vals) * 0.95) - 1)
            return vals[idx]

        def p99(self, name: str) -> float:
            vals = sorted(self._metrics.get(name, []))
            if not vals:
                return 0.0
            idx = max(0, int(len(vals) * 0.99) - 1)
            return vals[idx]

        def mean(self, name: str) -> float:
            vals = self._metrics.get(name, [])
            if not vals:
                return 0.0
            return sum(vals) / len(vals)

        def clear(self) -> None:
            self._metrics.clear()

    collector = MetricsCollector()
    yield collector
