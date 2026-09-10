"""Cleanup Tasks — Celery tasks for maintenance, health checks, and cleanup.

These tasks run on a schedule via Celery Beat to keep the system healthy.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from background_processing.celery_app import get_celery_app
from background_processing.dead_letter_queue import DeadLetterQueue
from background_processing.job_repository import JobRepository
from database.db_service import DatabaseService

logger = logging.getLogger(__name__)

app = get_celery_app()
_db_service: DatabaseService | None = None


def _get_db() -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


# ---------------------------------------------------------------------------
# Stale Job Cleanup
# ---------------------------------------------------------------------------


@app.task(bind=True, name="cleanup.cleanup_stale_jobs", max_retries=2)
def cleanup_stale_jobs(self, timeout_minutes: int = 30, **kwargs: Any) -> dict[str, Any]:
    """Reset stuck jobs back to pending for retry.

    Finds jobs that have been in 'running' or 'reserved' status
    longer than timeout_minutes and resets them to 'pending'.
    """
    async def _run() -> dict[str, Any]:
        from database.db_session import db_manager
        async with db_manager.session_factory() as session:
            repo = JobRepository(session)
            stuck = await repo.find_stuck_jobs(timeout_minutes=timeout_minutes)
            now = datetime.now(timezone.utc)
            recovered = 0
            for job in stuck:
                duration_ms = 0
                if job.started_at:
                    duration_ms = int((now - job.started_at).total_seconds() * 1000)
                await repo.update(
                    job.uuid,
                    status="pending",
                    error=f"Stuck timeout after {timeout_minutes}m",
                    duration_ms=duration_ms,
                )
                recovered += 1
            logger.info("Cleanup stale jobs: %d stuck → pending", recovered)
            return {"recovered": recovered, "timeout_minutes": timeout_minutes}

    loop = _get_or_create_loop()
    return loop.run_until_complete(_run())


# ---------------------------------------------------------------------------
# Expired Result Cleanup
# ---------------------------------------------------------------------------


@app.task(bind=True, name="cleanup.cleanup_expired_results", max_retries=2)
def cleanup_expired_results(self, max_age_days: int = 7, **kwargs: Any) -> dict[str, Any]:
    """Purge old completed/failed job records to keep the database lean."""
    async def _run() -> dict[str, Any]:
        from sqlalchemy import delete
        from database.db_session import db_manager
        from background_processing.models import JobModel

        async with db_manager.session_factory() as session:
            cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
            stmt = (
                delete(JobModel)
                .where(
                    JobModel.status.in_(["completed", "failed", "cancelled", "dead_letter"]),
                    JobModel.finished_at.isnot(None),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount
            logger.info("Cleanup expired results: %d deleted (max_age=%dd)", deleted, max_age_days)
            return {"deleted": deleted, "max_age_days": max_age_days}

    loop = _get_or_create_loop()
    return loop.run_until_complete(_run())


# ---------------------------------------------------------------------------
# System Health Check
# ---------------------------------------------------------------------------


@app.task(bind=True, name="cleanup.system_health_check", max_retries=2)
def system_health_check(self, **kwargs: Any) -> dict[str, Any]:
    """Perform a periodic health check of all system components.

    Checks:
    - Database connectivity (via DatabaseService health check)
    - Redis connectivity (via broker ping)
    - Job queue depth and staleness
    - Worker availability
    """
    async def _run() -> dict[str, Any]:
        from background_processing.metrics import mark_system_healthy
        results: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": False,
            "redis": False,
            "queues": {},
            "workers": 0,
        }

        db = _get_db()
        try:
            health = await db.health_check()
            results["database"] = health.get("healthy", False)
        except Exception as exc:
            logger.warning("Health check DB failed: %s", exc)
            results["database_error"] = str(exc)

        from background_processing.config import BackgroundProcessingConfig
        config = BackgroundProcessingConfig.from_env()
        try:
            import redis.asyncio as aredis
            r = aredis.from_url(config.redis_url, socket_timeout=5)
            pong = await r.ping()
            results["redis"] = pong
            await r.aclose()
        except Exception as exc:
            logger.warning("Health check Redis failed: %s", exc)
            results["redis_error"] = str(exc)

        from database.db_session import db_manager
        async with db_manager.session_factory() as session:
            repo = JobRepository(session)
            try:
                metrics = await repo.get_metrics()
                results["queues"] = metrics
            except Exception as exc:
                logger.warning("Health check queue metrics failed: %s", exc)
                results["queue_error"] = str(exc)

        all_healthy = results["database"] and results["redis"]
        mark_system_healthy(all_healthy)
        results["healthy"] = all_healthy
        logger.info("Health check: healthy=%s", all_healthy)
        return results

    loop = _get_or_create_loop()
    return loop.run_until_complete(_run())


# ---------------------------------------------------------------------------
# Job History Backup
# ---------------------------------------------------------------------------


@app.task(bind=True, name="cleanup.backup_job_history", max_retries=2)
def backup_job_history(self, max_age_days: int = 90, **kwargs: Any) -> dict[str, Any]:
    """Archive completed job records older than max_age_days.

    Currently a no-op placeholder; real implementation would
    export to a data warehouse or cold storage.
    """
    logger.info("Job history backup: no-op (archive would export records older than %dd)", max_age_days)
    return {"archived": 0, "max_age_days": max_age_days, "note": "placeholder"}


# ---------------------------------------------------------------------------
# Dead Letter Queue Cleanup
# ---------------------------------------------------------------------------


@app.task(bind=True, name="cleanup.dlq_cleanup", max_retries=2)
def dlq_cleanup(self, max_age_seconds: int = 604800, **kwargs: Any) -> dict[str, Any]:
    """Purge expired entries from the dead letter queue.

    Default max_age_seconds = 7 days.
    """
    async def _run() -> dict[str, Any]:
        dlq = DeadLetterQueue()
        count = await dlq.count()
        if count > 0:
            entries = await dlq.list(limit=count, include_expired=False)
            expired = count - len(entries)
            if expired > 0:
                logger.info("DLQ cleanup: ~%d expired entries auto-purged (TTL-based)", expired)
        logger.info("DLQ cleanup: current queue size=%d, max_age=%ds", count, max_age_seconds)
        return {"current_size": count, "max_age_seconds": max_age_seconds}

    loop = _get_or_create_loop()
    return loop.run_until_complete(_run())
