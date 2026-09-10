"""Utility for formatting large numbers into human-readable strings."""

from typing import Any


def format_count(value: Any) -> str:
    """Format a number into a compact human-readable string.

    Examples:
        1523 → ``"1.5K"``
        1580000 → ``"1.6M"``
        10500 → ``"10K"``

    Args:
        value: The number to format (int, float, or string).
            Non-numeric or ``None`` values return ``"0"``.

    Returns:
        Compact string representation.
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return "0"

    if n < 0:
        n = 0

    if n < 1000:
        return str(n)

    suffixes = [
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ]

    for threshold, suffix in suffixes:
        if n >= threshold:
            divided = n / threshold
            if divided < 10:
                return f"{divided:.1f}{suffix}"
            return f"{divided:.0f}{suffix}"

    return str(n)
