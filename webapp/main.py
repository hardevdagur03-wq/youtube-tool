"""
YouTube CSV Export â€” FastAPI Application (v3)

Architecture
============
- Exports run as background threads managed by JobManager.
- POST /api/export returns immediately with a job_id.
- Frontend polls GET /api/export/{job_id}/progress for real-time updates.
- Supports cancellation via POST /api/export/{job_id}/cancel.
- Redis/in-memory caching for channel lookups and playlist IDs.
- Streaming CSV writer with constant memory usage.
- Structured JSON logging with correlation IDs.
- Metrics collection for monitoring.

Endpoints
=========
GET    /api/health                          Health check
POST   /api/export                          Start export (returns job_id)
GET    /api/export/{job_id}/progress        Poll export progress
GET    /api/export/{job_id}/result          Get export result
GET    /api/export/{job_id}/download        Download CSV
POST   /api/export/{job_id}/cancel          Cancel export
DELETE /api/export/{job_id}                 Delete export and cleanup
GET    /api/export/jobs/active              List active jobs
GET    /api/export/jobs/history             List completed jobs
GET    /api/metrics                         System metrics
GET    /api/cache/stats                     Cache statistics
GET    /api/quota                           YouTube API quota status
GET    /api/validate-url                    Validate YouTube URL
GET    /api/video-metadata/{video_id}       Get single video metadata
GET    /api/transcript/{video_id}           Get transcript
(plus all existing transcript, analysis, blog, SEO, export endpoints)
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import is_youtube_api_key_valid, settings
from export_engine.models import ExportRequest
from export_engine.async_pipeline import AsyncExportPipeline
from infrastructure.logging import setup_logging
from infrastructure.monitoring import metrics
from infrastructure.rate_limiter import quota_tracker, rate_limiter
from infrastructure.validation import RequestValidationMiddleware
from models.api_response import error_response, success_response
from services.english_converter import english_converter

from database.db_session import db_lifespan, get_db_health
from observability.config import ObservabilityConfig
from observability.instrumentation import instrument_fastapi
from observability.telemetry import TelemetryOrchestrator

setup_logging()

CURRENT_DIR = Path(__file__).resolve().parent
RUNS_DIR = CURRENT_DIR / "runs"
TEMPLATES_DIR = CURRENT_DIR / "templates"
STATIC_DIR = CURRENT_DIR / "static"
FRONTEND_DIST = CURRENT_DIR.parent / "frontend" / "dist"

logger = logging.getLogger("webapp")

_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")

_export_path = Path(__file__).resolve().parent.parent
import sys as _sys
if str(_export_path) not in _sys.path:
    _sys.path.insert(0, str(_export_path))


def _safe_run_id(raw: str) -> str | None:
    if _RUN_ID_PATTERN.match(raw):
        return raw
    return None


# ---------------------------------------------------------------------------
# Global services
# ---------------------------------------------------------------------------

_async_pipeline = AsyncExportPipeline()
_running_tasks: dict[str, asyncio.Task] = {}
_running_tasks_lock = asyncio.Lock()


async def _run_async_pipeline(job_id: str, request: ExportRequest) -> None:
    try:
        await _async_pipeline.run(job_id, request)
    except asyncio.CancelledError:
        logger.info("Job %s was cancelled", job_id)
        await _async_pipeline.cancel_job(job_id)
    except Exception:
        logger.exception("Job %s failed with unexpected error", job_id)
    finally:
        async with _running_tasks_lock:
            _running_tasks.pop(job_id, None)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------



def _to_thread(func, *args, **kwargs):
    """Run a sync function in a thread pool to avoid blocking the event loop."""
    import asyncio
    loop = asyncio.get_running_loop()
    import functools
    return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Async webapp v3 starting")
    logger.info("Open http://localhost:8000 in your browser")

    # Initialize observability (structured logging, tracing, metrics, Sentry)
    _telemetry.initialize()

    # Initialize database connection pool and create tables
    async with db_lifespan():
        # Clean stale run dirs
        if RUNS_DIR.exists():
            stale_cutoff = time.time() - 3600
            for entry in RUNS_DIR.iterdir():
                if entry.is_dir() and _RUN_ID_PATTERN.match(entry.name):
                    result_file = entry / "result.json"
                    if not result_file.exists() and entry.stat().st_mtime < stale_cutoff:
                        shutil.rmtree(str(entry), ignore_errors=True)
        # Phase 23: Scan for recoverable workflows on startup
        _recovery_scan_result = _dup_engine._recovery.scan_and_recover(
            _dup_engine._executions
        )
        if _recovery_scan_result:
            logger.info(
                "Phase 23: Recovered %d workflow(s) on startup",
                len(_recovery_scan_result),
            )

        yield
        # Cleanup (inside db_lifespan context â€” DB still available)
        async with _running_tasks_lock:
            for task in _running_tasks.values():
                task.cancel()
            _running_tasks.clear()
        await _async_pipeline.close()

    # Shutdown observability (after DB connections are closed)
    _telemetry.shutdown()


app = FastAPI(title="YouTube Export Tool v3 (Async)", lifespan=lifespan)

# Observability: create orchestrator at module level; initialize() called in lifespan
_telemetry = TelemetryOrchestrator(ObservabilityConfig.from_env())

# Network/transport middleware first (innermost wrapping)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origins] if settings.cors_origins != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestValidationMiddleware)

# Instrument FastAPI last (outermost wrapping â€” captures all requests)
instrument_fastapi(app, _telemetry.metrics, _telemetry.tracing)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
_frontend_assets = FRONTEND_DIST / "assets"
_frontend_assets.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(_frontend_assets)), name="frontend-assets")


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = time.time()
    response = await call_next(request)
    elapsed = round(time.time() - start, 3)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Elapsed-Ms"] = str(int(elapsed * 1000))
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = uuid.uuid4().hex[:8]
    logger.exception("[%s] Unhandled exception on %s %s: %s", rid, request.method, request.url.path, exc)
    import traceback
    content: dict = {
        "success": False,
        "error": str(exc) or "An unexpected error occurred.",
        "trace_id": rid,
        "exception_type": type(exc).__name__,
    }
    return JSONResponse(
        status_code=500,
        content=content,
    )


def _spa_index() -> FileResponse | HTMLResponse:
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return HTMLResponse(
        "<h1>Frontend not built</h1><p>Run <code>npm --prefix frontend run build</code> to build frontend production assets.</p>",
        status_code=503,
    )


@app.get("/")
@app.get("/metadata")
@app.get("/transcript")
@app.get("/analysis")
@app.get("/blog")
@app.get("/blog/{path:path}")
async def spa_routes(path: str = ""):
    return _spa_index()


# ---------------------------------------------------------------------------
# Export API (Async)
# ---------------------------------------------------------------------------


@app.post("/api/export")
async def api_export(request: Request) -> dict:
    rid = uuid.uuid4().hex[:8]
    body = await request.json()

    channel_input = body.get("channel", "").strip()
    limit = int(body.get("limit", 0))

    if not channel_input:
        return JSONResponse(status_code=400, content={"success": False, "error": "Channel identifier cannot be empty.", "trace_id": rid})

    client_host = getattr(request.client, "host", None) or "unknown"
    if not rate_limiter.allow(f"export:{client_host}"):
        return JSONResponse(status_code=429, content={"success": False, "error": "Too many requests.", "trace_id": rid})

    key_ok, key_error = is_youtube_api_key_valid()
    if not key_ok:
        return JSONResponse(status_code=503, content={"success": False, "error": key_error, "trace_id": rid})

    if not quota_tracker.record_call(1):
        return JSONResponse(status_code=429, content={"success": False, "error": "Daily API quota reached.", "trace_id": rid})

    job_id = uuid.uuid4().hex[:12]
    export_req = ExportRequest(channel_input=channel_input, limit=limit)

    # Start async background task
    run_dir = RUNS_DIR / job_id
    run_dir.mkdir(parents=True, exist_ok=True)

    task = asyncio.create_task(_run_async_pipeline(job_id, export_req))
    async with _running_tasks_lock:
        _running_tasks[job_id] = task

    logger.info("[%s] Async export started: channel=%s, limit=%d, job_id=%s", rid, channel_input, limit, job_id)

    return {"success": True, "job_id": job_id, "trace_id": rid, "status": "pending"}


@app.get("/api/export/{job_id}/progress")
async def api_export_progress(job_id: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    if not _safe_run_id(job_id):
        return {"success": False, "error": "Invalid job ID", "trace_id": rid}

    progress = await _async_pipeline.get_progress(job_id)
    if progress is None:
        # Fall back to disk
        progress_path = RUNS_DIR / job_id / "progress.json"
        if progress_path.exists():
            try:
                progress = json.loads(progress_path.read_text())
            except Exception:
                pass
    if progress is None:
        return {"success": False, "error": "Job not found", "trace_id": rid}

    return {"success": True, "job_id": job_id, "trace_id": rid, **progress}


@app.get("/api/export/{job_id}/result")
async def api_export_result(job_id: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    if not _safe_run_id(job_id):
        return {"success": False, "error": "Invalid job ID", "trace_id": rid}

    result = await _async_pipeline.get_result(job_id)
    if result is None:
        result_path = RUNS_DIR / job_id / "result.json"
        if result_path.exists():
            try:
                result = json.loads(result_path.read_text())
            except Exception:
                pass
    if result is None:
        return {"success": False, "error": "Export not ready", "trace_id": rid}

    return {"success": True, "job_id": job_id, "result": result, "trace_id": rid}


@app.get("/api/export/{job_id}/download")
async def api_export_download(job_id: str):
    rid = uuid.uuid4().hex[:8]
    if not _safe_run_id(job_id):
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid job ID", "trace_id": rid})

    csv_path = RUNS_DIR / job_id / "videos.csv"
    if not csv_path.exists():
        return JSONResponse(status_code=404, content={"success": False, "error": "CSV file not found", "trace_id": rid})
    if csv_path.stat().st_size == 0:
        return JSONResponse(status_code=422, content={"success": False, "error": "CSV file is empty", "trace_id": rid})

    return FileResponse(str(csv_path), media_type="text/csv", filename="videos.csv")


@app.post("/api/export/{job_id}/cancel")
async def api_export_cancel(job_id: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    if not _safe_run_id(job_id):
        return {"success": False, "error": "Invalid job ID", "trace_id": rid}

    async with _running_tasks_lock:
        task = _running_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            _running_tasks.pop(job_id, None)
            logger.info("[%s] Job %s cancelled", rid, job_id)
            return {"success": True, "job_id": job_id, "status": "cancelled", "trace_id": rid}
    return {"success": False, "error": "Job not running or already completed", "trace_id": rid}


@app.delete("/api/export/{job_id}")
async def api_export_delete(job_id: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    if not _safe_run_id(job_id):
        return {"success": False, "error": "Invalid job ID", "trace_id": rid}
    run_dir = RUNS_DIR / job_id
    if run_dir.exists():
        shutil.rmtree(str(run_dir), ignore_errors=True)
    return {"success": True, "job_id": job_id, "trace_id": rid}


@app.get("/api/export/jobs/active")
async def api_export_active() -> dict:
    async with _running_tasks_lock:
        jobs = [
            {"job_id": jid, "status": "running"}
            for jid in _running_tasks
            if not _running_tasks[jid].done()
        ]
    return {"success": True, "count": len(jobs), "jobs": jobs}


# ---------------------------------------------------------------------------
# Legacy endpoints (delegated to async)
# ---------------------------------------------------------------------------


@app.post("/run")
async def legacy_run(channel: str = Form(default=""), limit: int = Form(default=0)):
    import json
    from fastapi import Request as FastAPIRequest
    scope = {
        "type": "http", "method": "POST", "path": "/api/export",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"", "client": ("127.0.0.1", 0), "server": ("127.0.0.1", 8000),
        "scheme": "http", "root_path": "",
    }
    fake_req = FastAPIRequest(scope)
    fake_req._body = json.dumps({"channel": channel.strip(), "limit": limit}).encode()
    return await api_export(fake_req)


@app.get("/api/progress/{run_id}")
async def api_progress(run_id: str) -> dict:
    return await api_export_progress(run_id)


@app.get("/api/result/{run_id}")
async def api_result(run_id: str) -> dict:
    return await api_export_result(run_id)


@app.get("/api/download/{run_id}")
async def api_download(run_id: str):
    return await api_export_download(run_id)


# ---------------------------------------------------------------------------
# Monitoring & Metrics
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def api_health():
    key_ok, key_error = is_youtube_api_key_valid()
    db_health = await get_db_health()
    redis_healthy = False
    try:
        import redis as _redis
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        redis_healthy = True
    except Exception:
        pass
    import shutil
    base_path = Path(__file__).resolve().parent.parent
    usage = shutil.disk_usage(base_path)
    disk_healthy = usage.free / usage.total > 0.1
    ai_providers = {'openai': bool(settings.openai_api_key) if hasattr(settings, 'openai_api_key') else False, 'gemini': bool(settings.gemini_api_key) if hasattr(settings, 'gemini_api_key') else False, 'anthropic': bool(settings.anthropic_api_key) if hasattr(settings, 'anthropic_api_key') else False}
    any_ai = any(ai_providers.values())
    status = "ok" if key_ok else "degraded"
    if not key_ok:
        logger.warning("Health check: degraded state - %s", key_error)
    async with _running_tasks_lock:
        active_count = len([t for t in _running_tasks.values() if not t.done()])
    return success_response(
        data={
            "status": status,
            "version": "3.0",
            "database": db_health,
            "redis": {"healthy": redis_healthy},
            "storage": {"healthy": disk_healthy, "free_percent": round(usage.free / usage.total * 100, 1)},
            "ai_providers": ai_providers,
            "youtube_api_key_configured": key_ok,
            "youtube_api_key_error": key_error if not key_ok else None,
            "active_exports": active_count,
        },
        message="Service health check",
    )
@app.get("/api/metrics")
async def api_metrics():
    return metrics.get_metrics()


@app.get("/api/quota")
async def api_quota():
    return {"success": True, "quota": quota_tracker.usage()}


@app.get("/api/cache/stats")
async def api_cache_stats():
    from infrastructure.cache import cache_service
    return {"success": True, "cache": cache_service.stats}


@app.get("/api/active-exports")
async def api_active_exports():
    return await api_export_active()


# ---------------------------------------------------------------------------
# Dashboard (legacy)
# ---------------------------------------------------------------------------


@app.get("/dashboard/{run_id}")
async def dashboard(request: Request, run_id: str):
    if not _safe_run_id(run_id):
        return HTMLResponse("Invalid run ID", status_code=400)
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return HTMLResponse("Run not found", status_code=404)
    from jinja2 import Environment, FileSystemLoader
    jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    return HTMLResponse(jinja_env.get_template("dashboard.html").render(request=request, run_id=run_id))


# ---------------------------------------------------------------------------
# All remaining existing routes from v2 (unchanged)
# ---------------------------------------------------------------------------

import contextvars
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_url_parser = None
_metadata_service = None
_transcript_service = None
_content_analysis_service = None
_blog_service = None
_seo_service = None
_export_engine = None
_transcript_processor = None
_review_engine = None
_channel_service = None
_video_service = None


def _get_request_id() -> str:
    rid = _request_id_var.get()
    if not rid:
        rid = uuid.uuid4().hex[:8]
        _request_id_var.set(rid)
    return rid


def _get_url_parser():
    global _url_parser
    if _url_parser is None:
        from services.youtube_url_parser import YouTubeURLParser
        _url_parser = YouTubeURLParser()
    return _url_parser


def _get_metadata_service():
    global _metadata_service
    if _metadata_service is None:
        from services.youtube_metadata_service import YouTubeMetadataService
        _metadata_service = YouTubeMetadataService()
    return _metadata_service


def _get_transcript_service():
    global _transcript_service
    if _transcript_service is None:
        from services.transcript_service import TranscriptService
        _transcript_service = TranscriptService()
    return _transcript_service


def _get_transcript_processor():
    global _transcript_processor
    if _transcript_processor is None:
        from services.transcript_processor import TranscriptProcessor
        _transcript_processor = TranscriptProcessor()
    return _transcript_processor


def _get_content_analysis_service():
    global _content_analysis_service
    if _content_analysis_service is None:
        from services.content_analysis_service import ContentAnalysisService
        _content_analysis_service = ContentAnalysisService()
    return _content_analysis_service


def _get_blog_service():
    global _blog_service
    if _blog_service is None:
        from modules.blog.blog_service import BlogGenerationService
        _blog_service = BlogGenerationService()
    return _blog_service


def _get_seo_service():
    global _seo_service
    if _seo_service is None:
        from modules.seo.seo_service import SEOService
        _seo_service = SEOService()
    return _seo_service


def _get_export_engine():
    global _export_engine
    if _export_engine is None:
        from export.engine import ExportEngine
        _export_engine = ExportEngine()
    return _export_engine


def _get_review_engine():
    global _review_engine
    if _review_engine is None:
        from review.engine import ReviewEngine
        _review_engine = ReviewEngine()
    return _review_engine


def _get_channel_service():
    global _channel_service
    if _channel_service is None:
        from api.channel_service import ChannelService
        _channel_service = ChannelService()
    return _channel_service


def _get_video_service():
    global _video_service
    if _video_service is None:
        from api.video_service import VideoService
        _video_service = VideoService()
    return _video_service


# --- Transcript endpoints ---

@app.get("/api/transcript/{video_id}")
async def api_transcript(video_id: str, language: str | None = None, force_refresh: bool = False, allow_whisper: bool = True) -> dict:
    rid = uuid.uuid4().hex[:8]
    logger.info("[%s] Transcript request: video_id=%s", rid, video_id)
    try:
        service = _get_transcript_service()
        result = await _to_thread(service.get_transcript, video_id=video_id, language=language, force_refresh=force_refresh, allow_whisper=allow_whisper)
        return result.model_dump()
    except Exception as exc:
        logger.exception("[%s] Transcript fetch failed for %s", rid, video_id)
        raise


@app.get("/api/transcript/{video_id}/all")
async def api_transcript_all(video_id: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    service = _get_transcript_service()
    return await _to_thread(service.get_all_transcripts, video_id)


@app.get("/api/transcript/{video_id}/status")
async def api_transcript_status(video_id: str) -> dict:
    service = _get_transcript_service()
    return await _to_thread(service.get_transcript_status, video_id)


@app.get("/api/transcript/{video_id}/translate/{target_language}")
async def api_translate_transcript(video_id: str, target_language: str) -> dict:
    rid = uuid.uuid4().hex[:8]
    try:
        service = _get_transcript_service()
        result = await _to_thread(service.translate_transcript, video_id=video_id, target_language=target_language)
        return result.model_dump()
    except Exception as exc:
        logger.exception("[%s] Translation failed", rid)
        raise


@app.get("/api/transcript/{video_id}/list-all")
async def api_transcript_list_all(video_id: str) -> dict:
    try:
        service = _get_transcript_service()
        return await _to_thread(service.get_transcript_status, video_id)
    except Exception as exc:
        return {"success": False, "video_id": video_id, "error": str(exc)}


@app.post("/api/transcript/{video_id}/process")
async def api_process_transcript(video_id: str, remove_fillers: bool = False) -> dict:
    import json
    transcript_service = _get_transcript_service()
    transcript = await _to_thread(transcript_service.get_transcript, video_id)
    if not transcript.success:
        raise HTTPException(status_code=404, detail={"success": False, "error": transcript.error or "No transcript available."})
    processor = _get_transcript_processor()
    result = await _to_thread(processor.process, segments=transcript.segments, video_id=video_id, remove_fillers=remove_fillers)
    return json.loads(result.model_dump_json())


@app.post("/api/process-transcript")
async def api_process_transcript_direct(request: Request) -> dict:
    import json
    body = await request.json()
    segments = body.get("segments", [])
    vid = body.get("video_id", "")
    remove = body.get("remove_fillers", False)
    if not segments:
        raise HTTPException(status_code=400, detail={"success": False, "error": "No segments provided."})
    processor = _get_transcript_processor()
    result = await _to_thread(processor.process, segments=segments, video_id=vid, remove_fillers=remove)
    return json.loads(result.model_dump_json())


# ---------------------------------------------------------------------------
# ISO 8601 Duration Helpers
# ---------------------------------------------------------------------------


def _parse_iso_duration(iso: str) -> int:
    """Parse ISO 8601 duration string (e.g. PT15M51S, PT1H2M3S) to total seconds."""
    import re
    match = re.match(r'^PT?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', iso)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _format_duration(total_seconds: int) -> str:
    """Format seconds to readable duration (e.g. 845 -> '14:05', 3720 -> '1:02:00')."""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


# --- Simplified Transcript v2 endpoint (Workflow 2 — returns ONLY title, duration, transcript) ---


@app.get("/api/transcriptv2/{video_id}")
async def api_transcript_v2(video_id: str):
    """Return ONLY title, duration, and transcript text for a video.

    Minimal endpoint for the simplified Transcript workflow. Fetches only
    the bare minimum metadata (title, duration) alongside the transcript.
    No statistics, no segments, no pipeline info, no source metadata.
    """
    rid = uuid.uuid4().hex[:8]
    logger.info("[%s] Transcript v2 request: video_id=%s", rid, video_id)

    title = ""
    duration = "0:00"
    transcript_text = ""

    # Fetch minimal metadata (only title + duration needed)
    try:
        video_svc = _get_video_service()
        items = await _to_thread(video_svc.get_videos_batch, [video_id])
        if items:
            snippet = items[0].get("snippet", {})
            cd = items[0].get("contentDetails", {})
            title = snippet.get("title", "")
            channel_title = snippet.get("channelTitle", "")
            duration = _format_duration(_parse_iso_duration(cd.get("duration", "PT0S")))
    except Exception as exc:
        logger.warning("[%s] Minimal metadata fetch failed for %s: %s", rid, video_id, exc)

    # Fetch transcript
    transcript = None
    try:
        transcript_svc = _get_transcript_service()
        transcript = await _to_thread(
            transcript_svc.get_transcript,
            video_id,
            video_title=title,
            channel_title=channel_title if 'channel_title' in locals() else None,
        )
        if transcript.success:
            transcript_text = transcript.plain_text or transcript.paragraph_text or ""
    except Exception as exc:
        logger.warning("[%s] Transcript fetch failed for %s: %s", rid, video_id, exc)

    status = "success" if (transcript and transcript.success and transcript_text) else "failed"
    source = None
    method = None
    language = "en"
    raw_transcript_text = getattr(transcript, "raw_transcript", "") or transcript_text
    error_code = None
    error_message = None

    if transcript:
        source = getattr(transcript.source, "value", str(transcript.source)) if transcript.source else None
        method = getattr(transcript, "method", None)
        language = transcript.language or "English (India)"
        if language and language.lower() in ("hinglish", "en", "english", "en-in", "hi", "hindi", "english (india)"):
            language = "English (India)"
        if not transcript.success:
            error_code = getattr(transcript, "error_code", None) or "TRANSCRIPT_NOT_FOUND"
            error_message = transcript.error or "Failed to fetch transcript"

    if status == "failed":
        if not error_code:
            error_code = "TRANSCRIPT_NOT_FOUND"
            error_message = "No transcript could be extracted for this video."
        if error_code == "VIDEO_UNAVAILABLE" and not error_message:
            error_message = "This video is unavailable, private, or deleted."

    script = "Roman"

    logger.info("[%s] Returning v2 result for %s: title='%s', status='%s', method='%s', len=%d",
                rid, video_id, title, status, method, len(transcript_text))

    return {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "duration": duration,
        "language": language,
        "script": script,
        "status": status,
        "transcript": transcript_text,
        "raw_transcript": raw_transcript_text,
        "source": source,
        "method": method,
        "error_code": error_code,
        "error_message": error_message,
    }


# --- Channel Transcript endpoint ---


@app.get("/api/channel/{handle}/transcripts")
async def api_channel_transcripts(
    handle: str,
    limit: int = 100,
    concurrency: int = 5,
    allow_whisper: bool = True,
):
    """Fetch transcripts for a YouTube channel with duration filtering (3–30 min).

    Resolves the channel handle, discovers video IDs from the upload playlist,
    fetches video metadata for duration filtering, and fetches transcripts with
    caption-first retrieval and speech-to-text (Whisper) fallback.

    Returns channel info, statistics, and per-video results including metadata.
    Only processes videos with duration 3:00 <= duration < 30:00 (180s <= dur < 1800s).
    """
    rid = uuid.uuid4().hex[:8]
    clean = handle.lstrip("@")
    start_time = time.time()
    logger.info(
        "[%s] Channel transcript request: handle=%s, limit=%d, concurrency=%d, allow_whisper=%s",
        rid, clean, limit, concurrency, allow_whisper,
    )

    try:
        channel_svc = _get_channel_service()
        video_svc = _get_video_service()
        transcript_svc = _get_transcript_service()

        # Step 1: Resolve channel
        logger.info("[%s] Stage 1/5: Resolving channel handle: %s", rid, clean)
        channel_data = await _to_thread(channel_svc.resolve_handle, clean)
        channel_id = channel_data["id"]
        channel_title = channel_data["snippet"]["title"]
        logger.info("[%s] Channel resolved: id=%s, title='%s'", rid, channel_id, channel_title)

        # Step 2: Get upload playlist ID
        logger.info("[%s] Stage 2/5: Getting upload playlist for channel %s", rid, channel_id)
        playlist_id = await _to_thread(video_svc.get_uploads_playlist_id, channel_id)
        logger.info("[%s] Upload playlist: %s", rid, playlist_id)

        # Step 3: Paginate playlist for video IDs
        logger.info("[%s] Stage 3/5: Discovering videos from upload playlist", rid)
        all_video_ids: list[str] = []
        next_page: str | None = None
        pages_fetched = 0
        while len(all_video_ids) < limit:
            page = await _to_thread(
                video_svc.get_playlist_items, playlist_id, next_page,
            )
            video_ids = page.get("video_ids", [])
            for vid in video_ids:
                if vid and vid not in all_video_ids:
                    all_video_ids.append(vid)
                    if len(all_video_ids) >= limit:
                        break
            next_page = page.get("next_page_token")
            pages_fetched += 1
            logger.info(
                "[%s]  Playlist page %d: %d videos (total %d so far)",
                rid, pages_fetched, len(video_ids), len(all_video_ids),
            )
            if not next_page:
                break
        logger.info("[%s] Stage 3/5 complete: %d videos discovered", rid, len(all_video_ids))

        # Step 4: Fetch video metadata for duration filtering
        logger.info("[%s] Stage 4/5: Fetching video metadata (durations, titles)", rid)
        videos_metadata: dict[str, dict] = {}
        for i in range(0, len(all_video_ids), 50):
            batch = all_video_ids[i:i + 50]
            try:
                metadata_items = await _to_thread(video_svc.get_videos_batch, batch)
                for item in metadata_items:
                    vid = item.get("id")
                    if not vid:
                        continue
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})
                    duration_iso = content_details.get("duration", "PT0S")
                    duration_seconds = _parse_iso_duration(duration_iso)
                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail = None
                    for quality in ("medium", "high", "standard", "default"):
                        if quality in thumbnails:
                            thumbnail = thumbnails[quality].get("url")
                            break
                    live_status = snippet.get("liveBroadcastContent", "none")
                    videos_metadata[vid] = {
                        "title": snippet.get("title", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "duration_seconds": duration_seconds,
                        "duration_readable": _format_duration(duration_seconds),
                        "live_status": live_status,
                    }
            except Exception as exc:
                logger.warning("[%s] Failed to fetch metadata batch of %d videos: %s", rid, len(batch), exc)

        # Filter by duration (3:00 <= duration < 30:00) and exclude live streams using evaluate_duration
        from services.duration_filter import evaluate_duration
        eligible_videos: list[str] = []
        short_videos: list[str] = []
        long_videos: list[str] = []
        live_videos: list[str] = []

        for vid in all_video_ids:
            meta = videos_metadata.get(vid, {})
            duration = meta.get("duration_seconds", 0)
            live_status = meta.get("live_status", "none")

            filter_res = evaluate_duration(
                duration_seconds=duration,
                live_status=live_status,
                min_seconds=180,
                max_seconds=1800,
            )
            if filter_res.is_eligible:
                eligible_videos.append(vid)
            elif filter_res.skip_reason == "LIVE_STREAM":
                live_videos.append(vid)
            elif filter_res.skip_reason == "TOO_SHORT":
                short_videos.append(vid)
            elif filter_res.skip_reason == "TOO_LONG":
                long_videos.append(vid)
            else:
                short_videos.append(vid)

        logger.info(
            "[%s] Stage 4/5 complete: %d eligible (3–30 min), %d short, %d long, %d live",
            rid, len(eligible_videos), len(short_videos), len(long_videos), len(live_videos),
        )

        # Step 5: Fetch transcripts in parallel
        logger.info(
            "[%s] Stage 5/5: Fetching transcripts for %d eligible videos (concurrency=%d)",
            rid, len(eligible_videos), concurrency,
        )
        semaphore = asyncio.Semaphore(concurrency)

        async def _fetch_one(video_id: str, idx: int) -> dict:
            async with semaphore:
                meta = videos_metadata.get(video_id, {})
                title = meta.get("title", "")
                published_at = meta.get("published_at", "")
                dur_sec = meta.get("duration_seconds", 0)
                dur_str = meta.get("duration_readable", "0:00")
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # 1. Try caption first
                try:
                    res = await _to_thread(
                        transcript_svc.get_transcript, video_id, allow_whisper=False,
                    )
                    if res.success and (res.plain_text or res.paragraph_text):
                        return {
                            "index": idx,
                            "video_id": video_id,
                            "video_url": video_url,
                            "channel_id": channel_id,
                            "channel_title": channel_title,
                            "title": title,
                            "published_at": published_at,
                            "duration_seconds": dur_sec,
                            "duration": dur_str,
                            "language": res.language or "en",
                            "status": "success",
                            "transcript": res.plain_text or res.paragraph_text or "",
                            "raw_transcript": getattr(res, "raw_transcript", "") or (res.plain_text or res.paragraph_text or ""),
                            "source": "youtube",
                            "method": "caption",
                            "error_code": None,
                            "error_message": None,
                        }
                except Exception as exc:
                    logger.debug("[%s] Caption fetch exception for %s: %s", rid, video_id, exc)

                # 2. Try Whisper fallback if enabled
                if allow_whisper and settings.whisper_enabled:
                    try:
                        w_res = await _to_thread(
                            transcript_svc.get_transcript,
                            video_id,
                            allow_whisper=True,
                            video_title=title,
                            channel_title=channel_title,
                        )
                        if w_res.success and (w_res.plain_text or w_res.paragraph_text):
                            return {
                                "index": idx,
                                "video_id": video_id,
                                "video_url": video_url,
                                "channel_id": channel_id,
                                "channel_title": channel_title,
                                "title": title,
                                "published_at": published_at,
                                "duration_seconds": dur_sec,
                                "duration": dur_str,
                                "language": w_res.language or "English (India)",
                                "status": "success",
                                "transcript": w_res.plain_text or w_res.paragraph_text or "",
                                "raw_transcript": getattr(w_res, "raw_transcript", "") or (w_res.plain_text or w_res.paragraph_text or ""),
                                "source": "whisper",
                                "method": "speech_to_text",
                                "error_code": None,
                                "error_message": None,
                            }
                        else:
                            return {
                                "index": idx,
                                "video_id": video_id,
                                "video_url": video_url,
                                "channel_id": channel_id,
                                "channel_title": channel_title,
                                "title": title,
                                "published_at": published_at,
                                "duration_seconds": dur_sec,
                                "duration": dur_str,
                                "language": "en",
                                "status": "failed",
                                "transcript": "",
                                "source": None,
                                "method": None,
                                "error_code": w_res.error_code or "NO_CAPTIONS",
                                "error_message": w_res.error or "No captions available",
                            }
                    except Exception as exc:
                        logger.warning("[%s] Whisper fallback failed for %s: %s", rid, video_id, exc)
                        return {
                            "index": idx,
                            "video_id": video_id,
                            "video_url": video_url,
                            "channel_id": channel_id,
                            "channel_title": channel_title,
                            "title": title,
                            "published_at": published_at,
                            "duration_seconds": dur_sec,
                            "duration": dur_str,
                            "language": "en",
                            "status": "failed",
                            "transcript": "",
                            "source": None,
                            "method": None,
                            "error_code": "STT_FAILED",
                            "error_message": f"Speech-to-text failed: {exc}",
                        }

                # Captions unavailable and whisper disabled
                return {
                    "index": idx,
                    "video_id": video_id,
                    "video_url": video_url,
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                    "title": title,
                    "published_at": published_at,
                    "duration_seconds": dur_sec,
                    "duration": dur_str,
                    "language": "en",
                    "status": "failed",
                    "transcript": "",
                    "source": None,
                    "method": None,
                    "error_code": "NO_CAPTIONS",
                    "error_message": "No transcript/caption track is available for this video.",
                }

        tasks = [_fetch_one(vid, i) for i, vid in enumerate(eligible_videos)]
        raw_results = await asyncio.gather(*tasks)
        raw_results.sort(key=lambda r: r["index"])
        video_results = [{k: v for k, v in r.items() if k != "index"} for r in raw_results]

        successful_count = sum(1 for v in video_results if v.get("status") == "success")
        caption_count = sum(1 for v in video_results if v.get("method") == "caption")
        whisper_count = sum(1 for v in video_results if v.get("method") == "speech_to_text")
        failed_count = sum(1 for v in video_results if v.get("status") != "success")
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "[%s] Complete: %d/%d transcripts (%d captions, %d whisper, %d failed), %dms elapsed",
            rid, successful_count, len(eligible_videos), caption_count, whisper_count, failed_count, elapsed_ms,
        )

        return success_response(
            data={
                "channel_id": channel_id,
                "channel_title": channel_title,
                "total_discovered": len(all_video_ids),
                "eligible_count": len(eligible_videos),
                "skipped_count": len(short_videos) + len(long_videos) + len(live_videos),
                "successful_count": successful_count,
                "caption_count": caption_count,
                "whisper_count": whisper_count,
                "failed_count": failed_count,
                "videos": video_results,
            },
            message=(
                f"Fetched {successful_count} transcript(s) ({caption_count} captions, {whisper_count} STT) "
                f"for {len(eligible_videos)} eligible videos in {channel_title}"
            ),
        )
    except Exception as exc:
        logger.exception("[%s] Channel transcript failed for %s", rid, handle)
        return error_response(
            message=f"Failed to fetch channel transcripts: {exc}",
            status_code=500,
        )


# --- Transcript Background Job endpoints ---


class TranscriptJobCreateRequest(BaseModel):
    max_videos: int = 0
    force_refresh: bool = False
    caption_concurrency: int = 5
    whisper_concurrency: int = 1


@app.post("/api/channel/{handle}/transcript-job")
async def api_start_channel_transcript_job(
    handle: str,
    max_videos: int = 0,
    force_refresh: bool = False,
    req: TranscriptJobCreateRequest | None = None,
):
    """Launch asynchronous background job for channel transcripts."""
    from services.jobs.transcript_job_manager import transcript_job_manager
    try:
        eff_max = req.max_videos if req and req.max_videos > 0 else max_videos
        eff_refresh = req.force_refresh if req else force_refresh
        eff_caption_conc = req.caption_concurrency if req else 5
        eff_whisper_conc = req.whisper_concurrency if req else 1
        progress = await transcript_job_manager.start_channel_job(
            channel_handle=handle,
            max_videos=eff_max,
            force_refresh=eff_refresh,
            caption_concurrency=eff_caption_conc,
            whisper_concurrency=eff_whisper_conc,
        )
        return success_response(
            data=progress.model_dump(),
            message=f"Transcript job {progress.job_id} queued for {progress.channel_title or handle}",
        )
    except Exception as exc:
        logger.exception("Failed to start channel transcript job: %s", exc)
        return error_response(message=f"Failed to start job: {exc}", status_code=500)


@app.get("/api/transcript/jobs/{job_id}")
async def api_get_transcript_job_status(job_id: str):
    """Poll progress, counters, and video results for a background job."""
    from services.jobs.transcript_job_manager import transcript_job_manager
    job = transcript_job_manager.get_job(job_id)
    if not job:
        return error_response(message=f"Job '{job_id}' not found", status_code=404)
    return success_response(data=job.model_dump())


@app.post("/api/transcript/jobs/{job_id}/cancel")
async def api_cancel_transcript_job(job_id: str):
    """Cancel a running background transcript job."""
    from services.jobs.transcript_job_manager import transcript_job_manager
    cancelled = await transcript_job_manager.cancel_job(job_id)
    if not cancelled:
        return error_response(message=f"Job '{job_id}' could not be cancelled or not found", status_code=400)
    return success_response(message=f"Job '{job_id}' successfully cancelled")


@app.get("/api/transcript/jobs/{job_id}/download")
async def api_download_transcript_job(job_id: str):
    """Download 15-column CSV for a transcript background job."""
    from services.jobs.transcript_job_manager import transcript_job_manager
    job = transcript_job_manager.get_job(job_id)
    if not job:
        return error_response(message=f"Job '{job_id}' not found", status_code=404)
    csv_content = transcript_job_manager.generate_csv(job_id)
    clean_handle = (job.channel_handle or "channel").lstrip("@")
    filename = f"{clean_handle}_transcripts_{job_id}.csv"
    encoded = csv_content.encode("utf-8-sig")
    return StreamingResponse(
        iter([encoded]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(encoded)),
        },
    )


# ---------------------------------------------------------------------------
# Transcript CSV Export
# ---------------------------------------------------------------------------


class TranscriptExportRequest(BaseModel):
    video_url: str | None = None
    channel_handle: str | None = None
    format: str = "csv"
    max_videos: int = 1000


def _csv_escape(text: str | None) -> str:
    """Escape a string for CSV, handling commas, quotes, and newlines."""
    if text is None:
        return ""
    s = str(text)
    if "," in s or '"' in s or "\n" in s or "\r" in s:
        s = s.replace('"', '""')
        s = f'"{s}"'
    return s


def _build_csv_rows(videos: list[dict]) -> str:
    """Build a complete 15-column CSV string from a list of video dicts.

    Columns:
        video_id, video_url, channel_id, channel_title, title, published_at,
        duration_seconds, duration, language, status, transcript,
        source, method, error_code, error_message
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    header = [
        "video_id",
        "video_url",
        "channel_id",
        "channel_title",
        "title",
        "published_at",
        "duration_seconds",
        "duration",
        "language",
        "status",
        "transcript",
        "source",
        "method",
        "error_code",
        "error_message",
    ]
    writer.writerow(header)

    for v in videos:
        transcript_text = v.get("transcript", "")
        if isinstance(transcript_text, dict):
            transcript_text = transcript_text.get("plain_text") or transcript_text.get("paragraph_text") or ""

        vid = v.get("video_id", "")
        url = v.get("video_url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        status = v.get("status") or ("success" if transcript_text else "failed")

        lang = v.get("language", "")
        if lang and str(lang).lower() in ("hinglish", "en", "english", "en-in", "hi", "hindi", "english (india)"):
            lang = "English (India)"

        row = [
            vid,
            url,
            v.get("channel_id", ""),
            v.get("channel_title", ""),
            v.get("title", ""),
            v.get("published_at", ""),
            v.get("duration_seconds", ""),
            v.get("duration", "") or v.get("duration_readable", ""),
            lang,
            status,
            transcript_text,
            v.get("source", ""),
            v.get("method", ""),
            v.get("error_code", ""),
            v.get("error_message", "") or v.get("error", ""),
        ]
        writer.writerow(row)

    return output.getvalue()


def _resolve_video_id(url: str) -> str | None:
    """Extract a YouTube video ID from a URL."""
    patterns = [
        r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@app.post("/api/transcript/export")
async def api_transcript_csv_export(req: TranscriptExportRequest):
    """Export transcripts as CSV for a single video or entire channel.

    Accepts either a video_url or a channel_handle. Returns a downloadable
    CSV file with one row per video. Never aborts on individual video failures.
    """
    rid = uuid.uuid4().hex[:8]
    start_time = time.time()
    logger.info("[%s] Transcript CSV export request: video_url=%s, channel_handle=%s",
                rid, req.video_url, req.channel_handle)

    if not req.video_url and not req.channel_handle:
        return error_response(
            message="Either video_url or channel_handle is required.",
            status_code=400,
        )

    try:
        videos_data: list[dict] = []

        if req.channel_handle:
            # --- Channel handle path ---
            channel_svc = _get_channel_service()
            video_svc = _get_video_service()
            transcript_svc = _get_transcript_service()

            clean = req.channel_handle.lstrip("@")

            # Resolve channel
            channel_data = await _to_thread(channel_svc.resolve_handle, clean)
            channel_id = channel_data["id"]
            channel_title = channel_data["snippet"]["title"]

            # Get upload playlist
            playlist_id = await _to_thread(video_svc.get_uploads_playlist_id, channel_id)

            # Paginate playlist for video IDs
            all_video_ids: list[str] = []
            next_page: str | None = None
            while len(all_video_ids) < req.max_videos:
                page = await _to_thread(
                    video_svc.get_playlist_items, playlist_id, next_page,
                )
                video_ids = page.get("video_ids", [])
                for vid in video_ids:
                    if vid and vid not in all_video_ids:
                        all_video_ids.append(vid)
                        if len(all_video_ids) >= req.max_videos:
                            break
                next_page = page.get("next_page_token")
                if not next_page:
                    break

            logger.info("[%s] Discovered %d videos for CSV export", rid, len(all_video_ids))

            # Fetch metadata for duration filtering
            videos_meta: dict[str, dict] = {}
            for i in range(0, len(all_video_ids), 50):
                batch = all_video_ids[i:i + 50]
                try:
                    items = await _to_thread(video_svc.get_videos_batch, batch)
                    for item in items:
                        vid = item.get("id")
                        if not vid:
                            continue
                        snippet = item.get("snippet", {})
                        content_details = item.get("contentDetails", {})
                        duration_iso = content_details.get("duration", "PT0S")
                        duration_seconds = _parse_iso_duration(duration_iso)
                        live_status = snippet.get("liveBroadcastContent", "none")
                        videos_meta[vid] = {
                            "title": snippet.get("title", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "duration_seconds": duration_seconds,
                            "duration_readable": _format_duration(duration_seconds),
                            "live_status": live_status,
                        }
                except Exception as exc:
                    logger.warning("[%s] Metadata batch failed for %d videos: %s", rid, len(batch), exc)

            # Filter 3:00 <= duration < 30:00 and exclude live streams using evaluate_duration
            from services.duration_filter import evaluate_duration
            eligible: list[str] = []
            for vid in all_video_ids:
                meta = videos_meta.get(vid, {})
                duration = meta.get("duration_seconds", 0)
                live_status = meta.get("live_status", "none")
                f_res = evaluate_duration(
                    duration_seconds=duration,
                    live_status=live_status,
                    min_seconds=180,
                    max_seconds=1800,
                )
                if f_res.is_eligible:
                    eligible.append(vid)

            logger.info("[%s] %d eligible (3–30 min, no live), fetching transcripts...", rid, len(eligible))

            semaphore = asyncio.Semaphore(5)

            async def _fetch_one(video_id: str) -> dict:
                async with semaphore:
                    meta = videos_meta.get(video_id, {})
                    title = meta.get("title", "")
                    published_at = meta.get("published_at", "")
                    dur_sec = meta.get("duration_seconds", 0)
                    dur_str = meta.get("duration_readable", "0:00")
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    try:
                        transcript = await _to_thread(
                            transcript_svc.get_transcript,
                            video_id,
                            allow_whisper=settings.whisper_enabled,
                            video_title=title,
                            channel_title=channel_title,
                        )
                        if transcript and transcript.success and (transcript.plain_text or transcript.paragraph_text):
                            src = getattr(transcript.source, "value", str(transcript.source)) if transcript.source else "youtube"
                            mth = getattr(transcript, "method", None) or ("speech_to_text" if src == "whisper" else "caption")
                            return {
                                "video_id": video_id,
                                "video_url": video_url,
                                "channel_id": channel_id,
                                "channel_title": channel_title,
                                "title": title,
                                "published_at": published_at,
                                "duration_seconds": dur_sec,
                                "duration": dur_str,
                                "language": transcript.language or "English (India)",
                                "status": "success",
                                "transcript": transcript.plain_text or transcript.paragraph_text or "",
                                "source": src,
                                "method": mth,
                                "error_code": None,
                                "error_message": None,
                            }
                        else:
                            return {
                                "video_id": video_id,
                                "video_url": video_url,
                                "channel_id": channel_id,
                                "channel_title": channel_title,
                                "title": title,
                                "published_at": published_at,
                                "duration_seconds": dur_sec,
                                "duration": dur_str,
                                "language": "English (India)",
                                "status": "failed",
                                "transcript": "",
                                "source": None,
                                "method": None,
                                "error_code": getattr(transcript, "error_code", None) or "NO_CAPTIONS",
                                "error_message": getattr(transcript, "error", None) or "No captions available",
                            }
                    except Exception as exc:
                        logger.warning("[%s] Transcript fetch failed for %s: %s", rid, video_id, exc)
                        return {
                            "video_id": video_id,
                            "video_url": video_url,
                            "channel_id": channel_id,
                            "channel_title": channel_title,
                            "title": title,
                            "published_at": published_at,
                            "duration_seconds": dur_sec,
                            "duration": dur_str,
                            "language": "English (India)",
                            "status": "failed",
                            "transcript": "",
                            "source": None,
                            "method": None,
                            "error_code": "EXTRACTION_ERROR",
                            "error_message": f"Speech-to-text failed: {exc}",
                        }

            tasks = [_fetch_one(vid) for vid in eligible]
            raw = await asyncio.gather(*tasks)
            videos_data = list(raw)

            logger.info("[%s] CSV export: %d rows generated for channel %s",
                        rid, len(videos_data), channel_title)

        elif req.video_url:
            # --- Single video URL path ---
            video_svc = _get_video_service()
            transcript_svc = _get_transcript_service()
            video_id = _resolve_video_id(req.video_url)
            if not video_id:
                return error_response(
                    message="Could not extract a valid video ID from the URL.",
                    status_code=400,
                )

            # Fetch minimal metadata
            title = ""
            published_at = ""
            duration = "0:00"
            duration_seconds = 0
            channel_id = ""
            channel_title = ""
            try:
                items = await _to_thread(video_svc.get_videos_batch, [video_id])
                if items:
                    snippet = items[0].get("snippet", {})
                    cd = items[0].get("contentDetails", {})
                    title = snippet.get("title", "")
                    published_at = snippet.get("publishedAt", "")
                    channel_id = snippet.get("channelId", "")
                    channel_title = snippet.get("channelTitle", "")
                    duration_seconds = _parse_iso_duration(cd.get("duration", "PT0S"))
                    duration = _format_duration(duration_seconds)
            except Exception as exc:
                logger.warning("[%s] Metadata fetch failed for %s: %s", rid, video_id, exc)

            # Fetch transcript (captions first, then whisper fallback)
            transcript_text = ""
            status = "failed"
            source = None
            method = None
            language = "en"
            error_code = None
            error_message = None
            try:
                transcript = await _to_thread(
                    transcript_svc.get_transcript,
                    video_id,
                    allow_whisper=settings.whisper_enabled,
                    video_title=title,
                    channel_title=channel_title,
                )
                if transcript and transcript.success and (transcript.plain_text or transcript.paragraph_text):
                    transcript_text = transcript.plain_text or transcript.paragraph_text or ""
                    status = "success"
                    source = getattr(transcript.source, "value", str(transcript.source)) if transcript.source else "youtube"
                    method = getattr(transcript, "method", None) or ("speech_to_text" if source == "whisper" else "caption")
                    language = transcript.language or "English (India)"
                else:
                    error_code = getattr(transcript, "error_code", None) or "NO_CAPTIONS"
                    error_message = getattr(transcript, "error", None) or "No captions available"
            except Exception as exc:
                logger.warning("[%s] Transcript fetch failed for %s: %s", rid, video_id, exc)
                error_code = "EXTRACTION_ERROR"
                error_message = str(exc)

            videos_data = [{
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "channel_id": channel_id,
                "channel_title": channel_title,
                "title": title,
                "published_at": published_at,
                "duration_seconds": duration_seconds,
                "duration": duration,
                "language": language,
                "status": status,
                "transcript": transcript_text,
                "source": source,
                "method": method,
                "error_code": error_code,
                "error_message": error_message,
            }]

            logger.info("[%s] CSV export: 1 row for video %s", rid, video_id)

        # Generate CSV
        csv_content = _build_csv_rows(videos_data)
        elapsed = round(time.time() - start_time, 2)
        logger.info("[%s] CSV export complete: %d rows, %d bytes, %.2fs elapsed",
                    rid, len(videos_data), len(csv_content.encode("utf-8")), elapsed)

        filename = "transcripts.csv"
        if req.channel_handle:
            clean = req.channel_handle.lstrip("@")
            filename = f"{clean}_transcripts.csv"

        return StreamingResponse(
            iter([csv_content.encode("utf-8-sig")]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(csv_content.encode("utf-8-sig"))),
            },
        )

    except Exception as exc:
        logger.exception("[%s] CSV export failed", rid)
        return error_response(
            message=f"Transcript CSV export failed: {exc}",
            status_code=500,
        )


# --- Analysis endpoints ---

@app.get("/api/analyze/{video_id}")
async def api_analyze_transcript(video_id: str, force_refresh: bool = False) -> dict:
    import json
    transcript_service = _get_transcript_service()
    transcript = await _to_thread(transcript_service.get_transcript, video_id)
    if not transcript.success:
        raise HTTPException(status_code=404, detail={"success": False, "error": transcript.error or "No transcript available."})
    processor = _get_transcript_processor()
    processed = await _to_thread(processor.process, segments=transcript.segments, video_id=video_id)
    if not processed.success:
        raise HTTPException(status_code=422, detail={"success": False, "error": processed.error or "Failed to process."})
    meta_service = _get_metadata_service()
    metadata = await _to_thread(meta_service.get_metadata, video_id) if video_id else None
    service = _get_content_analysis_service()
    result = await _to_thread(service.analyze, transcript=processed.clean_transcript, video_id=video_id, metadata=metadata.model_dump() if metadata else None)
    return json.loads(result.model_dump_json())


@app.post("/api/analyze")
async def api_analyze_direct(request: Request) -> dict:
    import json
    from schemas.analysis_response import AnalyzeTranscriptRequest
    body = await request.json()
    req = AnalyzeTranscriptRequest(**body)
    service = _get_content_analysis_service()
    result = await _to_thread(service.analyze, transcript=req.transcript, video_id=req.video_id, metadata=req.metadata)
    return json.loads(result.model_dump_json())


# --- Blog endpoints ---

@app.get("/api/blog/{video_id}")
async def api_generate_blog(video_id: str, force_refresh: bool = False) -> dict:
    import json
    transcript_service = _get_transcript_service()
    transcript = await _to_thread(transcript_service.get_transcript, video_id)
    if not transcript.success:
        raise HTTPException(status_code=404, detail={"success": False, "error": transcript.error or "No transcript available."})
    processor = _get_transcript_processor()
    processed = await _to_thread(processor.process, segments=transcript.segments, video_id=video_id)
    if not processed.success:
        raise HTTPException(status_code=422, detail={"success": False, "error": processed.error or "Failed to process."})
    service = _get_blog_service()
    result = await _to_thread(service.generate, transcript=processed.clean_transcript, video_id=video_id)
    return json.loads(result.model_dump_json())


@app.post("/api/blog")
async def api_generate_blog_direct(request: Request) -> dict:
    import json
    from models.blog_generation import BlogGenerationRequest
    body = await request.json()
    req = BlogGenerationRequest(**body)
    service = _get_blog_service()
    result = await _to_thread(service.generate, transcript=req.transcript, video_id=req.video_id, metadata=req.metadata, analysis=req.analysis)
    return json.loads(result.model_dump_json())


# --- SEO endpoints ---

@app.post("/api/seo")
async def api_seo_optimize(request: Request) -> dict:
    import json
    from models.seo_package import SEORequest
    body = await request.json()
    req = SEORequest(**body)
    service = _get_seo_service()
    result = await _to_thread(service.optimize, blog_data=req.blog, video_id=req.video_id)
    return json.loads(result.model_dump_json())


@app.post("/api/seo/pipeline")
async def api_seo_full_pipeline(request: Request) -> dict:
    import json
    from models.blog_generation import BlogGenerationRequest
    body = await request.json()
    req = BlogGenerationRequest(**body)
    blog_service = _get_blog_service()
    blog_result = await _to_thread(blog_service.generate, transcript=req.transcript, video_id=req.video_id)
    if not blog_result.success:
        return json.loads(blog_result.model_dump_json())
    seo_service = _get_seo_service()
    seo_result = await _to_thread(seo_service.optimize, blog_data=json.loads(blog_result.model_dump_json()).get("blog", {}), video_id=req.video_id)
    return {"success": True, "video_id": req.video_id, "blog": json.loads(blog_result.model_dump_json()).get("blog"), "seo_package": json.loads(seo_result.model_dump_json()).get("seo_package")}


# --- Blog export endpoints ---

@app.post("/api/blog-export")
async def api_export_blog(request: Request) -> dict:
    import json
    from models.blog_export import ExportRequest
    body = await request.json()
    req = ExportRequest(**body)
    engine = _get_export_engine()
    result = await _to_thread(engine.export, req)
    response = json.loads(result.model_dump_json())
    return response


@app.get("/api/blog-export/download/{filename:path}")
async def api_export_download_blog(filename: str):
    from export.engine import EXPORT_DIR
    filepath = EXPORT_DIR / filename
    if not filepath.exists():
        for sub in EXPORT_DIR.iterdir():
            if sub.is_dir():
                candidate = sub / filename
                if candidate.exists():
                    filepath = candidate
                    break
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    mime_map = {".md": "text/markdown", ".html": "text/html", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".pdf": "application/pdf", ".zip": "application/zip"}
    mime = mime_map.get(filepath.suffix.lower(), "application/octet-stream")
    return FileResponse(str(filepath), media_type=mime, filename=filepath.name)


@app.get("/api/blog/{video_id}/export-ready")
async def api_export_ready(video_id: str) -> dict:
    try:
        from repositories.blog_repository import BlogRepository
        repo = BlogRepository()
        blog_data = await _to_thread(repo.get, video_id)
        if blog_data:
            from models.blog_generation import BlogGenerationResult
            blog = BlogGenerationResult(**blog_data)
            if blog.success and blog.blog:
                return {"success": True, "ready": True, "blog": blog.model_dump()}
        return {"success": True, "ready": False, "blog": None}
    except Exception as exc:
        return {"success": False, "ready": False, "error": str(exc)}


@app.post("/api/review")
async def api_review_blog(request: Request) -> dict:
    import json
    body = await request.json()
    from models.blog_review import BlogReviewRequest
    req = BlogReviewRequest(**body)
    engine = _get_review_engine()
    response = await _to_thread(engine.review, req)
    return json.loads(response.model_dump_json())


# --- Validation endpoint ---

@app.get("/api/validate-url")
async def api_validate_url(url: str = "") -> dict:
    from services.youtube_url_parser import YouTubeURLParser
    parser = YouTubeURLParser()
    result = await _to_thread(parser.parse, url)
    return result.model_dump()


# --- Video metadata endpoint ---

@app.get("/api/video-metadata/{video_id}")
async def api_video_metadata(video_id: str) -> dict:
    service = _get_metadata_service()
    result = await _to_thread(service.get_metadata, video_id)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Project Management API (NEW â€” does not modify existing endpoints)
# ---------------------------------------------------------------------------

from projects.project_service import ProjectService
from orchestrator import PipelineOrchestrator
from orchestrator.stages import (
    MetadataStage, TranscriptStage, AnalysisStage,
    SEOStage, OutlineStage, SectionsStage,
    MergeStage, ReviewStage, ExportStage,
    KnowledgeGraphStage,
    SEOIntelligenceStage,
    OutlineGeneratorStage,
)

from editor.editor_service import EditorService
from editor.editor_models import (
    AIActionRequest, FindReplaceRequest, TranslationRequest,
    ViewMode, EditorConfig,
)

from production_pipeline.workflow import DurableWorkflowEngine
from production_pipeline.transaction_logger import TransactionLogger
from production_pipeline.execution_history import ExecutionHistory
from production_pipeline.error_handler import ErrorHandler
from production_pipeline.recovery_manager import RecoveryManager
from production_pipeline.resume_engine import ResumeEngine
from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.idempotency import IdempotencyFramework
from production_pipeline.snapshot_manager import SnapshotManager
from production_pipeline.timeout_manager import TimeoutManager
from production_pipeline.dead_letter_queue import PipelineDeadLetterQueue
from production_pipeline.retry_framework import RetryFramework
from production_pipeline.stage_validator import StageValidator

_project_service = ProjectService()

# Pipeline Orchestrator â€” registers all stages (existing, unchanged)
_orchestrator = PipelineOrchestrator(project_manager=_project_service.manager)

# Durable Workflow Engine â€” adds checkpointing, idempotency, resume, recovery
_tx_log = TransactionLogger()
_dup_engine = DurableWorkflowEngine(
    checkpoint_manager=CheckpointManager(),
    snapshot_manager=SnapshotManager(),
    idempotency=IdempotencyFramework(),
    transaction_logger=_tx_log,
    execution_history=ExecutionHistory(_tx_log),
    error_handler=ErrorHandler(),
    retry_framework=RetryFramework(),
    timeout_manager=TimeoutManager(),
    dead_letter_queue=PipelineDeadLetterQueue(),
    recovery_manager=RecoveryManager(),
    resume_engine=ResumeEngine(CheckpointManager()),
    stage_validator=StageValidator(),
)
_orchestrator.register_stage(MetadataStage())
_orchestrator.register_stage(TranscriptStage())
_orchestrator.register_stage(AnalysisStage())
_orchestrator.register_stage(SEOStage())
_orchestrator.register_stage(OutlineStage())
_orchestrator.register_stage(SectionsStage())
_orchestrator.register_stage(MergeStage())
_orchestrator.register_stage(ReviewStage())
_orchestrator.register_stage(ExportStage())
_orchestrator.register_stage(KnowledgeGraphStage())
_orchestrator.register_stage(SEOIntelligenceStage())
_orchestrator.register_stage(OutlineGeneratorStage())


@app.post("/api/projects")
async def api_create_project(request: Request) -> dict:
    """Create a new project from a YouTube URL."""
    body = await request.json()
    url = body.get("url", "")
    video_id = body.get("video_id", "")
    if not url and not video_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "url or video_id required"})
    result = _project_service.create_from_url(url=url, video_id=video_id)
    return {"success": True, "project": result}


