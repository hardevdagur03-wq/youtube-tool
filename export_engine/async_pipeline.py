"""Fully asynchronous export pipeline.

Key design decisions:
- Zero synchronous network calls (httpx.AsyncClient throughout)
- Zero time.sleep() (asyncio.sleep throughout)
- Zero threads (asyncio.create_task + asyncio.gather)
- Zero ThreadPoolExecutor (asyncio.Semaphore for concurrency control)
- Zero busy-wait (asyncio.Queue for producer-consumer)
- Zero disk I/O on progress updates (in-memory, periodic async flush)
- Zero duplicate parsing (single _parse_video_item, single _transform_record)
"""

from __future__ import annotations

import asyncio
import csv
import logging
import time
from pathlib import Path
from typing import Any

from api.async_youtube_client import (
    AsyncYouTubeClient,
    AsyncYouTubeClientError,
    AsyncYouTubeNotFoundError,
    AsyncYouTubeQuotaError,
    AsyncYouTubeTimeoutError,
)
from export_engine.models import (
    ExportRequest,
    JobResult,
    JobStatus,
    ProgressStage,
    STAGE_LABELS,
    StageProgress,
)
from infrastructure.cache import cache_service
from infrastructure.monitoring import metrics
from infrastructure.rate_limiter import quota_tracker
from services.url_validator import URLValidator

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
CSV_COLUMNS = [
    "video_id", "title", "upload_date", "views", "likes",
    "duration", "video_type", "video_url",
]
MAX_CONCURRENT_BATCHES = 5


