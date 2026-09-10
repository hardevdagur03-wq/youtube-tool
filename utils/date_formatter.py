"""Utility for formatting dates into human-readable strings."""

from datetime import datetime, timezone
from typing import Any


def format_date(iso_date: Any) -> dict[str, str | None]:
    """Format an ISO 8601 date string into multiple representations.

    Args:
        iso_date: ISO 8601 date string (e.g. ``2024-03-18T12:30:11Z``).

    Returns:
        Dict with keys:
            - ``iso``: Original ISO string.
            - ``localized``: Formatted date (e.g. ``March 18, 2024``).
            - ``relative``: Relative time string (e.g. ``2 years ago``).
    """
    if not iso_date or not isinstance(iso_date, str):
        return {"iso": None, "localized": None, "relative": None}

    try:
        if iso_date.endswith("Z"):
            parsed = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        else:
            parsed = datetime.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return {"iso": iso_date, "localized": None, "relative": None}

    # Localized: March 18, 2024
    localized = parsed.strftime("%B %d, %Y")

    # Relative time
    now = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    delta = now - parsed
    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        relative = "just now"
    elif total_seconds < 60:
        relative = "just now"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        relative = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        relative = f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif total_seconds < 2592000:
        days = total_seconds // 86400
        relative = f"{days} day{'s' if days != 1 else ''} ago"
    elif total_seconds < 31536000:
        months = total_seconds // 2592000
        relative = f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = total_seconds // 31536000
        relative = f"{years} year{'s' if years != 1 else ''} ago"

    return {
        "iso": iso_date,
        "localized": localized,
        "relative": relative,
    }
