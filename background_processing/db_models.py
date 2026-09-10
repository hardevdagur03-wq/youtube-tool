"""Additional Database Models for the Enterprise Background Processing Platform.

Adds tables for execution tracking, worker nodes, queue metrics, and task events.
Extends the existing JobModel without modifying it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from database.base import BaseModel as DBBaseModel
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class JobExecutionModel(DBBaseModel):
    """Individual execution attempt for a job (supports retries)."""
    __tablename__ = "background_job_executions"

    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    traceback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class WorkerNodeModel(DBBaseModel):
    """Registered worker node with health and capacity info."""
    __tablename__ = "background_worker_nodes"

    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    queues: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False, default="prefork")
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_rss_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    active_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_processed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tasks_failed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="")


class QueueMetricsModel(DBBaseModel):
    """Snapshots of queue metrics over time for monitoring."""
    __tablename__ = "background_queue_metrics"

    queue_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_wait_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    throughput_per_minute: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(),
    )


class TaskEventModel(DBBaseModel):
    """Audit trail of all task lifecycle events."""
    __tablename__ = "background_task_events"

    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, default="", index=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(),
        index=True,
    )
