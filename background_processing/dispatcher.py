"""Job Dispatcher — service abstraction for creating, routing, and managing async jobs.

Business logic must NEVER directly create Celery tasks.
All job creation flows through this dispatcher.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from celery import Celery

from background_processing.celery_app import get_celery_app
from background_processing.config import BackgroundProcessingConfig
from background_processing.distributed_lock import DistributedLock
from background_processing.event_bus import EventBus, EventType, get_event_bus
from background_processing.idempotency import IdempotencyEngine
from background_processing.job_repository import JobRepository
from background_processing.models import (
    BatchJobRequest, BatchJobResponse, JobCreate, JobModel,
    JobPriority, JobResponse, JobStatus, JobType, make_uuid, utc_now,
)
from background_processing.progress_emitter import ProgressEmitter
from background_processing.queue_router import QueueRouter
from background_processing.rate_limiter import RateLimiter
from background_processing.resource_manager import ResourceManager
from background_processing.security import PayloadValidationError, SecurityManager
from background_processing.task_registry import resolve as resolve_task_path

logger = logging.getLogger(__name__)


class JobDispatchError(Exception):
    """Raised when a job cannot be dispatched."""


class JobDispatcher:
    """Enterprise job dispatcher — routes, validates, and submits jobs.

    Features:
    - Idempotent job creation via unique job keys
    - Intelligent queue routing based on type/priority/tenant
    - Rate limiting per tenant/project/user
    - Resource management (concurrency, quotas)
    - Distributed locking for critical operations
    - Full lifecycle event emission
    - Batch dispatch with fan-out/fan-in
    """

    def __init__(
        self,
        job_repo: JobRepository,
        queue_router: QueueRouter | None = None,
        idempotency: IdempotencyEngine | None = None,
        rate_limiter: RateLimiter | None = None,
        resource_manager: ResourceManager | None = None,
        distributed_lock: DistributedLock | None = None,
        event_bus: EventBus | None = None,
        progress_emitter: ProgressEmitter | None = None,
        celery_app: Celery | None = None,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._repo = job_repo
        self._router = queue_router or QueueRouter(config=config)
        self._idempotency = idempotency or IdempotencyEngine()
        self._rate_limiter = rate_limiter or RateLimiter(config=config)
        self._resource_mgr = resource_manager or ResourceManager(config=config)
        self._lock = distributed_lock or DistributedLock(config=config)
        self._bus = event_bus or get_event_bus()
        self._emitter = progress_emitter or ProgressEmitter(job_repo, self._bus)
        self._app = celery_app or get_celery_app()
        self._config = config or BackgroundProcessingConfig.from_env()
        self._security = SecurityManager()

    async def dispatch(
        self,
        job_create: JobCreate,
        tenant_id: str = "",
        user_id: str = "",
        workspace_id: str = "",
    ) -> JobResponse:
        """Submit a job for async execution.

        This is the single entry point for all job creation.
        Handles idempotency, rate limiting, resource checks, queue routing,
        persistence, and event emission.

        Args:
            job_create: The job to dispatch.
            tenant_id: Optional tenant/organization for multi-tenant isolation.
            user_id: Optional user that created the job.
            workspace_id: Optional workspace/project context.

        Returns:
            JobResponse with status and metadata.

        Raises:
            JobDispatchError: If the job cannot be dispatched.
        """
        try:
            job_create = self._security.validate_job(job_create)
        except PayloadValidationError as exc:
            raise JobDispatchError(str(exc))

        job_key = self._build_job_key(job_create, tenant_id)
        dedup_result = await self._idempotency.check(job_key)
        if dedup_result.is_duplicate:
            logger.info("Duplicate job detected: key=%s, existing=%s", job_key, dedup_result.existing_job_id)
            existing = await self._repo.get(dedup_result.existing_job_id)
            if existing:
                return self._model_to_response(existing)
            await self._idempotency.release(job_key)

        if not await self._rate_limiter.allow(tenant_id, user_id, job_create.job_type):
            raise JobDispatchError(f"Rate limit exceeded for tenant={tenant_id} user={user_id} type={job_create.job_type}")

        if not await self._resource_mgr.can_accept(job_create, tenant_id):
            raise JobDispatchError(f"Resource quota exceeded for tenant={tenant_id} type={job_create.job_type}")

        queue = await self._router.route(job_create, tenant_id=tenant_id)
        job_create.queue = queue

        job_id = make_uuid()
        celery_task_id = str(uuid.uuid4())
        task_path = self._resolve_task(job_create.job_type)

        now = datetime.now(timezone.utc)
        scheduled_dt: datetime | None = None
        if isinstance(job_create.scheduled_at, str) and job_create.scheduled_at:
            scheduled_dt = datetime.fromisoformat(job_create.scheduled_at)
        elif isinstance(job_create.scheduled_at, datetime):
            scheduled_dt = job_create.scheduled_at

        job_record = await self._repo.create(
            uuid=job_id,
            project_id=job_create.project_id,
            job_type=job_create.job_type,
            status=JobStatus.QUEUED.value,
            priority=job_create.priority.value if isinstance(job_create.priority, JobPriority) else job_create.priority,
            queue=queue,
            payload=job_create.payload,
            max_retries=job_create.max_retries,
            celery_task_id=celery_task_id,
            parent_job_id=job_create.parent_job_id,
            tags=job_create.tags,
            scheduled_at=scheduled_dt,
            created_at=now,
            updated_at=now,
            recoverable=True,
        )

        await self._idempotency.record(job_key, job_id, ttl=86400)
        await self._emitter.on_created(job_id, job_create.project_id, job_create.job_type)

        lock_key = f"dispatch:{job_id}"
        try:
            async with self._lock.lock(lock_key, ttl=30):
                await self._dispatch_task(task_path, job_create, queue, celery_task_id, job_id)
        except Exception as exc:
            logger.warning("Dispatch lock unavailable (proceeding without lock): %s", exc)
            await self._dispatch_task(task_path, job_create, queue, celery_task_id, job_id)

        await self._emitter.on_queued(job_id, job_create.project_id)

        return JobResponse(
            job_id=job_id,
            job_type=job_create.job_type,
            project_id=job_create.project_id,
            status=JobStatus.QUEUED,
            priority=job_create.priority if isinstance(job_create.priority, JobPriority) else JobPriority(job_create.priority),
            queue=queue,
            celery_task_id=celery_task_id,
            created_at=utc_now(),
        )

    async def dispatch_batch(
        self,
        batch: BatchJobRequest,
        tenant_id: str = "",
        user_id: str = "",
        workspace_id: str = "",
    ) -> BatchJobResponse:
        """Dispatch multiple jobs, optionally in parallel."""
        batch_id = make_uuid()
        job_ids: list[str] = []

        for job_create in batch.jobs:
            try:
                resp = await self.dispatch(job_create, tenant_id=tenant_id, user_id=user_id, workspace_id=workspace_id)
                job_ids.append(resp.job_id)
            except JobDispatchError as exc:
                logger.warning("Batch dispatch skipped job %s: %s", job_create.job_type, exc)

        if batch.parallel and len(job_ids) > 1:
            try:
                from celery import group
                tasks = []
                for jid in job_ids:
                    job = await self._repo.get(jid)
                    if job and job.celery_task_id:
                        task_path = self._resolve_task(job.job_type)
                        sig = self._app.signature(task_path, args=(job.project_id, jid), kwargs=job.payload, queue=job.queue)
                        tasks.append(sig)
                if tasks:
                    for chunk in [tasks[i:i + batch.max_concurrency] for i in range(0, len(tasks), batch.max_concurrency)]:
                        job_group = group(*chunk)
                        job_group.delay()
            except Exception as exc:
                logger.warning("Batch parallel dispatch failed (non-critical): %s", exc)

        logger.info("Batch dispatch: batch_id=%s jobs=%d parallel=%s", batch_id[:8], len(job_ids), batch.parallel)
        return BatchJobResponse(batch_id=batch_id, job_ids=job_ids, total=len(job_ids))

    async def cancel(self, job_id: str, reason: str = "") -> bool:
        """Cancel a pending or running job."""
        job = await self._repo.get(job_id)
        if job is None:
            return False
        if job.status in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value, JobStatus.DEAD_LETTER.value):
            return False

        await self._repo.update_status(job_id, JobStatus.CANCELLED.value, error=reason)
        if job.celery_task_id:
            self._app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
        await self._emitter.on_cancelled(job_id, job.project_id, reason)
        await self._bus.publish_event(job.project_id, EventType.JOB_CANCELLED, {"job_id": job_id, "reason": reason})
        return True

    async def retry(self, job_id: str) -> JobResponse | None:
        """Re-dispatch a failed or dead-letter job."""
        job = await self._repo.get(job_id)
        if job is None:
            return None
        await self._repo.update_status(job_id, JobStatus.QUEUED.value, attempts=0, error="", traceback="")

        celery_task_id = str(uuid.uuid4())
        await self._repo.update(job_id, celery_task_id=celery_task_id)
        task_path = self._resolve_task(job.job_type)

        self._app.send_task(
            task_path,
            args=(job.project_id, job_id),
            kwargs=job.payload,
            queue=job.queue,
            task_id=celery_task_id,
        )

        await self._emitter.on_recovered(job_id, job.project_id)
        return await self.get_status(job_id)

    async def pause(self, job_id: str) -> bool:
        """Pause a running job (mark as paused, revoke from Celery)."""
        job = await self._repo.get(job_id)
        if job is None or job.status != JobStatus.RUNNING.value:
            return False
        await self._repo.update_status(job_id, "paused")
        if job.celery_task_id:
            self._app.control.revoke(job.celery_task_id, terminate=False)
        return True

    async def resume(self, job_id: str) -> JobResponse | None:
        """Resume a paused job by re-dispatching."""
        job = await self._repo.get(job_id)
        if job is None or job.status != "paused":
            return None
        return await self.retry(job_id)

    async def get_status(self, job_id: str) -> JobResponse | None:
        """Get current job status and progress."""
        job = await self._repo.get(job_id)
        if job is None:
            return None
        return self._model_to_response(job)

    async def list_by_project(
        self, project_id: str, limit: int = 100, offset: int = 0
    ) -> Sequence[JobResponse]:
        jobs = await self._repo.list_by_project(project_id, limit=limit, offset=offset)
        return [self._model_to_response(j) for j in jobs]

    async def list_by_status(
        self, status: str, limit: int = 100, offset: int = 0
    ) -> Sequence[JobResponse]:
        jobs = await self._repo.list_by_status(status, limit=limit, offset=offset)
        return [self._model_to_response(j) for j in jobs]

    async def get_metrics(self) -> dict[str, Any]:
        return await self._repo.get_metrics()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_job_key(self, job_create: JobCreate, tenant_id: str) -> str:
        parts = [tenant_id or "_", job_create.project_id or "_", job_create.job_type]
        if job_create.payload:
            stable = {k: v for k, v in sorted(job_create.payload.items()) if k != "_tid"}
            parts.append(json.dumps(stable, sort_keys=True, default=str))
        return ":".join(parts)

    def _resolve_task(self, job_type: str) -> str:
        try:
            return resolve_task_path(job_type)
        except KeyError:
            raise JobDispatchError(f"Unknown job type: {job_type}")

    def _priority_to_int(self, priority: JobPriority | str) -> int:
        mapping = {
            "critical": 0, "high": 3, "normal": 5, "low": 8, "background": 10, "system": 1,
        }
        key = priority.value if isinstance(priority, JobPriority) else priority
        return mapping.get(key, 5)

    async def _dispatch_task(self, task_path: str, job_create: JobCreate, queue: str, celery_task_id: str, job_id: str) -> None:
        if job_create.scheduled_at:
            eta = datetime.fromisoformat(job_create.scheduled_at) if isinstance(job_create.scheduled_at, str) else job_create.scheduled_at
            self._app.send_task(
                task_path,
                args=(job_create.project_id, job_id),
                kwargs=job_create.payload,
                queue=queue,
                task_id=celery_task_id,
                eta=eta,
            )
            logger.info("Scheduled job %s for %s on queue=%s", job_id[:8], eta.isoformat(), queue)
        else:
            self._app.send_task(
                task_path,
                args=(job_create.project_id, job_id),
                kwargs=job_create.payload,
                queue=queue,
                task_id=celery_task_id,
                priority=self._priority_to_int(job_create.priority),
            )
            logger.info("Dispatched job %s type=%s queue=%s", job_id[:8], job_create.job_type, queue)

    def _model_to_response(self, job: JobModel) -> JobResponse:
        return JobResponse(
            job_id=job.uuid,
            job_type=job.job_type,
            project_id=job.project_id or "",
            status=JobStatus(job.status) if job.status in JobStatus._value2member_map_ else JobStatus.PENDING,
            priority=JobPriority(job.priority) if job.priority in JobPriority._value2member_map_ else JobPriority.NORMAL,
            queue=job.queue,
            progress=job.progress or {},
            attempts=job.attempts or 0,
            max_retries=job.max_retries,
            celery_task_id=job.celery_task_id or "",
            worker_id=job.worker_id or "",
            created_at=job.created_at.isoformat() if job.created_at else "",
            started_at=job.started_at.isoformat() if job.started_at else "",
            finished_at=job.finished_at.isoformat() if job.finished_at else "",
            error=job.error or "",
            tags=job.tags or [],
            parent_job_id=job.parent_job_id or "",
        )
