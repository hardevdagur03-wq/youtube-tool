"""Tests for the Queue Router — type-based, priority-based, and tenant-aware routing."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.models import JobCreate, JobPriority, JobType
from background_processing.queue_router import QueueRouter


class TestQueueRouter:
    @pytest.fixture
    def router(self):
        return QueueRouter()

    async def test_route_pipeline_analysis_to_ai(self, router):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1")
        queue = await router.route(job)
        assert queue == "ai"

    async def test_route_pipeline_transcript_to_transcript(self, router):
        job = JobCreate(job_type="pipeline.transcript", project_id="p1")
        queue = await router.route(job)
        assert queue == "transcript"

    async def test_route_export_to_export(self, router):
        job = JobCreate(job_type="export.single", project_id="p1")
        queue = await router.route(job)
        assert queue == "export"

    async def test_route_cleanup_to_maintenance(self, router):
        job = JobCreate(job_type="cleanup.project", project_id="p1")
        queue = await router.route(job)
        assert queue == "maintenance"

    async def test_route_system_to_maintenance(self, router):
        job = JobCreate(job_type="system.backup", project_id="p1")
        queue = await router.route(job)
        assert queue == "maintenance"

    async def test_route_default_queue(self, router):
        job = JobCreate(job_type="email.send", project_id="p1")
        queue = await router.route(job)
        assert queue == "default"

    async def test_priority_critical_overrides_to_critical(self, router):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", priority=JobPriority.CRITICAL)
        queue = await router.route(job)
        assert queue == "critical"

    async def test_priority_background_overrides_to_background(self, router):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", priority=JobPriority.BACKGROUND)
        queue = await router.route(job)
        assert queue == "background"

    async def test_tenant_isolation(self, router):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1")
        queue = await router.route(job, tenant_id="tenant-xyz")
        assert "tenant-xyz" in queue or ":" in queue

    async def test_route_batch(self, router):
        jobs = [
            JobCreate(job_type="pipeline.analysis", project_id="p1"),
            JobCreate(job_type="export.single", project_id="p1"),
            JobCreate(job_type="system.health_check", project_id="p1"),
        ]
        queues = await router.route_batch(jobs)
        assert len(queues) == 3
        assert queues[0] == "ai"
        assert queues[1] == "export"
        assert queues[2] == "maintenance"

    async def test_register_custom_routing(self, router):
        router.register_routing("custom.task", "custom-queue")
        job = JobCreate(job_type="custom.task", project_id="p1")
        queue = await router.route(job)
        assert queue == "custom-queue"

    async def test_get_available_queues(self, router):
        queues = await router.get_available_queues()
        assert "ai" in queues
        assert "transcript" in queues
        assert "export" in queues
        assert "maintenance" in queues
        assert "critical" in queues
        assert len(queues) >= 6

    async def test_unknown_job_type_uses_default(self, router):
        job = JobCreate(job_type="completely.unknown.task", project_id="p1")
        queue = await router.route(job)
        assert queue == "default"

    async def test_normal_priority_pipeline_stays_ai(self, router):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", priority=JobPriority.NORMAL)
        queue = await router.route(job)
        assert queue == "ai"
