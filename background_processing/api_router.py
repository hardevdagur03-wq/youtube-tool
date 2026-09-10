"""Background Processing API Router — FastAPI endpoints for job management.

Provides RESTful APIs for:
- Create job (dispatch)
- Get job status
- List jobs (by project, status, type)
- Cancel job
- Retry job (failed/dead-letter)
- Pause/resume job
- Queue metrics
- Worker status
- Dead letter queue management
- Metrics
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from background_processing.dead_letter_queue import DeadLetterQueue
from background_processing.dispatcher import JobDispatcher
from background_processing.models import (
    BatchJobRequest, BatchJobResponse, DeadLetterEntry,
    JobCreate, JobPriority, JobResponse, JobStatus, JobType,
)
from background_processing.rate_limiter import RateLimiter
from background_processing.security import SecurityManager
from background_processing.worker_manager import WorkerManager

router = APIRouter(prefix="/api/background", tags=["background-processing"])


def get_router() -> APIRouter:
    """Return the configured router for mounting in the main app."""
    return router


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job_create: JobCreate,
    dispatcher: JobDispatcher = Depends(_get_dispatcher),
    security: SecurityManager = Depends(_get_security),
):
    """Create and dispatch a background job."""
    try:
        validated = security.validate_job(job_create)
        resp = await dispatcher.dispatch(validated)
        return _success(resp.model_dump())
    except Exception as exc:
        return _error(str(exc), 400)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Get job status and progress."""
    resp = await dispatcher.get_status(job_id)
    if resp is None:
        return _error("Job not found", 404)
    return _success(resp.model_dump())


@router.get("/jobs")
async def list_jobs(
    project_id: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    dispatcher: JobDispatcher = Depends(_get_dispatcher),
):
    """List jobs with optional filtering."""
    if project_id:
        jobs = await dispatcher.list_by_project(project_id, limit=limit, offset=offset)
    elif status:
        jobs = await dispatcher.list_by_status(status, limit=limit, offset=offset)
    else:
        from database.config import DatabaseConfig
        from database.session import db_manager
        from background_processing.job_repository import JobRepository
        async with db_manager.session_factory() as session:
            repo = JobRepository(session)
            models = await repo.list_recent(limit=limit, offset=offset)
            jobs = [JobResponse(
                job_id=m.uuid, job_type=m.job_type, project_id=m.project_id or "",
                status=JobStatus(m.status) if m.status in JobStatus._value2member_map_ else JobStatus.PENDING,
                priority=JobPriority(m.priority) if m.priority in JobPriority._value2member_map_ else JobPriority.NORMAL,
                queue=m.queue,
                created_at=m.created_at.isoformat() if m.created_at else "",
            ) for m in models]

    return _success({"jobs": [j.model_dump() if hasattr(j, 'model_dump') else j for j in jobs], "count": len(jobs)})


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, reason: str = Query(default=""), dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Cancel a pending or running job."""
    result = await dispatcher.cancel(job_id, reason=reason)
    if not result:
        return _error("Job not found or already terminal", 404)
    return _success({"cancelled": True})


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Retry a failed or dead-letter job."""
    result = await dispatcher.retry(job_id)
    if result is None:
        return _error("Job not found or not retryable", 404)
    return _success(result.model_dump())


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str, dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Pause a running job."""
    result = await dispatcher.pause(job_id)
    if not result:
        return _error("Job not running", 404)
    return _success({"paused": True})


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str, dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Resume a paused job."""
    result = await dispatcher.resume(job_id)
    if result is None:
        return _error("Job not found or not paused", 404)
    return _success(result.model_dump())


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


@router.post("/jobs/batch", response_model=BatchJobResponse)
async def create_batch(
    batch: BatchJobRequest,
    dispatcher: JobDispatcher = Depends(_get_dispatcher),
):
    """Create and dispatch multiple jobs in batch."""
    resp = await dispatcher.dispatch_batch(batch)
    return _success(resp.model_dump())


# ---------------------------------------------------------------------------
# Dead Letter Queue
# ---------------------------------------------------------------------------


@router.get("/dead-letter")
async def list_dead_letter(limit: int = Query(default=100), offset: int = Query(default=0)):
    """List dead letter queue entries."""
    dlq = DeadLetterQueue()
    entries = await dlq.list(limit=limit, offset=offset)
    count = await dlq.count()
    return _success({"entries": [e.model_dump() for e in entries], "total": count})