@app.get("/api/projects")
async def api_list_projects(limit: int = 50, offset: int = 0, search: str = "") -> dict:
    """List all projects with optional search."""
    if search:
        projects = _project_service.search(search, limit=limit)
    else:
        projects = _project_service.list_all(limit=limit, offset=offset)
    return {"success": True, "projects": projects, "count": len(projects)}


@app.get("/api/projects/stats")
async def api_project_stats() -> dict:
    """Get project statistics."""
    stats = _project_service.get_stats()
    return {"success": True, **stats}


@app.get("/api/projects/{project_id}")
async def api_get_project(project_id: str) -> dict:
    """Get a single project with full details."""
    project = _project_service.get(project_id)
    if project is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})
    return {"success": True, "project": project}


@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: str, permanent: bool = False) -> dict:
    """Delete a project (soft delete by default)."""
    return _project_service.delete(project_id, permanent=permanent)


@app.post("/api/projects/{project_id}/resume")
async def api_resume_project(project_id: str) -> dict:
    """Resume a paused or failed project."""
    result = _project_service.resume(project_id)
    if result is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})
    return {"success": True, "project": result}


@app.post("/api/projects/{project_id}/pause")
async def api_pause_project(project_id: str) -> dict:
    """Pause a running project."""
    return _project_service.pause(project_id)


