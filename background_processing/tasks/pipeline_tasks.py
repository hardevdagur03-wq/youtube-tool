"""Pipeline Tasks — Celery task definitions for each pipeline stage.

Each task is a thin async wrapper that calls the corresponding
DatabaseService method within a job lifecycle managed by ProgressEmitter.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from background_processing.celery_app import get_celery_app
from background_processing.job_repository import JobRepository
from background_processing.progress_emitter import ProgressEmitter
from background_processing.retry_manager import RetryManager
from database.db_service import DatabaseService
from transcript_reliability import TranscriptManager
from transcript_reliability.providers import get_default_providers

logger = logging.getLogger(__name__)

app = get_celery_app()
_db_service: DatabaseService | None = None


def _get_db() -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


# ---------------------------------------------------------------------------
# Shared task runner — wraps each pipeline stage with job lifecycle
# ---------------------------------------------------------------------------


async def _run_pipeline_stage(
    stage_name: str,
    project_id: str,
    job_id: str,
    stage_func,
    progress_steps: list[tuple[float, str]] | None = None,
) -> dict[str, Any]:
    """Execute a pipeline stage with progress tracking and error handling.

    Args:
        stage_name: Human-readable stage name for logging.
        project_id: Target project UUID.
        job_id: Background job UUID (for progress updates).
        stage_func: Async callable that performs the actual work.
        progress_steps: Optional list of (pct, message) milestones.

    Returns:
        The stage result data.
    """
    db = _get_db()
    from database.db_session import db_manager
    async with db_manager.session_factory() as session:
        repo = JobRepository(session)
        emitter = ProgressEmitter(repo)

        await emitter.on_started(job_id, project_id)
        start = time.time()

        try:
            if progress_steps:
                total = len(progress_steps)
                for idx, (pct, msg) in enumerate(progress_steps):
                    logger.info("[%s] %s (%.0f%%)", stage_name, msg, pct)
                    result = await stage_func(idx, total)
                    await emitter.on_progress(job_id, project_id, pct, msg, stage=stage_name)
                    await emitter.on_stage_completed(job_id, project_id, stage_name, result)
            else:
                result = await stage_func(0, 1)
                await emitter.on_progress(job_id, project_id, 100.0, f"{stage_name} complete", stage=stage_name)

            elapsed_ms = int((time.time() - start) * 1000)
            await emitter.on_completed(job_id, project_id, elapsed_ms, result)
            logger.info("[%s] completed in %dms", stage_name, elapsed_ms)
            return result

        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error("[%s] failed after %dms: %s", stage_name, elapsed_ms, exc)
            await emitter.on_failed(job_id, project_id, str(exc), recoverable=True)
            raise


# ---------------------------------------------------------------------------
# Individual pipeline stage tasks
# ---------------------------------------------------------------------------


@app.task(bind=True, name="pipeline.process_video", max_retries=3, default_retry_delay=60)
def process_video(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Fetch and store video metadata."""
    async def _run() -> dict[str, Any]:
        db = _get_db()
        url = kwargs.get("url", "")
        video_id = kwargs.get("video_id", "")
        data = {"url": url, "video_id": video_id, **kwargs}
        result = await db.save_video(project_id, data)
        await db.stage_completed(project_id, "videos")
        return result or data

    loop = _get_or_create_loop()
    return loop.run_until_complete(_run_pipeline_stage(
        "process_video", project_id, job_id,
        lambda i, t: asyncio.ensure_future(_run()),
    ))


