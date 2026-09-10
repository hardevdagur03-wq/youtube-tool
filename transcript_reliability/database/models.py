"""SQLAlchemy models for the Transcript Reliability Engine — 10 new tables."""

from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Text, func
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.base import BaseModel


class TranscriptProviderModel(BaseModel):
    """Registered transcript providers with configuration."""

    __tablename__ = "transcript_providers"

    provider_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    capabilities: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    cost_per_minute: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    supported_languages: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    def __repr__(self) -> str:
        return f"<TranscriptProviderModel id={self.provider_id} enabled={self.enabled}>"


class ProviderHealthModel(BaseModel):
    """Rolling health scores and error tracking per provider."""

    __tablename__ = "provider_health"

    provider_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown"
    )
    availability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p99_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_usage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_error_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    last_success_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    recent_errors: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    def __repr__(self) -> str:
        return f"<ProviderHealthModel id={self.provider_id} status={self.status}>"


class TranscriptVersionModel(BaseModel):
    """Versioned snapshots of transcripts with full recovery support."""

    __tablename__ = "transcript_versions"

    transcript_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    version_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current"
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    parent_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=""
    )
    change_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    version_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptVersionModel video={self.video_id} "
            f"type={self.version_type} v{self.version_number}>"
        )


class TranscriptCacheModel(BaseModel):
    """L3 persistent cache store for transcripts."""

    __tablename__ = "transcript_cache"

    cache_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    version_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current"
    )
    data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<TranscriptCacheModel key={self.cache_key}>"


class TranscriptValidationModel(BaseModel):
    """Validation results for a transcript."""

    __tablename__ = "transcript_validations"

    transcript_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    failed_checks: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    errors: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptValidationModel video={self.video_id} "
            f"passed={self.passed} score={self.overall_score}>"
        )


class TranscriptQualityModel(BaseModel):
    """Quality scores and dimension breakdowns for transcripts."""

    __tablename__ = "transcript_quality"

    transcript_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    overall: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="fair")
    dimensions: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    provider_reliability_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptQualityModel video={self.video_id} "
            f"grade={self.grade} overall={self.overall}>"
        )


class TranscriptMetricModel(BaseModel):
    """Usage metrics for transcript retrievals."""

    __tablename__ = "transcript_metrics"

    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    total_duration_ms: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_level: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provider_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    circuit_breaker_events: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    errors: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptMetricModel video={self.video_id} "
            f"provider={self.provider_id} duration={self.total_duration_ms}>"
        )


class TranscriptFailureModel(BaseModel):
    """Records of transcript failures for analysis and debugging."""

    __tablename__ = "transcript_failures"

    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    error_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_chain: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    circuit_breaker_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="closed"
    )
    recoverable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<TranscriptFailureModel video={self.video_id} "
            f"provider={self.provider_id} error={self.error_type}>"
        )


class TranscriptRetryModel(BaseModel):
    """Retry history for transcript requests."""

    __tablename__ = "transcript_retries"

    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delay_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="retry")

    def __repr__(self) -> str:
        return (
            f"<TranscriptRetryModel video={self.video_id} "
            f"attempt={self.attempt_number} decision={self.decision}>"
        )


class ProviderStatisticsModel(BaseModel):
    """Aggregate provider statistics over time windows."""

    __tablename__ = "provider_statistics"

    provider_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p99_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quota_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_incurred: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    window_start: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    window_end: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    def __repr__(self) -> str:
        return (
            f"<ProviderStatisticsModel id={self.provider_id} "
            f"requests={self.total_requests}>"
        )