@app.post("/api/projects/{project_id}/cancel")
async def api_cancel_project(project_id: str) -> dict:
    """Cancel a project."""
    return _project_service.cancel(project_id)


@app.get("/api/projects/{project_id}/history")
async def api_project_history(project_id: str, limit: int = 50) -> dict:
    """Get project history/audit trail."""
    history = _project_service.get_history(project_id, limit=limit)
    return {"success": True, "history": history}


@app.get("/api/projects/{project_id}/checkpoints")
async def api_project_checkpoints(project_id: str) -> dict:
    """Get project checkpoints."""
    checkpoints = _project_service.get_checkpoints(project_id)
    return {"success": True, "checkpoints": checkpoints}


@app.get("/api/projects/{project_id}/versions")
async def api_project_versions(project_id: str) -> dict:
    """Get project version history."""
    versions = _project_service.get_versions(project_id)
    return {"success": True, "versions": versions}


@app.post("/api/projects/{project_id}/restore/{version_number}")
async def api_restore_version(project_id: str, version_number: int) -> dict:
    """Restore a project to a previous version."""
    result = _project_service.restore_version(project_id, version_number)
    if result is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Version not found"})
    return {"success": True, "project": result}


@app.get("/api/projects/{project_id}/validate")
async def api_validate_project(project_id: str) -> dict:
    """Validate project artifacts."""
    issues = _project_service.validate(project_id)
    return {"success": True, "issues": issues, "healthy": len(issues) == 0}


