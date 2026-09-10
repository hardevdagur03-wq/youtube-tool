"""Tests for TaskScheduler — periodic, delayed, and batch task scheduling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from background_processing.task_scheduler import ScheduledTask, TaskScheduler


@pytest.fixture
def scheduler():
    app = MagicMock()
    app.conf.beat_schedule = {}
    app.send_task = MagicMock(return_value=MagicMock(id="task-id-001"))
    return TaskScheduler(celery_app=app)


class TestTaskScheduler:
    def test_default_scheduled_tasks(self):
        tasks = TaskScheduler.default_scheduled_tasks()
        assert len(tasks) == 5
        names = [t.name for t in tasks]
        assert "cleanup-stale-jobs" in names
        assert "cleanup-expired-results" in names
        assert "system-health-check" in names
        assert "backup-job-history" in names
        assert "dlq-cleanup" in names

    def test_register_periodic_tasks(self, scheduler):
        tasks = [
            ScheduledTask(
                name="test-task",
                task_path="test.task",
                schedule_def=300,
                queue="background",
            )
        ]
        scheduler.register_periodic_tasks(tasks)
        assert "test-task" in scheduler._app.conf.beat_schedule

    def test_register_disabled_task(self, scheduler):
        tasks = [
            ScheduledTask(
                name="disabled-task",
                task_path="test.disabled",
                schedule_def=300,
                enabled=False,
            )
        ]
        scheduler.register_periodic_tasks(tasks)
        assert "disabled-task" not in scheduler._app.conf.beat_schedule

    def test_schedule_delayed(self, scheduler):
        result = scheduler.schedule_delayed(
            "test.task", args=(1,), kwargs={"key": "val"}, delay_seconds=60, queue="default"
        )
        assert result.id == "task-id-001"
        scheduler._app.send_task.assert_called_once_with(
            "test.task", args=(1,), kwargs={"key": "val"}, queue="default",
            task_id=None, countdown=60,
        )

    def test_schedule_delayed_zero_delay(self, scheduler):
        result = scheduler.schedule_delayed("test.task", queue="default")
        assert result is not None

    def test_schedule_at(self, scheduler):
        eta = datetime.now(timezone.utc) + timedelta(hours=1)
        result = scheduler.schedule_at(
            "test.task", args=(1,), kwargs={}, eta=eta, queue="high"
        )
        assert result.id == "task-id-001"
        scheduler._app.send_task.assert_called_once_with(
            "test.task", args=(1,), kwargs={}, queue="high",
            task_id=None, eta=eta,
        )

    def test_schedule_batch(self, scheduler):
        scheduler._app.send_task = MagicMock(
            side_effect=[MagicMock(id=f"task-{i}") for i in range(3)]
        )
        import asyncio
        task_ids = asyncio.run(
            scheduler.schedule_batch("test.task", list(range(25)), chunk_size=10, queue="low")
        )
        assert len(task_ids) == 3
        assert scheduler._app.send_task.call_count == 3

    def test_schedule_batch_with_delay(self, scheduler):
        scheduler._app.send_task = MagicMock(
            side_effect=[MagicMock(id=f"task-{i}") for i in range(2)]
        )
        import asyncio
        task_ids = asyncio.run(
            scheduler.schedule_batch("test.task", list(range(15)), chunk_size=10,
                                      queue="default", delay_between_chunks=5)
        )
        assert len(task_ids) == 2

    def test_register_cron(self, scheduler):
        scheduler.register_cron(
            name="cron-task",
            task_path="test.cron_task",
            minute="0", hour="*/6", queue="background",
        )
        assert "cron-task" in scheduler._app.conf.beat_schedule
