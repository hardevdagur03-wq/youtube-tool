"""Background Processing Platform — Enterprise-grade Celery-based async job execution.

Provides a complete distributed task execution framework with:
- Celery workers with priority queues and task routing (15 queues)
- Redis-backed job state management and dead letter queue
- Real-time progress events via Redis Pub/Sub
- Distributed locking for idempotent execution
- Prometheus metrics and OpenTelemetry tracing
- Worker lifecycle management and health monitoring
- Task scheduling via Celery Beat
- Job dispatcher with rate limiting, idempotency, security
- Queue router with intelligent type/priority/tenant routing
- Workflow engine with chains, groups, chords, conditional branching
- Failure recovery with auto-detection and re-dispatch
- Multi-tenant isolation and resource management
"""

from background_processing.celery_app import create_celery_app, get_celery_app
from background_processing.celery_enterprise import (
    QUEUE_DEFINITIONS, ENTERPRISE_TASK_ROUTES, WORKER_POOLS,
    configure_enterprise_queues, get_worker_command,
)
from background_processing.config import BackgroundProcessingConfig
from background_processing.db_models import (
    JobExecutionModel, QueueMetricsModel, TaskEventModel, WorkerNodeModel,
)
from background_processing.dead_letter_queue import DeadLetterQueue
from background_processing.dispatcher import JobDispatchError, JobDispatcher
from background_processing.distributed_lock import DistributedLock
from background_processing.event_bus import EventBus, EventType
from background_processing.failure_recovery import FailureRecovery
from background_processing.idempotency import DedupResult, IdempotencyEngine
from background_processing.job_repository import JobRepository
from background_processing.models import (
    BatchJobRequest, BatchJobResponse, DeadLetterEntry,
    JobCreate, JobModel, JobPriority, JobProgress, JobResponse,
    JobStatus, JobType, QueueMetrics, RetryAttempt, WorkerInfo,
    STAGE_ORDER,
)
from background_processing.progress_emitter import ProgressEmitter
from background_processing.queue_router import QueueRouter
from background_processing.rate_limiter import RateLimiter
from background_processing.resource_manager import ResourceManager
from background_processing.retry_manager import RetryManager
from background_processing.security import SecurityManager
from background_processing.task_registry import register as register_task
from background_processing.task_registry import resolve as resolve_task
from background_processing.task_scheduler import TaskScheduler
from background_processing.worker_manager import WorkerManager
from background_processing.workflow_engine import WorkflowEngine, WorkflowStatus

__all__ = [
    "BackgroundProcessingConfig",
    "BatchJobRequest", "BatchJobResponse",
    "configure_enterprise_queues",
    "create_celery_app",
    "DeadLetterEntry", "DeadLetterQueue",
    "DedupResult",
    "DistributedLock",
    "ENTERPRISE_TASK_ROUTES",
    "EventBus", "EventType",
    "FailureRecovery",
    "get_celery_app",
    "get_worker_command",
    "IdempotencyEngine",
    "JobCreate", "JobDispatchError", "JobDispatcher",
    "JobExecutionModel",
    "JobModel", "JobPriority", "JobProgress",
    "JobResponse", "JobStatus", "JobType",
    "ProgressEmitter",
    "QUEUE_DEFINITIONS",
    "QueueMetrics", "QueueMetricsModel",
    "QueueRouter",
    "RateLimiter",
    "register_task", "resolve_task",
    "ResourceManager",
    "RetryAttempt", "RetryManager",
    "SecurityManager",
    "STAGE_ORDER",
    "TaskEventModel",
    "TaskScheduler",
    "WorkerInfo", "WorkerManager", "WorkerNodeModel",
    "WorkflowEngine", "WorkflowStatus",
    "WORKER_POOLS",
]