@app.put("/api/projects/{project_id}/settings")
async def api_update_settings(project_id: str, request: Request) -> dict:
    """Update project settings."""
    body = await request.json()
    result = _project_service.update_settings(project_id, body)
    if result is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})
    return {"success": True, "project": result}


# ---------------------------------------------------------------------------
# Knowledge Graph API (NEW â€” does not modify existing endpoints)
# ---------------------------------------------------------------------------

from knowledge_graph.knowledge_graph_service import KnowledgeGraphService

_knowledge_graph_service = KnowledgeGraphService(
    project_manager=_project_service.manager,
    cache_manager=_orchestrator.cache,
)


@app.post("/api/knowledge-graph/build")
async def api_kg_build(request: Request) -> dict:
    """Build a knowledge graph from existing project artifacts."""
    body = await request.json()
    project_id = body.get("project_id", "")
    if not project_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "project_id required"})

    project = _project_service.get(project_id)
    if project is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

    metadata = _project_service.manager.load_stage_data(project_id, "metadata")
    transcript = _project_service.manager.load_stage_data(project_id, "transcript")
    analysis = _project_service.manager.load_stage_data(project_id, "analysis")

    kg = _knowledge_graph_service.build(
        project_id=project_id,
        metadata=metadata,
        transcript=transcript,
        analysis=analysis,
    )
    return {"success": True, "knowledge_graph": kg.model_dump(), "summary": kg.summary}


