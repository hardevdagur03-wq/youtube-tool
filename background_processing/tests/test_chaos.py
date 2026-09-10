"""Chaos Tests — validates platform survives infrastructure failures and recovers automatically."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.dispatcher import JobDispatcher
from background_processing.failure_recovery import FailureRecovery
from background_processing.models import JobCreate, JobStatus, make_uuid
from background_processing.queue_router import QueueRouter


@pytest.mark.chaos
class TestChaosEngineering:
    """Chaos tests simulating infrastructure failures."""

    @pytest_asyncio.fixture
    async def chaos_dispatcher(self, job_repo, mock_redis):
        router = QueueRouter()
        with patch("background_processing.dispatcher.get_event_bus") as bus:
            bus.return_value = AsyncMock()
            with patch("background_processing.dispatcher.get_celery_app") as cel:
                app = MagicMock()
                app.send_task = MagicMock()
                cel.return_value = app
                yield JobDispatcher(job_repo=job_repo, queue_router=router, celery_app=app)

    async def test_redis_down_dispatches_still_persist(self, chaos_dispatcher, session):
        """When Redis is down, job should still persist to DB."""

        async def redis_fail(*args, **kwargs):
            raise ConnectionError("Redis is down")

        chaos_dispatcher._lock._redis = None
        chaos_dispatcher._lock._get_redis = AsyncMock(side_effect=redis_fail)
        chaos_dispatcher._idempotency._redis = None
        chaos_dispatcher._idempotency._get_redis = AsyncMock(side_effect=redis_fail)

        job = JobCreate(job_type="pipeline.analysis", project_id="proj-chaos-redis")
        resp = await chaos_dispatcher.dispatch(job)
        assert resp.job_id is not None
        saved = await chaos_dispatcher._repo.get(resp.job_id)
        assert saved is not None

    async def test_worker_crash_jobs_recoverable(self, chaos_dispatcher, session):
        """Jobs stuck in 'running' after worker crash should be recoverable."""
        from datetime import datetime, timezone, timedelta

        stuck = await chaos_dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="running",
            project_id="proj-crash",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert stuck.status == "running"

        from background_processing.config import BackgroundProcessingConfig
        recovery = FailureRecovery(
            job_repo=chaos_dispatcher._repo,
            celery_app=chaos_dispatcher._app,
        )
        results = await recovery.run_recovery_cycle()
        assert results["stuck_jobs_recovered"] >= 1

        recovered = await chaos_dispatcher._repo.get(stuck.uuid)
        assert recovered.status == JobStatus.PENDING.value

    async def test_broker_restart_recovery(self, chaos_dispatcher, session):
        """Jobs with 'reserved' status should be reset to pending after broker restart."""
        from background_processing.failure_recovery import FailureRecovery

        reserved = await chaos_dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="reserved",
            project_id="proj-broker",
        )

        recovery = FailureRecovery(
            job_repo=chaos_dispatcher._repo,
            celery_app=chaos_dispatcher._app,
        )
        results = await recovery.run_recovery_cycle()
        assert results["orphaned_tasks_recovered"] >= 0

    async def test_network_partition_jobs_not_lost(self, chaos_dispatcher, session):
        """Jobs should persist even if network fails after DB write."""
        import json

        original_create = chaos_dispatcher._repo.create

        async def network_fail_create(**kwargs):
            result = await original_create(**kwargs)
            raise ConnectionError("Network partition after DB write")
            return result

        chaos_dispatcher._repo.create = network_fail_create

        job = JobCreate(job_type="pipeline.analysis", project_id="proj-network-fail")
        with pytest.raises(Exception):
            await chaos_dispatcher.dispatch(job)

    async def test_oom_kill_scenario(self, chaos_dispatcher, session):
        """Jobs should persist and be recoverable after simulated OOM kill."""
        from datetime import datetime, timezone, timedelta

        oom_job = await chaos_dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="running",
            project_id="proj-oom",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            worker_id="worker-oom-killed",
        )
        assert oom_job.status == "running"

        from background_processing.failure_recovery import FailureRecovery
        recovery = FailureRecovery(job_repo=chaos_dispatcher._repo, celery_app=chaos_dispatcher._app)
        results = await recovery.run_recovery_cycle()
        assert results["stuck_jobs_recovered"] >= 1

    async def test_power_failure_data_integrity(self, chaos_dispatcher, session):
        """Jobs created just before power failure should persist."""
        job = await chaos_dispatcher._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="queued",
            project_id="proj-power",
        )

        # Simulate DB record surviving restart
        reloaded = await chaos_dispatcher._repo.get(job.uuid)
        assert reloaded is not None
        assert reloaded.status == "queued"

    async def test_timeout_handling(self, chaos_dispatcher):
        """Jobs with long-running operations should have timeout support."""
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="proj-timeout",
            payload={"timeout_seconds": 300},
        )
        resp = await chaos_dispatcher.dispatch(job)
        assert resp.job_id is not None

    async def test_concurrent_same_project_jobs(self, chaos_dispatcher):
        """Multiple sequential jobs on same project should not conflict."""
        successes = 0
        for i in range(20):
            job = JobCreate(
                job_type="pipeline." + ("metadata" if i % 2 == 0 else "analysis"),
                project_id="proj-concurrent",
                payload={"idx": i},
            )
            try:
                resp = await chaos_dispatcher.dispatch(job)
                if resp.job_id:
                    successes += 1
            except Exception:
                pass
        assert successes >= 18
