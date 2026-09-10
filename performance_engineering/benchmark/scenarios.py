"""Benchmark Scenarios — predefined performance test scenarios.

Provides standard benchmark scenarios for pipeline stages,
API endpoints, and cache performance testing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from performance_engineering.models import BenchmarkResult

logger = logging.getLogger(__name__)


class BenchmarkScenarios:
    """Standard benchmark scenarios for performance testing."""

    @staticmethod
    def pipeline_cold_start(
        run_pipeline_fn: Callable,
        video_id: str = "dQw4w9WgXcQ",
    ) -> dict[str, Any]:
        """Benchmark cold-start pipeline execution.

        Measures time for first-time pipeline execution (no cache).

        Args:
            run_pipeline_fn: Async function to run the pipeline.
            video_id: Video ID to process.

        Returns:
            Dict with timing data.
        """
        start = time.time()
        run_pipeline_fn(video_id)
        duration_ms = (time.time() - start) * 1000
        return {
            "scenario": "pipeline_cold_start",
            "duration_ms": round(duration_ms, 1),
        }

    @staticmethod
    def pipeline_warm_start(
        run_pipeline_fn: Callable,
        video_id: str = "dQw4w9WgXcQ",
    ) -> dict[str, Any]:
        """Benchmark warm-start pipeline execution.

        Measures time for subsequent pipeline execution (with cache).

        Args:
            run_pipeline_fn: Async function to run the pipeline.
            video_id: Video ID to process.

        Returns:
            Dict with timing data.
        """
        start = time.time()
        run_pipeline_fn(video_id)
        duration_ms = (time.time() - start) * 1000
        return {
            "scenario": "pipeline_warm_start",
            "duration_ms": round(duration_ms, 1),
        }

    @staticmethod
    def metadata_lookup(
        metadata_fn: Callable,
        samples: int = 10,
    ) -> dict[str, Any]:
        """Benchmark metadata lookup performance.

        Args:
            metadata_fn: Function to get metadata.
            samples: Number of samples.

        Returns:
            Dict with timing percentiles.
        """
        timings = []
        for _ in range(samples):
            start = time.time()
            metadata_fn()
            timings.append((time.time() - start) * 1000)

        sorted_t = sorted(timings)
        n = len(sorted_t)
        return {
            "scenario": "metadata_lookup",
            "avg_ms": round(sum(sorted_t) / n, 1),
            "p50_ms": round(sorted_t[int(n * 0.50)], 1),
            "p95_ms": round(sorted_t[int(n * 0.95)], 1),
            "samples": n,
        }

    @staticmethod
    def cache_hit(
        cache_get_fn: Callable,
        cache_set_fn: Callable,
        key: str = "benchmark_key",
        value: Any = "benchmark_value",
        samples: int = 100,
    ) -> dict[str, Any]:
        """Benchmark cache hit performance.

        Args:
            cache_get_fn: Cache get function.
            cache_set_fn: Cache set function.
            key: Cache key.
            value: Cache value.
            samples: Number of samples.

        Returns:
            Dict with timing percentiles.
        """
        cache_set_fn(key, value)
        timings = []
        for _ in range(samples):
            start = time.time()
            cache_get_fn(key)
            timings.append((time.time() - start) * 1000)

        sorted_t = sorted(timings)
        n = len(sorted_t)
        return {
            "scenario": "cache_hit",
            "avg_ms": round(sum(sorted_t) / n, 4),
            "p50_ms": round(sorted_t[int(n * 0.50)], 4),
            "p95_ms": round(sorted_t[int(n * 0.95)], 4),
            "samples": n,
        }

    @staticmethod
    def api_endpoint(
        api_fn: Callable,
        samples: int = 50,
    ) -> dict[str, Any]:
        """Benchmark API endpoint latency.

        Args:
            api_fn: API endpoint function.
            samples: Number of samples.

        Returns:
            Dict with timing percentiles.
        """
        timings = []
        for _ in range(samples):
            start = time.time()
            api_fn()
            timings.append((time.time() - start) * 1000)

        sorted_t = sorted(timings)
        n = len(sorted_t)
        return {
            "scenario": "api_endpoint",
            "avg_ms": round(sum(sorted_t) / n, 1),
            "p50_ms": round(sorted_t[int(n * 0.50)], 1),
            "p95_ms": round(sorted_t[int(n * 0.95)], 1),
            "p99_ms": round(sorted_t[int(n * 0.99)], 1),
            "samples": n,
        }
