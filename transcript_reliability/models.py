"""Pydantic models for the Transcript Reliability Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from transcript_reliability.constants import (
    CircuitState,
    ProviderCapability,
    ProviderStatus,
    QualityGrade,
    RetryAction,
)


# ===================================================================
# Provider Models
# ===================================================================


class ProviderInfo(BaseModel):
    """Metadata about a registered provider."""
    provider_id: str = ""
    name: str = ""
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    cost_per_minute: float = 0.0
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Health Models
# ===================================================================


class HealthRecord(BaseModel):
    """A single health observation for a provider."""
    timestamp: float = 0.0
    success: bool = True
    latency_ms: float = 0.0
    error_type: str = ""
    quota_remaining: float = 1.0


class ProviderHealth(BaseModel):
    """Rolling health status for a single provider."""
    provider_id: str = ""
    status: ProviderStatus = ProviderStatus.UNKNOWN
    availability: float = 1.0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    failure_count: int = 0
    total_requests: int = 0
    quota_usage: float = 0.0
    last_error: str = ""
    last_error_at: str = ""
    last_success_at: str = ""
    rolling_window_seconds: float = 60.0
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)


# ===================================================================
# Retry Models
# ===================================================================


class RetryPolicy(BaseModel):
    """Retry configuration for a provider or request."""
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: float = 0.25
    retry_on_timeout: bool = True
    retry_on_429: bool = True
    retry_on_5xx: bool = True
    retry_on_network_error: bool = True
    retry_on_auth_error: bool = False
    retry_budget: int = 10


class RetryDecision(BaseModel):
    """Decision from the retry engine."""
    action: RetryAction = RetryAction.RETRY
    delay_seconds: float = 0.0
    attempt: int = 0
    reason: str = ""
    next_provider_id: str = ""


class RetryAttempt(BaseModel):
    """Record of a single retry attempt."""
    attempt_number: int = 0
    provider_id: str = ""
    delay_seconds: float = 0.0
    error: str = ""
    timestamp: float = 0.0


# ===================================================================
# Circuit Breaker Models
# ===================================================================


class CircuitBreakerState(BaseModel):
    """Current state of a circuit breaker for a provider."""
    provider_id: str = ""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: float = 0.0
    last_success_at: float = 0.0
    opened_at: float = 0.0
    half_open_probes: int = 0
    recovery_timeout: float = 30.0
    failure_threshold: int = 5
    success_threshold: int = 2


# ===================================================================
# Language Models
# ===================================================================


class LanguageDetectionResult(BaseModel):
    """Result of language detection on transcript text."""
    primary: str = "en"
    secondary: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    detection_source: str = "heuristic"
    dialect: str | None = None
    all_languages: dict[str, float] = Field(default_factory=dict)


# ===================================================================
# Validation Models
# ===================================================================


class ValidationResult(BaseModel):
    """Result of a single validation check."""
    check_name: str = ""
    passed: bool = True
    score: float = 1.0
    detail: str = ""


class ValidationReport(BaseModel):
    """Complete validation report for a transcript."""
    overall_score: float = 1.0
    passed: bool = True
    checks: list[ValidationResult] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ===================================================================
# Duplicate Removal Models
# ===================================================================


class DuplicateReport(BaseModel):
    """Report of duplicate content found and removed."""
    total_duplicates_found: int = 0
    total_duplicates_removed: int = 0
    strategies_triggered: list[str] = Field(default_factory=list)
    details: list[dict[str, Any]] = Field(default_factory=list)
    original_word_count: int = 0
    cleaned_word_count: int = 0


# ===================================================================
# Silence Detection Models
# ===================================================================


class SilenceResult(BaseModel):
    """Result of silence/music/noise detection."""
    is_silent: bool = False
    confidence: float = 0.0
    patterns_detected: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Quality Models
# ===================================================================


class QualityDimension(BaseModel):
    """A single dimension of transcript quality."""
    name: str = ""
    score: float = 0.0
    weight: float = 0.0
    detail: str = ""


class QualityScore(BaseModel):
    """Overall quality assessment for a transcript."""
    overall: float = 0.0
    grade: QualityGrade = QualityGrade.FAIR
    dimensions: list[QualityDimension] = Field(default_factory=list)
    provider_reliability_score: float = 0.0
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ===================================================================
# Version Models
# ===================================================================


class VersionRecord(BaseModel):
    """A versioned snapshot of a transcript."""
    version_id: str = ""
    transcript_id: str = ""
    video_id: str = ""
    version_type: str = "current"
    version_number: int = 1
    content_hash: str = ""
    plain_text: str = ""
    word_count: int = 0
    language: str = "en"
    source: str = ""
    parent_version_id: str = ""
    change_reason: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===================================================================
# Cache Models
# ===================================================================


class CacheEntry(BaseModel):
    """An entry in the transcript cache."""
    cache_key: str = ""
    video_id: str = ""
    language: str = "en"
    provider_id: str = ""
    version_type: str = "current"
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    expires_at: float = 0.0
    size_bytes: int = 0
    hit_count: int = 0


# ===================================================================
# Provider Statistics
# ===================================================================


class ProviderStats(BaseModel):
    """Aggregate statistics for a provider over a time window."""
    provider_id: str = ""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    quota_consumed: int = 0
    cost_incurred: float = 0.0
    window_start: float = 0.0
    window_end: float = 0.0


# ===================================================================
# Transcript Metric Models
# ===================================================================


class TranscriptMetrics(BaseModel):
    """Usage metrics for a transcript retrieval."""
    video_id: str = ""
    total_duration_ms: float = 0.0
    cache_hit: bool = False
    cache_level: str = ""
    provider_id: str = ""
    provider_attempts: int = 0
    retry_count: int = 0
    fallback_count: int = 0
    validation_score: float = 0.0
    quality_score: float = 0.0
    word_count: int = 0
    language: str = ""
    circuit_breaker_events: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
