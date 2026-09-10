"""Queue & Worker Metrics — monitors Celery queue health, worker utilization, job throughput.

Tracks:
- Queue length per queue (critical, high, default, low, etc.)
- Queue latency (time jobs wait before processing)
- Worker count, status, utilization
- Job throughput, retry rate, dead letter rate
- Worker CPU/memory usage
- Queue backlog alerts
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from observability.logger import get_logger

logger = get_logger(__name__)

PREFIX = "youtube_seo_queue"

# Gauges — queue state
queue_length = Gauge(f"{PREFIX}_length", "Current queue length", ["queue_name"])
queue_active = Gauge(f"{PREFIX}_active", "Currently active jobs in queue", ["queue_name"])
queue_reserved = Gauge(f"{PREFIX}_reserved", "Reserved jobs in queue", ["queue_name"])
queue_scheduled = Gauge(f"{PREFIX}_scheduled", "Scheduled jobs in queue", ["queue_name"])
queue_latency_seconds = Gauge(f"{PREFIX}_latency_seconds", "Avg job wait time in queue", ["queue_name"])
queue_throughput = Gauge(f"{PREFIX}_throughput_per_minute", "Jobs processed per minute", ["queue_name"])
queue_backlog = Gauge(f"{PREFIX}_backlog", "Backlog depth (length exceeding threshold)", ["queue_name"])

# Counters — job lifecycle
jobs_created = Counter(f"{PREFIX}_created_total", "Jobs created", ["queue_name", "job_type"])
jobs_started = Counter(f"{PREFIX}_started_total", "Jobs started", ["queue_name", "job_type"])
jobs_completed = Counter(f"{PREFIX}_completed_total", "Jobs completed", ["queue_name", "job_type"])
jobs_failed = Counter(f"{PREFIX}_failed_total", "Jobs failed", ["queue_name", "job_type", "recoverable"])
jobs_retried = Counter(f"{PREFIX}_retried_total", "Jobs retried", ["queue_name", "job_type"])
jobs_dead_letter = Counter(f"{PREFIX}_dead_letter_total", "Jobs sent to DLQ", ["queue_name", "job_type"])
jobs_cancelled = Counter(f"{PREFIX}_cancelled_total", "Jobs cancelled", ["queue_name", "job_type"])

# Histograms
job_duration = Histogram(
    f"{PREFIX}_job_duration_seconds",
    "Job execution duration",
    ["queue_name", "job_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)
job_queue_time = Histogram(
    f"{PREFIX}_job_queue_time_seconds",
    "Time job spent in queue before processing",
    ["queue_name", "job_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

# Worker gauges
worker_count = Gauge(f"{PREFIX}_worker_count", "Total workers", ["status"])
worker_cpu_percent = Gauge(f"{PREFIX}_worker_cpu_percent", "Worker CPU usage", ["worker_id", "queue_name"])
worker_memory_bytes = Gauge(f"{PREFIX}_worker_memory_bytes", "Worker memory usage", ["worker_id"])
worker_memory_percent = Gauge(f"{PREFIX}_worker_memory_percent", "Worker memory percent", ["worker_id"])
worker_tasks_processed = Counter(f"{PREFIX}_worker_tasks_processed_total", "Tasks processed by worker", ["worker_id", "queue_name"])

# System gauges
system_healthy = Gauge(f"{PREFIX}_system_healthy", "Overall system health (1=healthy)", ["component"])


@dataclass
class QueueMetricsSnapshot:
    queue_name: str = ""
    length: int = 0
    active: int = 0
    reserved: int = 0
    scheduled: int = 0
    total_created: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    dead_letter_count: int = 0
    avg_latency_ms: float = 0.0
    throughput_per_minute: float = 0.0
    timestamp: str = ""


class QueueMetricsCollector:
    """Collects and exposes queue and worker metrics to Prometheus."""

    def __init__(self):
        self._throughput_counts: dict[str, list[float]] = defaultdict(list)

    def update_queue_length(self, queue_name: str, length: int) -> None:
        queue_length.labels(queue_name=queue_name).set(length)

    def update_queue_active(self, queue_name: str, active: int) -> None:
        queue_active.labels(queue_name=queue_name).set(active)

    def update_queue_reserved(self, queue_name: str, reserved: int) -> None:
        queue_reserved.labels(queue_name=queue_name).set(reserved)

    def update_queue_scheduled(self, queue_name: str, scheduled: int) -> None:
        queue_scheduled.labels(queue_name=queue_name).set(scheduled)

    def update_queue_latency(self, queue_name: str, latency_seconds: float) -> None:
        queue_latency_seconds.labels(queue_name=queue_name).set(latency_seconds)

    def update_queue_throughput(self, queue_name: str, throughput: float) -> None:
        queue_throughput.labels(queue_name=queue_name).set(throughput)

    def update_queue_backlog(self, queue_name: str, backlog: int) -> None:
        queue_backlog.labels(queue_name=queue_name).set(backlog)

    def record_job_created(self, queue_name: str, job_type: str) -> None:
        jobs_created.labels(queue_name=queue_name, job_type=job_type).inc()
        self._record_throughput(queue_name)

    def record_job_started(self, queue_name: str, job_type: str) -> None:
        jobs_started.labels(queue_name=queue_name, job_type=job_type).inc()

    def record_job_completed(self, queue_name: str, job_type: str, duration_ms: int = 0) -> None:
        jobs_completed.labels(queue_name=queue_name, job_type=job_type).inc()
        if duration_ms > 0:
            job_duration.labels(queue_name=queue_name, job_type=job_type).observe(duration_ms / 1000.0)

    def record_job_failed(self, queue_name: str, job_type: str, recoverable: bool = True) -> None:
        jobs_failed.labels(queue_name=queue_name, job_type=job_type, recoverable=str(recoverable)).inc()

    def record_job_retried(self, queue_name: str, job_type: str) -> None:
        jobs_retried.labels(queue_name=queue_name, job_type=job_type).inc()

    def record_job_dead_letter(self, queue_name: str, job_type: str) -> None:
        jobs_dead_letter.labels(queue_name=queue_name, job_type=job_type).inc()

    def record_job_cancelled(self, queue_name: str, job_type: str) -> None:
        jobs_cancelled.labels(queue_name=queue_name, job_type=job_type).inc()

    def record_job_queue_time(self, queue_name: str, job_type: str, seconds: float) -> None:
        job_queue_time.labels(queue_name=queue_name, job_type=job_type).observe(seconds)

    def update_worker_count(self, status: str, count: int) -> None:
        worker_count.labels(status=status).set(count)

    def update_worker_cpu(self, worker_id: str, cpu: float, queue_name: str = "") -> None:
        worker_cpu_percent.labels(worker_id=worker_id, queue_name=queue_name or "unknown").set(cpu)

    def update_worker_memory(self, worker_id: str, memory_bytes: int, memory_percent: float = 0.0) -> None:
        worker_memory_bytes.labels(worker_id=worker_id).set(memory_bytes)
        worker_memory_percent.labels(worker_id=worker_id).set(memory_percent)

    def record_worker_task(self, worker_id: str, queue_name: str) -> None:
        worker_tasks_processed.labels(worker_id=worker_id, queue_name=queue_name).inc()

    def mark_system_healthy(self, component: str, healthy: bool) -> None:
        system_healthy.labels(component=component).set(1 if healthy else 0)

    def _record_throughput(self, queue_name: str) -> None:
        now = time.time()
        self._throughput_counts[queue_name].append(now)
        cutoff = now - 60
        self._throughput_counts[queue_name] = [t for t in self._throughput_counts[queue_name] if t > cutoff]

    def get_throughput(self, queue_name: str) -> float:
        now = time.time()
        cutoff = now - 60
        recent = [t for t in self._throughput_counts.get(queue_name, []) if t > cutoff]
        return len(recent)

    def get_snapshot(self, queue_name: str = "") -> QueueMetricsSnapshot:
        return QueueMetricsSnapshot(
            queue_name=queue_name or "all",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


_queue_metrics: QueueMetricsCollector | None = None


def get_queue_metrics() -> QueueMetricsCollector:
    global _queue_metrics
    if _queue_metrics is None:
        _queue_metrics = QueueMetricsCollector()
    return _queue_metrics
