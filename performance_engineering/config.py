"""Performance Engineering Configuration — all settings environment-driven."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if not val:
        return default
    return val in ("1", "true", "yes", "y")


def _env_list(key: str, default: str) -> list[str]:
    val = os.environ.get(key, default)
    return [v.strip() for v in val.split(",") if v.strip()]


@dataclass
class PerformanceConfig:
    """Performance engineering configuration — all env-driven."""

    # Async executor
    async_max_workers: int = _env_int("PERF_ASYNC_MAX_WORKERS", 8)
    async_executor_timeout: int = _env_int("PERF_ASYNC_EXECUTOR_TIMEOUT", 60)
    async_enabled: bool = _env_bool("PERF_ASYNC_ENABLED", True)

    # Parallel scheduler
    parallel_enabled: bool = _env_bool("PERF_PARALLEL_ENABLED", True)
    parallel_max_concurrent_stages: int = _env_int("PERF_PARALLEL_MAX_CONCURRENT", 4)

    # Batch AI
    batch_ai_enabled: bool = _env_bool("PERF_BATCH_AI_ENABLED", True)
    batch_ai_max_tasks: int = _env_int("PERF_BATCH_AI_MAX_TASKS", 5)

    # Cache
    cache_prompt_enabled: bool = _env_bool("PERF_CACHE_PROMPT_ENABLED", True)
    cache_prompt_ttl: int = _env_int("PERF_CACHE_PROMPT_TTL", 86400)
    cache_embedding_enabled: bool = _env_bool("PERF_CACHE_EMBEDDING_ENABLED", True)
    cache_embedding_ttl: int = _env_int("PERF_CACHE_EMBEDDING_TTL", 604800)
    cache_query_enabled: bool = _env_bool("PERF_CACHE_QUERY_ENABLED", True)
    cache_query_ttl: int = _env_int("PERF_CACHE_QUERY_TTL", 600)

    # Connection pool
    pool_http_max_connections: int = _env_int("PERF_POOL_HTTP_MAX_CONNECTIONS", 100)
    pool_http_max_keepalive: int = _env_int("PERF_POOL_HTTP_MAX_KEEPALIVE", 30)
    pool_db_pool_size: int = _env_int("PERF_POOL_DB_POOL_SIZE", 20)
    pool_db_max_overflow: int = _env_int("PERF_POOL_DB_MAX_OVERFLOW", 40)
    pool_redis_max_connections: int = _env_int("PERF_POOL_REDIS_MAX_CONNECTIONS", 50)

    # Streaming
    streaming_enabled: bool = _env_bool("PERF_STREAMING_ENABLED", True)
    streaming_buffer_size: int = _env_int("PERF_STREAMING_BUFFER_SIZE", 8192)

    # Queue
    queue_ai_concurrency: int = _env_int("PERF_QUEUE_AI_CONCURRENCY", 4)
    queue_export_concurrency: int = _env_int("PERF_QUEUE_EXPORT_CONCURRENCY", 2)

    # Memory
    memory_max_heap_mb: int = _env_int("PERF_MEMORY_MAX_HEAP_MB", 500)
    memory_gc_threshold: int = _env_int("PERF_MEMORY_GC_THRESHOLD", 10000)
    memory_track_enabled: bool = _env_bool("PERF_MEMORY_TRACK_ENABLED", True)

    # Benchmarking
    benchmark_enabled: bool = _env_bool("PERF_BENCHMARK_ENABLED", False)
    benchmark_warmup_requests: int = _env_int("PERF_BENCHMARK_WARMUP", 100)
    benchmark_sample_size: int = _env_int("PERF_BENCHMARK_SAMPLE_SIZE", 1000)

    @classmethod
    def from_env(cls) -> PerformanceConfig:
        return cls()
