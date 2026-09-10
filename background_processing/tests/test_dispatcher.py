"""Tests for the Job Dispatcher — routing, idempotency, rate limiting, lifecycle."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.dispatcher import JobDispatcher, JobDispatchError
from background_processing.models import (
    BatchJobRequest, JobCreate, JobPriority, JobStatus, JobType,
    make_uuid,
)
from background_processing.queue_router import QueueRouter


@pytest_asyncio.fixture
async def dispatcher(mock_redis, job_repo):
    """Create a JobDispatcher with mocked dependencies."""
    router = QueueRouter()
    with patch("background_processing.dispatcher.get_event_bus") as mock_bus:
        mock_bus.return_value = AsyncMock()
        with patch("background_processing.dispatcher.get_celery_app") as mock_celery:
            mock_app = MagicMock()
            mock_app.send_task = MagicMock()
            mock_celery.return_value = mock_app
            d = JobDispatcher(
                job_repo=job_repo,
                queue_router=router,
                celery_app=mock_app,
            )
            yield d


class TestJobDispatcher:
    async def test_dispatch_creates_and_submits_job(self, dispatcher, session):
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="proj-123",
            payload={"video_id": "vid456"},
        )
        resp = await dispatcher.dispatch(job)

        assert resp.job_id
        assert resp.status == JobStatus.QUEUED
        assert resp.queue in ("ai", "default")

        # Verify DB persistence
        saved = await dispatcher._repo.get(resp.job_id)
        assert saved is not None
        assert saved.job_type == "pipeline.analysis"

    async def test_dispatch_idempotency_prevents_duplicates(self, dispatcher):
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="proj-dup",
            payload={"video_id": "vid456"},
        )
        resp1 = await dispatcher.dispatch(job)
        resp2 = await dispatcher.dispatch(job)

        assert resp1.job_id == resp2.job_id  # Same job returned

    async def test_dispatch_batch(self, dispatcher):
        batch = BatchJobRequest(
            jobs=[
                JobCreate(job_type="pipeline.analysis", project_id="p1", payload={"key": "a"}),
                JobCreate(job_type="pipeline.seo", project_id="p2", payload={"key": "b"}),
            ],
            parallel=True,
        )
        resp = await dispatcher.dispatch_batch(batch)

        assert len(resp.job_ids) == 2
        assert resp.total == 2

    async def test_cancel_running_job(self, dispatcher, session):
        job = await dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="running",
            project_id="proj-1",
        )
        result = await dispatcher.cancel(job.uuid)
        assert result is True

        cancelled = await dispatcher._repo.get(job.uuid)
        assert cancelled.status == "cancelled"

    async def test_cancel_completed_job_returns_false(self, dispatcher, session):
        job = await dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="completed",
            project_id="proj-1",
        )
        result = await dispatcher.cancel(job.uuid)
        assert result is False

    async def test_retry_failed_job(self, dispatcher, session):
        job = await dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="failed",
            project_id="proj-1",
            error="Something broke",
        )
        result = await dispatcher.retry(job.uuid)
        assert result is not None
        assert result.status in (JobStatus.QUEUED, JobStatus.RECOVERED)

    async def test_pause_and_resume_job(self, dispatcher, session):
        job = await dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="running",
            project_id="proj-1",
        )
        paused = await dispatcher.pause(job.uuid)
        assert paused is True

        resumed = await dispatcher.resume(job.uuid)
        assert resumed is not None
        assert resumed.status in (JobStatus.QUEUED, JobStatus.RECOVERED)

    async def test_get_status(self, dispatcher, session):
        job = await dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="completed",
            project_id="proj-1",
        )
        resp = await dispatcher.get_status(job.uuid)
        assert resp is not None
        assert resp.job_id == job.uuid
        assert resp.status == JobStatus.COMPLETED

    async def test_get_status_not_found(self, dispatcher):
        resp = await dispatcher.get_status("nonexistent")
        assert resp is None

    async def test_list_by_project(self, dispatcher, session):
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.a", status="pending", project_id="proj-list")
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.b", status="completed", project_id="proj-list")
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.c", status="failed", project_id="other")

        jobs = await dispatcher.list_by_project("proj-list")
        assert len(jobs) == 2

    async def test_list_by_status(self, dispatcher, session):
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.a", status="failed", project_id="p1")
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.b", status="failed", project_id="p2")

        jobs = await dispatcher.list_by_status("failed")
        assert len(jobs) >= 2

    async def test_dispatch_with_schedule(self, dispatcher):
        from datetime import datetime, timedelta, timezone
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="proj-sched",
            payload={},
            scheduled_at=future,
        )
        resp = await dispatcher.dispatch(job)
        assert resp.job_id
        assert resp.status == JobStatus.QUEUED

    async def test_dispatch_invalid_job_type(self, dispatcher):
        job = JobCreate(job_type="nonexistent.task", project_id="proj-1")
        with pytest.raises(JobDispatchError):
            await dispatcher.dispatch(job)


class TestDispatcherMetrics:
    async def test_get_metrics(self, dispatcher, session):
        await dispatcher._repo.create(uuid=make_uuid(), job_type="pipeline.a", status="completed", project_id="p1", duration_ms=100)
        metrics = await dispatcher.get_metrics()
        assert "total" in metrics
        assert "by_status" in metrics
        assert "by_type" in metrics
