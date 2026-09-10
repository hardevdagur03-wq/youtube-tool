"""Read time estimation for transcript text."""

_AVERAGE_WPM = 200


def estimate_read_time(word_count: int, words_per_minute: int = _AVERAGE_WPM) -> str:
    """Estimate reading time from word count.

    Args:
        word_count: Number of words in the transcript.
        words_per_minute: Reading speed (default 200 WPM).

    Returns:
        Human-readable duration like "5 min" or "< 1 min".
    """
    if word_count <= 0:
        return "< 1 min"

    minutes_raw = word_count / words_per_minute

    if minutes_raw < 1:
        return "< 1 min"

    minutes = round(minutes_raw)

    if minutes == 1:
        return "1 min"
    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remainder = minutes % 60
    if remainder == 0:
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    return f"{hours} hr {remainder} min" if hours == 1 else f"{hours} hrs {remainder} min"
