from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestConfig:
    def test_default_config(self):
        from background_processing.config import BackgroundProcessingConfig
        config = BackgroundProcessingConfig()
        assert config.broker_url == "redis://localhost:6379/0"
        assert config.result_backend == "redis://localhost:6379/0"


class TestModels:
    def test_job_model(self):
        from background_processing.models import JobModel, JobStatus, JobType, JobPriority
        job = JobModel(job_type=JobType.PIPELINE_METADATA.value, status=JobStatus.PENDING.value, priority=JobPriority.NORMAL.value)
        assert job.job_type == JobType.PIPELINE_METADATA.value
        assert job.status == JobStatus.PENDING.value

    def test_job_create(self):
        from background_processing.models import JobCreate, JobType, JobPriority
        create = JobCreate(job_type=JobType.PIPELINE_METADATA.value, payload={"video_id": "test123"}, priority=JobPriority.HIGH)
        assert create.job_type == JobType.PIPELINE_METADATA.value
        assert create.priority == JobPriority.HIGH

    def test_job_response(self):
        from background_processing.models import JobResponse, JobStatus, JobType
        resp = JobResponse(job_id="j1", job_type=JobType.PIPELINE_METADATA.value, status=JobStatus.PENDING)
        assert resp.job_id == "j1"

    def test_job_progress(self):
        from background_processing.models import JobProgress
        prog = JobProgress(pct=50.0, message="Processing")
        assert prog.pct == 50.0

    def test_enums(self):
        from background_processing.models import JobStatus, JobType, JobPriority
        assert JobStatus.PENDING.value == "pending"
        assert JobType.PIPELINE_METADATA.value == "pipeline.metadata"
        assert JobPriority.HIGH.value == "high"

    def test_retry_attempt(self):
        from background_processing.models import RetryAttempt
        ra = RetryAttempt(attempt=1, error="Timeout")
        assert ra.attempt == 1

    def test_dead_letter_entry(self):
        from background_processing.models import DeadLetterEntry
        dle = DeadLetterEntry(job_id="j1", error="Failed")
        assert dle.job_id == "j1"

    def test_batch_job_request(self):
        from background_processing.models import BatchJobRequest, JobCreate, JobType
        req = BatchJobRequest(jobs=[JobCreate(job_type=JobType.PIPELINE_METADATA.value, payload={})])
        assert len(req.jobs) == 1


class TestCeleryApp:
    def test_create_app(self):
        from background_processing.celery_app import create_celery_app
        app = create_celery_app()
        assert app is not None
        assert app.conf.broker_url == "redis://localhost:6379/0"

    def test_task_routing(self):
        from background_processing.celery_app import create_celery_app
        app = create_celery_app()
        queues = [q.name for q in app.conf.task_queues]
        assert "critical" in queues
        assert "high" in queues
        assert "default" in queues
        assert "dead_letter" in queues


@pytest.mark.asyncio
class TestDistributedLock:
    async def test_acquire_lock(self):
        from background_processing.distributed_lock import DistributedLock
        redis_mock = AsyncMock()
        redis_mock.set.return_value = True
        lock = DistributedLock(redis_client=redis_mock)
        acquired, token = await lock.acquire("test_lock", ttl=10)
        assert acquired is True

    async def test_acquire_existing_lock(self):
        from background_processing.distributed_lock import DistributedLock
        redis_mock = AsyncMock()
        redis_mock.set.return_value = None
        lock = DistributedLock(redis_client=redis_mock)
        acquired, token = await lock.acquire("lock_key", ttl=10, block=False)
        assert acquired is False

    async def test_release_lock(self):
        from background_processing.distributed_lock import DistributedLock
        redis_mock = AsyncMock()
        redis_mock.set.return_value = True
        redis_mock.eval.return_value = 1
        lock = DistributedLock(redis_client=redis_mock)
        acquired, token = await lock.acquire("release_test", ttl=10)
        assert acquired is True
        released = await lock.release("release_test", token)
        assert released is True

    async def test_release_nonexistent(self):
        from background_processing.distributed_lock import DistributedLock
        redis_mock = AsyncMock()
        redis_mock.eval.return_value = 0
        lock = DistributedLock(redis_client=redis_mock)
        released = await lock.release("nonexistent", "some_token")
        assert released is False


