"""Observability — provider metrics, latency tracking, and Prometheus integration.

Tracks provider latency, success rates, retries, fallback counts,
circuit breaker events, cache hit rates, and transcript quality.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from transcript_reliability.models import TranscriptMetrics

logger = logging.getLogger(__name__)

# Try optional Prometheus client
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


class TranscriptObservability:
    """Tracks and exposes transcript reliability metrics.

    Supports both in-memory aggregation and Prometheus exposition.
    """

    def __init__(self, prometheus_port: int = 8001, enable_prometheus: bool = False) -> None:
        self._lock = Lock()
        self._metrics: list[TranscriptMetrics] = []
        self._provider_latencies: dict[str, list[float]] = defaultdict(list)
        self._provider_success: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._cache_stats: dict[str, int] = {"hits": 0, "misses": 0}
        self._circuit_breaker_events: dict[str, int] = defaultdict(int)
        self._retry_counts: dict[str, int] = defaultdict(int)
        self._fallback_counts: dict[str, int] = defaultdict(int)
        self._validation_failures: dict[str, int] = defaultdict(int)
        self._quality_scores: list[float] = []
        self._prometheus_port = prometheus_port
        self._prometheus_started = False

        if enable_prometheus and _HAS_PROMETHEUS:
            self._setup_prometheus()

    def _setup_prometheus(self) -> None:
        """Initialize Prometheus metrics and start HTTP server."""
        if not _HAS_PROMETHEUS:
            logger.warning("prometheus_client not installed — Prometheus metrics disabled")
            return

        self._prom_provider_latency = Histogram(
            "transcript_provider_latency_ms",
            "Provider latency in milliseconds",
            ["provider"],
            buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000],
        )
        self._prom_provider_success = Gauge(
            "transcript_provider_success_rate",
            "Provider success rate (rolling)",
            ["provider"],
        )
        self._prom_cache_hits = Counter(
            "transcript_cache_hits_total",
            "Total cache hits",
            ["level"],
        )
        self._prom_cache_misses = Counter(
            "transcript_cache_misses_total",
            "Total cache misses",
        )
        self._prom_circuit_breaker = Counter(
            "transcript_circuit_breaker_events_total",
            "Circuit breaker events by state",
            ["provider", "state"],
        )
        self._prom_retries = Counter(
            "transcript_retries_total",
            "Total retries by provider",
            ["provider"],
        )
        self._prom_fallbacks = Counter(
            "transcript_fallbacks_total",
            "Total provider fallbacks",
            ["from_provider", "to_provider"],
        )
        self._prom_quality = Gauge(
            "transcript_quality_score",
            "Transcript quality score",
            ["video_id"],
        )
        self._prom_validation_failures = Counter(
            "transcript_validation_failures_total",
            "Validation failures by check",
            ["check"],
        )

        try:
            start_http_server(self._prometheus_port)
            self._prometheus_started = True
            logger.info("Prometheus metrics server started on port %d", self._prometheus_port)
        except Exception as exc:
            logger.warning("Failed to start Prometheus server: %s", exc)

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_provider_latency(self, provider_id: str, latency_ms: float) -> None:
        """Record provider request latency."""
        with self._lock:
            self._provider_latencies[provider_id].append(latency_ms)
            # Keep last 1000
            if len(self._provider_latencies[provider_id]) > 1000:
                self._provider_latencies[provider_id] = self._provider_latencies[provider_id][-1000:]

        if self._prometheus_started:
            self._prom_provider_latency.labels(provider=provider_id).observe(latency_ms)

    def record_provider_success(self, provider_id: str, success: bool) -> None:
        """Record a provider success or failure."""
        with self._lock:
            total, successes = self._provider_success[provider_id]
            self._provider_success[provider_id] = (total + 1, successes + (1 if success else 0))

        if self._prometheus_started:
            total, successes = self._provider_success[provider_id]
            rate = successes / max(total, 1)
            self._prom_provider_success.labels(provider=provider_id).set(rate)

    def record_cache_hit(self, level: str) -> None:
        """Record a cache hit at a specific level."""
        with self._lock:
            self._cache_stats["hits"] += 1
        if self._prometheus_started:
            self._prom_cache_hits.labels(level=level).inc()

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self._cache_stats["misses"] += 1
        if self._prometheus_started:
            self._prom_cache_misses.inc()

    def record_circuit_breaker_event(self, provider_id: str, state: str) -> None:
        """Record a circuit breaker state transition."""
        with self._lock:
            self._circuit_breaker_events[f"{provider_id}:{state}"] += 1
        if self._prometheus_started:
            self._prom_circuit_breaker.labels(provider=provider_id, state=state).inc()

    def record_retry(self, provider_id: str) -> None:
        """Record a retry attempt."""
        with self._lock:
            self._retry_counts[provider_id] += 1
        if self._prometheus_started:
            self._prom_retries.labels(provider=provider_id).inc()

    def record_fallback(self, from_provider: str, to_provider: str) -> None:
        """Record a provider fallback."""
        with self._lock:
            self._fallback_counts[f"{from_provider}->{to_provider}"] += 1
        if self._prometheus_started:
            self._prom_fallbacks.labels(from_provider=from_provider, to_provider=to_provider).inc()

    def record_validation_failure(self, check_name: str) -> None:
        """Record a validation failure."""
        with self._lock:
            self._validation_failures[check_name] += 1
        if self._prometheus_started:
            self._prom_validation_failures.labels(check=check_name).inc()

    def record_quality_score(self, video_id: str, score: float) -> None:
        """Record a transcript quality score."""
        with self._lock:
            self._quality_scores.append(score)
        if self._prometheus_started:
            self._prom_quality.labels(video_id=video_id).set(score)

    def record_metrics(self, metrics: TranscriptMetrics) -> None:
        """Record a full set of transcript metrics at once."""
        with self._lock:
            self._metrics.append(metrics)
            if len(self._metrics) > 10000:
                self._metrics = self._metrics[-10000:]

        if metrics.provider_id:
            self.record_provider_latency(metrics.provider_id, metrics.total_duration_ms)
            self.record_provider_success(metrics.provider_id, len(metrics.errors) == 0)

        if metrics.cache_hit:
            self.record_cache_hit(metrics.cache_level or "unknown")
        else:
            self.record_cache_miss()

        for _ in range(metrics.retry_count):
            self.record_retry(metrics.provider_id)

        for error in metrics.errors:
            self.record_validation_failure(error)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_provider_latency_stats(self, provider_id: str) -> dict[str, float]:
        """Get latency statistics for a provider."""
        with self._lock:
            latencies = self._provider_latencies.get(provider_id, [])
        if not latencies:
            return {"avg": 0, "p50": 0, "p95": 0, "p99": 0, "count": 0}
        sorted_lat = sorted(latencies)
        return {
            "avg": round(sum(sorted_lat) / len(sorted_lat), 2),
            "p50": round(sorted_lat[len(sorted_lat) // 2], 2),
            "p95": round(sorted_lat[int(len(sorted_lat) * 0.95)], 2),
            "p99": round(sorted_lat[int(len(sorted_lat) * 0.99)], 2),
            "count": len(sorted_lat),
        }

    def get_provider_success_rate(self, provider_id: str) -> float:
        """Get the success rate for a provider."""
        with self._lock:
            total, successes = self._provider_success.get(provider_id, (0, 0))
        return successes / max(total, 1)

    def get_cache_hit_rate(self) -> float:
        """Get the overall cache hit rate."""
        with self._lock:
            hits = self._cache_stats["hits"]
            misses = self._cache_stats["misses"]
        return hits / max(hits + misses, 1)

    def get_summary(self) -> dict[str, Any]:
        """Get a comprehensive metrics summary."""
        with self._lock:
            all_total = sum(t for t, _ in self._provider_success.values())
            all_success = sum(s for _, s in self._provider_success.values())

        return {
            "provider_success_rate": round(all_success / max(all_total, 1), 4),
            "cache_hit_rate": round(self.get_cache_hit_rate(), 4),
            "total_requests": all_total,
            "total_failures": all_total - all_success,
            "circuit_breaker_events": dict(self._circuit_breaker_events),
            "retries": dict(self._retry_counts),
            "fallbacks": dict(self._fallback_counts),
            "validation_failures": dict(self._validation_failures),
            "provider_count": len(self._provider_latencies),
            "prometheus_active": self._prometheus_started,
        }
