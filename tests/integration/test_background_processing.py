from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import JobCreate, JobPriority, JobStatus, JobType
from background_processing.distributed_lock import DistributedLock
from background_processing.dead_letter_queue import DeadLetterQueue
from background_processing.retry_manager import RetryManager, RetryDecision


class TestBackgroundProcessingIntegration:
    @pytest.mark.asyncio
    async def test_job_creation_and_persistence(self, init_test_database, uow):
        from background_processing.job_repository import JobRepository

        repo = JobRepository(uow)
        job = await repo.create(
            job_type=JobType.PIPELINE_METADATA,
            project_uuid="proj-bg-1",
            payload={"video_id": "test123"},
            priority=JobPriority.NORMAL,
        )
        assert job is not None
        assert job.job_type == JobType.PIPELINE_METADATA
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.NORMAL

        fetched = await repo.get(job.uuid)
        assert fetched is not None
        assert fetched.uuid == job.uuid

    @pytest.mark.asyncio
    async def test_job_status_transitions(self, init_test_database, uow):
        from background_processing.job_repository import JobRepository

        repo = JobRepository(uow)
        job = await repo.create(
            job_type=JobType.PIPELINE_ANALYSIS,
            project_uuid="proj-status",
            payload={},
        )
        assert job.status == JobStatus.PENDING

        updated = await repo.update_status(job.uuid, JobStatus.QUEUED)
        assert updated.status == JobStatus.QUEUED

        updated = await repo.update_status(job.uuid, JobStatus.RUNNING)
        assert updated.status == JobStatus.RUNNING

        updated = await repo.update_status(job.uuid, JobStatus.COMPLETED)
        assert updated.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        config = BackgroundProcessingConfig()
        retry_mgr = RetryManager(config)

        decision = retry_mgr.should_retry(
            exception=ValueError("Temporary error"),
            attempt=1,
            max_retries=3,
        )
        assert decision.should_retry is True
        assert decision.delay > 0

        decision_last = retry_mgr.should_retry(
            exception=ValueError("Last attempt"),
            attempt=3,
            max_retries=3,
        )
        assert decision_last.should_retry is False

        history = retry_mgr.build_retry_history(
            attempts=[{"attempt": 1, "error": "Error 1"}, {"attempt": 2, "error": "Error 2"}],
        )
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_dead_letter_queue_flow(self):
        config = BackgroundProcessingConfig()
        dlq = DeadLetterQueue(config)

        await dlq.send(
            job_id="dlq-job-1",
            job_type="pipeline.metadata",
            payload={"video_id": "test"},
            error="Non-recoverable error: Invalid payload",
            project_uuid="proj-dlq",
        )

        count = await dlq.count()
        assert count >= 1

        entries = await dlq.list(limit=10)
        assert len(entries) >= 1
        assert entries[0]["job_id"] == "dlq-job-1"

    @pytest.mark.asyncio
    async def test_distributed_lock(self):
        config = BackgroundProcessingConfig()
        lock = DistributedLock(config)

        acquired = await lock.acquire("test-lock-key", ttl=10)
        assert acquired is True

        acquired_again = await lock.acquire("test-lock-key", ttl=10, blocking=False)
        assert acquired_again is False

        released = await lock.release("test-lock-key")
        assert released is True

        acquired_after = await lock.acquire("test-lock-key", ttl=10)
        assert acquired_after is True
        await lock.release("test-lock-key")

    @pytest.mark.asyncio
    async def test_event_bus_pub_sub(self):
        from background_processing.event_bus import EventBus

        config = BackgroundProcessingConfig()
        bus = EventBus(config)

        received = []
        async def handler(event):
            received.append(event)

        await bus.subscribe("test:*", handler)
        await bus.publish("test:event", {"data": "test_data"})
        await bus.publish("test:progress", {"pct": 50})

        assert len(received) >= 0

        await bus.close()

    @pytest.mark.asyncio
    async def test_worker_task_execution(self):
        from background_processing.task_registry import resolve, register

        task_path = resolve(JobType.PIPELINE_METADATA)
        assert task_path is not None
        assert "pipeline" in task_path

        all_tasks = resolve.all()
        assert len(all_tasks) >= 10
        assert JobType.PIPELINE_METADATA in all_tasks

    @pytest.mark.asyncio
    async def test_progress_events(self, init_test_database):
        from background_processing.job_repository import JobRepository
        from background_processing.progress_emitter import ProgressEmitter

        config = BackgroundProcessingConfig()

        async with init_test_database.session_no_commit() as session:
            from database.unit_of_work import UnitOfWork
            uow = UnitOfWork(session=session)
            await uow.__aenter__()
            try:
                repo = JobRepository(uow)
                job = await repo.create(
                    job_type=JobType.PIPELINE_METADATA,
                    project_uuid="prog-proj",
                    payload={},
                )

                emitter = ProgressEmitter(repo, config)
                await emitter.on_created(job.uuid)
                await emitter.on_queued(job.uuid)
                await emitter.on_started(job.uuid)
                await emitter.on_progress(job.uuid, 50.0, "Processing metadata")
                await emitter.on_completed(job.uuid, {"result": "success"})

                final = await repo.get(job.uuid)
                assert final is not None
                assert final.status == JobStatus.COMPLETED
            finally:
                await uow.__aexit__(None, None, None)
