"""Pydantic request/response schemas for transcript API endpoints."""

from pydantic import BaseModel, Field


class TranscriptRequest(BaseModel):
    """Request schema for transcript retrieval."""

    video_id: str = Field(
        ..., min_length=11, max_length=11, description="YouTube video ID"
    )
    language: str | None = Field(
        default=None, description="Preferred language code (e.g. 'en', 'es')"
    )
    force_refresh: bool = Field(
        default=False, description="Bypass cache and re-fetch transcript"
    )
    allow_whisper: bool = Field(
        default=True, description="Allow Whisper speech-to-text fallback"
    )


class TranscriptStatusResponse(BaseModel):
    """Response schema for transcript availability check."""

    video_id: str
    cached: bool = False
    source: str | None = Field(default=None)
    manual_available: bool = False
    auto_available: bool = False
    whisper_possible: bool = True