@router.post("/dead-letter/{job_id}/replay")
async def replay_dead_letter(job_id: str):
    """Replay a dead letter job back to the queue."""
    from database.config import DatabaseConfig
    from database.session import db_manager
    from background_processing.job_repository import JobRepository
    dlq = DeadLetterQueue()
    async with db_manager.session_factory() as session:
        repo = JobRepository(session)
        result = await dlq.replay(job_id, repo)
        if result is None:
            return _error("Dead letter entry not found", 404)
        return _success({"replayed": True, "job_id": job_id})


@router.post("/dead-letter/replay-all")
async def replay_all_dead_letter():
    """Replay all dead letter jobs."""
    from database.config import DatabaseConfig
    from database.session import db_manager
    from background_processing.job_repository import JobRepository
    dlq = DeadLetterQueue()
    async with db_manager.session_factory() as session:
        repo = JobRepository(session)
        count = await dlq.replay_all(repo)
        return _success({"replayed": count})


@router.delete("/dead-letter/{job_id}")
async def purge_dead_letter(job_id: str):
    """Remove a job from dead letter queue permanently."""
    dlq = DeadLetterQueue()
    await dlq.purge(job_id)
    return _success({"purged": True})


# ---------------------------------------------------------------------------
# Metrics & Status
# ---------------------------------------------------------------------------


@router.get("/metrics")
async def get_metrics(dispatcher: JobDispatcher = Depends(_get_dispatcher)):
    """Get job and queue metrics."""
    metrics = await dispatcher.get_metrics()
    return _success(metrics)


@router.get("/queues")
async def get_queue_status():
    """Get status of all queues."""
    from background_processing.config import BackgroundProcessingConfig
    from background_processing.celery_app import get_celery_app
    app = get_celery_app()
    config = BackgroundProcessingConfig.from_env()

    queues = {}
    for name in config.task_queues:
        try:
            inspect = app.control.inspect()
            active = inspect.active(safe=True) or {}
            reserved = inspect.reserved(safe=True) or {}
            scheduled = inspect.scheduled(safe=True) or {}
            queues[name] = {
                "active": len(active.get(name, []) if isinstance(active, dict) else []),
                "reserved": len(reserved.get(name, []) if isinstance(reserved, dict) else []),
                "scheduled": len(scheduled.get(name, []) if isinstance(scheduled, dict) else []),
            }
        except Exception:
            queues[name] = {"error": "inspect unavailable"}

    return _success({"queues": queues})


@router.get("/workers")
async def get_workers():
    """Get worker status and health."""
    mgr = WorkerManager()
    workers = mgr.list_workers()
    system = mgr.get_system_metrics()
    return _success({"workers": [w.model_dump() for w in workers], "system": system})


@router.get("/health")
async def health_check():
    """Comprehensive background processing health check."""
    from background_processing.config import BackgroundProcessingConfig
    from background_processing.celery_app import get_celery_app

    healthy = True
    checks = {}

    try:
        config = BackgroundProcessingConfig.from_env()
        import redis.asyncio as aredis
        r = aredis.from_url(config.redis_url, socket_timeout=5)
        pong = await r.ping()
        checks["redis"] = pong
        await r.aclose()
    except Exception as exc:
        checks["redis"] = str(exc)
        healthy = False

    try:
        app = get_celery_app()
        inspect = app.control.inspect()
        ping = inspect.ping(safe=True) or {}
        checks["celery"] = bool(ping)
    except Exception as exc:
        checks["celery"] = str(exc)
        healthy = False

    try:
        from database.session import db_manager
        checks["database"] = db_manager.is_healthy()
        if not checks["database"]:
            healthy = False
    except Exception as exc:
        checks["database"] = str(exc)
        healthy = False

    return _success({"healthy": healthy, "checks": checks})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _success(data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(content={"success": True, "data": data})


def _error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        content={"success": False, "error": message},
        status_code=status_code,
    )


def _get_dispatcher() -> JobDispatcher:
    """Dependency injection for JobDispatcher."""
    from database.config import DatabaseConfig
    from database.session import db_manager
    from background_processing.job_repository import JobRepository

    if not hasattr(_get_dispatcher, "_cached"):
        config = DatabaseConfig.from_env()
        if not db_manager._config:
            db_manager.initialize(config)
        session = db_manager._make_session()
        repo = JobRepository(session)
        _get_dispatcher._cached = JobDispatcher(job_repo=repo)
    return _get_dispatcher._cached


def _get_security() -> SecurityManager:
    if not hasattr(_get_security, "_cached"):
        _get_security._cached = SecurityManager()
    return _get_security._cached