@app.task(bind=True, name="pipeline.generate_transcript", max_retries=3, default_retry_delay=60)
def generate_transcript(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Fetch and store transcript using TranscriptManager with automatic failover."""
    _transcript_manager: TranscriptManager | None = None

    def _get_manager() -> TranscriptManager:
        nonlocal _transcript_manager
        if _transcript_manager is None:
            _transcript_manager = TranscriptManager()
            for provider in get_default_providers():
                _transcript_manager.register_provider(provider)
        return _transcript_manager

    async def _run() -> dict[str, Any]:
        db = _get_db()
        video_id = kwargs.get("video_id", "")
        if not video_id:
            return {"success": False, "error": "video_id is required"}

        manager = _get_manager()
        result = manager.get_transcript(video_id=video_id)

        if not result.success:
            logger.warning(
                "generate_transcript: all providers failed for %s: %s",
                video_id, result.error,
            )
            transcript_data = {
                "plain_text": "",
                "language": "en",
                "word_count": 0,
                "success": False,
                "error": result.error,
            }
        else:
            transcript_data = {
                "plain_text": result.plain_text,
                "language": result.language,
                "word_count": result.word_count,
                "source": result.source.value if hasattr(result.source, 'value') else str(result.source),
                "duration_seconds": result.duration_seconds,
                "success": True,
            }

        saved = await db.save_transcript(project_id, transcript_data)
        await db.stage_completed(project_id, "transcripts")
        return saved or transcript_data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_analysis", max_retries=3, default_retry_delay=60)
def generate_analysis(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        transcript = await db.get_transcript(project_id) or {}
        analysis = {"summary": kwargs.get("summary", ""), "topics": kwargs.get("topics", []),
                     "key_points": kwargs.get("key_points", []), "sentiment": kwargs.get("sentiment", ""),
                     "readability_score": kwargs.get("readability_score", 0), **kwargs}
        result = await db.save_analysis(project_id, analysis)
        await db.stage_completed(project_id, "analyses")
        return result or analysis

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_knowledge_graph", max_retries=3, default_retry_delay=60)
def generate_knowledge_graph(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"entities": kwargs.get("entities", []), "relationships": kwargs.get("relationships", []),
                "quality_score": kwargs.get("quality_score", 0), "summary": kwargs.get("summary", ""), **kwargs}
        result = await db.save_knowledge_graph(project_id, data)
        await db.stage_completed(project_id, "knowledge_graphs")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_seo_analysis", max_retries=3, default_retry_delay=60)
def generate_seo_analysis(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"seo_score": kwargs.get("seo_score", 0), "primary_keyword": kwargs.get("primary_keyword", ""),
                "meta_description": kwargs.get("meta_description", ""),
                "search_intent": kwargs.get("search_intent", ""), **kwargs}
        result = await db.save_seo(project_id, data)
        await db.stage_completed(project_id, "seo")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_outline", max_retries=3, default_retry_delay=60)
def generate_outline(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"title": kwargs.get("title", {}), "sections": kwargs.get("sections", []), **kwargs}
        result = await db.save_outline(project_id, data)
        await db.stage_completed(project_id, "outlines")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_sections", max_retries=3, default_retry_delay=60)
def generate_sections(self, project_id: str, job_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    async def _run() -> list[dict[str, Any]]:
        db = _get_db()
        sections = kwargs.get("sections", [])
        result = await db.save_sections(project_id, sections)
        await db.stage_completed(project_id, "sections")
        return result

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_draft", max_retries=3, default_retry_delay=60)
def generate_draft(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"markdown_content": kwargs.get("markdown_content", ""),
                "html_content": kwargs.get("html_content", ""),
                "word_count": kwargs.get("word_count", 0),
                "reading_time_minutes": kwargs.get("reading_time_minutes", 0),
                "section_count": kwargs.get("section_count", 0),
                "toc": kwargs.get("toc", []), **kwargs}
        result = await db.save_draft(project_id, data)
        await db.stage_completed(project_id, "drafts")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_review", max_retries=3, default_retry_delay=60)
def generate_review(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"overall_score": kwargs.get("overall_score", 0),
                "publication_status": kwargs.get("publication_status", ""),
                "issues": kwargs.get("issues", []),
                "summary": kwargs.get("summary", ""),
                "recommendations": kwargs.get("recommendations", []), **kwargs}
        result = await db.save_review(project_id, data)
        await db.stage_completed(project_id, "reviews")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_optimization", max_retries=3, default_retry_delay=60)
def generate_optimization(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"optimization_round": kwargs.get("optimization_round", 1),
                "pre_optimization_scores": kwargs.get("pre_optimization_scores", {}),
                "post_optimization_scores": kwargs.get("post_optimization_scores", {}),
                "changes_applied": kwargs.get("changes_applied", []),
                "summary": kwargs.get("summary", ""), **kwargs}
        result = await db.save_optimization(project_id, data)
        await db.stage_completed(project_id, "optimizations")
        return result or data

    return _sync_run(_run, self, project_id, job_id)


@app.task(bind=True, name="pipeline.generate_export", max_retries=3, default_retry_delay=60)
def generate_export(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        db = _get_db()
        data = {"export_format": kwargs.get("export_format", "markdown"),
                "file_path": kwargs.get("file_path", ""),
                "file_size_bytes": kwargs.get("file_size_bytes", 0),
                "filename": kwargs.get("filename", ""), **kwargs}
        result = await db.save_export(project_id, data)
        await db.stage_completed(project_id, "exports")
        await db.complete_project(project_id)
        return result or data

    return _sync_run(_run, self, project_id, job_id)


# ---------------------------------------------------------------------------
# Composite tasks
# ---------------------------------------------------------------------------


@app.task(bind=True, name="pipeline.run_full_pipeline", max_retries=1, default_retry_delay=300)
def run_full_pipeline(self, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Orchestrate the full pipeline by chaining individual stage tasks.

    Each stage is submitted as a separate Celery task with dependency
    tracking for proper sequencing.
    """
    from celery import chain, group
    from background_processing.models import STAGE_ORDER

    stages = {
        "pipeline.metadata": process_video.s(project_id, job_id, **kwargs),
        "pipeline.transcript": generate_transcript.s(project_id, job_id, **kwargs),
        "pipeline.analysis": generate_analysis.s(project_id, job_id, **kwargs),
        "pipeline.knowledge_graph": generate_knowledge_graph.s(project_id, job_id, **kwargs),
        "pipeline.seo": generate_seo_analysis.s(project_id, job_id, **kwargs),
        "pipeline.seo_intelligence": generate_seo_analysis.s(project_id, job_id, **kwargs),
        "pipeline.outline": generate_outline.s(project_id, job_id, **kwargs),
        "pipeline.sections": generate_sections.s(project_id, job_id, **kwargs),
        "pipeline.merge": generate_draft.s(project_id, job_id, **kwargs),
        "pipeline.review": generate_review.s(project_id, job_id, **kwargs),
        "pipeline.optimization": generate_optimization.s(project_id, job_id, **kwargs),
        "pipeline.export": generate_export.s(project_id, job_id, **kwargs),
    }

    ordered_stages = [stages[s] for s in STAGE_ORDER if s in stages]
    if not ordered_stages:
        return {"project_id": project_id, "status": "no_stages"}

    workflow = chain(*ordered_stages)
    result = workflow.delay()
    return {"project_id": project_id, "chain_id": result.id, "stage_count": len(ordered_stages)}


@app.task(bind=True, name="pipeline.run_pipeline_stage", max_retries=3, default_retry_delay=60)
def run_pipeline_stage(self, stage: str, project_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
    """Run a single named pipeline stage by dispatching to the appropriate task."""
    stage_map = {
        "videos": process_video,
        "transcripts": generate_transcript,
        "analyses": generate_analysis,
        "knowledge_graphs": generate_knowledge_graph,
        "seo": generate_seo_analysis,
        "seo_intelligence": generate_seo_analysis,
        "outlines": generate_outline,
        "sections": generate_sections,
        "drafts": generate_draft,
        "reviews": generate_review,
        "optimizations": generate_optimization,
        "exports": generate_export,
    }
    task_func = stage_map.get(stage)
    if task_func is None:
        raise ValueError(f"Unknown pipeline stage: {stage}")
    return task_func.delay(project_id, job_id, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _sync_run(coro_func, self, project_id: str, job_id: str) -> Any:
    """Execute an async coroutine within a synchronous Celery task."""
    loop = _get_or_create_loop()
    try:
        return loop.run_until_complete(_run_pipeline_stage(
            self.name.split(".")[-1] if self.name else "unknown",
            project_id, job_id,
            lambda i, t: asyncio.ensure_future(coro_func()),
        ))
    except Exception:
        raise
