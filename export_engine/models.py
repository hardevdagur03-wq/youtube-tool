from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressStage(str, Enum):
    VALIDATE_URL = "validate_url"
    CHECK_CACHE = "check_cache"
    RESOLVE_CHANNEL = "resolve_channel"
    FETCH_PLAYLIST = "fetch_playlist"
    FETCH_VIDEO_IDS = "fetch_video_ids"
    FETCH_METADATA = "fetch_metadata"
    GENERATE_CSV = "generate_csv"
    COMPLETE = "complete"
    ERROR = "error"


STAGE_LABELS: dict[ProgressStage, str] = {
    ProgressStage.VALIDATE_URL: "Validate URL",
    ProgressStage.CHECK_CACHE: "Check Cache",
    ProgressStage.RESOLVE_CHANNEL: "Resolve Channel",
    ProgressStage.FETCH_PLAYLIST: "Fetch Upload Playlist",
    ProgressStage.FETCH_VIDEO_IDS: "Fetch Video IDs",
    ProgressStage.FETCH_METADATA: "Fetch Metadata",
    ProgressStage.GENERATE_CSV: "Generate CSV",
    ProgressStage.COMPLETE: "Completed",
    ProgressStage.ERROR: "Error",
}


class StageProgress(BaseModel):
    stage: ProgressStage
    status: JobStatus = JobStatus.PENDING
    label: str = ""
    detail: str = ""
    progress_pct: float = 0.0
    current_page: int = 0
    total_pages: int = 0
    processed: int = 0
    total: int = 0
    remaining: int = 0
    eta_seconds: float = 0.0
    api_calls: int = 0
    rows_written: int = 0
    elapsed: float = 0.0
    error: str = ""


class ProgressUpdate(BaseModel):
    job_id: str = ""
    status: JobStatus = JobStatus.RUNNING
    stages: dict[str, StageProgress] = Field(default_factory=dict)
    current_stage: str = ""
    overall_progress_pct: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0
    error: str = ""
    error_type: str = ""
    error_action: str = ""


class ExportRequest(BaseModel):
    channel_input: str
    limit: int = 0
    user_agent: str = ""


class JobResult(BaseModel):
    success: bool
    job_id: str
    channel_title: str = ""
    channel_id: str = ""
    total_videos: int = 0
    total_discovered: int = 0
    total_api_calls: int = 0
    file_size_bytes: int = 0
    elapsed_seconds: float = 0.0
    error: str = ""
    error_type: str = ""
    csv_path: str = ""
    cache_hits: int = 0
    cache_misses: int = 0
    total_retries: int = 0


class JobState(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: JobStatus = JobStatus.PENDING
    request: ExportRequest | None = None
    result: JobResult | None = None
    progress: ProgressUpdate = Field(default_factory=ProgressUpdate)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled: bool = False
    cancel_requested: bool = False
    error: str = ""
    progress_file: str = ""
    result_file: str = ""
    csv_path: str = ""


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: ProgressUpdate | None = None
    result: JobResult | None = None
    created_at: str = ""
    elapsed_seconds: float = 0.0
