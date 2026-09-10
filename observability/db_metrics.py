"""Database Metrics — monitors connection pool, query performance, and replication health.

Tracks:
- Active/idle/waiting connections
- Connection pool utilization
- Query execution time (P50/P95/P99)
- Slow query count
- Transaction rate and rollback rate
- Cache hit ratio
- Replication lag
- Deadlock count
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from observability.logger import get_logger

logger = get_logger(__name__)

PREFIX = "youtube_seo_database"

# Connection pool gauges
db_connections_active = Gauge(f"{PREFIX}_connections_active", "Active database connections")
db_connections_idle = Gauge(f"{PREFIX}_connections_idle", "Idle database connections")
db_connections_waiting = Gauge(f"{PREFIX}_connections_waiting", "Connections waiting in pool")
db_connections_usage_pct = Gauge(f"{PREFIX}_connections_usage_pct", "Connection pool usage percentage")
db_pool_size = Gauge(f"{PREFIX}_pool_size", "Maximum connection pool size")
db_pool_overflow = Gauge(f"{PREFIX}_pool_overflow", "Connection pool overflow count")

# Query performance
query_duration = Histogram(
    f"{PREFIX}_query_duration_seconds",
    "Query execution duration",
    ["query_type", "table"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
)
slow_queries = Counter(f"{PREFIX}_slow_queries_total", "Slow queries (>threshold)", ["query_type", "table"])
queries_total = Counter(f"{PREFIX}_queries_total", "Total queries executed", ["query_type", "table"])

# Transactions
transactions_total = Counter(f"{PREFIX}_transactions_total", "Total transactions", ["type"])
transactions_rollback = Counter(f"{PREFIX}_transactions_rollback_total", "Transaction rollbacks", ["type"])
transaction_duration = Histogram(
    f"{PREFIX}_transaction_duration_seconds",
    "Transaction duration",
    ["type"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0),
)

# Cache
cache_hit_ratio = Gauge(f"{PREFIX}_cache_hit_ratio", "Database cache hit ratio (0-1)")
query_cache_hits = Counter(f"{PREFIX}_query_cache_hits_total", "Query cache hits")
query_cache_misses = Counter(f"{PREFIX}_query_cache_misses_total", "Query cache misses")

# Replication & health
db_replication_lag = Gauge(f"{PREFIX}_replication_lag_seconds", "Replication lag in seconds")
db_deadlocks = Counter(f"{PREFIX}_deadlocks_total", "Database deadlock count")
db_health = Gauge(f"{PREFIX}_health", "Database health (1=healthy, 0=unhealthy)")

# Slow query latency percentiles
db_query_latency_p50 = Gauge(f"{PREFIX}_query_latency_p50_seconds", "P50 query latency", ["query_type"])
db_query_latency_p95 = Gauge(f"{PREFIX}_query_latency_p95_seconds", "P95 query latency", ["query_type"])
db_query_latency_p99 = Gauge(f"{PREFIX}_query_latency_p99_seconds", "P99 query latency", ["query_type"])


@dataclass
class DatabaseMetricsSnapshot:
    active_connections: int = 0
    idle_connections: int = 0
    pool_usage_pct: float = 0.0
    total_queries: int = 0
    slow_query_count: int = 0
    cache_hit_ratio: float = 0.0
    replication_lag_seconds: float = 0.0
    deadlock_count: int = 0
    transaction_count: int = 0
    rollback_count: int = 0
    avg_query_latency_ms: float = 0.0
    timestamp: str = ""


class DatabaseMetricsCollector:
    """Collects and exposes database performance metrics to Prometheus."""

    def __init__(self):
        self._query_times: dict[str, list[float]] = defaultdict(list)

    def record_query(
        self,
        query_type: str,
        table: str = "",
        duration_ms: float = 0.0,
        slow_threshold_ms: float = 1000.0,
    ) -> None:
        queries_total.labels(query_type=query_type, table=table or "unknown").inc()
        if duration_ms > 0:
            query_duration.labels(query_type=query_type, table=table or "unknown").observe(duration_ms / 1000.0)
            key = f"{query_type}:{table}"
            self._query_times[key].append(duration_ms)
            if len(self._query_times[key]) > 1000:
                self._query_times[key] = self._query_times[key][-1000:]
        if duration_ms > slow_threshold_ms:
            slow_queries.labels(query_type=query_type, table=table or "unknown").inc()

    def record_transaction(self, tx_type: str = "read") -> None:
        transactions_total.labels(type=tx_type).inc()

    def record_rollback(self, tx_type: str = "read") -> None:
        transactions_rollback.labels(type=tx_type).inc()

    def record_transaction_duration(self, tx_type: str, duration_ms: float) -> None:
        transaction_duration.labels(type=tx_type).observe(duration_ms / 1000.0)

    def update_connection_pool(
        self, active: int, idle: int, waiting: int, pool_size: int, overflow: int = 0,
    ) -> None:
        db_connections_active.set(active)
        db_connections_idle.set(idle)
        db_connections_waiting.set(waiting)
        db_pool_size.set(pool_size)
        db_pool_overflow.set(overflow)
        total = active + idle
        usage = (active / total * 100) if total > 0 else 0
        db_connections_usage_pct.set(usage)

    def record_cache_hit(self) -> None:
        query_cache_hits.inc()

    def record_cache_miss(self) -> None:
        query_cache_misses.inc()

    def update_cache_hit_ratio(self, ratio: float) -> None:
        cache_hit_ratio.set(max(0.0, min(1.0, ratio)))

    def update_replication_lag(self, lag_seconds: float) -> None:
        db_replication_lag.set(lag_seconds)

    def record_deadlock(self) -> None:
        db_deadlocks.inc()

    def mark_healthy(self, healthy: bool) -> None:
        db_health.set(1 if healthy else 0)

    def update_query_percentiles(self) -> None:
        for key, times in self._query_times.items():
            if not times:
                continue
            query_type = key.split(":")[0]
            sorted_times = sorted(times)
            n = len(sorted_times)
            db_query_latency_p50.labels(query_type=query_type).set(sorted_times[int(n * 0.5)] / 1000.0)
            db_query_latency_p95.labels(query_type=query_type).set(sorted_times[int(n * 0.95)] / 1000.0)
            db_query_latency_p99.labels(query_type=query_type).set(sorted_times[int(n * 0.99)] / 1000.0)

    def get_snapshot(self) -> DatabaseMetricsSnapshot:
        return DatabaseMetricsSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


_db_metrics: DatabaseMetricsCollector | None = None


def get_db_metrics() -> DatabaseMetricsCollector:
    global _db_metrics
    if _db_metrics is None:
        _db_metrics = DatabaseMetricsCollector()
    return _db_metrics
