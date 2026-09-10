"""Tests for JobRepository — SQLite-backed persistence for background jobs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from background_processing.models import JobModel, JobStatus


class TestJobRepository:
    async def test_create_job(self, job_repo, sample_job_data):
        job = await job_repo.create(**sample_job_data)
        assert job.uuid is not None
        assert job.job_type == "pipeline.analysis"
        assert job.status == "pending"
        assert job.project_id == "proj-123"

    async def test_get_job_by_uuid(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        retrieved = await job_repo.get(created.uuid)
        assert retrieved is not None
        assert retrieved.uuid == created.uuid
        assert retrieved.job_type == "pipeline.analysis"

    async def test_get_job_not_found(self, job_repo):
        result = await job_repo.get("nonexistent-uuid")
        assert result is None

    async def test_get_by_celery_id(self, job_repo, sample_job_data):
        data = {**sample_job_data, "celery_task_id": "celery-task-001"}
        created = await job_repo.create(**data)
        retrieved = await job_repo.get_by_celery_id("celery-task-001")
        assert retrieved is not None
        assert retrieved.uuid == created.uuid

    async def test_update_job(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        updated = await job_repo.update(created.uuid, status="running", worker_id="worker-1")
        assert updated is not None
        assert updated.status == "running"
        assert updated.worker_id == "worker-1"

    async def test_update_status(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        await job_repo.update_status(created.uuid, "running")
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.status == "running"
        assert retrieved.started_at is not None

    async def test_update_status_completed(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        await job_repo.update_status(created.uuid, "completed", duration_ms=1500)
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.status == "completed"
        assert retrieved.duration_ms == 1500
        assert retrieved.finished_at is not None

    async def test_update_status_failed(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        await job_repo.update_status(created.uuid, "failed", error="Something broke")
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.status == "failed"
        assert "Something broke" in retrieved.error

    async def test_update_progress(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        await job_repo.update_progress(created.uuid, 50.0, "Halfway there", stage="analysis")
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.progress["pct"] == 50.0
        assert retrieved.progress["message"] == "Halfway there"
        assert retrieved.progress["stage"] == "analysis"

    async def test_increment_attempts(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        assert created.attempts == 0
        await job_repo.increment_attempts(created.uuid)
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.attempts == 1
        await job_repo.increment_attempts(created.uuid)
        retrieved = await job_repo.get(created.uuid)
        assert retrieved.attempts == 2

    async def test_soft_delete(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        assert await job_repo.soft_delete(created.uuid) is True
        retrieved = await job_repo.get(created.uuid)
        assert retrieved is None

    async def test_hard_delete(self, job_repo, sample_job_data):
        created = await job_repo.create(**sample_job_data)
        assert await job_repo.hard_delete(created.uuid) is True
        retrieved = await job_repo.get(created.uuid)
        assert retrieved is None

    async def test_list_recent(self, job_repo):
        for i in range(5):
            await job_repo.create(job_type="pipeline.test", project_id="p1", queue="default")
        jobs = await job_repo.list_recent(limit=10)
        assert len(jobs) == 5

    async def test_list_by_status(self, job_repo):
        for i in range(3):
            await job_repo.create(job_type="test", project_id="p1", queue="q", status="running")
        for i in range(2):
            await job_repo.create(job_type="test", project_id="p1", queue="q", status="completed")
        running = await job_repo.list_by_status("running")
        completed = await job_repo.list_by_status("completed")
        assert len(running) == 3
        assert len(completed) == 2

    async def test_list_by_type(self, job_repo):
        for i in range(4):
            await job_repo.create(job_type="pipeline.export", project_id="p1", queue="q")
        jobs = await job_repo.list_by_type("pipeline.export")
        assert len(jobs) == 4

    async def test_list_by_project(self, job_repo):
        for i in range(3):
            await job_repo.create(job_type="test", project_id="project-alpha", queue="q")
        jobs = await job_repo.list_by_project("project-alpha")
        assert len(jobs) == 3

    async def test_count_by_status(self, job_repo):
        await job_repo.create(job_type="t1", project_id="p1", queue="q", status="pending")
        await job_repo.create(job_type="t2", project_id="p1", queue="q", status="running")
        await job_repo.create(job_type="t3", project_id="p1", queue="q", status="completed")
        counts = await job_repo.count_by_status()
        assert counts.get("pending") == 1
        assert counts.get("running") == 1
        assert counts.get("completed") == 1

    async def test_find_stuck_jobs(self, job_repo):
        old_start = datetime.now(timezone.utc) - timedelta(hours=2)
        created = await job_repo.create(
            job_type="test", project_id="p1", queue="q", status="running",
            started_at=old_start,
        )
        stuck = await job_repo.find_stuck_jobs(timeout_minutes=30)
        uuids = [j.uuid for j in stuck]
        assert created.uuid in uuids

    async def test_find_stuck_jobs_no_false_positives(self, job_repo):
        now = datetime.now(timezone.utc)
        created = await job_repo.create(
            job_type="test", project_id="p1", queue="q", status="running",
            started_at=now,
        )
        stuck = await job_repo.find_stuck_jobs(timeout_minutes=30)
        uuids = [j.uuid for j in stuck]
        assert created.uuid not in uuids

    async def test_get_metrics(self, job_repo):
        await job_repo.create(job_type="t1", project_id="p1", queue="q", status="completed", duration_ms=500)
        await job_repo.create(job_type="t2", project_id="p1", queue="q", status="running")
        metrics = await job_repo.get_metrics()
        assert metrics["total"] == 2
        assert metrics["by_status"]["completed"] == 1
        assert metrics["by_status"]["running"] == 1
        assert metrics["avg_duration_ms"] == 500.0

    async def test_pagination(self, job_repo):
        for i in range(25):
            await job_repo.create(job_type="test", project_id="p1", queue="q")
        page1 = await job_repo.list_recent(limit=10, offset=0)
        page2 = await job_repo.list_recent(limit=10, offset=10)
        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].uuid != page2[0].uuid
