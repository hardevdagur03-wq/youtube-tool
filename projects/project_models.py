"""Pydantic models for the Project Management Layer.

All models are strongly typed with validation.
No existing business logic is modified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    FETCHING_METADATA = "fetching_metadata"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    AI_ANALYSIS = "ai_analysis"
    OUTLINE_GENERATION = "outline_generation"
    BLOG_GENERATION = "blog_generation"
    BLOG_REVIEW = "blog_review"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RESUMED = "resumed"
    CANCELLED = "cancelled"


class PipelineStage(str, Enum):
    METADATA = "metadata"
    TRANSCRIPT = "transcript"
    ANALYSIS = "analysis"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SEO = "seo"
    SEO_INTELLIGENCE = "seo_intelligence"
    OUTLINE = "outline"
    SECTIONS = "sections"
    MERGE = "merge"
    BLOG = "blog"
    REVIEW = "review"
    EXPORT = "export"


STAGE_ORDER = [
    PipelineStage.METADATA,
    PipelineStage.TRANSCRIPT,
    PipelineStage.ANALYSIS,
    PipelineStage.KNOWLEDGE_GRAPH,
    PipelineStage.SEO,
    PipelineStage.SEO_INTELLIGENCE,
    PipelineStage.OUTLINE,
    PipelineStage.SECTIONS,
    PipelineStage.MERGE,
    PipelineStage.BLOG,
    PipelineStage.REVIEW,
    PipelineStage.EXPORT,
]


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"


class StageInfo(BaseModel):
    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    progress_pct: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    retry_count: int = 0
    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    output_file: str = ""
    checkpoint_id: str = ""


class PipelineStatus(BaseModel):
    stages: dict[str, StageInfo] = Field(default_factory=dict)
    current_stage: str = ""
    overall_progress_pct: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    retry_count: int = 0
    is_paused: bool = False


class Checkpoint(BaseModel):
    checkpoint_id: str = ""
    stage: str = ""
    created_at: str = ""
    reason: str = ""
    files: dict[str, str] = Field(default_factory=dict)
    checksums: dict[str, str] = Field(default_factory=dict)
    state_snapshot: dict[str, Any] = Field(default_factory=dict)


class Version(BaseModel):
    version_id: str = ""
    version_number: int = 1
    created_at: str = ""
    reason: str = ""
    changed_files: list[str] = Field(default_factory=list)
    checksum: str = ""
    parent_version: str = ""
    rollback_data: dict[str, Any] = Field(default_factory=dict)


class HistoryEntry(BaseModel):
    entry_id: str = ""
    timestamp: str = ""
    action: str = ""
    stage: str = ""
    previous_state: str = ""
    new_state: str = ""
    duration_seconds: float = 0.0
    user_action: bool = False
    system_action: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    retry_count: int = 0
    details: str = ""


class ProjectSettings(BaseModel):
    language: str = "en"
    llm_provider: str = ""
    llm_model: str = ""
    seo_enabled: bool = True
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "html", "docx"])
    max_retries: int = 3
    auto_save: bool = True
    auto_recover: bool = True
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class ProjectStatistics(BaseModel):
    video_duration_seconds: float = 0.0
    word_count: int = 0
    character_count: int = 0
    transcript_segments: int = 0
    blog_word_count: int = 0
    quality_score: float = 0.0
    seo_score: float = 0.0
    export_file_count: int = 0
    total_api_calls: int = 0
    total_retries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class ArtifactInfo(BaseModel):
    path: str = ""
    file_type: str = ""
    file_size_bytes: int = 0
    created_at: str = ""
    checksum: str = ""
    stage: str = ""


class ProjectSummary(BaseModel):
    """Lightweight summary for listing projects (no full pipeline state)."""
    project_id: str
    short_id: str
    name: str
    video_id: str
    url: str
    thumbnail: str = ""
    status: ProjectStatus = ProjectStatus.CREATED
    current_stage: str = ""
    overall_progress_pct: float = 0.0
    version: int = 1
    language: str = "en"
    quality_score: float = 0.0
    seo_score: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    error: str = ""
    tags: list[str] = Field(default_factory=list)


class Project(BaseModel):
    """Complete project model — single source of truth."""
    project_id: str = ""
    short_id: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    video_id: str = ""
    thumbnail: str = ""
    channel_title: str = ""
    channel_id: str = ""

    status: ProjectStatus = ProjectStatus.CREATED
    version: int = 1
    language: str = "en"

    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    folder_path: str = ""

    pipeline: PipelineStatus = Field(default_factory=PipelineStatus)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    statistics: ProjectStatistics = Field(default_factory=ProjectStatistics)

    checkpoints: list[Checkpoint] = Field(default_factory=list)
    versions: list[Version] = Field(default_factory=list)
    history: list[HistoryEntry] = Field(default_factory=list)
    artifacts: list[ArtifactInfo] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)
    transcript: dict[str, Any] = Field(default_factory=dict)
    analysis: dict[str, Any] = Field(default_factory=dict)
    outline: dict[str, Any] = Field(default_factory=dict)
    blog: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    export: dict[str, Any] = Field(default_factory=dict)

    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    retry_count: int = 0
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
