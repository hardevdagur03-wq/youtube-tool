"""Queue Router — intelligent job-to-queue routing based on type, priority, and tenant.

No single queue bottleneck.
Routing is extensible and configurable.
"""

from __future__ import annotations

import logging
from typing import Any

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import JobCreate, JobPriority, JobType

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


DEFAULT_QUEUE_MAP: dict[str, str] = {
    JobType.PIPELINE_METADATA.value: "transcript",
    JobType.PIPELINE_TRANSCRIPT.value: "transcript",
    JobType.PIPELINE_ANALYSIS.value: "ai",
    JobType.PIPELINE_KNOWLEDGE_GRAPH.value: "ai",
    JobType.PIPELINE_SEO.value: "ai",
    JobType.PIPELINE_SEO_INTELLIGENCE.value: "ai",
    JobType.PIPELINE_OUTLINE.value: "ai",
    JobType.PIPELINE_SECTIONS.value: "ai",
    JobType.PIPELINE_MERGE.value: "ai",
    JobType.PIPELINE_REVIEW.value: "ai",
    JobType.PIPELINE_OPTIMIZATION.value: "ai",
    JobType.PIPELINE_EXPORT.value: "export",
    JobType.EXPORT_SINGLE.value: "export",
    JobType.EXPORT_BULK.value: "export",
    JobType.CLEANUP_PROJECT.value: "maintenance",
    JobType.CLEANUP_CACHE.value: "maintenance",
    JobType.SYSTEM_BACKUP.value: "maintenance",
    JobType.SYSTEM_HEALTH_CHECK.value: "maintenance",
}

PRIORITY_QUEUE_OVERRIDE: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "low": "low",
    "background": "background",
}


class QueueRouter:
    """Determines the target queue for a job based on type, priority, and tenant.

    Routing strategy:
    1. Job type maps to a functional queue (e.g., ai, transcript, export)
    2. Priority may override to a priority queue (critical, high, low)
    3. Tenant may have dedicated queue isolation
    4. Queue health and load may influence routing

    Business logic never creates Celery tasks directly — it uses this router.
    """

    def __init__(
        self,
        config: BackgroundProcessingConfig | None = None,
        queue_map: dict[str, str] | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._queue_map = {**DEFAULT_QUEUE_MAP, **(queue_map or {})}

    async def route(
        self,
        job: JobCreate,
        tenant_id: str = "",
    ) -> str:
        """Determine the target queue for a job.

        Args:
            job: The job creation request.
            tenant_id: Optional tenant ID for isolated routing.

        Returns:
            Queue name string.
        """
        queue = self._route_by_type(job.job_type)
        queue = self._apply_priority_override(job.priority, queue)
        queue = self._apply_tenant_isolation(tenant_id, queue)
        return queue

    async def route_batch(
        self,
        jobs: list[JobCreate],
        tenant_id: str = "",
    ) -> list[str]:
        """Route multiple jobs, returning a queue per job."""
        return [await self.route(j, tenant_id=tenant_id) for j in jobs]

    def _route_by_type(self, job_type: str) -> str:
        return self._queue_map.get(job_type, "default")

    def _apply_priority_override(self, priority: JobPriority | str, current_queue: str) -> str:
        key = priority.value if isinstance(priority, JobPriority) else priority
        override = PRIORITY_QUEUE_OVERRIDE.get(key)
        if override and override != current_queue:
            logger.debug("Priority override: %s → %s (was %s)", key, override, current_queue)
            return override
        return current_queue

    def _apply_tenant_isolation(self, tenant_id: str, current_queue: str) -> str:
        if tenant_id and self._config:
            return f"{current_queue}:{tenant_id[:8]}"
        return current_queue

    async def get_available_queues(self) -> list[str]:
        """Return all known queue names."""
        queues = set(self._queue_map.values())
        queues.update(PRIORITY_QUEUE_OVERRIDE.values())
        return sorted(queues)

    def register_routing(self, job_type: str, queue: str) -> None:
        """Register or override a job type → queue mapping at runtime."""
        self._queue_map[job_type] = queue
        logger.info("Route registered: %s → %s", job_type, queue)
