"""Transcript Job Manager — asynchronous background execution for channel transcripts.

Manages channel transcript discovery, duration filtering, controlled concurrency,
progress tracking, and CSV generation for large channels.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import settings
from models.transcript_job import JobStatus, TranscriptJobProgress, TranscriptVideoItem
from services.duration_filter import evaluate_duration, parse_iso_duration

logger = logging.getLogger(__name__)


def _to_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    import functools
    return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


class TranscriptJobManager:
    """Manages long-running channel transcript background jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, TranscriptJobProgress] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> TranscriptJobProgress | None:
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(job_id)
            job = self._jobs.get(job_id)
            if task and not task.done():
                task.cancel()
                if job:
                    job.status = JobStatus.CANCELLED
                    job.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    async def start_channel_job(
        self,
        channel_handle: str,
        max_videos: int = 0,
        min_duration: int = 180,
        max_duration: int = 1800,
        force_refresh: bool = False,
        caption_concurrency: int = 5,
        whisper_concurrency: int = 1,
    ) -> TranscriptJobProgress:
        """Initialize and launch background transcript job for a YouTube channel."""
        clean_handle = channel_handle.strip().lstrip("@")
        job_id = uuid.uuid4().hex[:12]

        progress = TranscriptJobProgress(
            job_id=job_id,
            channel_handle=channel_handle,
            channel_id="",
            channel_title=clean_handle,
            status=JobStatus.QUEUED,
            total_discovered=0,
            eligible_videos=0,
            skipped_videos=0,
            remaining=0,
            videos=[],
        )
        self._jobs[job_id] = progress

        # Launch background task for discovery + processing
        task = asyncio.create_task(
            self._discover_and_run(
                progress=progress,
                clean_handle=clean_handle,
                max_videos=max_videos,
                min_duration=min_duration,
                max_duration=max_duration,
                force_refresh=force_refresh,
                caption_concurrency=caption_concurrency,
                whisper_concurrency=whisper_concurrency,
            )
        )
        self._tasks[job_id] = task

        logger.info(
            "Queued transcript job %s for channel '%s' (async background execution)",
            job_id, clean_handle,
        )
        return progress

    async def _discover_and_run(
        self,
        progress: TranscriptJobProgress,
        clean_handle: str,
        max_videos: int,
        min_duration: int,
        max_duration: int,
        force_refresh: bool,
        caption_concurrency: int,
        whisper_concurrency: int,
    ) -> None:
        from api.channel_service import ChannelService
        from api.video_service import VideoService

        progress.status = JobStatus.RUNNING
        progress.updated_at = datetime.now(timezone.utc).isoformat()

        try:
            channel_svc = ChannelService()
            video_svc = VideoService()

            channel_data = await _to_thread(channel_svc.resolve_handle, clean_handle)
            channel_id = channel_data["id"]
            channel_title = channel_data["snippet"]["title"]

            progress.channel_id = channel_id
            progress.channel_title = channel_title
            progress.updated_at = datetime.now(timezone.utc).isoformat()

            # Get uploads playlist ID
            playlist_id = await _to_thread(video_svc.get_uploads_playlist_id, channel_id)

            # Discover videos with pagination
            all_video_ids: list[str] = []
            next_page: str | None = None
            target_limit = max_videos if max_videos > 0 else 50000

            while len(all_video_ids) < target_limit:
                if progress.status == JobStatus.CANCELLED:
                    return
                page = await _to_thread(video_svc.get_playlist_items, playlist_id, next_page)
                vids = page.get("video_ids", [])
                for vid in vids:
                    if vid and vid not in all_video_ids:
                        all_video_ids.append(vid)
                        if len(all_video_ids) >= target_limit:
                            break
                next_page = page.get("next_page_token")
                if not next_page:
                    break

            progress.total_discovered = len(all_video_ids)
            progress.updated_at = datetime.now(timezone.utc).isoformat()

            # Batch metadata fetch (50 per batch)
            metadata_map: dict[str, dict] = {}
            for i in range(0, len(all_video_ids), 50):
                if progress.status == JobStatus.CANCELLED:
                    return
                batch = all_video_ids[i : i + 50]
                try:
                    items = await _to_thread(video_svc.get_videos_batch, batch)
                    for item in items:
                        vid = item.get("id")
                        if vid:
                            metadata_map[vid] = item
                except Exception as exc:
                    logger.warning("Failed to fetch metadata batch: %s", exc)

            eligible_items: list[TranscriptVideoItem] = []
            skipped_count = 0

            for vid in all_video_ids:
                item = metadata_map.get(vid, {})
                snippet = item.get("snippet", {})
                cd = item.get("contentDetails", {})
                title = snippet.get("title", "")
                published_at = snippet.get("publishedAt", "")
                duration_iso = cd.get("duration", "PT0S")
                duration_seconds = parse_iso_duration(duration_iso)
                live_status = snippet.get("liveBroadcastContent", "none")

                filter_res = evaluate_duration(
                    duration_seconds=duration_seconds,
                    live_status=live_status,
                    min_seconds=min_duration,
                    max_seconds=max_duration,
                )

                if filter_res.is_eligible:
                    eligible_items.append(
                        TranscriptVideoItem(
                            video_id=vid,
                            video_url=f"https://www.youtube.com/watch?v={vid}",
                            channel_id=channel_id,
                            channel_title=channel_title,
                            title=title,
                            published_at=published_at,
                            duration_seconds=filter_res.duration_seconds,
                            duration=filter_res.duration_formatted,
                            status="pending",
                        )
                    )
                else:
                    skipped_count += 1

            progress.eligible_videos = len(eligible_items)
            progress.skipped_videos = skipped_count
            progress.remaining = len(eligible_items)
            progress.videos = eligible_items
            progress.updated_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                "Job %s discovery complete: channel='%s', discovered=%d, eligible=%d",
                progress.job_id, channel_title, len(all_video_ids), len(eligible_items),
            )

            # Process eligible items
            await self._run_job(
                progress,
                force_refresh=force_refresh,
                caption_concurrency=caption_concurrency,
                whisper_concurrency=whisper_concurrency,
            )

        except Exception as exc:
            logger.exception("Job %s encountered error: %s", progress.job_id, exc)
            progress.status = JobStatus.FAILED
            progress.error = str(exc)
            progress.updated_at = datetime.now(timezone.utc).isoformat()

    async def _run_job(
        self,
        job: TranscriptJobProgress,
        force_refresh: bool = False,
        caption_concurrency: int = 5,
        whisper_concurrency: int = 1,
    ) -> None:
        """Worker executing transcript retrieval with caption-first -> whisper fallback."""
        from services.transcript_service import TranscriptService

        transcript_svc = TranscriptService()
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(timezone.utc).isoformat()

        caption_sem = asyncio.Semaphore(caption_concurrency)
        whisper_sem = asyncio.Semaphore(whisper_concurrency)

        async def _process_video(video_item: TranscriptVideoItem) -> None:
            video_id = video_item.video_id
            video_item.status = "processing"
            video_item.attempt_count += 1

            # Step 1: Attempt caption-first
            async with caption_sem:
                try:
                    res = await _to_thread(
                        transcript_svc.get_transcript,
                        video_id=video_id,
                        force_refresh=force_refresh,
                        allow_whisper=False,
                    )
                    if res.success and (res.plain_text or res.paragraph_text):
                        video_item.status = "success"
                        video_item.transcript = res.plain_text or res.paragraph_text or ""
                        video_item.raw_transcript = getattr(res, "raw_transcript", "") or video_item.transcript
                        video_item.language = res.language or "en"
                        video_item.source = "youtube"
                        video_item.method = "caption"
                        video_item.completed_at = datetime.now(timezone.utc).isoformat()
                        return
                except Exception as exc:
                    logger.debug("Caption fetch exception for %s: %s", video_id, exc)

            # Step 2: Speech-to-Text Fallback via Whisper
            if settings.whisper_enabled:
                async with whisper_sem:
                    try:
                        whisper_res = await _to_thread(
                            transcript_svc.get_transcript,
                            video_id=video_id,
                            force_refresh=force_refresh,
                            allow_whisper=True,
                        )
                        if whisper_res.success and (whisper_res.plain_text or whisper_res.paragraph_text):
                            video_item.status = "success"
                            video_item.transcript = whisper_res.plain_text or whisper_res.paragraph_text or ""
                            video_item.raw_transcript = getattr(whisper_res, "raw_transcript", "") or video_item.transcript
                            video_item.language = whisper_res.language or "Hinglish"
                            video_item.source = "whisper"
                            video_item.method = "speech_to_text"
                            video_item.completed_at = datetime.now(timezone.utc).isoformat()
                            return
                        else:
                            video_item.status = "failed"
                            video_item.error_code = whisper_res.error_code or "STT_FAILED"
                            video_item.error_message = whisper_res.error or "Speech-to-text transcription failed."
                            video_item.completed_at = datetime.now(timezone.utc).isoformat()
                            return
                    except Exception as exc:
                        logger.warning("Whisper exception for %s: %s", video_id, exc)
                        video_item.status = "failed"
                        video_item.error_code = "STT_FAILED"
                        video_item.error_message = f"Speech-to-text failed: {exc}"
                        video_item.completed_at = datetime.now(timezone.utc).isoformat()
                        return

            # No captions and whisper disabled/failed
            video_item.status = "failed"
            video_item.error_code = "NO_CAPTIONS"
            video_item.error_message = "No transcript/caption track is available for this video."
            video_item.completed_at = datetime.now(timezone.utc).isoformat()

        # Execute all items with progress updating
        try:
            for item in job.videos:
                if job.status == JobStatus.CANCELLED:
                    break

                await _process_video(item)

                # Update progress counters
                job.processed += 1
                job.remaining = max(0, job.eligible_videos - job.processed)
                job.progress_percent = int((job.processed / max(1, job.eligible_videos)) * 100)

                if item.status == "success":
                    job.successful += 1
                    if item.method == "caption":
                        job.caption_count += 1
                    elif item.method == "speech_to_text":
                        job.whisper_count += 1
                elif item.error_code in ("NO_CAPTIONS", "CAPTIONS_DISABLED"):
                    job.no_captions += 1
                else:
                    job.failed += 1

                job.updated_at = datetime.now(timezone.utc).isoformat()

            if job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "Job %s completed: %d/%d success (captions=%d, whisper=%d, failed=%d)",
                    job.job_id, job.successful, job.eligible_videos,
                    job.caption_count, job.whisper_count, job.failed,
                )
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            logger.exception("Job %s crashed: %s", job.job_id, exc)
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.updated_at = datetime.now(timezone.utc).isoformat()

    def generate_csv(self, job_id: str) -> str:
        """Generate 15-column compliant CSV for the job."""
        job = self.get_job(job_id)
        if not job:
            return ""

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        headers = [
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
        writer.writerow(headers)

        for v in job.videos:
            writer.writerow([
                v.video_id,
                v.video_url,
                v.channel_id,
                v.channel_title,
                v.title,
                v.published_at,
                v.duration_seconds,
                v.duration,
                v.language or "",
                v.status,
                v.transcript,
                v.source or "",
                v.method or "",
                v.error_code or "",
                v.error_message or "",
            ])

        return output.getvalue()


# Global Singleton
transcript_job_manager = TranscriptJobManager()
