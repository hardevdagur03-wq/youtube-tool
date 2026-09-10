"""Business logic for fetching metadata for a list of video IDs.

Supports streaming mode: yields records as they arrive from the API,
enabling incremental CSV writing for large datasets with low memory.
"""

import logging
from collections import OrderedDict
from typing import Any, Iterator

from api.video_service import VideoService, VideoServiceError

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class VideoMetadataError(Exception):
    """Base exception for video metadata errors."""
    pass


def _parse_video_item(item: dict[str, Any]) -> dict[str, Any]:
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    content_details = item.get("contentDetails", {})

    raw_views = statistics.get("viewCount")
    raw_likes = statistics.get("likeCount")

    return {
        "video_id": item.get("id", ""),
        "title": snippet.get("title"),
        "upload_date": snippet.get("publishedAt"),
        "views": int(raw_views) if raw_views is not None else 0,
        "likes": int(raw_likes) if raw_likes is not None else 0,
        "duration": content_details.get("duration"),
    }


def _deduplicate_preserve_order(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for vid in ids:
        if vid not in seen:
            seen.add(vid)
            result.append(vid)
    return result


def metadata_stream(
    video_ids: list[str],
    video_service: VideoService | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream metadata records from the API one batch at a time.

    Yields parsed records as each batch arrives.  A single failed batch
    is logged but does NOT terminate the stream — the error is collected
    and reported at the end.

    Args:
        video_ids: List of YouTube video IDs.
        video_service: Optional injected VideoService.

    Yields:
        Dict per video: ``video_id``, ``title``, ``upload_date``,
        ``views``, ``likes``, ``duration``.
    """
    if not video_ids:
        return

    service = video_service or VideoService()
    original_count = len(video_ids)
    deduped = _deduplicate_preserve_order(video_ids)
    dup_count = original_count - len(deduped)
    if dup_count:
        logger.warning("Removed %d duplicate ID(s)", dup_count)

    batches = [deduped[i : i + BATCH_SIZE] for i in range(0, len(deduped), BATCH_SIZE)]
    logger.info("Metadata stream: %d video(s) in %d batch(es)", len(deduped), len(batches))

    batch_errors = 0
    for batch_num, batch in enumerate(batches, start=1):
        try:
            items = service.get_videos_batch(batch)
        except VideoServiceError as exc:
            logger.error("Batch %d/%d failed: %s", batch_num, len(batches), exc)
            batch_errors += 1
            continue

        for item in items:
            yield _parse_video_item(item)

        logger.info(
            "Batch %d/%d: %d records streamed",
            batch_num,
            len(batches),
            len(items),
        )

    if batch_errors:
        logger.warning(
            "Metadata stream completed with %d failed batch(es) out of %d",
            batch_errors,
            len(batches),
        )


class VideoMetadataService:
    """Orchestrates metadata retrieval for a collection of video IDs.

    Supports both batch (list-based) and streaming (iterator-based) retrieval.
    The streaming variant is memory-efficient for large channels.
    """

    def __init__(self, video_service: VideoService | None = None) -> None:
        self._video_service = video_service or VideoService()

    def fetch_metadata(self, video_ids: list[str]) -> dict[str, Any]:
        """Fetch metadata for all provided video IDs (batch mode, in-memory).

        For large datasets, prefer ``metadata_stream()`` which yields records
        as they arrive and uses constant memory.

        Args:
            video_ids: List of YouTube video IDs.

        Returns:
            Dictionary with keys: ``videos``, ``total_input``,
            ``total_retrieved``, ``total_requests``, ``deduplicated``,
            ``success``.
        """
        if not video_ids:
            logger.info("No video IDs provided; returning empty result.")
            return {
                "videos": [],
                "total_input": 0,
                "total_retrieved": 0,
                "total_requests": 0,
                "deduplicated": 0,
                "success": True,
            }

        logger.info("Metadata fetch started: %d video IDs received", len(video_ids))

        original_count = len(video_ids)
        deduped = _deduplicate_preserve_order(video_ids)
        dup_count = original_count - len(deduped)
        if dup_count:
            logger.warning("Removed %d duplicate ID(s)", dup_count)

        batches = [
            deduped[i : i + BATCH_SIZE] for i in range(0, len(deduped), BATCH_SIZE)
        ]
        logger.info("Split into %d batch(es) of max %d", len(batches), BATCH_SIZE)

        all_records: list[dict[str, Any]] = []
        total_requests = 0
        input_order_index: dict[str, int] = {
            vid: idx for idx, vid in enumerate(deduped)
        }

        for batch_num, batch in enumerate(batches, start=1):
            try:
                items = self._video_service.get_videos_batch(batch)
            except VideoServiceError as exc:
                logger.error("Batch %d/%d failed: %s", batch_num, len(batches), exc)
                raise VideoMetadataError(str(exc)) from exc

            total_requests += 1

            for item in items:
                record = _parse_video_item(item)
                all_records.append(record)

            logger.info(
                "Batch %d/%d: %d records parsed",
                batch_num,
                len(batches),
                len(items),
            )

        all_records.sort(key=lambda r: input_order_index.get(r["video_id"], 999999))

        retrieved = len(all_records)
        logger.info(
            "Metadata fetch complete: %d/%d videos retrieved in %d request(s)",
            retrieved,
            len(deduped),
            total_requests,
        )

        return {
            "videos": all_records,
            "total_input": len(deduped),
            "total_retrieved": retrieved,
            "total_requests": total_requests,
            "deduplicated": dup_count,
            "success": True,
        }
