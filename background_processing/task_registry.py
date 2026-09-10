"""Task Registry — maps JobType enums to Celery task functions.

Provides a single source of truth for looking up which Celery task
handles a given job type, enabling dynamic task dispatch.

Expanded to support 25+ job types for enterprise workflows.
"""

from __future__ import annotations

from typing import Any

from background_processing.models import JobType

_registry: dict[str, str] = {}


def register(job_type: JobType | str, task_path: str) -> None:
    """Register a mapping from JobType to Celery task path.

    Args:
        job_type: The JobType enum value or string key.
        task_path: The fully-qualified Celery task name.
    """
    key = job_type.value if isinstance(job_type, JobType) else job_type
    _registry[key] = task_path


def resolve(job_type: JobType | str) -> str:
    """Resolve a JobType to its Celery task path.

    Args:
        job_type: The JobType enum value or string key.

    Returns:
        The Celery task path string.

    Raises:
        KeyError: If the job type has not been registered.
    """
    key = job_type.value if isinstance(job_type, JobType) else job_type
    if key not in _registry:
        raise KeyError(f"Job type '{key}' is not registered. Available: {list(_registry.keys())}")
    return _registry[key]


def resolve_all(job_types: list[JobType | str]) -> list[str]:
    """Resolve multiple job types to their task paths."""
    return [resolve(jt) for jt in job_types]


def get_registry() -> dict[str, str]:
    """Return a copy of the current registry."""
    return dict(_registry)


def clear() -> None:
    """Clear all registrations (useful for testing)."""
    _registry.clear()


# ---------------------------------------------------------------------------
# Enterprise registrations — 25+ job types
# ---------------------------------------------------------------------------

# Pipeline
register(JobType.PIPELINE_METADATA, "pipeline.process_video")
register(JobType.PIPELINE_TRANSCRIPT, "pipeline.generate_transcript")
register(JobType.PIPELINE_ANALYSIS, "pipeline.generate_analysis")
register(JobType.PIPELINE_KNOWLEDGE_GRAPH, "pipeline.generate_knowledge_graph")
register(JobType.PIPELINE_SEO, "pipeline.generate_seo_analysis")
register(JobType.PIPELINE_SEO_INTELLIGENCE, "pipeline.generate_seo_analysis")
register(JobType.PIPELINE_OUTLINE, "pipeline.generate_outline")
register(JobType.PIPELINE_SECTIONS, "pipeline.generate_sections")
register(JobType.PIPELINE_MERGE, "pipeline.generate_draft")
register(JobType.PIPELINE_REVIEW, "pipeline.generate_review")
register(JobType.PIPELINE_OPTIMIZATION, "pipeline.generate_optimization")
register(JobType.PIPELINE_EXPORT, "pipeline.generate_export")

# Export
register(JobType.EXPORT_SINGLE, "export.export_project")
register(JobType.EXPORT_BULK, "export.batch_export")

# Cleanup & System
register(JobType.CLEANUP_PROJECT, "cleanup.cleanup_stale_jobs")
register(JobType.CLEANUP_CACHE, "cleanup.cleanup_expired_results")
register(JobType.SYSTEM_BACKUP, "cleanup.backup_job_history")
register(JobType.SYSTEM_HEALTH_CHECK, "cleanup.system_health_check")

# Pipeline hardening tasks
register("pipeline.durable_run", "pipeline.durable_run_workflow")
register("pipeline.checkpoint_cleanup", "pipeline.checkpoint_cleanup")
register("pipeline.dlq_replay", "pipeline.dlq_replay")
register("pipeline.recovery_scan", "pipeline.recovery_scan")

# Extended job types
register("transcript.translate", "transcript.translate_transcript")
register("transcript.generate", "pipeline.generate_transcript")
register("ai.custom", "ai.execute_custom")
register("ai.embedding", "ai.generate_embedding")
register("ai.summarize", "ai.generate_summary")
register("email.send", "email.send_email")
register("email.batch", "email.send_batch")
register("notification.push", "notification.push_notification")
register("notification.webhook", "notification.send_webhook")
register("publishing.cms", "publishing.publish_to_cms")
register("publishing.schedule", "publishing.schedule_publish")
register("analytics.process", "analytics.process_data")
register("analytics.report", "analytics.generate_report")
register("backup.database", "backup.backup_database")
register("backup.files", "backup.backup_files")
register("cache.refresh", "cache.refresh_cache")
register("cache.warm", "cache.warm_cache")