@app.get("/api/knowledge-graph/{project_id}")
async def api_kg_get(project_id: str) -> dict:
    """Get stored knowledge graph for a project."""
    kg = _knowledge_graph_service.get_stored(project_id)
    if kg is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Knowledge graph not found"})
    return {"success": True, "knowledge_graph": kg.model_dump(), "summary": kg.summary}


@app.get("/api/knowledge-graph/{project_id}/summary")
async def api_kg_summary(project_id: str) -> dict:
    """Get knowledge graph summary statistics."""
    kg = _knowledge_graph_service.get_stored(project_id)
    if kg is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Knowledge graph not found"})
    return {"success": True, "summary": kg.summary}


@app.get("/api/knowledge-graph/{project_id}/entities")
async def api_kg_entities(project_id: str) -> dict:
    """Get entities from knowledge graph."""
    kg = _knowledge_graph_service.get_stored(project_id)
    if kg is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Knowledge graph not found"})
    return {
        "success": True,
        "entities": [e.model_dump() for e in kg.entities],
        "count": kg.entity_count(),
    }


@app.get("/api/knowledge-graph/{project_id}/relationships")
async def api_kg_relationships(project_id: str) -> dict:
    """Get relationships from knowledge graph."""
    kg = _knowledge_graph_service.get_stored(project_id)
    if kg is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Knowledge graph not found"})
    return {
        "success": True,
        "relationships": [r.model_dump() for r in kg.relationships],
        "count": kg.relationship_count(),
    }


