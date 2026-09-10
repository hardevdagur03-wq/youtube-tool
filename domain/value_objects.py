"""Domain value objects for the YouTube SEO Blog platform.

All value objects are immutable and have zero framework dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from domain.common.base import ValueObject


@dataclass(unsafe_hash=True)
class VideoId(ValueObject):
    """YouTube video identifier (11 characters)."""
    value: str

    PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")

    def __post_init__(self) -> None:
        if not self.PATTERN.match(self.value):
            raise ValueError(f"Invalid video ID: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass
class ChannelId(ValueObject):
    """YouTube channel identifier (starts with UC)."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class ProjectId(ValueObject):
    """Project identifier."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Url(ValueObject):
    """URL value object."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Language(ValueObject):
    """Language code (ISO 639-1)."""
    code: str

    def __str__(self) -> str:
        return self.code


class TranscriptSource(str, Enum):
    MANUAL = "manual"
    AUTO_GENERATED = "auto"
    WHISPER = "whisper"


class TranscriptProvider(str, Enum):
    YOUTUBE_MANUAL = "youtube_manual"
    YOUTUBE_AUTO = "youtube_auto"
    FASTER_WHISPER = "faster_whisper"


class ContentCategory(str, Enum):
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    SCIENCE = "science"
    BUSINESS = "business"
    LIFESTYLE = "lifestyle"
    NEWS = "news"
    TUTORIAL = "tutorial"
    OTHER = "other"


class ContentType(str, Enum):
    TUTORIAL = "tutorial"
    EXPLAINER = "explainer"
    REVIEW = "review"
    CASE_STUDY = "case_study"
    INTERVIEW = "interview"
    VLOG = "vlog"
    DOCUMENTARY = "documentary"
    PODCAST = "podcast"
    LIVE_STREAM = "live_stream"
    OTHER = "other"


class SearchIntent(str, Enum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    NAVIGATIONAL = "navigational"
    COMPARATIVE = "comparative"
    TRANSACTIONAL = "transactional"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    ALL_LEVELS = "all_levels"


class PipelineStage(str, Enum):
    METADATA = "metadata"
    TRANSCRIPT = "transcript"
    ANALYSIS = "analysis"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SEO = "seo"
    SEO_INTELLIGENCE = "seo_intelligence"
    OUTLINE = "outline"
    SECTIONS = "sections"
    DRAFT = "draft"
    REVIEW = "review"
    OPTIMIZATION = "optimization"
    EXPORT = "export"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"
    JSON = "json"
    ZIP = "zip"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranscriptSegment(ValueObject):
    """A single segment of a transcript."""
    start: float
    end: float
    text: str
    duration: float = 0.0

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("Start time cannot be negative")
        if self.end <= self.start:
            raise ValueError("End time must be after start time")


@dataclass
class AnalysisSummary(ValueObject):
    """Summary of content analysis."""
    short: str = ""
    executive: str = ""
    detailed: str = ""
    bullet_points: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.bullet_points is None:
            object.__setattr__(self, "bullet_points", [])


@dataclass
class KeywordSet(ValueObject):
    """Keyword analysis results."""
    primary: list[str] = None  # type: ignore[assignment]
    secondary: list[str] = None  # type: ignore[assignment]
    long_tail: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.primary is None:
            object.__setattr__(self, "primary", [])
        if self.secondary is None:
            object.__setattr__(self, "secondary", [])
        if self.long_tail is None:
            object.__setattr__(self, "long_tail", [])


@dataclass
class QualityScores(ValueObject):
    """Quality assessment scores."""
    topic_coverage: float = 0.0
    depth: float = 0.0
    readability: float = 0.0
    seo_potential: float = 0.0
    evergreen_score: float = 0.0


@dataclass
class BlogSection(ValueObject):
    """A section of a blog post."""
    heading: str = ""
    content: str = ""
    subsections: list[BlogSubsection] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.subsections is None:
            object.__setattr__(self, "subsections", [])


@dataclass
class BlogSubsection(ValueObject):
    """A subsection of a blog post."""
    heading: str = ""
    content: str = ""


@dataclass
class BlogStatistics(ValueObject):
    """Statistics for a blog post."""
    word_count: int = 0
    reading_time_minutes: int = 0
    estimated_seo_score: float = 0.0
    section_count: int = 0
    heading_count: int = 0


@dataclass
class SEOKeyword(ValueObject):
    """SEO keyword with metrics."""
    keyword: str = ""
    density: float = 0.0
    count: int = 0
    prominence: str = ""


@dataclass
class SEOScore(ValueObject):
    """Overall SEO score components."""
    total: float = 0.0
    title_score: float = 0.0
    meta_score: float = 0.0
    keyword_score: float = 0.0
    structure_score: float = 0.0
    readability_score: float = 0.0
    link_score: float = 0.0
    schema_score: float = 0.0


@dataclass
class ExportFile(ValueObject):
    """Information about an exported file."""
    filename: str = ""
    format: str = ""
    size_bytes: int = 0
    url: str = ""
    mime_type: str = ""


@dataclass
class Timestamp(ValueObject):
    """An ISO timestamp."""
    value: str = ""

    @staticmethod
    def now() -> Timestamp:
        return Timestamp(
            value=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        )
