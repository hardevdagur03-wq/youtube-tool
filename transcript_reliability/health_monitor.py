"""Provider Health Monitor — continuously monitors provider health.

Maintains rolling health scores per provider, automatically downgrades
unhealthy providers, and provides real-time health status.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import ProviderStatus
from transcript_reliability.models import HealthRecord, ProviderHealth, ProviderStats

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors provider health using rolling window statistics.

    Maintains per-provider health records within a configurable time window.
    Automatically computes health scores and downgrades unhealthy providers.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()
        self._lock = threading.Lock()
        # provider_id -> deque of HealthRecord
        self._records: dict[str, deque[HealthRecord]] = defaultdict(
            lambda: deque(maxlen=self._config.health_window_max_requests)
        )
        # provider_id -> cached ProviderHealth
        self._cached_health: dict[str, ProviderHealth] = {}
        # provider_id -> aggregate stats
        self._stats: dict[str, ProviderStats] = {}

    def record_success(
        self,
        provider_id: str,
        latency_ms: float = 0.0,
        quota_remaining: float = 1.0,
    ) -> None:
        """Record a successful provider request.

        Args:
            provider_id: Provider identifier.
            latency_ms: Request latency in milliseconds.
            quota_remaining: Remaining quota as ratio (0.0-1.0).
        """
        with self._lock:
            record = HealthRecord(
                timestamp=time.time(),
                success=True,
                latency_ms=latency_ms,
                quota_remaining=quota_remaining,
            )
            self._records[provider_id].append(record)
            self._invalidate_cache(provider_id)

    def record_failure(
        self,
        provider_id: str,
        error_type: str = "",
        latency_ms: float = 0.0,
        quota_remaining: float = 1.0,
    ) -> None:
        """Record a failed provider request.

        Args:
            provider_id: Provider identifier.
            error_type: Type/category of error.
            latency_ms: Request latency in milliseconds.
            quota_remaining: Remaining quota as ratio (0.0-1.0).
        """
        with self._lock:
            record = HealthRecord(
                timestamp=time.time(),
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
                quota_remaining=quota_remaining,
            )
            self._records[provider_id].append(record)
            self._invalidate_cache(provider_id)

    def _invalidate_cache(self, provider_id: str) -> None:
        self._cached_health.pop(provider_id, None)
        self._stats.pop(provider_id, None)

    def get_health(self, provider_id: str) -> ProviderHealth:
        """Get current health status for a provider.

        Computes rolling window statistics and returns a health summary.
        Results are cached and recomputed on new records.

        Args:
            provider_id: Provider identifier.

        Returns:
            ``ProviderHealth`` with current status and statistics.
        """
        with self._lock:
            cached = self._cached_health.get(provider_id)
            if cached is not None:
                return cached

            records = self._records.get(provider_id, deque())
            now = time.time()
            window_start = now - self._config.health_window_seconds

            # Filter records within the rolling window
            window_records = [r for r in records if r.timestamp >= window_start]
            recent_records = [r for r in records if r.timestamp >= now - 300]  # last 5 min

            if not window_records:
                health = ProviderHealth(
                    provider_id=provider_id,
                    status=ProviderStatus.UNKNOWN,
                    rolling_window_seconds=self._config.health_window_seconds,
                )
                self._cached_health[provider_id] = health
                return health

            total = len(window_records)
            successes = sum(1 for r in window_records if r.success)
            failures = total - successes
            success_rate = successes / max(total, 1)
            latencies = [r.latency_ms for r in window_records if r.success]
            avg_latency = sum(latencies) / max(len(latencies), 1)
            sorted_latencies = sorted(latencies)
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0
            avg_quota = sum(r.quota_remaining for r in window_records) / max(total, 1)

            # Determine status based on thresholds
            status = ProviderStatus.HEALTHY
            if success_rate < self._config.health_disable_threshold:
                status = ProviderStatus.UNHEALTHY
            elif success_rate < self._config.health_downgrade_threshold:
                status = ProviderStatus.DEGRADED

            # Collect recent errors
            recent_errors = [
                {
                    "timestamp": r.timestamp,
                    "error_type": r.error_type,
                    "latency_ms": r.latency_ms,
                }
                for r in recent_records if not r.success
            ][-10:]  # last 10 errors

            last_error_record = next(
                (r for r in reversed(window_records) if not r.success),
                None,
            )
            last_success_record = next(
                (r for r in reversed(window_records) if r.success),
                None,
            )

            health = ProviderHealth(
                provider_id=provider_id,
                status=status,
                availability=success_rate,
                success_rate=success_rate,
                avg_latency_ms=round(avg_latency, 2),
                p95_latency_ms=round(p95, 2),
                p99_latency_ms=round(p99, 2),
                failure_count=failures,
                total_requests=total,
                quota_usage=avg_quota,
                last_error=last_error_record.error_type if last_error_record else "",
                last_error_at=str(last_error_record.timestamp) if last_error_record else "",
                last_success_at=str(last_success_record.timestamp) if last_success_record else "",
                rolling_window_seconds=self._config.health_window_seconds,
                recent_errors=recent_errors,
            )
            self._cached_health[provider_id] = health
            return health

    def get_stats(self, provider_id: str) -> ProviderStats:
        """Get aggregate statistics for a provider.

        Args:
            provider_id: Provider identifier.

        Returns:
            ``ProviderStats`` with aggregate data.
        """
        with self._lock:
            cached = self._stats.get(provider_id)
            if cached is not None:
                return cached

            records = self._records.get(provider_id, deque())
            now = time.time()

            if not records:
                stats = ProviderStats(
                    provider_id=provider_id,
                    window_start=now - self._config.health_window_seconds,
                    window_end=now,
                )
                self._stats[provider_id] = stats
                return stats

            total = len(records)
            successes = sum(1 for r in records if r.success)
            failures = total - successes
            latencies = [r.latency_ms for r in records if r.success]
            avg_latency = sum(latencies) / max(len(latencies), 1)
            sorted_latencies = sorted(latencies)
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0
            start_time = min((r.timestamp for r in records), default=now)
            end_time = max((r.timestamp for r in records), default=now)

            stats = ProviderStats(
                provider_id=provider_id,
                total_requests=total,
                successful_requests=successes,
                failed_requests=failures,
                total_latency_ms=sum(latencies),
                avg_latency_ms=round(avg_latency, 2),
                p95_latency_ms=round(p95, 2),
                p99_latency_ms=round(p99, 2),
                window_start=start_time,
                window_end=end_time,
            )
            self._stats[provider_id] = stats
            return stats

    def get_all_health(self) -> dict[str, ProviderHealth]:
        """Get health status for all tracked providers."""
        provider_ids = list(self._records.keys())
        return {pid: self.get_health(pid) for pid in provider_ids}

    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of all provider health."""
        all_health = self.get_all_health()
        return {
            "providers": {
                pid: {
                    "status": h.status.value,
                    "success_rate": round(h.success_rate, 3),
                    "avg_latency_ms": h.avg_latency_ms,
                    "total_requests": h.total_requests,
                    "failure_count": h.failure_count,
                }
                for pid, h in all_health.items()
            },
            "healthy_count": sum(
                1 for h in all_health.values() if h.status == ProviderStatus.HEALTHY
            ),
            "degraded_count": sum(
                1 for h in all_health.values() if h.status == ProviderStatus.DEGRADED
            ),
            "unhealthy_count": sum(
                1 for h in all_health.values() if h.status == ProviderStatus.UNHEALTHY
            ),
        }

    def reset(self, provider_id: str) -> None:
        """Reset health tracking for a provider."""
        with self._lock:
            self._records.pop(provider_id, None)
            self._cached_health.pop(provider_id, None)
            self._stats.pop(provider_id, None)

    def reset_all(self) -> None:
        """Reset all health tracking."""
        with self._lock:
            self._records.clear()
            self._cached_health.clear()
            self._stats.clear()
