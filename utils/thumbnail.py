"""Utility for handling YouTube video thumbnails."""

from typing import Any

_THUMBNAIL_PRIORITY = [
    "maxres",
    "standard",
    "high",
    "medium",
    "default",
]


def extract_thumbnails(thumbnails_data: Any) -> dict[str, str | None]:
    """Extract all available thumbnail URLs from YouTube API response data.

    Args:
        thumbnails_data: The ``thumbnails`` dict from a YouTube API
            video resource (e.g. ``item["snippet"]["thumbnails"]``).

    Returns:
        Dict with keys ``default``, ``medium``, ``high``, ``standard``,
        ``maxres`` — each mapping to a URL string or ``None``.
    """
    result: dict[str, str | None] = {
        "default": None,
        "medium": None,
        "high": None,
        "standard": None,
        "maxres": None,
    }

    if not thumbnails_data or not isinstance(thumbnails_data, dict):
        return result

    for key in _THUMBNAIL_PRIORITY:
        entry = thumbnails_data.get(key)
        if entry and isinstance(entry, dict):
            url = entry.get("url")
            if url and isinstance(url, str):
                result[key] = url

    return result


def best_thumbnail(thumbnails: dict[str, str | None]) -> str | None:
    """Return the highest-quality available thumbnail URL.

    Args:
        thumbnails: Thumbnail dict from ``extract_thumbnails()``.

    Returns:
        URL string of the best available thumbnail, or ``None``.
    """
    for key in _THUMBNAIL_PRIORITY:
        url = thumbnails.get(key)
        if url:
            return url
    return None