# ---------------------------------------------------------------------------
# SEO Intelligence API (NEW â€” does not modify existing endpoints)
# ---------------------------------------------------------------------------

from seo_intelligence.seo_service import SEOService as _SEOService

_seo_service = _SEOService(
    project_manager=_project_service.manager,
    cache_manager=_orchestrator.cache,
)


@app.post("/api/seo-intelligence/build")
async def api_seo_build(request: Request) -> dict:
    """Build an SEO plan from existing project artifacts."""
    body = await request.json()
    project_id = body.get("project_id", "")
    if not project_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "project_id required"})

    project = _project_service.get(project_id)
    if project is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

    kg = _project_service.manager.load_stage_data(project_id, "knowledge_graph")
    analysis = _project_service.manager.load_stage_data(project_id, "analysis")
    metadata = _project_service.manager.load_stage_data(project_id, "metadata")

    plan = _seo_service.build(
        project_id=project_id,
        knowledge_graph=kg,
        analysis=analysis,
        metadata=metadata,
    )
    return {"success": True, "seo_plan": plan.model_dump(), "summary": plan.summary}


@app.get("/api/seo-intelligence/{project_id}")
async def api_seo_get(project_id: str) -> dict:
    """Get stored SEO plan for a project."""
    plan = _seo_service.get_stored(project_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "SEO plan not found"})
    return {"success": True, "seo_plan": plan.model_dump(), "summary": plan.summary}