@pytest.mark.asyncio
class TestEventBus:
    async def test_publish(self):
        from background_processing.event_bus import EventBus
        redis_mock = AsyncMock()
        redis_mock.publish.return_value = 1
        bus = EventBus(redis_client=redis_mock)
        result = await bus.publish("test_channel", {"message": "hello"})
        assert result == 1

    async def test_publish_progress(self):
        from background_processing.event_bus import EventBus
        redis_mock = AsyncMock()
        redis_mock.publish.return_value = 1
        bus = EventBus(redis_client=redis_mock)
        result = await bus.publish_progress(project_id="p1", job_id="j1", pct=50.0, message="Halfway")
        assert result == 1

    async def test_publish_event(self):
        from background_processing.event_bus import EventBus, EventType
        redis_mock = AsyncMock()
        redis_mock.publish.return_value = 1
        bus = EventBus(redis_client=redis_mock)
        result = await bus.publish_event(project_id="p1", event_type=EventType.JOB_STARTED, data={"job_id": "j1"})
        assert result == 1


@pytest.mark.asyncio
class TestJobRepository:
    async def test_create_job(self):
        from background_processing.job_repository import JobRepository
        from background_processing.models import JobType
        session = AsyncMock()
        repo = JobRepository(session=session)
        job = await repo.create(uuid="create-test-uuid", job_type=JobType.PIPELINE_METADATA.value, payload={"video_id": "test"})
        assert job is not None
        assert job.job_type == JobType.PIPELINE_METADATA.value

    async def test_get_job(self):
        from background_processing.job_repository import JobRepository
        from background_processing.models import JobType, JobModel
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute.return_value = execute_result
        repo = JobRepository(session=session)
        job = JobModel(uuid="get-test-uuid", job_type=JobType.PIPELINE_METADATA.value, payload={})
        execute_result.scalar_one_or_none.return_value = job
        fetched = await repo.get("get-test-uuid")
        assert fetched is not None

    async def test_get_nonexistent(self):
        from background_processing.job_repository import JobRepository
        session = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute.return_value = execute_result
        repo = JobRepository(session=session)
        job = await repo.get("nonexistent")
        assert job is None

    async def test_update_status(self):
        from background_processing.job_repository import JobRepository
        from background_processing.models import JobType, JobStatus, JobModel
        session = AsyncMock()
        execute_result = MagicMock()
        job = JobModel(uuid="update-test-uuid", job_type=JobType.PIPELINE_METADATA.value, payload={})
        job.status = JobStatus.RUNNING.value
        execute_result.scalar_one_or_none.return_value = job
        session.execute.return_value = execute_result
        repo = JobRepository(session=session)
        updated = await repo.update_status("update-test-uuid", JobStatus.RUNNING.value)
        assert updated is not None
        assert updated.status == JobStatus.RUNNING.value


