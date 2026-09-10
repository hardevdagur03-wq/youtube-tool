"""Utilities for parsing ISO 8601 duration strings and formatting durations."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_ISO_DURATION_RE = re.compile(
    r"^PT"
    r"(?:(\d+)H)?"
    r"(?:(\d+)M)?"
    r"(?:(\d+)S)?"
    r"$"
)

# Ensure at least one time component is present
_ISO_DURATION_HAS_VALUE = re.compile(r"PT(?:[0-9]+[HMS])+")


def parse_duration_to_seconds(duration: Any) -> int | None:
    """Parse an ISO 8601 duration string to total seconds.

    Expected format: ``PT[n]H[n]M[n]S``.

    Examples:

    - ``PT30S`` → 30
    - ``PT1M30S`` → 90
    - ``PT1H`` → 3600
    - ``PT1H30M15S`` → 5415

    Args:
        duration: The ISO 8601 duration string (e.g. ``PT12M35S``).

    Returns:
        Total seconds as an integer, or ``None`` if the input is
        ``None``, empty, or cannot be parsed.
    """
    if duration is None or not isinstance(duration, str) or not duration.strip():
        return None

    duration = duration.strip()
    if not _ISO_DURATION_HAS_VALUE.match(duration):
        logger.warning("Could not parse ISO 8601 duration: '%s'", duration)
        return None

    match = _ISO_DURATION_RE.match(duration)
    if not match:
        logger.warning("Could not parse ISO 8601 duration: '%s'", duration)
        return None

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: Any) -> str | None:
    """Format a total-seconds value into a human-readable duration string.

    Rules:

    - ``None`` → ``None``
    - 0 seconds → ``"0:00"``
    - < 3600 seconds → ``"M:SS"`` (e.g. ``12:35``)
    - ≥ 3600 seconds → ``"H:MM:SS"`` (e.g. ``1:30:15``)

    Args:
        seconds: Total seconds (int or ``None``).

    Returns:
        Formatted duration string, or ``None``.
    """
    if seconds is None or not isinstance(seconds, int):
        return None

    if seconds < 0:
        logger.warning("Negative seconds value: %d; coercing to 0", seconds)
        seconds = 0

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