@app.get("/api/seo-intelligence/{project_id}/summary")
async def api_seo_summary(project_id: str) -> dict:
    """Get SEO plan summary."""
    plan = _seo_service.get_stored(project_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "SEO plan not found"})
    return {"success": True, "summary": plan.summary}


@app.get("/api/seo-intelligence/{project_id}/keywords")
async def api_seo_keywords(project_id: str) -> dict:
    """Get keyword strategy from SEO plan."""
    plan = _seo_service.get_stored(project_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "SEO plan not found"})
    return {
        "success": True,
        "keyword_strategy": plan.keyword_strategy.model_dump(),
    }


@app.get("/api/seo-intelligence/{project_id}/scores")
async def api_seo_scores(project_id: str) -> dict:
    """Get SEO scores."""
    plan = _seo_service.get_stored(project_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "SEO plan not found"})
    return {"success": True, "scores": plan.scores.model_dump()}


# ---------------------------------------------------------------------------
# Outline Generator API (NEW â€” does not modify existing endpoints)
# ---------------------------------------------------------------------------

from outline_generator.outline_service import OutlineService as _OutlineService

_outline_service = _OutlineService(
    project_manager=_project_service.manager,
    cache_manager=_orchestrator.cache,
)


@app.post("/api/outline/build")
async def api_outline_build(request: Request) -> dict:
    """Build a content outline from existing project artifacts."""
    body = await request.json()
    project_id = body.get("project_id", "")
    if not project_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "project_id required"})

    project = _project_service.get(project_id)
    if project is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Project not found"})

    kg = _project_service.manager.load_stage_data(project_id, "knowledge_graph")
    seo_plan = _project_service.manager.load_stage_data(project_id, "seo_intelligence")
    if not seo_plan:
        seo_plan = _project_service.manager.load_stage_data(project_id, "seo_plan")
    analysis = _project_service.manager.load_stage_data(project_id, "analysis")
    metadata = _project_service.manager.load_stage_data(project_id, "metadata")

    outline = _outline_service.build(
        project_id=project_id,
        knowledge_graph=kg,
        seo_plan=seo_plan,
        analysis=analysis,
        metadata=metadata,
    )
    return {"success": True, "outline": outline.model_dump(), "summary": outline.summary}


@app.get("/api/outline/{project_id}")
async def api_outline_get(project_id: str) -> dict:
    """Get stored outline for a project."""
    outline = _outline_service.get_stored(project_id)
    if outline is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Outline not found"})
    return {"success": True, "outline": outline.model_dump(), "summary": outline.summary}


@app.get("/api/outline/{project_id}/summary")
async def api_outline_summary(project_id: str) -> dict:
    """Get outline summary."""
    outline = _outline_service.get_stored(project_id)
    if outline is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Outline not found"})
    return {"success": True, "summary": outline.summary}


@app.get("/api/outline/{project_id}/sections")
async def api_outline_sections(project_id: str) -> dict:
    """Get sections from outline."""
    outline = _outline_service.get_stored(project_id)
    if outline is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Outline not found"})
    return {
        "success": True,
        "sections": [s.model_dump() for s in outline.sections],
        "count": len(outline.sections),
    }


# ---------------------------------------------------------------------------
# Pipeline Orchestrator API (NEW â€” does not modify existing endpoints)
# ---------------------------------------------------------------------------


@app.post("/api/pipeline/run")
async def api_pipeline_run(request: Request) -> dict:
    """Run the full pipeline for a video."""
    body = await request.json()
    video_id = body.get("video_id", "")
    url = body.get("url", "")
    project_id = body.get("project_id", "")

    if not video_id and not url:
        return JSONResponse(status_code=400, content={"success": False, "error": "video_id or url required"})

    # Create or reuse project
    if not project_id:
        result = _project_service.create_from_url(url=url, video_id=video_id)
        project_id = result["project_id"]

    result = await _orchestrator.run_pipeline(project_id, video_id=video_id, url=url)
    return {"success": True, **result}


@app.get("/api/pipeline/{project_id}/progress")
async def api_pipeline_progress(project_id: str) -> dict:
    """Get pipeline execution progress."""
    progress = _orchestrator.get_progress(project_id)
    if progress is None:
        return {"success": False, "error": "Pipeline not found"}
    return {"success": True, **progress}


@app.get("/api/pipeline/{project_id}/stages/{stage}")
async def api_pipeline_stage(project_id: str, stage: str) -> dict:
    """Get stage execution info."""
    info = _orchestrator.get_stage_info(project_id, stage)
    if info is None:
        return {"success": False, "error": "Stage not found"}
    return {"success": True, "stage": info}


@app.post("/api/pipeline/{project_id}/pause")
async def api_pipeline_pause(project_id: str) -> dict:
    """Pause pipeline execution."""
    success = await _orchestrator.pause_pipeline(project_id)
    return {"success": success}


@app.post("/api/pipeline/{project_id}/resume")
async def api_pipeline_resume(project_id: str) -> dict:
    """Resume pipeline execution."""
    success = await _orchestrator.resume_pipeline(project_id)
    return {"success": success}


@app.post("/api/pipeline/{project_id}/cancel")
async def api_pipeline_cancel(project_id: str) -> dict:
    """Cancel pipeline execution."""
    success = await _orchestrator.cancel_pipeline(project_id)
    return {"success": success}


@app.get("/api/pipeline/{project_id}/history")
async def api_pipeline_history(project_id: str, limit: int = 50) -> dict:
    """Get pipeline execution history (events)."""
    history = _orchestrator.get_history(project_id, limit=limit)
    return {"success": True, "history": history, "count": len(history)}


@app.get("/api/pipeline/active")
async def api_pipeline_active() -> dict:
    """List active pipelines."""
    active = _orchestrator.active_pipelines
    return {"success": True, "active": active, "count": len(active)}


@app.get("/api/pipeline/metrics")
async def api_pipeline_metrics() -> dict:
    """Get pipeline execution metrics."""
    metrics = _orchestrator.get_metrics_report()
    return {"success": True, "metrics": metrics}


@app.get("/api/pipeline/cache/stats")
async def api_pipeline_cache_stats() -> dict:
    """Get pipeline cache statistics."""
    stats = _orchestrator.get_cache_stats()
    return {"success": True, "cache": stats}


@app.delete("/api/pipeline/cache")
async def api_pipeline_cache_clear() -> dict:
    """Clear pipeline cache."""
    _orchestrator.clear_cache()
    return {"success": True}


# ---------------------------------------------------------------------------
# Phase 23 â€” Durable Pipeline API (additive, does not modify existing endpoints)
# ---------------------------------------------------------------------------


@app.post("/api/v2/pipeline/run")
async def api_v2_pipeline_run(request: Request) -> dict:
    """Run the full pipeline with durable execution guarantees.

    Features: checkpointing, idempotency, crash recovery, execution history.
    """
    body = await request.json()
    video_id = body.get("video_id", "")
    url = body.get("url", "")
    project_id = body.get("project_id", "")

    if not video_id and not url:
        return JSONResponse(status_code=400, content={
            "success": False, "error": "video_id or url required"
        })

    import uuid
    execution_id = str(uuid.uuid4())

    # Create or reuse project
    if not project_id:
        result = _project_service.create_from_url(url=url, video_id=video_id)
        project_id = result["project_id"]

    # Register stage executors from the existing orchestrator
    from orchestrator.stages import (
        MetadataStage, TranscriptStage, AnalysisStage,
        SEOStage, OutlineStage, SectionsStage,
        MergeStage, ReviewStage, ExportStage,
        KnowledgeGraphStage, SEOIntelligenceStage,
    )

    async def _wrap_stage(stage_class, stage_name):
        instance = stage_class()

        async def _execute(ctx):
            pipeline_ctx = type('obj', (object,), {
                'video_id': ctx.get('video_id', video_id),
                'project_id': ctx.get('project_id', project_id),
                'metadata': ctx.get('metadata', {}),
                'transcript': ctx.get('transcript', {}),
                'analysis': ctx.get('analysis', {}),
                'seo': ctx.get('seo', {}),
                'outline': ctx.get('outline', {}),
                'sections': ctx.get('sections', []),
                'merged_blog': ctx.get('merged_blog', {}),
                'review': ctx.get('review', {}),
                'export': ctx.get('export', {}),
            })
            result = await instance.execute(pipeline_ctx)
            if result.success:
                return result.data
            raise Exception(result.error)

        _dup_engine.register_stage_executor(stage_name, _execute)
        return _execute

    await _wrap_stage(MetadataStage, "metadata")
    await _wrap_stage(TranscriptStage, "transcript")
    await _wrap_stage(AnalysisStage, "analysis")
    await _wrap_stage(KnowledgeGraphStage, "knowledge_graph")
    await _wrap_stage(SEOStage, "seo")
    await _wrap_stage(SEOIntelligenceStage, "seo_intelligence")
    await _wrap_stage(OutlineStage, "outline")
    await _wrap_stage(SectionsStage, "sections")
    await _wrap_stage(MergeStage, "review")
    await _wrap_stage(ReviewStage, "review_quality")
    await _wrap_stage(ExportStage, "export")

    result = await _dup_engine.run_workflow(
        execution_id=execution_id,
        video_id=video_id,
        project_id=project_id,
    )

    return {
        "success": result["success"],
        "execution_id": execution_id,
        "project_id": project_id,
        "status": result.get("error", "completed") if not result["success"] else "completed",
        "completed_stages": result.get("completed_stages", []),
        "duration_ms": result.get("duration_ms", 0),
        "error": result.get("error", ""),
    }


