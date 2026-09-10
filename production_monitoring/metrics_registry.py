"""Metrics Registry — unified metrics collector for all system metrics.

Integrates with existing Prometheus client and adds high-level tracking
for API latency, pipeline stages, providers, cache, queues, AI costs.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from production_monitoring.config import ProductionMonitoringConfig
from production_monitoring.constants import (
    METRIC_API_LATENCY,
    METRIC_PIPELINE_DURATION,
    METRIC_STAGE_DURATION,
    METRIC_PROVIDER_LATENCY,
    METRIC_CACHE_HITS,
    METRIC_CACHE_MISSES,
    METRIC_QUEUE_DEPTH,
    METRIC_AI_TOKENS,
    METRIC_AI_COST,
    METRIC_ACTIVE_JOBS,
    METRIC_ERROR_COUNT,
    LABEL_ENDPOINT,
    LABEL_STATUS,
    LABEL_STAGE,
    LABEL_PROVIDER,
    LABEL_MODEL,
    LABEL_CACHE,
    LABEL_QUEUE,
)

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


class MetricsRegistry:
    """Unified metrics collector for all system metrics.

    Provides high-level methods for recording metrics across
    API, pipeline, providers, cache, queues, and costs.
    Automatically creates and exposes Prometheus metrics.
    """

    def __init__(self, config: ProductionMonitoringConfig | None = None) -> None:
        self._config = config or ProductionMonitoringConfig.from_env()
        self._enabled = self._config.metrics_enabled

        # In-memory latency tracking
        self._api_latencies: dict[str, list[float]] = defaultdict(list)
        self._stage_latencies: dict[str, list[float]] = defaultdict(list)
        self._provider_latencies: dict[str, list[float]] = defaultdict(list)
        self._max_samples = 10000

        # Prometheus metrics
        self._prom_metrics: dict[str, Any] = {}

        if _HAS_PROMETHEUS and self._enabled:
            self._init_prometheus()

    def _init_prometheus(self) -> None:
        """Initialize Prometheus metrics."""
        prefix = self._config.metrics_prefix

        self._prom_metrics["api_requests"] = Counter(
            f"{prefix}_api_requests_total",
            "Total API requests",
            ["endpoint", "method", "status"],
        )
        self._prom_metrics["api_latency"] = Histogram(
            f"{prefix}_api_latency_ms",
            "API request latency in ms",
            ["endpoint"],
            buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000],
        )
        self._prom_metrics["pipeline_duration"] = Histogram(
            f"{prefix}_pipeline_duration_ms",
            "Pipeline execution duration in ms",
            buckets=[1000, 5000, 10000, 30000, 60000, 120000, 300000],
        )
        self._prom_metrics["stage_duration"] = Histogram(
            f"{prefix}_stage_duration_ms",
            "Stage execution duration in ms",
            ["stage"],
            buckets=[100, 500, 1000, 2000, 5000, 10000, 30000, 60000],
        )
        self._prom_metrics["provider_latency"] = Histogram(
            f"{prefix}_provider_latency_ms",
            "Provider request latency in ms",
            ["provider"],
            buckets=[50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000],
        )
        self._prom_metrics["cache_hits"] = Counter(
            f"{prefix}_cache_hits_total",
            "Cache hits by cache name",
            ["cache_name"],
        )
        self._prom_metrics["cache_misses"] = Counter(
            f"{prefix}_cache_misses_total",
            "Cache misses by cache name",
            ["cache_name"],
        )
        self._prom_metrics["queue_depth"] = Gauge(
            f"{prefix}_queue_depth",
            "Current queue depth",
            ["queue"],
        )
        self._prom_metrics["ai_tokens"] = Counter(
            f"{prefix}_ai_tokens_total",
            "AI tokens used by model",
            ["provider", "model"],
        )
        self._prom_metrics["ai_cost"] = Counter(
            f"{prefix}_ai_cost_total",
            "AI cost by provider",
            ["provider"],
        )
        self._prom_metrics["active_jobs"] = Gauge(
            f"{prefix}_active_jobs",
            "Number of active jobs",
            ["type"],
        )
        self._prom_metrics["errors"] = Counter(
            f"{prefix}_errors_total",
            "Error count by type",
            ["error_type", "stage"],
        )

    def record_api_request(
        self, endpoint: str, method: str, status: int, duration_ms: float,
    ) -> None:
        """Record an API request.

        Args:
            endpoint: API endpoint path.
            method: HTTP method.
            status: HTTP status code.
            duration_ms: Request duration in ms.
        """
        # In-memory tracking
        self._api_latencies[endpoint].append(duration_ms)
        if len(self._api_latencies[endpoint]) > self._max_samples:
            self._api_latencies[endpoint] = self._api_latencies[endpoint][-self._max_samples:]

        # Prometheus
        if self._prom_metrics and self._enabled:
            self._prom_metrics["api_requests"].labels(
                endpoint=endpoint, method=method, status=str(status),
            ).inc()
            self._prom_metrics["api_latency"].labels(endpoint=endpoint).observe(duration_ms)

    def record_pipeline_stage(
        self, stage: str, duration_ms: float, success: bool = True,
    ) -> None:
        """Record a pipeline stage execution.

        Args:
            stage: Stage name.
            duration_ms: Stage duration in ms.
            success: Whether the stage succeeded.
        """
        self._stage_latencies[stage].append(duration_ms)
        if len(self._stage_latencies[stage]) > self._max_samples:
            self._stage_latencies[stage] = self._stage_latencies[stage][-self._max_samples:]

        if self._prom_metrics and self._enabled:
            self._prom_metrics["stage_duration"].labels(stage=stage).observe(duration_ms)
            if not success:
                self._prom_metrics["errors"].labels(error_type="stage_failure", stage=stage).inc()

    def record_pipeline_duration(self, duration_ms: float) -> None:
        """Record total pipeline execution duration.

        Args:
            duration_ms: Total pipeline duration in ms.
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["pipeline_duration"].observe(duration_ms)

    def record_provider_latency(
        self, provider: str, duration_ms: float, success: bool = True,
    ) -> None:
        """Record a provider request.

        Args:
            provider: Provider name.
            duration_ms: Request duration in ms.
            success: Whether the request succeeded.
        """
        self._provider_latencies[provider].append(duration_ms)
        if len(self._provider_latencies[provider]) > self._max_samples:
            self._provider_latencies[provider] = self._provider_latencies[provider][-self._max_samples:]

        if self._prom_metrics and self._enabled:
            self._prom_metrics["provider_latency"].labels(provider=provider).observe(duration_ms)
            if not success:
                self._prom_metrics["errors"].labels(
                    error_type="provider_failure", stage=provider,
                ).inc()

    def record_cache_hit(self, cache_name: str) -> None:
        """Record a cache hit.

        Args:
            cache_name: Cache name (e.g. 'prompt', 'embedding', 'query').
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["cache_hits"].labels(cache_name=cache_name).inc()

    def record_cache_miss(self, cache_name: str) -> None:
        """Record a cache miss.

        Args:
            cache_name: Cache name.
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["cache_misses"].labels(cache_name=cache_name).inc()

    def record_queue_depth(self, queue: str, depth: int) -> None:
        """Record queue depth.

        Args:
            queue: Queue name.
            depth: Current depth.
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["queue_depth"].labels(queue=queue).set(depth)

    def record_ai_cost(
        self, provider: str, model: str, tokens_prompt: int = 0,
        tokens_completion: int = 0, cost: float = 0.0,
    ) -> None:
        """Record AI token usage and cost.

        Args:
            provider: AI provider name.
            model: Model name.
            tokens_prompt: Prompt tokens used.
            tokens_completion: Completion tokens used.
            cost: Cost in USD.
        """
        if self._prom_metrics and self._enabled:
            total_tokens = tokens_prompt + tokens_completion
            self._prom_metrics["ai_tokens"].labels(
                provider=provider, model=model,
            ).inc(total_tokens)
            self._prom_metrics["ai_cost"].labels(provider=provider).inc(cost)

    def record_active_jobs(self, job_type: str, count: int) -> None:
        """Record active job count.

        Args:
            job_type: Job type (e.g. 'pipeline', 'export').
            count: Number of active jobs.
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["active_jobs"].labels(type=job_type).set(count)

    def record_error(self, error_type: str, stage: str = "") -> None:
        """Record an error occurrence.

        Args:
            error_type: Error type.
            stage: Stage where error occurred.
        """
        if self._prom_metrics and self._enabled:
            self._prom_metrics["errors"].labels(error_type=error_type, stage=stage).inc()

    def get_api_latency_percentiles(self, endpoint: str) -> dict[str, float]:
        """Get latency percentiles for an endpoint.

        Args:
            endpoint: API endpoint path.

        Returns:
            Dict with P50, P90, P95, P99, avg, count.
        """
        samples = sorted(self._api_latencies.get(endpoint, []))
        if not samples:
            return {"count": 0}
        n = len(samples)
        return {
            "p50_ms": samples[int(n * 0.50)],
            "p90_ms": samples[int(n * 0.90)],
            "p95_ms": samples[int(n * 0.95)],
            "p99_ms": samples[int(n * 0.99)],
            "avg_ms": sum(samples) / n,
            "count": n,
        }

    def get_stage_timing_summary(self, stage: str) -> dict[str, float]:
        """Get timing summary for a stage.

        Args:
            stage: Stage name.

        Returns:
            Dict with avg, p95, count.
        """
        samples = sorted(self._stage_latencies.get(stage, []))
        if not samples:
            return {"count": 0}
        n = len(samples)
        return {
            "avg_ms": sum(samples) / n,
            "p95_ms": samples[int(n * 0.95)],
            "count": n,
        }

    def get_cache_hit_rate(self, cache_name: str) -> float:
        """Get cache hit rate from Prometheus metrics.

        Args:
            cache_name: Cache name.

        Returns:
            Hit rate (0.0-1.0).
        """
        if not self._prom_metrics:
            return 0.0
        hits = self._prom_metrics["cache_hits"].labels(cache_name=cache_name)._value.get()
        misses = self._prom_metrics["cache_misses"].labels(cache_name=cache_name)._value.get()
        total = hits + misses
        return hits / total if total > 0 else 0.0

    def get_summary(self) -> dict[str, Any]:
        """Get a comprehensive metrics summary."""
        return {
            "api_endpoints_tracked": len(self._api_latencies),
            "stages_tracked": len(self._stage_latencies),
            "providers_tracked": len(self._provider_latencies),
        }