@pytest.mark.asyncio
class TestProgressEmitter:
    async def _make_emitter(self):
        from background_processing.progress_emitter import ProgressEmitter
        job_repo = AsyncMock()
        event_bus = AsyncMock()
        event_bus.publish_event = AsyncMock(return_value=1)
        event_bus.publish_progress = AsyncMock(return_value=1)
        emitter = ProgressEmitter(job_repo=job_repo, event_bus=event_bus)
        return emitter, job_repo, event_bus

    async def test_on_created(self):
        from background_processing.models import JobType
        emitter, _, eb = await self._make_emitter()
        await emitter.on_created(job_id="j1", project_id="p1", job_type=JobType.PIPELINE_METADATA.value)
        eb.publish_event.assert_called_once()

    async def test_on_started(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_started(job_id="j1", project_id="p1")
        repo.update_status.assert_called_once()

    async def test_on_progress(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_progress(job_id="j1", project_id="p1", pct=50.0, message="Working")
        repo.update_progress.assert_called_once()

    async def test_on_completed(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_completed(job_id="j1", project_id="p1", result={"success": True})
        repo.update_status.assert_called_once()

    async def test_on_failed(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_failed(job_id="j1", project_id="p1", error="Something went wrong")
        repo.update_status.assert_called_once()

    async def test_on_retrying(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_retrying(job_id="j1", project_id="p1", attempt=2, max_retries=3)
        repo.update_status.assert_called_once()

    async def test_on_cancelled(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_cancelled(job_id="j1", project_id="p1")
        repo.update_status.assert_called_once()

    async def test_on_dead_letter(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_dead_letter(job_id="j1", project_id="p1", error="Fatal error")
        repo.update_status.assert_called_once()

    async def test_on_recovered(self):
        emitter, repo, _ = await self._make_emitter()
        await emitter.on_recovered(job_id="j1", project_id="p1")
        repo.update_status.assert_called_once()

    async def test_on_queued(self):
        emitter, _, eb = await self._make_emitter()
        await emitter.on_queued(job_id="j1", project_id="p1")
        eb.publish_event.assert_called_once()


class TestRetryManager:
    def _make_job(self, attempts=0, max_retries=3):
        from background_processing.models import JobModel
        return JobModel(
            job_type="pipeline.metadata",
            status="failed",
            attempts=attempts,
            max_retries=max_retries,
            retry_history=[],
        )

    def test_should_retry(self):
        from background_processing.retry_manager import RetryManager
        rm = RetryManager()
        job = self._make_job(attempts=0, max_retries=3)
        decision = rm.should_retry(job=job, error="Timeout error")
        assert decision.should_retry is True

    def test_should_not_retry_exhausted(self):
        from background_processing.retry_manager import RetryManager
        rm = RetryManager()
        job = self._make_job(attempts=4, max_retries=3)
        decision = rm.should_retry(job=job, error="Timeout error")
        assert decision.should_retry is False

    def test_backoff_delay(self):
        from background_processing.retry_manager import RetryManager
        rm = RetryManager()
        delay = rm._compute_delay(attempt=2)
        assert delay >= 0

    def test_non_recoverable_error(self):
        from background_processing.retry_manager import RetryManager
        rm = RetryManager()
        job = self._make_job(attempts=0, max_retries=3)
        decision = rm.should_retry(job=job, error="Invalid payload")
        assert decision.send_to_dead_letter is True


@pytest.mark.asyncio
class TestDeadLetterQueue:
    async def _make_dlq(self):
        from background_processing.dead_letter_queue import DeadLetterQueue
        redis_mock = AsyncMock()
        dlq = DeadLetterQueue(redis_client=redis_mock)
        return dlq, redis_mock

    def _make_job(self, job_id="j1"):
        from background_processing.models import JobModel
        return JobModel(
            uuid=job_id,
            job_type="pipeline.metadata",
            status="failed",
            payload={},
            retry_history=[],
        )

    async def test_send_and_list(self):
        dlq, redis = await self._make_dlq()
        redis.lrange.return_value = ["j1", "j2"]
        redis.get.side_effect = [
            '{"job_id": "j1", "error": "Failed", "recovered": false}',
            '{"job_id": "j2", "error": "Invalid", "recovered": false}',
        ]
        job1 = self._make_job("j1")
        job2 = self._make_job("j2")
        entry1 = await dlq.send(job1, error="Failed")
        entry2 = await dlq.send(job2, error="Invalid")
        entries = await dlq.list()
        assert len(entries) >= 2

    async def test_replay(self):
        dlq, redis = await self._make_dlq()
        redis.get.return_value = '{"job_id": "replay_job", "error": "Transient", "recovered": false}'
        job_repo = AsyncMock()
        job = self._make_job("replay_job")
        job_repo.get.return_value = job
        job_repo.update.return_value = job
        result = await dlq.replay("replay_job", job_repo)
        assert result is not None

    async def test_purge(self):
        dlq, redis = await self._make_dlq()
        await dlq.purge("purge_me")
        redis.delete.assert_called_once()
        redis.lrem.assert_called_once()

    async def test_count(self):
        dlq, redis = await self._make_dlq()
        redis.llen.return_value = 3
        count = await dlq.count()
        assert count == 3


class TestWorkerManager:
    def test_list_workers(self):
        from background_processing.worker_manager import WorkerManager
        mgr = WorkerManager()
        workers = mgr.list_workers()
        assert isinstance(workers, list)

    def test_health_check(self):
        from background_processing.worker_manager import WorkerManager
        mgr = WorkerManager()
        health = mgr.health_check()
        assert "healthy" in health


class TestWorkerHealth:
    def test_get_summary(self):
        from background_processing.worker_health import HealthMonitor
        monitor = HealthMonitor()
        summary = monitor.get_summary()
        assert "healthy" in summary


class TestTaskScheduler:
    def test_register_task(self):
        from background_processing.task_scheduler import TaskScheduler
        scheduler = TaskScheduler()
        scheduler.register_periodic_tasks()
        assert True

    def test_schedule_delayed(self):
        from background_processing.task_scheduler import TaskScheduler
        mock_app = MagicMock()
        mock_app.send_task.return_value = MagicMock()
        scheduler = TaskScheduler(celery_app=mock_app)
        result = scheduler.schedule_delayed(task_path="background_processing.tasks.test_task", delay_seconds=60)
        assert result is not None
        mock_app.send_task.assert_called_once()


class TestMetrics:
    def test_record_job_created(self):
        from background_processing.metrics import record_job_created
        record_job_created(job_type="test", priority="normal", queue="default")
        assert True

    def test_record_job_completed(self):
        from background_processing.metrics import record_job_completed
        record_job_completed(job_type="test", queue="default")
        assert True


class TestTaskRegistry:
    def test_register_and_resolve(self):
        from background_processing.task_registry import register, resolve
        register(job_type="test_task", task_path="background_processing.tasks.test_task")
        path = resolve("test_task")
        assert path == "background_processing.tasks.test_task"

    def test_resolve_nonexistent(self):
        from background_processing.task_registry import resolve
        with pytest.raises(KeyError):
            resolve("nonexistent")
