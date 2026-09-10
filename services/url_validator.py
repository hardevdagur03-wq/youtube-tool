from __future__ import annotations

import re
from urllib.parse import urlparse

YOUTUBE_DOMAINS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "music.youtube.com", "youtube-nocookie.com",
}
HANDLE_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,30}$")
CHANNEL_ID_PATTERN = re.compile(r"^UC[\w-]{22,}$")
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
URL_PATTERN = re.compile(
    r"^https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/",
)


class URLValidator:
    """Validates and sanitizes YouTube URLs and channel identifiers."""

    @staticmethod
    def validate(raw: str) -> dict:
        """Validate a YouTube channel URL, handle, or channel ID.

        Returns:
            Dict with keys: ``valid``, ``input_type``, ``identifier``, ``error``.
        """
        if not raw or not raw.strip():
            return {"valid": False, "input_type": "", "identifier": "", "error": "Input cannot be empty."}

        stripped = raw.strip()

        if stripped.startswith("UC") and len(stripped) >= 24:
            if CHANNEL_ID_PATTERN.match(stripped):
                return {"valid": True, "input_type": "channel_id", "identifier": stripped, "error": ""}
            return {"valid": False, "input_type": "channel_id", "identifier": "", "error": "Invalid channel ID format."}

        if stripped.startswith("@"):
            handle = stripped[1:]
            if HANDLE_PATTERN.match(handle):
                return {"valid": True, "input_type": "handle", "identifier": stripped, "error": ""}
            return {"valid": False, "input_type": "handle", "identifier": "", "error": "Invalid handle format. Must be 3-30 characters."}

        if URL_PATTERN.match(stripped):
            try:
                parsed = urlparse(stripped)
                path = parsed.path.rstrip("/")
                at_match = re.search(r"/@([A-Za-z0-9._-]+)", path)
                if at_match:
                    return {"valid": True, "input_type": "url", "identifier": at_match.group(1), "error": ""}
                channel_match = re.search(r"/channel/(UC[\w-]+)", path)
                if channel_match:
                    return {"valid": True, "input_type": "url", "identifier": channel_match.group(1), "error": ""}
                c_match = re.search(r"/c/([\w-]+)", path)
                if c_match:
                    return {"valid": True, "input_type": "url", "identifier": c_match.group(1), "error": ""}
                if "youtu.be" in parsed.netloc:
                    vid_match = re.search(r"/([A-Za-z0-9_-]{11})", path)
                    if vid_match:
                        return {"valid": True, "input_type": "url", "identifier": vid_match.group(1), "error": ""}
                return {"valid": False, "input_type": "url", "identifier": "", "error": "Could not extract channel identifier from URL."}
            except Exception:
                return {"valid": False, "input_type": "url", "identifier": "", "error": "Invalid URL format."}

        if HANDLE_PATTERN.match(stripped):
            return {"valid": True, "input_type": "handle", "identifier": f"@{stripped}", "error": ""}

        return {"valid": False, "input_type": "unknown", "identifier": "", "error": "Could not identify a valid YouTube channel. Use @handle, UC... ID, or a YouTube URL."}

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize a URL to prevent XSS and injection."""
        if not url:
            return ""
        sanitized = url.strip()
        sanitized = sanitized.replace("\x00", "")
        sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")
        sanitized = sanitized.replace('"', "&quot;").replace("'", "&#x27;")
        return sanitized

    @staticmethod
    def validate_video_id(video_id: str) -> bool:
        return bool(video_id and VIDEO_ID_PATTERN.match(video_id))
