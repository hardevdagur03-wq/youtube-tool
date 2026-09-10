"""Task Scheduler — cron, delayed, recurring, and batch job scheduling.

Integrates with Celery Beat for periodic tasks and provides
programmatic scheduling for delayed and batch jobs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from celery import Celery
from celery.schedules import crontab, schedule

from background_processing.celery_app import get_celery_app
from background_processing.config import BackgroundProcessingConfig
from background_processing.models import JobPriority, JobType

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Descriptor for a recurring scheduled task."""

    def __init__(
        self,
        name: str,
        task_path: str,
        schedule_def: crontab | schedule | int | float,
        args: tuple | None = None,
        kwargs: dict[str, Any] | None = None,
        queue: str = "background",
        priority: JobPriority = JobPriority.BACKGROUND,
        enabled: bool = True,
        description: str = "",
    ) -> None:
        self.name = name
        self.task_path = task_path
        self.schedule_def = schedule_def
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.queue = queue
        self.priority = priority
        self.enabled = enabled
        self.description = description


class TaskScheduler:
    """Manages scheduled, delayed, and batch job execution.

    Registers periodic tasks with Celery Beat.
    Provides methods for ad-hoc delayed execution.
    """

    def __init__(
        self,
        config: BackgroundProcessingConfig | None = None,
        celery_app: Celery | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._app = celery_app or get_celery_app()

    # ------------------------------------------------------------------
    # Built-in scheduled tasks
    # ------------------------------------------------------------------

    @staticmethod
    def default_scheduled_tasks() -> list[ScheduledTask]:
        """Return the default set of scheduled maintenance tasks."""
        return [
            ScheduledTask(
                name="cleanup-stale-jobs",
                task_path="background_processing.tasks.cleanup_tasks.cleanup_stale_jobs",
                schedule_def=3600,  # every hour
                queue="background",
                priority=JobPriority.BACKGROUND,
                description="Reset stuck jobs back to pending",
            ),
            ScheduledTask(
                name="cleanup-expired-results",
                task_path="background_processing.tasks.cleanup_tasks.cleanup_expired_results",
                schedule_def=86400,  # daily
                queue="background",
                priority=JobPriority.BACKGROUND,
                description="Purge expired Celery result backend entries",
            ),
            ScheduledTask(
                name="system-health-check",
                task_path="background_processing.tasks.cleanup_tasks.system_health_check",
                schedule_def=300,  # every 5 minutes
                queue="system",
                priority=JobPriority.SYSTEM,
                description="Periodic health check of all system components",
            ),
            ScheduledTask(
                name="backup-job-history",
                task_path="background_processing.tasks.cleanup_tasks.backup_job_history",
                schedule_def=86400,  # daily
                queue="background",
                priority=JobPriority.BACKGROUND,
                description="Archive completed job records",
            ),
            ScheduledTask(
                name="dlq-cleanup",
                task_path="background_processing.tasks.cleanup_tasks.dlq_cleanup",
                schedule_def=86400,  # daily
                queue="background",
                priority=JobPriority.BACKGROUND,
                description="Purge expired dead letter entries",
            ),
        ]

    def register_periodic_tasks(
        self, tasks: list[ScheduledTask] | None = None
    ) -> None:
        """Register periodic tasks with Celery Beat.

        Call this at application startup to activate scheduled tasks.

        Args:
            tasks: List of ScheduledTask definitions. Uses defaults if None.
        """
        tasks = tasks or self.default_scheduled_tasks()
        beat_schedule = {}

        for task in tasks:
            if not task.enabled:
                continue
            beat_schedule[task.name] = {
                "task": task.task_path,
                "schedule": task.schedule_def,
                "args": task.args,
                "kwargs": {**task.kwargs, "_queue": task.queue},
                "options": {"queue": task.queue},
            }
            logger.info(
                "Scheduled task registered: %s → %s (%s)",
                task.name, task.task_path, task.queue,
            )

        self._app.conf.beat_schedule = {
            **self._app.conf.beat_schedule,
            **beat_schedule,
        }
        self._app.conf.beat_max_loop_interval = self._config.beat_max_loop_interval

    # ------------------------------------------------------------------
    # Delayed execution
    # ------------------------------------------------------------------

    def schedule_delayed(
        self,
        task_path: str,
        args: tuple | None = None,
        kwargs: dict[str, Any] | None = None,
        delay_seconds: int = 0,
        queue: str = "default",
        task_id: str | None = None,
    ) -> Any:
        """Schedule a task for delayed execution.

        Returns the Celery AsyncResult.
        """
        kwargs = kwargs or {}
        countdown = max(0, delay_seconds)
        result = self._app.send_task(
            task_path,
            args=args or (),
            kwargs=kwargs,
            queue=queue,
            task_id=task_id,
            countdown=countdown,
        )
        logger.debug(
            "Delayed task scheduled: %s (delay=%ds, queue=%s)",
            task_path, countdown, queue,
        )
        return result

    def schedule_at(
        self,
        task_path: str,
        args: tuple | None = None,
        kwargs: dict[str, Any] | None = None,
        eta: datetime | None = None,
        queue: str = "default",
        task_id: str | None = None,
    ) -> Any:
        """Schedule a task at a specific datetime."""
        kwargs = kwargs or {}
        result = self._app.send_task(
            task_path,
            args=args or (),
            kwargs=kwargs,
            queue=queue,
            task_id=task_id,
            eta=eta,
        )
        logger.debug(
            "Task scheduled at %s: %s (queue=%s)",
            eta.isoformat() if eta else "now", task_path, queue,
        )
        return result

    # ------------------------------------------------------------------
    # Batch execution
    # ------------------------------------------------------------------

    async def schedule_batch(
        self,
        task_path: str,
        items: list[Any],
        chunk_size: int = 10,
        queue: str = "default",
        delay_between_chunks: int = 0,
    ) -> list[str]:
        """Schedule a batch of tasks, chunked for parallel execution.

        Args:
            task_path: Celery task path to execute for each chunk.
            items: List of items to process (each chunk is a sublist).
            chunk_size: Number of items per task.
            queue: Target queue.
            delay_between_chunks: Delay in seconds between chunks.

        Returns:
            List of Celery task IDs.
        """
        task_ids = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            countdown = (i // chunk_size) * delay_between_chunks
            result = self._app.send_task(
                task_path,
                args=(chunk,),
                queue=queue,
                countdown=countdown,
            )
            task_ids.append(result.id)
        logger.info(
            "Batch scheduled: %d items in %d tasks (chunk_size=%d, queue=%s)",
            len(items), len(task_ids), chunk_size, queue,
        )
        return task_ids

    # ------------------------------------------------------------------
    # Recurring task registration helper
    # ------------------------------------------------------------------

    def register_cron(
        self,
        name: str,
        task_path: str,
        minute: str = "*",
        hour: str = "*",
        day_of_week: str = "*",
        day_of_month: str = "*",
        month_of_year: str = "*",
        kwargs: dict[str, Any] | None = None,
        queue: str = "background",
    ) -> None:
        """Register a cron-triggered task."""
        self._app.conf.beat_schedule[name] = {
            "task": task_path,
            "schedule": crontab(
                minute=minute,
                hour=hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
            ),
            "kwargs": kwargs or {},
            "options": {"queue": queue},
        }
        logger.info("Cron task registered: %s (%s %s %s %s %s)", name, minute, hour, day_of_month, month_of_year, day_of_week)
