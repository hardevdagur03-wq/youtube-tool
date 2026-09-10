"""Export Tasks — Celery tasks for exporting pipeline outputs.

Supports single and batch exports in markdown, HTML, and PDF formats.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from background_processing.celery_app import get_celery_app
from database.db_service import DatabaseService

logger = logging.getLogger(__name__)

app = get_celery_app()
_db_service: DatabaseService | None = None


def _get_db() -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


# ---------------------------------------------------------------------------
# Single Export Tasks
# ---------------------------------------------------------------------------


@app.task(bind=True, name="export.export_project", max_retries=3, default_retry_delay=60)
def export_project(self, project_id: str, export_format: str = "markdown", **kwargs: Any) -> dict[str, Any]:
    """Export a project's draft in the specified format.

    Builds the export payload from existing pipeline artifacts and
    persists it via DatabaseService.
    """
    async def _run() -> dict[str, Any]:
        db = _get_db()
        draft = await db.get_draft(project_id)
        project = await db.get_project(project_id)
        if not draft:
            raise ValueError(f"No draft found for project {project_id}")

        content = draft.get("markdown_content", "")
        title = (project or {}).get("name", "untitled")

        export_data = {
            "export_format": export_format,
            "filename": f"{title}.{export_format}",
            "file_path": f"exports/{project_id}/{title}.{export_format}",
            "file_size_bytes": len(content.encode("utf-8")),
            "content": content,
            "title": title,
            **kwargs,
        }
        result = await db.save_export(project_id, export_data)
        await db.log_event(project_id, "export.completed", extra_data={"format": export_format})
        return result or export_data

    loop = _get_or_create_loop()
    start = time.time()
    try:
        result = loop.run_until_complete(_run())
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info("Export completed for %s (%s) in %dms", project_id, export_format, elapsed_ms)
        return result
    except Exception:
        raise


@app.task(bind=True, name="export.export_project_markdown", max_retries=3, default_retry_delay=60)
def export_project_markdown(self, project_id: str, **kwargs: Any) -> dict[str, Any]:
    """Export project as Markdown."""
    return export_project.delay(project_id, "markdown", **kwargs)


@app.task(bind=True, name="export.export_project_html", max_retries=3, default_retry_delay=60)
def export_project_html(self, project_id: str, **kwargs: Any) -> dict[str, Any]:
    """Export project as HTML."""
    return export_project.delay(project_id, "html", **kwargs)


@app.task(bind=True, name="export.export_project_pdf", max_retries=3, default_retry_delay=60)
def export_project_pdf(self, project_id: str, **kwargs: Any) -> dict[str, Any]:
    """Export project as PDF."""
    return export_project.delay(project_id, "pdf", **kwargs)


# ---------------------------------------------------------------------------
# Batch Export
# ---------------------------------------------------------------------------


@app.task(bind=True, name="export.batch_export", max_retries=2, default_retry_delay=120)
def batch_export(self, project_ids: list[str], export_format: str = "markdown", **kwargs: Any) -> list[dict[str, Any]]:
    """Export multiple projects in batch."""
    async def _run() -> list[dict[str, Any]]:
        db = _get_db()
        results = []
        for pid in project_ids:
            try:
                draft = await db.get_draft(pid)
                project = await db.get_project(pid) or {}
                content = (draft or {}).get("markdown_content", "")
                title = project.get("name", "untitled")
                export_data = {
                    "export_format": export_format,
                    "filename": f"{title}.{export_format}",
                    "file_path": f"exports/{pid}/{title}.{export_format}",
                    "file_size_bytes": len(content.encode("utf-8")),
                    "content": content,
                    "title": title,
                }
                result = await db.save_export(pid, export_data)
                results.append({"project_id": pid, "status": "ok", "data": result or export_data})
            except Exception as exc:
                logger.warning("Batch export failed for %s: %s", pid, exc)
                results.append({"project_id": pid, "status": "error", "error": str(exc)})
        return results

    loop = _get_or_create_loop()
    try:
        return loop.run_until_complete(_run())
    except Exception:
        raise