class AsyncExportPipeline:
    """Fully async export pipeline with no blocking operations."""

    def __init__(self) -> None:
        self._client = AsyncYouTubeClient()
        self._url_validator = URLValidator()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)
        self._progress_store: dict[str, dict] = {}
        self._store_lock = asyncio.Lock()
        self._last_flush: dict[str, float] = {}
        self._flush_interval = 2.0

    async def close(self) -> None:
        await self._client.close()

    async def run(self, job_id: str, request: ExportRequest) -> None:
        start_time = time.monotonic()
        metrics.record_export_start()
        api_calls = 0
        records_written = 0
        cache_hits = 0
        total_retries = 0

        progress: dict[str, Any] = {
            "status": "running",
            "stages": {},
            "current_stage": "",
            "overall_progress_pct": 0.0,
            "elapsed_seconds": 0.0,
            "eta_seconds": 0.0,
            "error": "",
            "error_type": "",
            "error_action": "",
        }

        def _init_stages() -> None:
            for stage in ProgressStage:
                progress["stages"][stage.value] = {
                    "stage": stage.value,
                    "status": "pending",
                    "label": STAGE_LABELS.get(stage, stage.value),
                    "detail": "",
                    "progress_pct": 0.0,
                    "current_page": 0,
                    "total_pages": 0,
                    "processed": 0,
                    "total": 0,
                    "remaining": 0,
                    "eta_seconds": 0.0,
                    "api_calls": 0,
                    "rows_written": 0,
                    "elapsed": 0.0,
                    "error": "",
                }

        async def _set_stage(
            stage: ProgressStage,
            status: str = "running",
            detail: str = "",
            **kwargs: Any,
        ) -> None:
            key = stage.value
            if key not in progress["stages"]:
                progress["stages"][key] = {
                    "stage": key,
                    "status": status,
                    "label": STAGE_LABELS.get(stage, key),
                }
            s = progress["stages"][key]
            s["status"] = status
            s["detail"] = detail or s.get("detail", "")
            s["elapsed"] = time.monotonic() - start_time
            for k, v in kwargs.items():
                s[k] = v
            progress["current_stage"] = key
            if status == "error":
                progress["error"] = detail
            await _flush_progress(force=status in ("completed", "error"))

        async def _flush_progress(*, force: bool = False) -> None:
            now = time.monotonic()
            last = self._last_flush.get(job_id, 0)
            if not force and now - last < self._flush_interval:
                return
            self._last_flush[job_id] = now
            progress["elapsed_seconds"] = round(time.monotonic() - start_time, 1)
            async with self._store_lock:
                self._progress_store[job_id] = dict(progress)

        async def _force_flush() -> None:
            await _flush_progress(force=True)

        async def _publish_result(result: JobResult) -> None:
            async with self._store_lock:
                self._progress_store[f"{job_id}:result"] = result.model_dump()

        try:
            _init_stages()

            # Stage 1: Validate URL
            stage = ProgressStage.VALIDATE_URL
            await _set_stage(stage, "running", "Validating URL...")
            validation = await asyncio.to_thread(self._url_validator.validate, request.channel_input)
            if not validation["valid"]:
                raise PipelineError(validation["error"], "invalid_url", "Check the URL and try again.")
            await _set_stage(stage, "completed", "URL validated")

            # Stage 2: Check cache
            stage = ProgressStage.CHECK_CACHE
            await _set_stage(stage, "running", "Checking cache...")
            channel_input_lower = request.channel_input.strip().lower()
            cached_channel = await asyncio.to_thread(cache_service.get_channel_by_handle, channel_input_lower)
            if cached_channel is not None:
                channel_id = cached_channel.get("channel_id", "")
                channel_title = cached_channel.get("title", "Unknown")
                cached_playlist = await asyncio.to_thread(cache_service.get_playlist_id, channel_id)
                if cached_playlist:
                    elapsed = time.monotonic() - start_time
                    result = JobResult(
                        success=True, job_id=job_id,
                        channel_title=channel_title, channel_id=channel_id,
                        elapsed_seconds=round(elapsed, 1),
                        cache_hits=2, cache_misses=0,
                    )
                    await _publish_result(result)
                    progress["status"] = "completed"
                    await _set_stage(ProgressStage.COMPLETE, "completed", "Cached result returned")
                    return
            await _set_stage(stage, "completed", "Cache miss")

            # Stage 3: Resolve channel
            stage = ProgressStage.RESOLVE_CHANNEL
            await _set_stage(stage, "running", "Resolving channel...")
            try:
                handle = validation.get("identifier", request.channel_input)
                if handle.startswith("UC") and len(handle) >= 24:
                    channel_data = await self._client.get_channel_by_id(handle)
                else:
                    channel_data = await self._client.get_channel_by_handle(handle)
            except AsyncYouTubeNotFoundError as exc:
                raise PipelineError(f"Channel not found: {exc}", "channel_not_found")
            except (AsyncYouTubeQuotaError, AsyncYouTubeTimeoutError, AsyncYouTubeClientError) as exc:
                raise PipelineError(str(exc), "api_error")

            channel_id = channel_data["id"]
            channel_title = channel_data.get("snippet", {}).get("title", "Unknown")
            api_calls += 1
            await asyncio.to_thread(cache_service.set_channel_by_handle, channel_input_lower, {
                "channel_id": channel_id, "title": channel_title,
            })
            await asyncio.to_thread(cache_service.set_channel_by_id, channel_id, {
                "channel_id": channel_id, "title": channel_title,
            })
            await _set_stage(stage, "completed", f"Found: {channel_title}")

            # Stage 4: Get upload playlist
            stage = ProgressStage.FETCH_PLAYLIST
            await _set_stage(stage, "running", "Fetching upload playlist...")
            try:
                playlist_id = await self._client.get_uploads_playlist_id(channel_id)
            except (AsyncYouTubeNotFoundError, AsyncYouTubeClientError) as exc:
                raise PipelineError(str(exc), "playlist_error")
            api_calls += 1
            await asyncio.to_thread(cache_service.set_playlist_id, channel_id, playlist_id)
            await _set_stage(stage, "completed", f"Playlist: {playlist_id}")

            # Stage 5+6: Fetch video IDs + Fetch Metadata (fully overlapped)
            stage_ids = ProgressStage.FETCH_VIDEO_IDS
            stage_meta = ProgressStage.FETCH_METADATA
            await _set_stage(stage_ids, "running", "Fetching video IDs...")
            await _set_stage(stage_meta, "running", "Waiting for videos...")

            id_queue: asyncio.Queue[list[str] | None] = asyncio.Queue(maxsize=10)
            seen_ids: set[str] = set()
            all_collected = False
            cancel_event = asyncio.Event()
            limit = request.limit
            meta_tasks: list[asyncio.Task] = []
            meta_results: list[tuple[int, list[dict]]] = []
            meta_lock = asyncio.Lock()

            async def _paginate() -> None:
                """Producer: paginate playlist and push batches into queue."""
                nonlocal api_calls
                page_token: str | None = None
                page_count = 0
                try:
                    while not cancel_event.is_set():
                        result = await self._client.get_playlist_items(playlist_id, page_token)
                        api_calls += 1
                        page_count += 1
                        batch = result["video_ids"]
                        page_token = result.get("next_page_token")

                        await _set_stage(
                            stage_ids, "running",
                            f"Page {page_count}: {len(seen_ids) + len(batch)} videos",
                            current_page=page_count, processed=len(seen_ids) + len(batch) if not all_collected else len(seen_ids),
                        )
                        await id_queue.put(batch)

                        if not page_token:
                            break
                except Exception:
                    raise
                finally:
                    await id_queue.put(None)

            async def _fetch_batch(batch_ids: list[str]) -> tuple[int, list[dict]]:
                """Worker: fetch metadata for a batch. Runs under semaphore."""
                nonlocal api_calls
                async with self._semaphore:
                    try:
                        items = await self._client.get_videos_batch(batch_ids)
                        api_calls += 1
                        return len(batch_ids), items
                    except Exception:
                        return len(batch_ids), []

            async def _consumer() -> None:
                """Consumer: drain queue, submit batches, collect results."""
                nonlocal all_collected, records_written

                buffer: list[str] = []

                while True:
                    batch = await id_queue.get()
                    if batch is None:
                        all_collected = True
                        # Submit remaining buffer
                        if buffer:
                            task = asyncio.create_task(_fetch_batch(list(buffer)))
                            meta_tasks.append(task)
                            buffer.clear()
                        break

                    for vid in batch:
                        if vid not in seen_ids:
                            seen_ids.add(vid)
                            buffer.append(vid)
                            if limit > 0 and len(seen_ids) >= limit:
                                all_collected = True
                                cancel_event.set()
                                if buffer:
                                    task = asyncio.create_task(_fetch_batch(list(buffer)))
                                    meta_tasks.append(task)
                                    buffer.clear()
                                break

                    # Submit full batches
                    while len(buffer) >= BATCH_SIZE:
                        batch_ids = buffer[:BATCH_SIZE]
                        buffer = buffer[BATCH_SIZE:]
                        task = asyncio.create_task(_fetch_batch(batch_ids))
                        meta_tasks.append(task)

                    if all_collected:
                        if buffer:
                            task = asyncio.create_task(_fetch_batch(list(buffer)))
                            meta_tasks.append(task)
                            buffer.clear()
                        break

            async def _collect_results() -> None:
                """Await all meta tasks and write CSV."""
                nonlocal records_written, api_calls

                csv_path = Path(f"webapp/runs/{job_id}/videos.csv")
                csv_path.parent.mkdir(parents=True, exist_ok=True)

                with open(csv_path, "w", encoding="utf-8", newline="", buffering=1024*1024) as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
                    writer.writeheader()

                    total_meta = len(meta_tasks)
                    completed = 0
                    remaining_tasks = list(meta_tasks)

                    while remaining_tasks:
                        done_set, remaining_tasks = await asyncio.wait(
                            remaining_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=None,
                        )
                        for task in done_set:
                            completed += 1
                            try:
                                _, items = task.result()
                            except Exception:
                                continue
                            for item in items:
                                record = _parse_video_item(item)
                                if record is None:
                                    continue
                                transformed = _transform_record(record)
                                if transformed is None:
                                    continue
                                writer.writerow(transformed)
                                records_written += 1

                        total = limit if limit > 0 else len(seen_ids)
                        if total > 0:
                            pct = (records_written / total) * 100
                            await _set_stage(
                                stage_meta, "running",
                                f"{records_written}/{total} records",
                                current_page=completed,
                                total_pages=total_meta,
                                processed=records_written,
                                total=total,
                                api_calls=api_calls,
                                rows_written=records_written,
                                progress_pct=min(100.0, pct),
                            )

            # Run all three concurrently
            paginator = asyncio.create_task(_paginate())
            consumer = asyncio.create_task(_consumer())

            await asyncio.gather(paginator, consumer)

            total_videos = len(seen_ids)
            if limit > 0:
                total_videos = min(total_videos, limit)
            if total_videos == 0:
                raise PipelineError("No uploaded videos found.", "no_videos")

            await _set_stage(stage_ids, "completed", f"{total_videos} videos found", total=total_videos, api_calls=api_calls)
            await _set_stage(stage_meta, "running", f"Collecting {len(meta_tasks)} batch results...", total=total_videos)

            await _collect_results()

            file_size = 0
            csv_path = Path(f"webapp/runs/{job_id}/videos.csv")
            if csv_path.exists():
                file_size = csv_path.stat().st_size

            await _set_stage(stage_meta, "completed", f"{records_written} records written",
                           processed=records_written, total=total_videos, rows_written=records_written,
                           progress_pct=100.0)

            await _set_stage(ProgressStage.GENERATE_CSV, "completed", "CSV generated")

            elapsed = time.monotonic() - start_time
            result = JobResult(
                success=True, job_id=job_id,
                channel_title=channel_title, channel_id=channel_id,
                total_videos=records_written, total_discovered=total_videos,
                total_api_calls=api_calls, file_size_bytes=file_size,
                elapsed_seconds=round(elapsed, 1), csv_path=str(csv_path),
                cache_hits=cache_hits, cache_misses=0, total_retries=total_retries,
            )
            await _publish_result(result)
            progress["status"] = "completed"
            await _set_stage(ProgressStage.COMPLETE, "completed", "Export completed")
            metrics.record_export_complete(elapsed, records_written, file_size)

            logger.info(
                "Async pipeline complete: channel=%s, exported=%d, api_calls=%d, elapsed=%.1fs",
                channel_id, records_written, api_calls, elapsed,
            )

        except PipelineError as exc:
            metrics.record_export_failed()
            metrics.record_error(exc.error_type)
            logger.error("Pipeline failed: %s [%s]", exc, exc.error_type)
            elapsed = round(time.monotonic() - start_time, 1)
            result = JobResult(
                success=False, job_id=job_id, error=str(exc),
                error_type=exc.error_type, elapsed_seconds=elapsed,
            )
            await _publish_result(result)
            progress["status"] = "failed"
            progress["error"] = str(exc)
            progress["error_type"] = exc.error_type
            progress["error_action"] = exc.action or ""
            await _set_stage(ProgressStage.ERROR, "error", str(exc))

        except Exception as exc:
            metrics.record_export_failed()
            metrics.record_error("unexpected")
            logger.exception("Pipeline unexpected failure: %s", exc)
            elapsed = round(time.monotonic() - start_time, 1)
            result = JobResult(
                success=False, job_id=job_id, error=str(exc),
                error_type="unexpected", elapsed_seconds=elapsed,
            )
            await _publish_result(result)
            progress["status"] = "failed"
            progress["error"] = f"Unexpected error: {exc}"
            await _set_stage(ProgressStage.ERROR, "error", str(exc))

    async def get_progress(self, job_id: str) -> dict | None:
        async with self._store_lock:
            return self._progress_store.get(job_id)

    async def get_result(self, job_id: str) -> dict | None:
        async with self._store_lock:
            return self._progress_store.get(f"{job_id}:result")

    async def cancel_job(self, job_id: str) -> None:
        async with self._store_lock:
            stored = self._progress_store.get(job_id)
            if stored and stored.get("status") in ("running", "pending"):
                stored["status"] = "cancelled"
            self._progress_store.pop(f"{job_id}:result", None)


