"""Business logic for transforming raw metadata into business-ready records."""

import logging
from copy import deepcopy
from typing import Any

from utils.duration import format_duration, parse_duration_to_seconds
from utils.helper import classify_video_type, generate_video_url

logger = logging.getLogger(__name__)


class DataTransformerError(Exception):
    """Base exception for data transformation errors."""
    pass


def _transform_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Transform a single raw metadata record into a business-ready record.

    The transformation is non-destructive: all original fields are preserved.
    New fields are added alongside the originals.

    Args:
        record: A raw metadata dict from Phase 4.

    Returns:
        A transformed dict, or ``None`` if the record has no ``video_id``.
    """
    video_id = record.get("video_id")
    if not video_id:
        logger.warning("Skipping record with missing video_id: %s", record)
        return None

    raw_duration = record.get("duration")
    duration_seconds = parse_duration_to_seconds(raw_duration)
    formatted = format_duration(duration_seconds)

    return {
        "video_id": video_id,
        "title": record.get("title"),
        "upload_date": record.get("upload_date"),
        "views": record.get("views"),
        "likes": record.get("likes"),
        "duration_iso": raw_duration,
        "duration": formatted,
        "duration_seconds": duration_seconds,
        "video_type": classify_video_type(duration_seconds),
        "video_url": generate_video_url(video_id),
    }


class DataTransformer:
    """Transforms raw video metadata records into business-ready records.

    Performs three transformations:

    1. **Duration**: ISO 8601 string → human-readable ``M:SS`` / ``H:MM:SS``
       and total seconds.
    2. **Classification**: Short (≤60s) or Video (>60s).
    3. **URL**: Generates ``https://www.youtube.com/watch?v=VIDEO_ID``.

    The transformation is **non-destructive** — original API values are
    preserved; new fields are added.
    """

    @staticmethod
    def transform(
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Transform a batch of raw metadata records.

        Args:
            records: List of raw metadata dicts from Phase 4.

        Returns:
            Dictionary with keys:
            - ``videos``: List of transformed records.
            - ``total_input``: Number of input records.
            - ``transformed``: Number of successfully transformed records.
            - ``skipped``: Number of records skipped (missing ``video_id``).
            - ``success``: ``True``.
        """
        if not records:
            logger.info("No records to transform; returning empty result.")
            return {
                "videos": [],
                "total_input": 0,
                "transformed": 0,
                "skipped": 0,
                "success": True,
            }

        logger.info("Transformation started: %d record(s)", len(records))

        transformed: list[dict[str, Any]] = []
        skipped = 0

        for i, record in enumerate(records):
            result = _transform_record(record)
            if result is not None:
                transformed.append(result)
            else:
                skipped += 1

        result_count = len(transformed)
        logger.info(
            "Transformation complete: %d transformed, %d skipped",
            result_count,
            skipped,
        )

        return {
            "videos": transformed,
            "total_input": len(records),
            "transformed": result_count,
            "skipped": skipped,
            "success": True,
        }
