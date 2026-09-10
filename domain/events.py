"""Domain events for the YouTube SEO Blog platform.

Each event is a standalone dataclass without inheritance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _event_id() -> str:
    return uuid.uuid4().hex


@dataclass
class VideoCreated:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "VideoCreated"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    url: str = ""
    title: str = ""


@dataclass
class TranscriptGenerated:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "TranscriptGenerated"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    source: str = ""
    language: str = ""
    word_count: int = 0


@dataclass
class TranscriptFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "TranscriptFailed"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    error: str = ""
    source: str = ""


@dataclass
class AnalysisCompleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "AnalysisCompleted"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    primary_topic: str = ""
    llm_provider: str = ""
    total_tokens: int = 0


@dataclass
class AnalysisFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "AnalysisFailed"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    error: str = ""
    stage: str = ""


@dataclass
class KnowledgeGraphBuilt:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "KnowledgeGraphBuilt"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    entity_count: int = 0
    relationship_count: int = 0


@dataclass
class SEOAnalysisCompleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "SEOAnalysisCompleted"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    score: float = 0.0
    keyword_count: int = 0


@dataclass
class OutlineGenerated:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "OutlineGenerated"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    section_count: int = 0


@dataclass
class BlogGenerated:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "BlogGenerated"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    word_count: int = 0
    llm_provider: str = ""
    total_tokens: int = 0


@dataclass
class BlogFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "BlogFailed"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    error: str = ""
    stage: str = ""


@dataclass
class ExportCompleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "ExportCompleted"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    export_id: str = ""
    formats: list[str] = field(default_factory=list)
    total_size_bytes: int = 0


@dataclass
class ExportFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "ExportFailed"
    occurred_at: str = field(default_factory=_now)
    video_id: str = ""
    export_id: str = ""
    error: str = ""


@dataclass
class PipelineStarted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "PipelineStarted"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    video_id: str = ""


@dataclass
class PipelineStageCompleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "PipelineStageCompleted"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    stage: str = ""
    video_id: str = ""


@dataclass
class PipelineStageFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "PipelineStageFailed"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    stage: str = ""
    error: str = ""
    video_id: str = ""
    recoverable: bool = False


@dataclass
class PipelineCompleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "PipelineCompleted"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    video_id: str = ""
    total_stages: int = 0
    duration_seconds: float = 0.0


@dataclass
class PipelineFailed:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "PipelineFailed"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    video_id: str = ""
    error: str = ""
    failed_stage: str = ""


@dataclass
class ProjectCreated:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "ProjectCreated"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    video_id: str = ""
    url: str = ""


@dataclass
class ProjectDeleted:
    event_id: str = field(default_factory=_event_id)
    event_type: str = "ProjectDeleted"
    occurred_at: str = field(default_factory=_now)
    project_id: str = ""
    video_id: str = ""