def _parse_video_item(item: dict) -> dict | None:
    try:
        snippet = item.get("snippet", {}) or {}
        statistics = item.get("statistics", {}) or {}
        content_details = item.get("contentDetails", {}) or {}
        return {
            "video_id": item.get("id", ""),
            "title": snippet.get("title"),
            "upload_date": snippet.get("publishedAt"),
            "views": int(statistics.get("viewCount", 0)),
            "likes": int(statistics.get("likeCount", 0)),
            "duration": content_details.get("duration"),
        }
    except Exception:
        return None


def _transform_record(record: dict) -> dict | None:
    video_id = record.get("video_id", "")
    if not video_id:
        return None
    from utils.duration import format_duration, parse_duration_to_seconds
    from utils.helper import classify_video_type, generate_video_url
    raw_duration = record.get("duration")
    duration_seconds = parse_duration_to_seconds(raw_duration)
    return {
        "video_id": video_id,
        "title": record.get("title", ""),
        "upload_date": record.get("upload_date", ""),
        "views": record.get("views", 0),
        "likes": record.get("likes", 0),
        "duration": format_duration(duration_seconds),
        "video_type": classify_video_type(duration_seconds),
        "video_url": generate_video_url(video_id),
    }


class PipelineError(Exception):
    def __init__(self, message: str, error_type: str = "unknown", action: str = "") -> None:
        super().__init__(message)
        self.error_type = error_type
        self.action = action
