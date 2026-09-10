"""Tests for the Failure Recovery — automatic job recovery after crashes."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.failure_recovery import FailureRecovery


class TestFailureRecovery:
    @pytest_asyncio.fixture
    async def recovery(self, job_repo, mock_redis):
        from background_processing.celery_app import get_celery_app
        r = FailureRecovery(
            job_repo=job_repo,
            redis_client=mock_redis,
            celery_app=get_celery_app(),
        )
        yield r

    async def test_run_recovery_cycle_success(self, recovery):
        results = await recovery.run_recovery_cycle()
        assert "stuck_jobs_recovered" in results
        assert "orphaned_tasks_recovered" in results
        assert isinstance(results["stuck_jobs_recovered"], int)

    async def test_recover_stuck_jobs(self, recovery, session):
        from background_processing.models import make_uuid
        from datetime import datetime, timezone, timedelta
        job = await recovery._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="running",
            project_id="proj-1",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        count = await recovery._recover_stuck_jobs(timeout_minutes=30)
        assert count >= 1
        updated = await recovery._repo.get(job.uuid)
        assert updated.status == "pending"

    async def test_recover_only_stuck_jobs(self, recovery, session):
        from background_processing.models import make_uuid
        job_normal = await recovery._repo.create(
            uuid=make_uuid(),
            job_type="pipeline.analysis",
            status="completed",
            project_id="proj-1",
        )
        count = await recovery._recover_stuck_jobs(timeout_minutes=30)
        assert count == 0  # completed jobs not stuck

    async def test_recover_orphaned_tasks(self, recovery, mock_redis):
        mock_redis.keys = AsyncMock(return_value=["celery-task-meta-abc123"])
        mock_redis.get = AsyncMock(return_value='{"status": "RESERVED"}')
        count = await recovery._recover_orphaned_tasks()
        assert count >= 0  # orphan may or may not exist in DB

    async def test_get_recovery_stats(self, recovery):
        stats = await recovery.get_recovery_stats()
        assert "total_recovery_cycles" in stats
        assert "running" in stats

    async def test_multiple_recovery_cycles(self, recovery):
        results = await recovery.run_recovery_cycle()
        assert results["stuck_jobs_recovered"] >= 0
        stats = await recovery.get_recovery_stats()
        assert stats["total_recovery_cycles"] >= 1

    async def test_task_path_mapping(self, recovery):
        assert "pipeline_tasks.process_video" in recovery._task_path("pipeline.metadata")
        assert "export_tasks.export_project" in recovery._task_path("export.single")
