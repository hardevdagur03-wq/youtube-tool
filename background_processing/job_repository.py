"""Job Repository — Database persistence layer for background jobs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from background_processing.models import JobModel, JobStatus

logger = logging.getLogger(__name__)


class JobRepository:
    """Database-backed repository for background job persistence.

    All job state transitions are persisted immediately.
    Provides query methods for monitoring, metrics, and recovery.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: Any) -> JobModel:
        instance = JobModel(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        logger.debug("Job created: %s [%s]", instance.uuid[:8], kwargs.get("job_type", "?"))
        return instance

    async def get(self, job_id: str) -> JobModel | None:
        from sqlalchemy import select
        stmt = select(JobModel).where(
            JobModel.uuid == job_id,
            JobModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_celery_id(self, celery_task_id: str) -> JobModel | None:
        from sqlalchemy import select
        stmt = select(JobModel).where(
            JobModel.celery_task_id == celery_task_id,
            JobModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, job_id: str, **kwargs: Any) -> JobModel | None:
        instance = await self.get(job_id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key) and key not in ("uuid", "is_deleted"):
                setattr(instance, key, value)
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return instance

    async def update_status(
        self, job_id: str, status: str, **extra: Any
    ) -> JobModel | None:
        kwargs = {"status": status, **extra}
        if status == JobStatus.RUNNING.value:
            kwargs["started_at"] = datetime.now(timezone.utc)
        if status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value,
                      JobStatus.CANCELLED.value, JobStatus.DEAD_LETTER.value):
            kwargs["finished_at"] = datetime.now(timezone.utc)
            if "started_at" in extra or status == JobStatus.FAILED.value:
                pass
        return await self.update(job_id, **kwargs)

    async def increment_attempts(self, job_id: str) -> JobModel | None:
        instance = await self.get(job_id)
        if instance is None:
            return None
        instance.attempts = (instance.attempts or 0) + 1
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return instance

    async def update_progress(
        self, job_id: str, pct: float, message: str = "", stage: str = "",
        detail: dict[str, Any] | None = None,
    ) -> JobModel | None:
        instance = await self.get(job_id)
        if instance is None:
            return None
        instance.progress = {
            "pct": pct,
            "message": message,
            "stage": stage,
            "detail": detail or {},
        }
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return instance

    async def list_by_project(
        self, project_id: str, limit: int = 100, offset: int = 0
    ) -> Sequence[JobModel]:
        from sqlalchemy import select
        stmt = (
            select(JobModel)
            .where(JobModel.project_id == project_id, JobModel.is_deleted == False)
            .order_by(desc(JobModel.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(
        self, status: str, limit: int = 100, offset: int = 0
    ) -> Sequence[JobModel]:
        from sqlalchemy import select
        stmt = (
            select(JobModel)
            .where(JobModel.status == status, JobModel.is_deleted == False)
            .order_by(desc(JobModel.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_type(
        self, job_type: str, limit: int = 100, offset: int = 0
    ) -> Sequence[JobModel]:
        from sqlalchemy import select
        stmt = (
            select(JobModel)
            .where(JobModel.job_type == job_type, JobModel.is_deleted == False)
            .order_by(desc(JobModel.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[JobModel]:
        from sqlalchemy import select
        stmt = (
            select(JobModel)
            .where(JobModel.is_deleted == False)
            .order_by(desc(JobModel.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_status(self) -> dict[str, int]:
        from sqlalchemy import select
        stmt = (
            select(JobModel.status, func.count(JobModel.uuid))
            .where(JobModel.is_deleted == False)
            .group_by(JobModel.status)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result}

    async def count_by_type(self) -> dict[str, int]:
        from sqlalchemy import select
        stmt = (
            select(JobModel.job_type, func.count(JobModel.uuid))
            .where(JobModel.is_deleted == False)
            .group_by(JobModel.job_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result}

    async def get_metrics(self) -> dict[str, Any]:
        total = await self._count_all()
        by_status = await self.count_by_status()
        by_type = await self.count_by_type()
        avg_duration = await self._avg_duration()
        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "avg_duration_ms": round(avg_duration or 0, 1),
        }

    async def find_stuck_jobs(
        self, timeout_minutes: int = 30
    ) -> Sequence[JobModel]:
        from sqlalchemy import select
        cutoff = datetime.now(timezone.utc).timestamp() - timeout_minutes * 60
        stmt = (
            select(JobModel)
            .where(
                JobModel.status.in_(["running", "reserved"]),
                JobModel.started_at.isnot(None),
                func.strftime("%s", JobModel.started_at) < str(int(cutoff)),
                JobModel.is_deleted == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def soft_delete(self, job_id: str) -> bool:
        instance = await self.get(job_id)
        if instance is None:
            return False
        instance.is_deleted = True
        instance.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def hard_delete(self, job_id: str) -> bool:
        instance = await self.get(job_id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def _count_all(self) -> int:
        from sqlalchemy import select
        stmt = select(func.count()).select_from(JobModel).where(
            JobModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _avg_duration(self) -> float | None:
        from sqlalchemy import select
        stmt = select(func.avg(JobModel.duration_ms)).where(
            JobModel.status == "completed",
            JobModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar()
