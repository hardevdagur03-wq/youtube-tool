"""Helper utilities for URL generation and video classification."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def generate_video_url(video_id: Any) -> str | None:
    """Generate a full YouTube watch URL from a video ID.

    Args:
        video_id: The YouTube video ID string.

    Returns:
        Full URL string, or ``None`` if the ID is missing or not a string.
    """
    if not video_id or not isinstance(video_id, str):
        return None
    return YOUTUBE_WATCH_URL.format(video_id=video_id)


def classify_video_type(duration_seconds: Any) -> str:
    """Classify a video as **Short** or **Video** based on duration.

    Rule:
        Duration ≤ 60 seconds → ``"Short"``
        Duration > 60 seconds → ``"Video"``

    Args:
        duration_seconds: Total duration in seconds (int or ``None``).

    Returns:
        ``"Short"`` or ``"Video"``.
    """
    if isinstance(duration_seconds, int) and duration_seconds <= 60:
        return "Short"
    return "Video"
