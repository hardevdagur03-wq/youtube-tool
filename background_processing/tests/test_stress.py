"""Stress Tests — validates platform handles edge cases and resource limits gracefully."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.dispatcher import JobDispatchError, JobDispatcher
from background_processing.models import JobCreate, JobPriority, JobType, make_uuid


@pytest.mark.stress
class TestStressHandling:
    """Stress tests for system boundaries and extreme conditions."""

    @pytest_asyncio.fixture
    async def stress_dispatcher(self, job_repo, mock_redis):
        with patch("background_processing.dispatcher.get_event_bus") as bus:
            bus.return_value = AsyncMock()
            with patch("background_processing.dispatcher.get_celery_app") as cel:
                app = MagicMock()
                app.send_task = MagicMock()
                cel.return_value = app
                from background_processing.queue_router import QueueRouter
                yield JobDispatcher(job_repo=job_repo, queue_router=QueueRouter(), celery_app=app)

    async def test_extremely_large_payload(self, stress_dispatcher):
        """Job with large payload should be rejected by security."""
        big_payload = {"data": "x" * (1024 * 1024 + 1)}  # > 1MB limit
        job = JobCreate(job_type="pipeline.analysis", project_id="proj-big", payload=big_payload)
        with pytest.raises(JobDispatchError):
            await stress_dispatcher.dispatch(job)

    async def test_empty_payload_job(self, stress_dispatcher):
        """Job with empty payload should succeed."""
        job = JobCreate(job_type="pipeline.analysis", project_id="proj-empty")
        resp = await stress_dispatcher.dispatch(job)
        assert resp.job_id is not None

    async def test_duplicate_dispatch_100_times(self, stress_dispatcher):
        """Dispatch the exact same job 100 times — only 1 should be created."""
        job = JobCreate(job_type="pipeline.analysis", project_id="proj-dup-100", payload={"key": "same"})
        first = await stress_dispatcher.dispatch(job)
        for _ in range(99):
            dup = await stress_dispatcher.dispatch(job)
            assert dup.job_id == first.job_id

    async def test_missing_project_id(self, stress_dispatcher):
        """Jobs without project_id should still work."""
        job = JobCreate(job_type="pipeline.analysis")
        resp = await stress_dispatcher.dispatch(job)
        assert resp.job_id is not None

    async def test_unknown_job_type_rejected(self, stress_dispatcher):
        """Unknown job types should raise JobDispatchError."""
        job = JobCreate(
            job_type="completely.invalid.job.type.that.does.not.exist",
            project_id="proj-1",
        )
        with pytest.raises(JobDispatchError):
            await stress_dispatcher.dispatch(job)

    async def test_maximum_priority_job(self, stress_dispatcher):
        """Critical priority job should be dispatched successfully."""
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="proj-critical",
            priority=JobPriority.CRITICAL,
        )
        resp = await stress_dispatcher.dispatch(job)
        assert resp.priority == JobPriority.CRITICAL

    async def test_all_priorities(self, stress_dispatcher):
        """Jobs of every priority should dispatch successfully."""
        for priority in JobPriority:
            job = JobCreate(
                job_type="pipeline.analysis",
                project_id=f"proj-{priority.value}",
                priority=priority,
            )
            resp = await stress_dispatcher.dispatch(job)
            assert resp.job_id is not None
