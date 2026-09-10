"""Performance Monitor — aggregates performance metrics from all sources.

Collects latency, cache hit rates, queue depths, throughput, and memory
metrics into a unified dashboard view. Supports Prometheus exposition.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from performance_engineering.cache import PromptCache, EmbeddingCache, QueryCache, CacheInvalidator
from performance_engineering.pipeline import AsyncExecutor, ParallelScheduler
from performance_engineering.queue import PriorityRouter, ThroughputOptimizer
from performance_engineering.streaming import SSEManager
from performance_engineering.memory import MemoryOptimizer
from performance_engineering.connection_pool import ConnectionPoolManager
from performance_engineering.models import LatencyPercentiles

logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """Aggregates performance metrics from all components.

    Collects latency, cache, queue, throughput, and memory metrics
    into a unified view. Provides real-time and historical stats.
    """

    def __init__(
        self,
        async_executor: AsyncExecutor | None = None,
        parallel_scheduler: ParallelScheduler | None = None,
        prompt_cache: PromptCache | None = None,
        embedding_cache: EmbeddingCache | None = None,
        query_cache: QueryCache | None = None,
        cache_invalidator: CacheInvalidator | None = None,
        priority_router: PriorityRouter | None = None,
        throughput_optimizer: ThroughputOptimizer | None = None,
        sse_manager: SSEManager | None = None,
        memory_optimizer: MemoryOptimizer | None = None,
        connection_pool: ConnectionPoolManager | None = None,
    ) -> None:
        self._async = async_executor
        self._parallel = parallel_scheduler
        self._prompt_cache = prompt_cache
        self._embedding_cache = embedding_cache
        self._query_cache = query_cache
        self._cache_invalidator = cache_invalidator
        self._router = priority_router
        self._throughput = throughput_optimizer
        self._sse = sse_manager
        self._memory = memory_optimizer
        self._pool = connection_pool
        self._latency_samples: dict[str, list[float]] = defaultdict(list)
        self._max_samples = 10000

    def record_latency(self, endpoint: str, duration_ms: float) -> None:
        """Record a latency sample for an endpoint.

        Args:
            endpoint: Endpoint name (e.g. 'api/transcript').
            duration_ms: Request duration in ms.
        """
        samples = self._latency_samples[endpoint]
        samples.append(duration_ms)
        if len(samples) > self._max_samples:
            self._latency_samples[endpoint] = samples[-self._max_samples:]

    def get_latency_percentiles(self, endpoint: str) -> LatencyPercentiles:
        """Get latency percentiles for an endpoint.

        Args:
            endpoint: Endpoint name.

        Returns:
            ``LatencyPercentiles`` with P50/P90/P95/P99.
        """
        samples = sorted(self._latency_samples.get(endpoint, []))
        if not samples:
            return LatencyPercentiles()
        n = len(samples)
        return LatencyPercentiles(
            p50_ms=samples[int(n * 0.50)],
            p90_ms=samples[int(n * 0.90)],
            p95_ms=samples[int(n * 0.95)],
            p99_ms=samples[int(n * 0.99)],
            avg_ms=sum(samples) / n,
            min_ms=samples[0],
            max_ms=samples[-1],
            sample_count=n,
        )

    def get_all_latency_percentiles(self) -> dict[str, dict[str, float]]:
        """Get latency percentiles for all endpoints.

        Returns:
            Dict of endpoint -> percentiles.
        """
        return {
            endpoint: self.get_latency_percentiles(endpoint).model_dump()
            for endpoint in sorted(self._latency_samples.keys())
        }

    def get_full_dashboard(self) -> dict[str, Any]:
        """Get the complete performance dashboard.

        Returns:
            Dict with all performance metrics.
        """
        dashboard = {
            "latency": self.get_all_latency_percentiles(),
            "cache": {},
            "async_executor": {},
            "queues": {},
            "memory": {},
            "connection_pools": {},
            "streaming": {},
            "timestamp": time.time(),
        }

        if self._prompt_cache:
            dashboard["cache"]["prompt"] = self._prompt_cache.stats
        if self._embedding_cache:
            dashboard["cache"]["embedding"] = self._embedding_cache.stats
        if self._query_cache:
            dashboard["cache"]["query"] = self._query_cache.stats
        if self._cache_invalidator:
            dashboard["cache"]["overall"] = self._cache_invalidator.get_stats()

        if self._async:
            dashboard["async_executor"] = self._async.get_stats()

        if self._router:
            dashboard["queues"]["mapping"] = self._router.get_queue_map()
        if self._throughput:
            dashboard["queues"]["throughput"] = self._throughput.get_summary()

        if self._memory:
            dashboard["memory"] = self._memory.get_summary()

        if self._pool:
            dashboard["connection_pools"] = self._pool.get_stats()

        if self._sse:
            dashboard["streaming"] = self._sse.get_stats()

        dashboard["endpoints_tracked"] = len(self._latency_samples)
        dashboard["total_latency_samples"] = sum(
            len(s) for s in self._latency_samples.values()
        )

        return dashboard
