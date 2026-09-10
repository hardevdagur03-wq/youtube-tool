"""Enterprise Celery Configuration — extended queue topology with 12+ queues and dedicated worker pools.

Queue Architecture:
  critical     — System-critical operations (priority 0, max-priority 10)
  high         — High-priority AI/pipeline jobs (priority 3)
  default      — Standard jobs (priority 5)
  low          — Low-priority jobs (priority 8)
  background   — Background maintenance (priority 10)
  system       — System health checks (priority 1)
  ai           — AI-intensive operations (LLM calls)
  transcript   — Transcript processing
  export       — Export operations (markdown, HTML, PDF)
  publishing   — CMS publishing operations
  email        — Email notifications
  notification — Push notifications / webhooks
  maintenance  — Cleanup, backup, health checks
  analytics    — Analytics processing
  dead_letter  — Failed job storage

Worker Pools:
  - AI Workers:    ai, high queues
  - Transcript:    transcript queue
  - Export:        export, publishing queues
  - Notification:  email, notification queues
  - Maintenance:   maintenance, background, system queues
  - Analytics:     analytics queue

No single queue bottleneck. Workers scale independently.
"""

from __future__ import annotations

import logging
from kombu import Exchange, Queue
from celery import Celery

logger = logging.getLogger(__name__)


# Full enterprise queue topology
QUEUE_DEFINITIONS = [
    Queue("critical",    Exchange("critical", type="direct"),    routing_key="critical",    queue_arguments={"x-max-priority": 10}),
    Queue("high",        Exchange("high", type="direct"),        routing_key="high",        queue_arguments={"x-max-priority": 10}),
    Queue("default",     Exchange("default", type="direct"),     routing_key="default",     queue_arguments={"x-max-priority": 10}),
    Queue("low",         Exchange("low", type="direct"),         routing_key="low",         queue_arguments={"x-max-priority": 10}),
    Queue("background",  Exchange("background", type="direct"),  routing_key="background",  queue_arguments={"x-max-priority": 10}),
    Queue("system",      Exchange("system", type="direct"),      routing_key="system",      queue_arguments={"x-max-priority": 10}),
    Queue("ai",          Exchange("ai", type="direct"),          routing_key="ai",          queue_arguments={"x-max-priority": 10}),
    Queue("transcript",  Exchange("transcript", type="direct"),  routing_key="transcript",  queue_arguments={"x-max-priority": 10}),
    Queue("export",      Exchange("export", type="direct"),      routing_key="export",      queue_arguments={"x-max-priority": 10}),
    Queue("publishing",  Exchange("publishing", type="direct"),  routing_key="publishing",  queue_arguments={"x-max-priority": 10}),
    Queue("email",       Exchange("email", type="direct"),       routing_key="email",       queue_arguments={"x-max-priority": 10}),
    Queue("notification",Exchange("notification", type="direct"),routing_key="notification", queue_arguments={"x-max-priority": 10}),
    Queue("maintenance", Exchange("maintenance", type="direct"), routing_key="maintenance", queue_arguments={"x-max-priority": 10}),
    Queue("analytics",   Exchange("analytics", type="direct"),   routing_key="analytics",   queue_arguments={"x-max-priority": 10}),
    Queue("dead_letter", Exchange("dead_letter", type="direct"), routing_key="dead_letter", queue_arguments={"x-max-priority": 10}),
]

# Enterprise routing table
ENTERPRISE_TASK_ROUTES = {
    "pipeline.*":            {"queue": "high"},
    "transcript.*":          {"queue": "transcript"},
    "ai.*":                  {"queue": "ai"},
    "export.*":              {"queue": "export"},
    "publishing.*":          {"queue": "publishing"},
    "email.*":               {"queue": "email"},
    "notification.*":        {"queue": "notification"},
    "cleanup.*":             {"queue": "maintenance"},
    "system.*":              {"queue": "system"},
    "analytics.*":           {"queue": "analytics"},
    "backup.*":              {"queue": "maintenance"},
    "cache.*":               {"queue": "background"},
    "embedding.*":           {"queue": "ai"},
}


def configure_enterprise_queues(app: Celery) -> None:
    """Configure the enterprise queue topology on an existing Celery app."""
    app.conf.task_queues = QUEUE_DEFINITIONS
    app.conf.task_routes = ENTERPRISE_TASK_ROUTES
    app.conf.task_default_queue = "default"
    app.conf.task_default_exchange = "default"
    app.conf.task_default_routing_key = "default"
    logger.info("Enterprise queue topology configured: %d queues", len(QUEUE_DEFINITIONS))


# Worker pool configuration helpers

WORKER_POOLS = {
    "ai": {
        "queues": "ai,high,critical",
        "concurrency": 2,
        "pool": "prefork",
        "max_tasks": 500,
        "max_memory": 400000,
    },
    "transcript": {
        "queues": "transcript",
        "concurrency": 4,
        "pool": "gevent",
        "max_tasks": 1000,
        "max_memory": 200000,
    },
    "export": {
        "queues": "export,publishing",
        "concurrency": 2,
        "pool": "prefork",
        "max_tasks": 500,
        "max_memory": 300000,
    },
    "notification": {
        "queues": "email,notification",
        "concurrency": 2,
        "pool": "threads",
        "max_tasks": 2000,
        "max_memory": 100000,
    },
    "maintenance": {
        "queues": "maintenance,background,system,dead_letter",
        "concurrency": 1,
        "pool": "solo",
        "max_tasks": 100,
        "max_memory": 100000,
    },
    "analytics": {
        "queues": "analytics,low",
        "concurrency": 1,
        "pool": "prefork",
        "max_tasks": 500,
        "max_memory": 200000,
    },
    "default": {
        "queues": "default,low,background",
        "concurrency": 4,
        "pool": "prefork",
        "max_tasks": 1000,
        "max_memory": 200000,
    },
}


def get_worker_command(pool_name: str, app_name: str = "background_processing.celery_app") -> list[str]:
    """Get the Celery worker command for a named worker pool."""
    cfg = WORKER_POOLS.get(pool_name)
    if cfg is None:
        raise ValueError(f"Unknown worker pool: {pool_name}. Available: {list(WORKER_POOLS.keys())}")

    return [
        "celery",
        "-A", app_name,
        "worker",
        "--loglevel", "INFO",
        "--concurrency", str(cfg["concurrency"]),
        "--pool", cfg["pool"],
        "--queues", cfg["queues"],
        "--max-tasks-per-child", str(cfg["max_tasks"]),
        "--max-memory-per-child", str(cfg["max_memory"]),
        "--hostname", f"{pool_name}@%h",
    ]
