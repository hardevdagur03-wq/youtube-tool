from __future__ import annotations

import csv
import math
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
from typing import Any

from api.video_service import VideoService, VideoServiceError
from api.channel_service import ChannelService
from api.youtube_client import YouTubeClient
from export_engine.job_manager import JobManager
from export_engine.models import (
    ExportRequest,
    JobResult,
    JobStatus,
    ProgressStage,
)
from infrastructure.cache import cache_service
from infrastructure.logging import get_logger
from infrastructure.monitoring import metrics
from infrastructure.rate_limiter import quota_tracker
from services.url_validator import URLValidator
from config.settings import settings

BATCH_SIZE = 50
CSV_COLUMNS = [
    "video_id", "title", "upload_date", "views", "likes",
    "duration", "video_type", "video_url",
]
MAX_CONCURRENT_BATCHES = getattr(settings, "youtube_batch_size", 50) // 10
MAX_CONCURRENT_BATCHES = max(3, min(MAX_CONCURRENT_BATCHES, 10))


class ExportPipeline:
    """Orchestrates the full export pipeline with parallel batch fetching,
    connection reuse, streaming CSV writes, and cancellation support."""

    def __init__(
        self,
        job_manager: JobManager,
        channel_service: ChannelService | None = None,
        video_service: VideoService | None = None,
    ) -> None:
        self._job_manager = job_manager
        shared_client = YouTubeClient()
        self._channel_service = channel_service or ChannelService(client=shared_client)
        self._video_service = video_service or VideoService(client=shared_client)
        self._url_validator = URLValidator()
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_BATCHES,
            thread_name_prefix="yt-batch",
        )

    def run(self, job_id: str, request: ExportRequest) -> None:
        logger = get_logger("pipeline", job_id=job_id)
        metrics.record_export_start()
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        total_retries = 0

        try:
            self._job_manager.start_job(job_id)

            stage = ProgressStage.VALIDATE_URL
            if self._check_cancelled(job_id, logger):
                return
            logger.info("Stage: validate URL")
            self._job_manager.update_stage(job_id, stage, JobStatus.RUNNING, "Validating URL...")
            validation = self._url_validator.validate(request.channel_input)
            if not validation["valid"]:
                raise PipelineError(validation["error"], "invalid_url", "Check the URL and try again.")
            self._job_manager.update_stage(job_id, stage, JobStatus.COMPLETED, "URL validated")

            stage = ProgressStage.CHECK_CACHE
            if self._check_cancelled(job_id, logger):
                return
            cached_data = self._try_cache_lookup(job_id, request, logger)

            if cached_data:
                channel_id = cached_data["channel_id"]
                channel_title = cached_data["channel_title"]
                playlist_id = cached_data["playlist_id"]
                cache_hits += cached_data.get("cache_hits", 2)
            else:
                stage = ProgressStage.RESOLVE_CHANNEL
                if self._check_cancelled(job_id, logger):
                    return
                logger.info("Stage: resolve channel")
                self._job_manager.update_stage(job_id, stage, JobStatus.RUNNING, "Resolving channel...")
                resolved = self._resolve_channel(job_id, request.channel_input, logger)
                channel_id = resolved["channel_id"]
                channel_title = resolved["title"]
                cache_hits += 1 if cache_service.get_channel_by_id(channel_id) else 0
                self._job_manager.update_stage(
                    job_id, stage, JobStatus.COMPLETED,
                    detail=f"Found: {channel_title}",
                )

                stage = ProgressStage.FETCH_PLAYLIST
                if self._check_cancelled(job_id, logger):
                    return
                logger.info("Stage: fetch playlist")
                self._job_manager.update_stage(job_id, stage, JobStatus.RUNNING, "Fetching upload playlist...")
                playlist_id = self._get_playlist_id(job_id, channel_id, logger)
                self._job_manager.update_stage(
                    job_id, stage, JobStatus.COMPLETED,
                    detail=f"Playlist: {playlist_id}",
                )

            # -----------------------------------------------------------------------
            # Stage: Fetch Video IDs + Metadata (overlapped producer-consumer)
            # -----------------------------------------------------------------------
            csv_path = Path(self._job_manager.get_job(job_id).csv_path)
            csv_path.parent.mkdir(parents=True, exist_ok=True)

            stage_video_ids = ProgressStage.FETCH_VIDEO_IDS
            stage_metadata = ProgressStage.FETCH_METADATA

            if self._check_cancelled(job_id, logger):
                return
            logger.info("Stage: fetch video IDs (with overlapped metadata)")

            self._job_manager.update_stage(
                job_id, stage_video_ids, JobStatus.RUNNING,
                detail="Fetching video IDs...",
            )
            self._job_manager.update_stage(
                job_id, stage_metadata, JobStatus.RUNNING,
                detail="Waiting for video IDs...",
                total=0,
            )

            # Producer-consumer: paginator fills queue, metadata fetcher drains it
            id_queue: Queue[list[str]] = Queue(maxsize=20)
            stop_event = Event()

            def _paginate_video_ids() -> None:
                """Producer: paginate playlist and push batches into queue."""
                page_token: str | None = None
                page_count = 0
                total_ids = 0
                try:
                    while not stop_event.is_set():
                        result = self._video_service.get_playlist_items(
                            playlist_id, page_token=page_token,
                        )
                        page_count += 1
                        batch = result["video_ids"]
                        total_ids += len(batch)
                        page_token = result.get("next_page_token")

                        self._job_manager.update_stage(
                            job_id, stage_video_ids, JobStatus.RUNNING,
                            detail=f"Page {page_count}: {total_ids} videos",
                            current_page=page_count,
                            processed=total_ids,
                        )

                        id_queue.put(batch)

                        if not page_token:
                            break
                except Exception as exc:
                    logger.error("Pagination failed: %s", exc)
                    raise
                finally:
                    id_queue.put(None)  # sentinel

            paginator_thread = Thread(target=_paginate_video_ids, daemon=True)
            paginator_thread.start()

            # Metadata fetcher with parallel batch execution
            total_videos = 0
            api_calls_meta = 0
            records_written = 0
            total_batches = 0
            pending_futures: dict[Any, int] = {}
            video_id_buffer: list[str] = []
            seen_ids: set[str] = set()
            all_video_ids_collected = False
            processed_batches = 0
            paginator_exc: Exception | None = None

            def _fetch_metadata_batch(batch_ids: list[str]) -> tuple[int, list[dict]]:
                """Fetch a single batch of metadata. Runs in thread pool."""
                batch_start = time.time()
                try:
                    items = self._video_service.get_videos_batch(batch_ids)
                    metrics.record_api_call(time.time() - batch_start)
                    return len(batch_ids), items
                except VideoServiceError as exc:
                    metrics.record_api_error()
                    logger.warning("Batch fetch failed for %d IDs: %s", len(batch_ids), exc)
                    return len(batch_ids), []

            with open(csv_path, "w", encoding="utf-8", newline="", buffering=1024*1024) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                csvfile.flush()

                while not all_video_ids_collected or not id_queue.empty() or pending_futures:
                    # Drain queue and submit batches
                    try:
                        while True:
                            batch = id_queue.get_nowait()
                            if batch is None:
                                all_video_ids_collected = True
                                break
                            for vid in batch:
                                if vid not in seen_ids:
                                    seen_ids.add(vid)
                                    video_id_buffer.append(vid)
                            # Enforce limit
                            if request.limit > 0 and len(video_id_buffer) >= request.limit:
                                video_id_buffer = video_id_buffer[:request.limit]
                                all_video_ids_collected = True
                    except Empty:
                        pass

                    # Submit buffered IDs as batches to thread pool
                    while len(video_id_buffer) >= BATCH_SIZE:
                        batch_ids = video_id_buffer[:BATCH_SIZE]
                        video_id_buffer = video_id_buffer[BATCH_SIZE:]
                        future = self._executor.submit(_fetch_metadata_batch, batch_ids)
                        pending_futures[future] = len(batch_ids)
                        total_batches += 1

                    if all_video_ids_collected and video_id_buffer and len(video_id_buffer) > 0:
                        # Final partial batch
                        future = self._executor.submit(_fetch_metadata_batch, list(video_id_buffer))
                        pending_futures[future] = len(video_id_buffer)
                        total_batches += 1
                        video_id_buffer.clear()

                    # Process completed futures
                    if pending_futures:
                        done = [f for f in pending_futures.keys() if f.done()]
                        if not done and all_video_ids_collected:
                            try:
                                for future in as_completed(list(pending_futures.keys()), timeout=1.0):
                                    done.append(future)
                                    break
                            except Exception:
                                pass

                        for future in done:
                            try:
                                batch_size, items = future.result()
                                api_calls_meta += 1
                                quota_tracker.record_call(1)
                                for item in items:
                                    record = self._parse_video_item(item)
                                    if record is None:
                                        continue
                                    transformed = self._transform_record(record)
                                    if transformed is None:
                                        continue
                                    writer.writerow(transformed)
                                    records_written += 1
                            except Exception as exc:
                                logger.warning("Batch future failed: %s", exc)
                            pending_futures.pop(future, None)
                            processed_batches += 1

                        if all_video_ids_collected:
                            total_videos = len(seen_ids)
                            if request.limit > 0:
                                total_videos = min(total_videos, request.limit)
                            progress_pct = (records_written / total_videos) * 100 if total_videos > 0 else 0
                            self._job_manager.update_stage(
                                job_id, stage_metadata, JobStatus.RUNNING,
                                detail=f"{records_written}/{total_videos} records",
                                current_page=processed_batches,
                                total_pages=total_batches,
                                processed=records_written,
                                total=total_videos,
                                api_calls=api_calls_meta,
                                rows_written=records_written,
                                progress_pct=progress_pct,
                            )

                    if self._check_cancelled(job_id, logger):
                        stop_event.set()
                        return

                # Process remaining futures with throttled progress updates
                for future in as_completed(list(pending_futures.keys())):
                    try:
                        batch_size, items = future.result()
                        api_calls_meta += 1
                        quota_tracker.record_call(1)
                        for item in items:
                            record = self._parse_video_item(item)
                            if record is None:
                                continue
                            transformed = self._transform_record(record)
                            if transformed is None:
                                continue
                            writer.writerow(transformed)
                            records_written += 1
                    except Exception as exc:
                        logger.warning("Final batch future failed: %s", exc)
                    pending_futures.pop(future, None)
                    processed_batches += 1

                    total_videos = len(seen_ids)
                    if request.limit > 0:
                        total_videos = min(total_videos, request.limit)
                    progress_pct = (records_written / total_videos) * 100 if total_videos > 0 else 0
                    self._job_manager.update_stage(
                        job_id, stage_metadata, JobStatus.RUNNING,
                        detail=f"{records_written}/{total_videos} records",
                        current_page=processed_batches,
                        total_pages=total_batches,
                        processed=records_written,
                        total=total_videos,
                        api_calls=api_calls_meta,
                        rows_written=records_written,
                        progress_pct=progress_pct,
                    )

            paginator_thread.join(timeout=5)

            total_videos = len(seen_ids) if request.limit == 0 else min(len(seen_ids), request.limit)
            total_api_calls = total_batches + (total_batches if total_batches > 0 else 0)
            file_size = csv_path.stat().st_size if csv_path.exists() else 0

            self._job_manager.update_stage(
                job_id, stage_video_ids, JobStatus.COMPLETED,
                detail=f"{total_videos} videos found",
                total=total_videos,
            )
            self._job_manager.update_stage(
                job_id, stage_metadata, JobStatus.COMPLETED,
                detail=f"{records_written} records written",
                processed=records_written,
                total=total_videos,
                api_calls=api_calls_meta,
                rows_written=records_written,
                progress_pct=100.0,
            )

            stage = ProgressStage.GENERATE_CSV
            self._job_manager.update_stage(job_id, stage, JobStatus.COMPLETED, "CSV generated")

            elapsed = time.time() - start_time
            result = JobResult(
                success=True,
                job_id=job_id,
                channel_title=channel_title,
                channel_id=channel_id,
                total_videos=records_written,
                total_discovered=total_videos,
                total_api_calls=total_api_calls,
                file_size_bytes=file_size,
                elapsed_seconds=round(elapsed, 1),
                csv_path=str(csv_path),
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                total_retries=total_retries,
            )
            self._job_manager.complete_job(job_id, result)
            metrics.record_export_complete(elapsed, records_written, file_size)

            logger.info(
                "Pipeline complete: channel=%s, exported=%d, api_calls=%d, "
                "elapsed=%.1fs, concurrent_batches=%d, cache_hits=%d",
                channel_id, records_written, total_api_calls, elapsed,
                MAX_CONCURRENT_BATCHES, cache_hits,
            )

        except PipelineError as exc:
            metrics.record_export_failed()
            metrics.record_error(exc.error_type)
            logger.error("Pipeline failed: %s [%s]", exc, exc.error_type)
            self._job_manager.fail_job(job_id, str(exc), exc.error_type, exc.action)
            self._job_manager.update_stage(
                job_id, ProgressStage.ERROR, JobStatus.FAILED,
                error=str(exc),
            )

        except Exception as exc:
            metrics.record_export_failed()
            metrics.record_error("unexpected")
            logger.exception("Pipeline unexpected failure: %s", exc)
            self._job_manager.fail_job(
                job_id,
                f"An unexpected error occurred: {exc}",
                "unexpected",
                "Please try again or contact support.",
            )
            self._job_manager.update_stage(
                job_id, ProgressStage.ERROR, JobStatus.FAILED,
                error=str(exc),
            )

    def _check_cancelled(self, job_id: str, logger: Any) -> bool:
        if self._job_manager.is_cancelled(job_id):
            logger.info("Job %s was cancelled", job_id)
            metrics.record_export_cancelled()
            return True
        return False

    def _try_cache_lookup(self, job_id: str, request: ExportRequest, logger: Any) -> dict | None:
        channel_input = request.channel_input.strip().lower()
        clean_handle = channel_input.lstrip("@").lower()
        cached = cache_service.get_channel_by_handle(clean_handle)
        if cached is None:
            cached = cache_service.get_channel_by_handle(channel_input)
        if cached is not None:
            logger.info("Cache hit for channel handle: %s", channel_input)
            channel_id = cached.get("channel_id", "")
            channel_title = cached.get("title", "Unknown")
            playlist_id = cache_service.get_playlist_id(channel_id)
            if playlist_id:
                logger.info("Cache hit for playlist: %s", playlist_id)
                self._job_manager.update_stage(
                    job_id, ProgressStage.CHECK_CACHE, JobStatus.COMPLETED,
                    detail="Cache hit",
                )
                self._job_manager.update_stage(
                    job_id, ProgressStage.RESOLVE_CHANNEL, JobStatus.COMPLETED,
                    detail=f"Found (cached): {channel_title}",
                )
                self._job_manager.update_stage(
                    job_id, ProgressStage.FETCH_PLAYLIST, JobStatus.COMPLETED,
                    detail=f"Playlist (cached): {playlist_id}",
                )
                return {
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                    "playlist_id": playlist_id,
                    "cache_hits": 2,
                }
        self._job_manager.update_stage(
            job_id, ProgressStage.CHECK_CACHE, JobStatus.COMPLETED,
            detail="Cache miss",
        )
        return None

    def _resolve_channel(self, job_id: str, channel_input: str, logger: Any) -> dict:
        from services.channel_resolver import ChannelResolver
        resolver = ChannelResolver(channel_service=self._channel_service)
        try:
            resolved = resolver.resolve(channel_input)
        except Exception as exc:
            raise PipelineError(
                f"Channel not found: {exc}",
                "channel_not_found",
                "Check the channel URL or handle and try again.",
            ) from exc
        cache_service.set_channel_by_handle(channel_input.strip().lower(), {
            "channel_id": resolved["channel_id"],
            "title": resolved["title"],
        })
        cache_service.set_channel_by_id(resolved["channel_id"], resolved)
        return resolved

    def _get_playlist_id(self, job_id: str, channel_id: str, logger: Any) -> str:
        cached = cache_service.get_playlist_id(channel_id)
        if cached:
            logger.info("Cache hit for playlist ID: %s", cached)
            return cached
        try:
            playlist_id = self._video_service.get_uploads_playlist_id(channel_id)
            cache_service.set_playlist_id(channel_id, playlist_id)
            return playlist_id
        except Exception as exc:
            raise PipelineError(
                f"Failed to get upload playlist: {exc}",
                "playlist_error",
                "The channel may not have public uploads.",
            ) from exc

    def _parse_video_item(self, item: dict) -> dict | None:
        try:
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
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

    def _transform_record(self, record: dict) -> dict | None:
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