@app.get("/api/v2/pipeline/{execution_id}/status")
async def api_v2_pipeline_status(execution_id: str) -> dict:
    """Get the status of a durable pipeline execution."""
    status = _dup_engine.get_workflow_status(execution_id)
    if status is None:
        return {"success": False, "error": "Execution not found"}
    return {"success": True, **status}


@app.get("/api/v2/pipeline/{execution_id}/history")
async def api_v2_pipeline_history(execution_id: str) -> dict:
    """Get the full execution timeline for a durable pipeline."""
    timeline = _dup_engine._exec_history.get_timeline(execution_id)
    return {"success": True, "execution_id": execution_id, "timeline": timeline, "count": len(timeline)}


@app.get("/api/v2/pipeline/{execution_id}/summary")
async def api_v2_pipeline_summary(execution_id: str) -> dict:
    """Get the execution summary for a durable pipeline."""
    summary = _dup_engine._exec_history.get_summary(execution_id)
    return {"success": True, **summary}


@app.get("/api/v2/pipeline/{execution_id}/checkpoints")
async def api_v2_pipeline_checkpoints(execution_id: str) -> dict:
    """Get all checkpoints for a durable pipeline execution."""
    checkpoints = _dup_engine._checkpoints.list_checkpoints(execution_id)
    return {
        "success": True,
        "checkpoints": [
            {
                "stage": cp.stage_name,
                "index": cp.stage_index,
                "status": cp.status,
                "duration_ms": cp.duration_ms,
                "input_hash": cp.input_hash[:12],
                "output_hash": cp.output_hash[:12],
            }
            for cp in checkpoints
        ],
        "count": len(checkpoints),
    }


@app.post("/api/v2/pipeline/{execution_id}/resume")
async def api_v2_pipeline_resume(execution_id: str) -> dict:
    """Resume a failed or recovering pipeline execution."""
    result = await _dup_engine.resume_workflow(execution_id)
    return {"success": True, **result}


@app.post("/api/v2/pipeline/{execution_id}/cancel")
async def api_v2_pipeline_cancel(execution_id: str) -> dict:
    """Cancel a running pipeline execution."""
    success = await _dup_engine.cancel_workflow(execution_id)
    return {"success": success}


# ---------------------------------------------------------------------------
# Editor API â€” Rich Blog Editor endpoints
# ---------------------------------------------------------------------------

_editor_service = EditorService(
    project_manager=_project_service.manager,
    storage_dir=Path(_project_service.manager.storage.base_path) if hasattr(_project_service.manager.storage, 'base_path') else None,
)


@app.get("/api/editor/{project_id}")
async def api_editor_load(project_id: str) -> dict:
    """Load editor state for a project."""
    result = _editor_service.load_draft(project_id)
    stats = _editor_service.get_statistics(project_id)
    seo_score = _editor_service.get_seo_score(project_id)
    headings = _editor_service.get_heading_navigation(project_id)
    versions = [v.model_dump() for v in _editor_service.list_versions(project_id)]
    return {
        "success": True,
        "project_id": project_id,
        "content": result.get("content", ""),
        "title": result.get("title", ""),
        "statistics": stats.model_dump(),
        "seo_score": seo_score,
        "headings": headings,
        "versions": versions,
    }


@app.post("/api/editor/{project_id}/save")
async def api_editor_save(project_id: str, request: Request) -> dict:
    """Save editor content."""
    body = await request.json()
    content = body.get("content", "")
    title = body.get("title", "")
    result = _editor_service.save_draft(project_id, content=content, title=title)
    return {
        "success": True,
        "project_id": project_id,
        "saved_at": result.get("saved_at", ""),
    }


@app.get("/api/editor/{project_id}/content")
async def api_editor_content(project_id: str) -> dict:
    """Get current editor content."""
    content = _editor_service.get_draft_content(project_id)
    return {"success": True, "content": content}


@app.post("/api/editor/{project_id}/content")
async def api_editor_set_content(project_id: str, request: Request) -> dict:
    """Set editor content."""
    body = await request.json()
    content = body.get("content", "")
    _editor_service.set_content(project_id, content)
    return {"success": True}


@app.get("/api/editor/{project_id}/stats")
async def api_editor_stats(project_id: str) -> dict:
    """Get document statistics."""
    stats = _editor_service.get_statistics(project_id)
    seo_score = _editor_service.get_seo_score(project_id)
    return {"success": True, "statistics": stats.model_dump(), "seo_score": seo_score}


@app.get("/api/editor/{project_id}/validate")
async def api_editor_validate(project_id: str) -> dict:
    """Validate document."""
    results = _editor_service.validate(project_id)
    return {"success": True, "validations": results, "count": len(results)}


@app.post("/api/editor/{project_id}/undo")
async def api_editor_undo(project_id: str) -> dict:
    """Undo last action."""
    result = _editor_service.undo(project_id)
    return {
        "success": True,
        "content": result or "",
        "can_undo": _editor_service.can_undo(project_id),
        "can_redo": _editor_service.can_redo(project_id),
    }


@app.post("/api/editor/{project_id}/redo")
async def api_editor_redo(project_id: str) -> dict:
    """Redo last undone action."""
    result = _editor_service.redo(project_id)
    return {
        "success": True,
        "content": result or "",
        "can_undo": _editor_service.can_undo(project_id),
        "can_redo": _editor_service.can_redo(project_id),
    }


@app.get("/api/editor/{project_id}/history")
async def api_editor_history(project_id: str) -> dict:
    """Get undo/redo state."""
    return {
        "success": True,
        "can_undo": _editor_service.can_undo(project_id),
        "can_redo": _editor_service.can_redo(project_id),
    }


@app.post("/api/editor/{project_id}/version")
async def api_editor_create_version(project_id: str, request: Request) -> dict:
    """Create a named version snapshot."""
    body = await request.json()
    label = body.get("label", "")
    reason = body.get("reason", "manual_save")
    version = _editor_service.create_version(project_id, label=label, reason=reason)
    return {"success": True, "version": version.model_dump()}


@app.get("/api/editor/{project_id}/versions")
async def api_editor_versions(project_id: str) -> dict:
    """List all versions."""
    versions = [v.model_dump() for v in _editor_service.list_versions(project_id)]
    return {"success": True, "versions": versions, "count": len(versions)}


@app.get("/api/editor/{project_id}/versions/{version_number}")
async def api_editor_version_content(project_id: str, version_number: int) -> dict:
    """Get content of a specific version."""
    content = _editor_service.get_version_content(project_id, version_number)
    if content is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Version not found"})
    return {"success": True, "content": content, "version": version_number}


@app.get("/api/editor/{project_id}/diff")
async def api_editor_diff(project_id: str, old: int = 0, new: int = 0) -> dict:
    """Diff two versions."""
    if old <= 0:
        old = 1
    if new <= 0:
        versions = _editor_service.list_versions(project_id)
        new = versions[-1].version_number if versions else 1
    diff = _editor_service.diff_versions(project_id, old, new)
    if diff is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Diff not available"})
    return {"success": True, "diff": diff.model_dump()}


@app.post("/api/editor/{project_id}/restore/{version_number}")
async def api_editor_restore(project_id: str, version_number: int) -> dict:
    """Restore document to a previous version."""
    content = _editor_service.restore_version(project_id, version_number)
    if content is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Version not found"})
    return {"success": True, "content": content, "version": version_number}


@app.post("/api/editor/{project_id}/find")
async def api_editor_find(project_id: str, request: Request) -> dict:
    """Find text in document."""
    body = await request.json()
    req = FindReplaceRequest(**body)
    result = _editor_service.find_in_document(project_id, req)
    return {"success": True, "result": result.model_dump()}


@app.post("/api/editor/{project_id}/replace")
async def api_editor_replace(project_id: str, request: Request) -> dict:
    """Replace text in document."""
    body = await request.json()
    req = FindReplaceRequest(**body)
    result = _editor_service.replace_in_document(project_id, req)
    return {"success": True, "result": result.model_dump()}


@app.post("/api/editor/{project_id}/ai")
async def api_editor_ai(project_id: str, request: Request) -> dict:
    """Execute an AI action on selected text."""
    body = await request.json()
    req = AIActionRequest(**body)
    result = _editor_service.execute_ai_action(project_id, req)
    return {"success": result.success, "result": result.model_dump()}


@app.post("/api/editor/{project_id}/translate")
async def api_editor_translate(project_id: str, request: Request) -> dict:
    """Translate document or selection."""
    body = await request.json()
    req = TranslationRequest(**body)
    result = _editor_service.translate_document(project_id, req)
    return {"success": result.success, "result": result.model_dump()}


@app.get("/api/editor/{project_id}/headings")
async def api_editor_headings(project_id: str) -> dict:
    """Get document heading outline."""
    headings = _editor_service.get_heading_navigation(project_id)
    return {"success": True, "headings": headings, "count": len(headings)}


@app.get("/api/editor/{project_id}/autosave")
async def api_editor_autosave_check(project_id: str) -> dict:
    """Check if autosave recovery data exists."""
    content = _editor_service.recover_autosave(project_id)
    return {
        "success": True,
        "has_recovery": content is not None,
        "content": content or "",
    }


@app.post("/api/editor/{project_id}/autosave/clear")
async def api_editor_autosave_clear(project_id: str) -> dict:
    """Clear autosave recovery data."""
    _editor_service.clear_autosave(project_id)
    return {"success": True}


@app.get("/api/editor/supported-languages")
async def api_editor_languages() -> dict:
    """Get supported translation languages."""
    from editor.translation_engine import LANGUAGE_MAP
    languages = [{"code": code, "name": name} for code, name in sorted(LANGUAGE_MAP.items(), key=lambda x: x[1])]
    return {"success": True, "languages": languages, "count": len(languages)}


# ---------------------------------------------------------------------------
# SPA catch-all
# ---------------------------------------------------------------------------


@app.api_route("/{path:path}", methods=["GET"])
async def spa_catch_all(path: str):
    if (
        path.startswith("api")
        or path.startswith("dashboard")
        or path.startswith("static")
        or path.startswith("assets")
        or path.startswith("docs")
        or path.startswith("openapi")
        or path.startswith("redoc")
    ):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _spa_index()



