"""Background Processing Configuration — Celery, Redis, broker, backend settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BackgroundProcessingConfig:
    """Central configuration for the background processing platform.
    
    All settings are configurable via environment variables with sensible defaults
    for development (Redis on localhost). Override via env for production.
    """

    # --- Broker ---
    broker_url: str = field(
        default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    )
    broker_transport_options: dict[str, Any] = field(default_factory=lambda: {
        "visibility_timeout": int(os.getenv("CELERY_BROKER_VISIBILITY_TIMEOUT", "3600")),
        "max_retries": int(os.getenv("CELERY_BROKER_MAX_RETRIES", "3")),
    })

    # --- Result Backend ---
    result_backend: str = field(
        default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    )
    result_expires: int = int(os.getenv("CELERY_RESULT_EXPIRES", "86400"))
    result_extended: bool = True

    # --- Redis (for locks, events, queues) ---
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0
    redis_retry_on_timeout: bool = True
    redis_health_check_interval: int = 30

    # --- Event Bus ---
    event_bus_redis_url: str = field(
        default_factory=lambda: os.getenv("EVENT_BUS_REDIS_URL", "redis://localhost:6379/1")
    )

    # --- Worker ---
    worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))
    worker_prefetch_multiplier: int = int(os.getenv("CELERY_WORKER_PREFETCH", "1"))
    worker_max_tasks_per_child: int = int(os.getenv("CELERY_WORKER_MAX_TASKS", "1000"))
    worker_max_memory_per_child: int = int(os.getenv("CELERY_WORKER_MAX_MEMORY", "200000"))
    worker_send_task_events: bool = True
    worker_task_log_format: str = "[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s"

    # --- Queues ---
    task_queues: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "critical": {"exchange": "critical", "routing_key": "critical", "priority": 0},
        "high": {"exchange": "high", "routing_key": "high", "priority": 3},
        "default": {"exchange": "default", "routing_key": "default", "priority": 5},
        "low": {"exchange": "low", "routing_key": "low", "priority": 8},
        "background": {"exchange": "background", "routing_key": "background", "priority": 10},
        "system": {"exchange": "system", "routing_key": "system", "priority": 1},
    })

    # --- Task Routing ---
    task_routes: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "pipeline.*": {"queue": "high"},
        "export.*": {"queue": "default"},
        "cleanup.*": {"queue": "background"},
        "system.*": {"queue": "system"},
        "ai.*": {"queue": "high"},
    })

    # --- Retry ---
    default_retry_max: int = int(os.getenv("CELERY_DEFAULT_RETRY_MAX", "3"))
    default_retry_delay: int = int(os.getenv("CELERY_DEFAULT_RETRY_DELAY", "60"))
    default_retry_backoff: bool = True
    default_retry_backoff_max: int = int(os.getenv("CELERY_DEFAULT_RETRY_BACKOFF_MAX", "600"))
    retry_jitter: bool = True

    # --- Dead Letter Queue ---
    dead_letter_queue_name: str = os.getenv("DEAD_LETTER_QUEUE", "dead_letter")
    dead_letter_max_retries: int = int(os.getenv("DEAD_LETTER_MAX_RETRIES", "5"))

    # --- Scheduling ---
    beat_schedule: dict[str, Any] = field(default_factory=dict)
    beat_max_loop_interval: int = 30

    # --- Locks ---
    lock_ttl: int = int(os.getenv("DISTRIBUTED_LOCK_TTL", "300"))
    lock_retry_interval: float = 0.1
    lock_max_retries: int = int(os.getenv("DISTRIBUTED_LOCK_MAX_RETRIES", "50"))

    # --- Progress ---
    progress_emit_interval: float = 0.5
    progress_channel_prefix: str = "progress:"

    # --- Batch ---
    batch_max_size: int = int(os.getenv("BATCH_MAX_SIZE", "100"))
    batch_chunk_size: int = int(os.getenv("BATCH_CHUNK_SIZE", "10"))

    # --- Monitoring ---
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9800"))
    flower_port: int = int(os.getenv("FLOWER_PORT", "5555"))
    flower_auth: bool = os.getenv("FLOWER_AUTH", "").lower() in ("1", "true", "yes")
    opentelemetry_enabled: bool = os.getenv("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")
    opentelemetry_service_name: str = os.getenv("OTEL_SERVICE_NAME", "yt-blog-background-processing")
    opentelemetry_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    # --- Database ---
    db_pool_size: int = int(os.getenv("BACKGROUND_DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("BACKGROUND_DB_MAX_OVERFLOW", "20"))

    @classmethod
    def from_env(cls) -> BackgroundProcessingConfig:
        return cls()

    @property
    def celery_kwargs(self) -> dict[str, Any]:
        return {
            "broker_url": self.broker_url,
            "result_backend": self.result_backend,
            "result_expires": self.result_expires,
            "result_extended": self.result_extended,
            "worker_send_task_events": self.worker_send_task_events,
            "worker_prefetch_multiplier": self.worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.worker_max_tasks_per_child,
            "worker_max_memory_per_child": self.worker_max_memory_per_child,
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_store_errors_even_if_ignored": True,
        }
