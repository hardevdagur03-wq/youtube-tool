"""Pydantic model for YouTube URL parsing results."""

from typing import Literal

from pydantic import BaseModel, Field

UrlType = Literal["watch", "shorts", "live", "youtu.be", "embed"] | None


class VideoURLResult(BaseModel):
    """Structured result from parsing a YouTube video URL.

    Attributes:
        valid: Whether the URL is a valid YouTube video URL.
        video_id: Extracted 11-character video ID, or ``None``.
        normalized_url: Canonical ``https://www.youtube.com/watch?v=VIDEO_ID`` URL.
        url_type: The type of YouTube URL detected.
        original_url: The raw URL that was parsed.
        error: Human-readable error message, or ``None``.
    """

    valid: bool = Field(default=False)
    video_id: str | None = Field(default=None)
    normalized_url: str | None = Field(default=None)
    url_type: UrlType = Field(default=None)
    original_url: str | None = Field(default=None)
    error: str | None = Field(default=None)
