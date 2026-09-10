"""Celery Application — configured with Redis broker, result backend, and all workers."""

from __future__ import annotations

import logging
from typing import Any

from celery import Celery
from celery.signals import (
    after_task_publish, before_task_publish, task_failure,
    task_postrun, task_prerun, task_rejected, task_retry, task_success,
    worker_init, worker_process_init, worker_ready, worker_shutdown,
)

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)

_config: BackgroundProcessingConfig | None = None
_celery_app: Celery | None = None


def create_celery_app(
    config: BackgroundProcessingConfig | None = None,
) -> Celery:
    """Create and configure the Celery application singleton.

    Call once at application startup. Subsequent calls return the same instance.
    """
    global _celery_app, _config

    if _celery_app is not None:
        return _celery_app

    _config = config or BackgroundProcessingConfig.from_env()
    cfg = _config

    app = Celery("yt_blog_worker")
    app.config_from_object(cfg.celery_kwargs)

    # --- Queue Configuration ---
    from kombu import Exchange, Queue

    app.conf.task_queues = [
        Queue(name, exchange=Exchange(exchange, type="direct"),
              routing_key=routing_key, queue_arguments={"x-max-priority": 10})
        for name, exchange, routing_key in [
            ("critical", "critical", "critical"),
            ("high", "high", "high"),
            ("default", "default", "default"),
            ("low", "low", "low"),
            ("background", "background", "background"),
            ("system", "system", "system"),
            ("dead_letter", "dead_letter", "dead_letter"),
        ]
    ]

    # --- Task Routing ---
    app.conf.task_routes = {
        "pipeline.*": {"queue": "high"},
        "export.*": {"queue": "default"},
        "cleanup.*": {"queue": "background"},
        "system.*": {"queue": "system"},
        "ai.*": {"queue": "high"},
    }

    # --- Beat Schedule (populated by external registration) ---
    app.conf.beat_schedule = {}
    app.conf.beat_max_loop_interval = cfg.beat_max_loop_interval

    # --- Broker Pool ---
    app.conf.broker_pool_limit = cfg.db_pool_size
    app.conf.broker_connection_retry_on_startup = True
    app.conf.broker_connection_max_retries = 10

    app.conf.worker_redirect_stdouts = True
    app.conf.worker_redirect_stdouts_level = "INFO"

    # --- Register signal handlers ---
    _register_signals(app)

    _celery_app = app
    logger.info("Celery app created: broker=%s, backend=%s", cfg.broker_url, cfg.result_backend)
    return app


def get_celery_app() -> Celery:
    """Return the existing Celery app or create one with default config."""
    if _celery_app is None:
        return create_celery_app()
    return _celery_app


def _register_signals(app: Celery) -> None:
    """Register Celery signal handlers for observability."""

    @before_task_publish.connect
    def on_before_publish(headers=None, body=None, **kwargs: Any) -> None:
        logger.debug("Task about to publish: %s", headers.get("task") if headers else "unknown")

    @after_task_publish.connect
    def on_after_publish(headers=None, body=None, **kwargs: Any) -> None:
        logger.debug("Task published: %s", headers.get("task") if headers else "unknown")

    @task_prerun.connect
    def on_task_prerun(task_id: str = "", task: Any = None, **kwargs: Any) -> None:
        logger.info("Task started: %s [%s]", task.name if task else "?", task_id[:8])

    @task_success.connect
    def on_task_success(sender: Any = None, result: Any = None, **kwargs: Any) -> None:
        logger.info("Task succeeded: %s", sender.name if sender else "?")

    @task_failure.connect
    def on_task_failure(
        sender: Any = None, task_id: str = "", exception: Exception | None = None,
        traceback: str = "", einfo: Any = None, **kwargs: Any,
    ) -> None:
        logger.error("Task failed: %s [%s]: %s",
                      sender.name if sender else "?", task_id[:8], exception)

    @task_retry.connect
    def on_task_retry(
        sender: Any = None, request: Any = None, reason: str = "", **kwargs: Any,
    ) -> None:
        logger.warning("Task retrying: %s: %s",
                       sender.name if sender else "?", reason)

    @task_rejected.connect
    def on_task_rejected(sender: Any = None, **kwargs: Any) -> None:
        logger.error("Task rejected: %s", sender.name if sender else "?")

    @worker_ready.connect
    def on_worker_ready(**kwargs: Any) -> None:
        logger.info("Worker ready, processing tasks...")

    @worker_shutdown.connect
    def on_worker_shutdown(**kwargs: Any) -> None:
        logger.info("Worker shutting down...")

    @worker_init.connect
    def on_worker_init(**kwargs: Any) -> None:
        logger.info("Worker initializing...")

    @task_postrun.connect
    def on_task_postrun(task_id: str = "", task: Any = None, **kwargs: Any) -> None:
        logger.debug("Task postrun: %s [%s]", task.name if task else "?", task_id[:8])


def celery_app() -> Celery:
    """Convenience accessor (same as get_celery_app)."""
    return get_celery_app()
