"""Metrics — Prometheus metrics and OpenTelemetry instrumentation for workers."""

from __future__ import annotations

import logging
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

# Job counters
jobs_created = Counter(
    "background_jobs_created_total",
    "Total number of jobs created",
    ["job_type", "priority", "queue"],
)

jobs_started = Counter(
    "background_jobs_started_total",
    "Total number of jobs started",
    ["job_type", "queue"],
)

jobs_completed = Counter(
    "background_jobs_completed_total",
    "Total number of jobs completed",
    ["job_type", "queue"],
)

jobs_failed = Counter(
    "background_jobs_failed_total",
    "Total number of jobs failed",
    ["job_type", "queue", "recoverable"],
)

jobs_retried = Counter(
    "background_jobs_retried_total",
    "Total number of job retries",
    ["job_type", "queue"],
)

jobs_cancelled = Counter(
    "background_jobs_cancelled_total",
    "Total number of jobs cancelled",
    ["job_type", "queue"],
)

jobs_dead_letter = Counter(
    "background_jobs_dead_letter_total",
    "Total number of jobs sent to dead letter queue",
    ["job_type", "queue"],
)

# Job durations (histogram)
job_duration_seconds = Histogram(
    "background_job_duration_seconds",
    "Duration of job execution in seconds",
    ["job_type", "queue"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

# Queue gauges
queue_length = Gauge(
    "background_queue_length",
    "Current queue length",
    ["queue_name"],
)

queue_active = Gauge(
    "background_queue_active",
    "Currently active (running) jobs per queue",
    ["queue_name"],
)

queue_latency_seconds = Gauge(
    "background_queue_latency_seconds",
    "Average time jobs spend waiting in queue",
    ["queue_name"],
)

# Worker gauges
worker_count = Gauge(
    "background_worker_count",
    "Number of active workers",
    ["status"],
)

worker_tasks_processed = Counter(
    "background_worker_tasks_processed_total",
    "Total tasks processed by worker",
    ["worker_id", "hostname"],
)

worker_memory_bytes = Gauge(
    "background_worker_memory_bytes",
    "Worker memory usage in bytes",
    ["worker_id"],
)

worker_cpu_percent = Gauge(
    "background_worker_cpu_percent",
    "Worker CPU usage percentage",
    ["worker_id"],
)

# System gauges
system_healthy = Gauge(
    "background_system_healthy",
    "Overall system health (1=healthy, 0=unhealthy)",
)

db_connection_pool_size = Gauge(
    "background_db_connection_pool_size",
    "Database connection pool size",
)

redis_connected = Gauge(
    "background_redis_connected",
    "Redis connection status (1=connected, 0=disconnected)",
)


def start_prometheus_server(port: int = 9800) -> None:
    """Start the Prometheus metrics HTTP server in a background thread."""
    try:
        start_http_server(port)
        logger.info("Prometheus metrics server started on port %d", port)
    except Exception as exc:
        logger.warning("Failed to start Prometheus server on port %d: %s", port, exc)


# ---------------------------------------------------------------------------
# OpenTelemetry Setup
# ---------------------------------------------------------------------------

_otel_initialized = False


def setup_opentelemetry(
    service_name: str = "yt-blog-background-processing",
    exporter_endpoint: str = "",
) -> None:
    """Initialize OpenTelemetry tracing for Celery workers.

    Only call once at worker startup. Configures the Celery instrumentation
    to automatically trace task execution.
    """
    global _otel_initialized
    if _otel_initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })

        provider = TracerProvider(resource=resource)

        if exporter_endpoint:
            exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        CeleryInstrumentor().instrument()
        _otel_initialized = True
        logger.info("OpenTelemetry initialized: service=%s endpoint=%s", service_name, exporter_endpoint or "none")
    except ImportError as exc:
        logger.warning("OpenTelemetry not available: %s", exc)
    except Exception as exc:
        logger.warning("OpenTelemetry init failed: %s", exc)


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------


def record_job_created(job_type: str, priority: str, queue: str) -> None:
    jobs_created.labels(job_type=job_type, priority=priority, queue=queue).inc()


def record_job_started(job_type: str, queue: str) -> None:
    jobs_started.labels(job_type=job_type, queue=queue).inc()


def record_job_completed(job_type: str, queue: str, duration_ms: int = 0) -> None:
    jobs_completed.labels(job_type=job_type, queue=queue).inc()
    if duration_ms > 0:
        job_duration_seconds.labels(job_type=job_type, queue=queue).observe(duration_ms / 1000.0)


def record_job_failed(job_type: str, queue: str, recoverable: bool = True) -> None:
    jobs_failed.labels(job_type=job_type, queue=queue, recoverable=str(recoverable)).inc()


def record_job_retried(job_type: str, queue: str) -> None:
    jobs_retried.labels(job_type=job_type, queue=queue).inc()


def record_job_cancelled(job_type: str, queue: str) -> None:
    jobs_cancelled.labels(job_type=job_type, queue=queue).inc()


def record_job_dead_letter(job_type: str, queue: str) -> None:
    jobs_dead_letter.labels(job_type=job_type, queue=queue).inc()


def update_queue_length(queue_name: str, length: int) -> None:
    queue_length.labels(queue_name=queue_name).set(length)


def update_queue_active(queue_name: str, active: int) -> None:
    queue_active.labels(queue_name=queue_name).set(active)


def update_worker_count(status: str, count: int) -> None:
    worker_count.labels(status=status).set(count)


def mark_system_healthy(healthy: bool) -> None:
    system_healthy.set(1 if healthy else 0)
