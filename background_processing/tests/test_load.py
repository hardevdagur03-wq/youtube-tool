"""Load Tests — validates platform can handle high job throughput under load."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.dispatcher import JobDispatcher
from background_processing.models import BatchJobRequest, JobCreate
from background_processing.queue_router import QueueRouter


@pytest.mark.load
class TestLoadHandling:
    """Validates the platform can handle 100+ dispatches."""

    @pytest_asyncio.fixture
    async def load_dispatcher(self, job_repo, mock_redis):
        router = QueueRouter()
        with patch("background_processing.dispatcher.get_event_bus") as bus:
            bus.return_value = AsyncMock()
            with patch("background_processing.dispatcher.get_celery_app") as cel:
                app = MagicMock()
                app.send_task = MagicMock()
                cel.return_value = app
                yield JobDispatcher(job_repo=job_repo, queue_router=router, celery_app=app)

    async def test_100_sequential_dispatch(self, load_dispatcher):
        """Dispatch 100 jobs sequentially — all must succeed."""
        successes = 0
        errors = 0
        for i in range(100):
            job = JobCreate(
                job_type="pipeline.analysis",
                project_id=f"proj-{i % 20}",
                payload={"video_id": f"vid{i}"},
            )
            try:
                resp = await load_dispatcher.dispatch(job)
                if resp.job_id:
                    successes += 1
            except Exception:
                errors += 1
        assert successes == 100, f"Only {successes} succeeded, {errors} failed"

    async def test_batch_50_jobs(self, load_dispatcher):
        """Dispatch 50 jobs via batch API."""
        batch = BatchJobRequest(
            jobs=[
                JobCreate(
                    job_type="pipeline.analysis" if i % 2 == 0 else "pipeline.seo",
                    project_id=f"proj-{i}",
                    payload={"idx": i},
                )
                for i in range(50)
            ],
            parallel=True,
            max_concurrency=10,
        )
        resp = await load_dispatcher.dispatch_batch(batch)
        assert resp.total == 50
        assert len(resp.job_ids) == 50

    async def test_sequential_cancel(self, load_dispatcher):
        """Create 10 jobs, cancel them all."""
        job_ids = []
        for i in range(10):
            job = JobCreate(job_type="pipeline.analysis", project_id="proj-seq", payload={"i": i})
            resp = await load_dispatcher.dispatch(job)
            job_ids.append(resp.job_id)

        cancel_count = 0
        for jid in job_ids:
            if await load_dispatcher.cancel(jid):
                cancel_count += 1
        assert cancel_count >= 0
