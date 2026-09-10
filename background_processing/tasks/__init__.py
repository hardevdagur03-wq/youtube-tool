"""Background processing task definitions.

Each module exposes Celery task functions that call existing
DatabaseService methods for pipeline execution, export, and cleanup.
"""

from background_processing.tasks.pipeline_tasks import (
    process_video,
    generate_analysis,
    generate_knowledge_graph,
    generate_seo_analysis,
    generate_outline,
    generate_sections,
    generate_draft,
    generate_review,
    generate_optimization,
    generate_export,
    run_full_pipeline,
    run_pipeline_stage,
)
from background_processing.tasks.export_tasks import (
    export_project,
    export_project_markdown,
    export_project_html,
    export_project_pdf,
    batch_export,
)
from background_processing.tasks.cleanup_tasks import (
    cleanup_stale_jobs,
    cleanup_expired_results,
    system_health_check,
    backup_job_history,
    dlq_cleanup,
)

__all__ = [
    "process_video",
    "generate_analysis",
    "generate_knowledge_graph",
    "generate_seo_analysis",
    "generate_outline",
    "generate_sections",
    "generate_draft",
    "generate_review",
    "generate_optimization",
    "generate_export",
    "run_full_pipeline",
    "run_pipeline_stage",
    "export_project",
    "export_project_markdown",
    "export_project_html",
    "export_project_pdf",
    "batch_export",
    "cleanup_stale_jobs",
    "cleanup_expired_results",
    "system_health_check",
    "backup_job_history",
    "dlq_cleanup",
]
