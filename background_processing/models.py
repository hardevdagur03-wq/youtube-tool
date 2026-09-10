"""Job Models — Pydantic schemas and SQLAlchemy model for job persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from database.base import BaseModel as DBBaseModel
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"
    SYSTEM = "system"


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RESERVED = "reserved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
    RECOVERED = "recovered"


class JobType(str, Enum):
    PIPELINE_METADATA = "pipeline.metadata"
    PIPELINE_TRANSCRIPT = "pipeline.transcript"
    PIPELINE_ANALYSIS = "pipeline.analysis"
    PIPELINE_KNOWLEDGE_GRAPH = "pipeline.knowledge_graph"
    PIPELINE_SEO = "pipeline.seo"
    PIPELINE_SEO_INTELLIGENCE = "pipeline.seo_intelligence"
    PIPELINE_OUTLINE = "pipeline.outline"
    PIPELINE_SECTIONS = "pipeline.sections"
    PIPELINE_MERGE = "pipeline.merge"
    PIPELINE_REVIEW = "pipeline.review"
    PIPELINE_OPTIMIZATION = "pipeline.optimization"
    PIPELINE_EXPORT = "pipeline.export"
    EXPORT_SINGLE = "export.single"
    EXPORT_BULK = "export.bulk"
    CLEANUP_PROJECT = "cleanup.project"
    CLEANUP_CACHE = "cleanup.cache"
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    AI_CUSTOM = "ai.custom"
    TRANSCRIPT_TRANSLATE = "transcript.translate"
    TRANSCRIPT_GENERATE = "transcript.generate"
    AI_EMBEDDING = "ai.embedding"
    AI_SUMMARIZE = "ai.summarize"
    EMAIL_SEND = "email.send"
    EMAIL_BATCH = "email.batch"
    NOTIFICATION_PUSH = "notification.push"
    NOTIFICATION_WEBHOOK = "notification.webhook"
    PUBLISHING_CMS = "publishing.cms"
    PUBLISHING_SCHEDULE = "publishing.schedule"
    ANALYTICS_PROCESS = "analytics.process"
    ANALYTICS_REPORT = "analytics.report"
    BACKUP_DATABASE = "backup.database"
    BACKUP_FILES = "backup.files"
    CACHE_REFRESH = "cache.refresh"
    CACHE_WARM = "cache.warm"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class JobProgress(BaseModel):
    pct: float = 0.0
    message: str = ""
    stage: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)


class RetryAttempt(BaseModel):
    attempt: int = 1
    scheduled_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    traceback: str = ""


class DeadLetterEntry(BaseModel):
    job_id: str = ""
    project_id: str = ""
    job_type: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    traceback: str = ""
    retry_history: list[RetryAttempt] = Field(default_factory=list)
    failed_at: str = ""
    recovery_recommendation: str = ""
    recovered: bool = False


class JobCreate(BaseModel):
    job_type: str
    project_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    queue: str = "default"
    scheduled_at: str | None = None
    max_retries: int = 3
    retry_delay: int = 60
    celery_task_id: str = ""
    tags: list[str] = Field(default_factory=list)
    parent_job_id: str = ""


class JobResponse(BaseModel):
    job_id: str = ""
    job_type: str = ""
    project_id: str = ""
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    queue: str = "default"
    progress: JobProgress = Field(default_factory=JobProgress)
    attempts: int = 0
    max_retries: int = 3
    celery_task_id: str = ""
    worker_id: str = ""
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    tags: list[str] = Field(default_factory=list)
    parent_job_id: str = ""


class BatchJobRequest(BaseModel):
    jobs: list[JobCreate] = Field(default_factory=list)
    parallel: bool = True
    max_concurrency: int = 5


class BatchJobResponse(BaseModel):
    batch_id: str = ""
    job_ids: list[str] = Field(default_factory=list)
    total: int = 0


class QueueMetrics(BaseModel):
    queue_name: str = ""
    length: int = 0
    active: int = 0
    reserved: int = 0
    scheduled: int = 0
    failed: int = 0
    avg_wait_time_ms: float = 0.0
    avg_duration_ms: float = 0.0
    throughput_per_minute: float = 0.0


class WorkerInfo(BaseModel):
    worker_id: str = ""
    hostname: str = ""
    status: str = "unknown"
    active_tasks: int = 0
    processed_tasks: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_rss_bytes: int = 0
    started_at: str = ""
    last_heartbeat: str = ""
    queues: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SQLAlchemy Model
# ---------------------------------------------------------------------------


class JobModel(DBBaseModel):
    __tablename__ = "background_jobs"

    project_id: Mapped[str] = mapped_column(String(36), nullable=False, default="", index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", index=True)
    queue: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    retry_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    traceback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parent_job_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    lock_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    recoverable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<JobModel uuid={self.uuid} type={self.job_type} status={self.status}>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_uuid() -> str:
    return str(uuid.uuid4())


# Pipeline stage order for dependency tracking
STAGE_ORDER = [
    "pipeline.metadata",
    "pipeline.transcript",
    "pipeline.analysis",
    "pipeline.knowledge_graph",
    "pipeline.seo",
    "pipeline.seo_intelligence",
    "pipeline.outline",
    "pipeline.sections",
    "pipeline.merge",
    "pipeline.review",
    "pipeline.optimization",
    "pipeline.export",
]
