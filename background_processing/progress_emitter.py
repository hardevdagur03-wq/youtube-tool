"""Progress Emitter — real-time job progress via Redis Pub/Sub.

Each job emits structured progress events that the frontend receives
through WebSocket/SSE relay. Progress is also persisted to the database.
"""

from __future__ import annotations

import logging
from typing import Any

from background_processing.event_bus import EventBus, EventType, get_event_bus
from background_processing.job_repository import JobRepository

logger = logging.getLogger(__name__)


class ProgressEmitter:
    """Emits real-time progress events and persists them to the database.

    Usage:
        emitter = ProgressEmitter(repo, event_bus)
        await emitter.on_started(job_id, project_id)
        await emitter.on_progress(job_id, project_id, 50, "Processing transcript...")
        await emitter.on_completed(job_id, project_id, result={...})
    """

    def __init__(
        self,
        job_repo: JobRepository,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repo = job_repo
        self._bus = event_bus or get_event_bus()

    async def on_created(
        self, job_id: str, project_id: str, job_type: str = ""
    ) -> None:
        await self._bus.publish_event(
            project_id, EventType.JOB_CREATED,
            {"job_id": job_id, "job_type": job_type},
        )

    async def on_queued(
        self, job_id: str, project_id: str
    ) -> None:
        await self._bus.publish_event(
            project_id, EventType.JOB_QUEUED,
            {"job_id": job_id},
        )

    async def on_started(
        self, job_id: str, project_id: str, worker_id: str = ""
    ) -> None:
        await self._repo.update_status(job_id, "running", worker_id=worker_id)
        await self._bus.publish_event(
            project_id, EventType.JOB_STARTED,
            {"job_id": job_id, "worker_id": worker_id},
        )

    async def on_progress(
        self,
        job_id: str,
        project_id: str,
        pct: float,
        message: str = "",
        stage: str = "",
        detail: dict[str, Any] | None = None,
    ) -> None:
        await self._repo.update_progress(job_id, pct, message, stage, detail)
        await self._bus.publish_progress(
            project_id, job_id, pct, message, stage, detail,
        )

    async def on_stage_completed(
        self,
        job_id: str,
        project_id: str,
        stage: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        await self._bus.publish_event(
            project_id, EventType.STAGE_COMPLETED,
            {"job_id": job_id, "stage": stage, "result": result or {}},
        )

    async def on_stage_failed(
        self,
        job_id: str,
        project_id: str,
        stage: str,
        error: str = "",
    ) -> None:
        await self._bus.publish_event(
            project_id, EventType.STAGE_FAILED,
            {"job_id": job_id, "stage": stage, "error": error},
        )

    async def on_completed(
        self,
        job_id: str,
        project_id: str,
        duration_ms: int = 0,
        result: dict[str, Any] | None = None,
    ) -> None:
        await self._repo.update_status(
            job_id, "completed",
            finished_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            duration_ms=duration_ms,
            result_data=result or {},
        )
        await self._bus.publish_event(
            project_id, EventType.JOB_COMPLETED,
            {"job_id": job_id, "duration_ms": duration_ms},
        )

    async def on_failed(
        self,
        job_id: str,
        project_id: str,
        error: str = "",
        traceback: str = "",
        recoverable: bool = True,
    ) -> None:
        await self._repo.update_status(
            job_id, "failed",
            error=error,
            traceback=traceback,
            recoverable=recoverable,
        )
        await self._bus.publish_event(
            project_id, EventType.JOB_FAILED,
            {"job_id": job_id, "error": error, "recoverable": recoverable},
        )

    async def on_cancelled(
        self, job_id: str, project_id: str, reason: str = ""
    ) -> None:
        await self._repo.update_status(job_id, "cancelled", error=reason)
        await self._bus.publish_event(
            project_id, EventType.JOB_CANCELLED,
            {"job_id": job_id, "reason": reason},
        )

    async def on_retrying(
        self,
        job_id: str,
        project_id: str,
        attempt: int,
        max_retries: int,
        error: str = "",
    ) -> None:
        await self._repo.update_status(job_id, "retrying")
        await self._bus.publish_event(
            project_id, EventType.JOB_RETRYING,
            {
                "job_id": job_id,
                "attempt": attempt,
                "max_retries": max_retries,
                "error": error,
            },
        )

    async def on_dead_letter(
        self, job_id: str, project_id: str, error: str = ""
    ) -> None:
        await self._repo.update_status(job_id, "dead_letter", error=error)
        await self._bus.publish_event(
            project_id, EventType.JOB_DEAD_LETTER,
            {"job_id": job_id, "error": error},
        )

    async def on_recovered(
        self, job_id: str, project_id: str
    ) -> None:
        await self._repo.update_status(job_id, "recovered")
        await self._bus.publish_event(
            project_id, EventType.JOB_RECOVERED,
            {"job_id": job_id},
        )
