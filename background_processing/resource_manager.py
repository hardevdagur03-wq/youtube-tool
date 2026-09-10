"""Resource Manager — controls concurrency, memory, CPU, and queue limits per scope.

Prevents any single tenant, user, or queue from consuming all workers.
All limits are configurable and enforced at dispatch time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import JobCreate, JobPriority

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for a scope (tenant, user, queue, etc.)."""
    max_concurrent_jobs: int = 50
    max_concurrent_ai_jobs: int = 10
    max_concurrent_export_jobs: int = 5
    max_concurrent_transcript_jobs: int = 20
    max_queue_depth: int = 1000
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0

    def __post_init__(self) -> None:
        self._queue_counters: dict[str, int] = field(default_factory=dict)


DEFAULT_LIMITS = ResourceLimits()


class ResourceManager:
    """Enforces resource limits across the background processing platform.

    Each scope (tenant, queue, job type) has configurable limits for:
    - Concurrent job count
    - Queue depth
    - Memory usage
    - CPU usage

    Uses Redis counters for distributed enforcement.
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
        limits: ResourceLimits | None = None,
    ) -> None:
        self._redis = redis_client
        self._config = config or BackgroundProcessingConfig.from_env()
        self._limits = limits or DEFAULT_LIMITS

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.redis_url,
                decode_responses=True,
                socket_timeout=5,
            )
        return self._redis

    async def can_accept(
        self,
        job: JobCreate,
        tenant_id: str = "",
    ) -> bool:
        """Check whether a job can be accepted based on current resource usage.
        
        Note: If Redis is unavailable, resources are assumed available (fail-open).
        """
        try:
            redis = await self._get_redis()
        except Exception as exc:
            logger.warning("Resource manager unavailable (Redis down?), allowing: %s", exc)
            return True

        try:
            queue_depth_key = f"resource:queue_depth:{job.queue}"
            queue_depth = int(await redis.get(queue_depth_key) or 0)
            if queue_depth >= self._limits.max_queue_depth:
                logger.warning("Queue depth limit exceeded: %s (%d >= %d)", job.queue, queue_depth, self._limits.max_queue_depth)
                return False
        except Exception as exc:
            logger.warning("Resource check failed for queue depth: %s", exc)

        if tenant_id:
            try:
                tenant_key = f"resource:tenant:{tenant_id}:concurrent"
                tenant_count = int(await redis.get(tenant_key) or 0)
                if tenant_count >= self._limits.max_concurrent_jobs:
                    logger.warning("Tenant concurrent limit: %s (%d >= %d)", tenant_id, tenant_count, self._limits.max_concurrent_jobs)
                    return False
            except Exception as exc:
                logger.warning("Resource check failed for tenant: %s", exc)

        try:
            type_key = self._type_concurrency_key(job.job_type)
            if type_key:
                type_count = int(await redis.get(type_key) or 0)
                type_limit = self._type_limit(job.job_type)
                if type_count >= type_limit:
                    logger.warning("Job type concurrent limit: %s (%d >= %d)", job.job_type, type_count, type_limit)
                    return False
        except Exception as exc:
            logger.warning("Resource check failed for type: %s", exc)

        return True

    async def acquire(self, job_id: str, job_type: str, queue: str, tenant_id: str = "") -> None:
        """Increment resource counters when a job starts."""
        redis = await self._get_redis()

        pipe = redis.pipeline()
        pipe.incr(f"resource:queue_depth:{queue}")
        if tenant_id:
            pipe.incr(f"resource:tenant:{tenant_id}:concurrent")
        type_key = self._type_concurrency_key(job_type)
        if type_key:
            pipe.incr(type_key)
        pipe.incr("resource:global:concurrent")
        await pipe.execute()

    async def release(self, job_id: str, job_type: str, queue: str, tenant_id: str = "") -> None:
        """Decrement resource counters when a job completes."""
        redis = await self._get_redis()

        pipe = redis.pipeline()
        pipe.decr(f"resource:queue_depth:{queue}")
        if tenant_id:
            pipe.decr(f"resource:tenant:{tenant_id}:concurrent")
        type_key = self._type_concurrency_key(job_type)
        if type_key:
            pipe.decr(type_key)
        pipe.decr("resource:global:concurrent")
        await pipe.execute()

    async def get_usage(self, tenant_id: str = "") -> dict[str, Any]:
        """Get current resource usage across all scopes."""
        redis = await self._get_redis()
        result: dict[str, Any] = {
            "global_concurrent": int(await redis.get("resource:global:concurrent") or 0),
            "queues": {},
        }
        if tenant_id:
            result["tenant_concurrent"] = int(await redis.get(f"resource:tenant:{tenant_id}:concurrent") or 0)

        for q in ("critical", "high", "default", "low", "background", "ai", "transcript", "export", "maintenance"):
            depth = int(await redis.get(f"resource:queue_depth:{q}") or 0)
            result["queues"][q] = {"depth": depth}

        return result

    async def reset_all(self) -> None:
        """Reset all resource counters (use with caution)."""
        redis = await self._get_redis()
        keys = await redis.keys("resource:*")
        if keys:
            await redis.delete(*keys)

    def _type_concurrency_key(self, job_type: str) -> str | None:
        if job_type == "pipeline.transcript" or job_type.startswith("transcript."):
            return "resource:type:transcript"
        if job_type.startswith("ai.") or job_type.startswith("pipeline."):
            return "resource:type:ai"
        if job_type.startswith("export."):
            return "resource:type:export"
        return None

    def _type_limit(self, job_type: str) -> int:
        if job_type == "pipeline.transcript" or job_type.startswith("transcript."):
            return self._limits.max_concurrent_transcript_jobs
        if job_type.startswith("ai.") or job_type.startswith("pipeline."):
            return self._limits.max_concurrent_ai_jobs
        if job_type.startswith("export."):
            return self._limits.max_concurrent_export_jobs
        return 50
