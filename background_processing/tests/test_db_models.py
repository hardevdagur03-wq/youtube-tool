"""Tests for the additional DB models — JobExecution, WorkerNode, QueueMetrics, TaskEvent."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select


class TestJobExecutionModel:
    async def test_create_job_execution(self, session):
        from background_processing.db_models import JobExecutionModel
        exec_entry = JobExecutionModel(
            job_id="job-123",
            attempt=1,
            status="running",
            worker_id="worker-1",
            celery_task_id="celery-abc",
            hostname="worker-host-1",
        )
        session.add(exec_entry)
        await session.flush()

        result = await session.execute(
            select(JobExecutionModel).where(JobExecutionModel.job_id == "job-123")
        )
        saved = result.scalar_one()
        assert saved.attempt == 1
        assert saved.status == "running"
        assert saved.worker_id == "worker-1"

    async def test_job_execution_unique_ids(self, session):
        from background_processing.db_models import JobExecutionModel
        from background_processing.models import make_uuid
        e1 = JobExecutionModel(uuid=make_uuid(), job_id="j1", attempt=1, status="running")
        e2 = JobExecutionModel(uuid=make_uuid(), job_id="j1", attempt=2, status="completed")
        session.add_all([e1, e2])
        await session.flush()


class TestWorkerNodeModel:
    async def test_create_worker_node(self, session):
        from background_processing.db_models import WorkerNodeModel
        node = WorkerNodeModel(
            worker_id="worker-1",
            hostname="host-1",
            status="active",
            queues="ai,high",
            concurrency=4,
            pool_type="prefork",
        )
        session.add(node)
        await session.flush()

        result = await session.execute(
            select(WorkerNodeModel).where(WorkerNodeModel.worker_id == "worker-1")
        )
        saved = result.scalar_one()
        assert saved.status == "active"
        assert saved.concurrency == 4


class TestQueueMetricsModel:
    async def test_create_queue_metrics(self, session):
        from background_processing.db_models import QueueMetricsModel
        from datetime import datetime
        qm = QueueMetricsModel(
            queue_name="ai",
            length=10,
            active=3,
            reserved=2,
            scheduled=1,
            completed_total=100,
            throughput_per_minute=5.5,
        )
        session.add(qm)
        await session.flush()

        result = await session.execute(
            select(QueueMetricsModel).where(QueueMetricsModel.queue_name == "ai")
        )
        saved = result.scalar_one()
        assert saved.length == 10
        assert saved.active == 3
        assert saved.throughput_per_minute == 5.5


class TestTaskEventModel:
    async def test_create_task_event(self, session):
        from background_processing.db_models import TaskEventModel
        event = TaskEventModel(
            job_id="job-123",
            project_id="proj-1",
            celery_task_id="celery-abc",
            event_type="job.started",
            event_data={"worker": "w1"},
            worker_id="worker-1",
        )
        session.add(event)
        await session.flush()

        result = await session.execute(
            select(TaskEventModel).where(TaskEventModel.job_id == "job-123")
        )
        saved = result.scalar_one()
        assert saved.event_type == "job.started"
        assert saved.event_data == {"worker": "w1"}

    async def test_task_event_indexes(self, session):
        from background_processing.db_models import TaskEventModel
        event = TaskEventModel(
            job_id="j1", event_type="test", event_data={},
        )
        session.add(event)
        await session.flush()
