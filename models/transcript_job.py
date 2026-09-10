"""Data models for background channel transcript jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TranscriptVideoItem(BaseModel):
    video_id: str
    video_url: str
    channel_id: str = ""
    channel_title: str = ""
    title: str = ""
    published_at: str = ""
    duration_seconds: int = 0
    duration: str = "0:00"
    language: str | None = None
    status: str = "pending"  # success | failed | skipped_short | skipped_long | skipped_live
    transcript: str = ""
    raw_transcript: str = ""
    transcript_timestamped: str = ""
    source: str | None = None  # youtube | whisper
    method: str | None = None  # caption | speech_to_text
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int = 0
    completed_at: str | None = None


class TranscriptJobProgress(BaseModel):
    job_id: str
    channel_handle: str
    channel_id: str
    channel_title: str
    status: JobStatus = JobStatus.QUEUED
    total_discovered: int = 0
    eligible_videos: int = 0
    skipped_videos: int = 0
    processed: int = 0
    successful: int = 0
    caption_count: int = 0
    whisper_count: int = 0
    no_captions: int = 0
    failed: int = 0
    remaining: int = 0
    progress_percent: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    error: str | None = None
    videos: list[TranscriptVideoItem] = Field(default_factory=list)
