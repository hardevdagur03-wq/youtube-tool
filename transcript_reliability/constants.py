"""Default constants and thresholds for the Transcript Reliability Engine."""

from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# Provider capabilities
# ---------------------------------------------------------------------------


class ProviderCapability(str, Enum):
    CAPTIONS = "captions"                   # YouTube captions API
    STT = "stt"                             # Speech-to-text
    TRANSLATION = "translation"             # Built-in translation
    LANGUAGE_DETECTION = "language_detection"
    REAL_TIME = "real_time"                 # Streaming support
    BATCH = "batch"                         # Batch/submit processing
    ASYNC = "async"                         # Async/polling processing


# ---------------------------------------------------------------------------
# Provider status
# ---------------------------------------------------------------------------


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Circuit breaker states
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Retry actions
# ---------------------------------------------------------------------------


class RetryAction(str, Enum):
    RETRY = "retry"
    FAILOVER = "failover"
    DEAD_LETTER = "dead_letter"
    ABORT = "abort"


# ---------------------------------------------------------------------------
# Quality grades
# ---------------------------------------------------------------------------


class QualityGrade(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Validation check names
# ---------------------------------------------------------------------------


VALIDATION_CHECKS = [
    "empty_transcript",
    "minimum_length",
    "broken_encoding",
    "timestamp_order",
    "repeated_blocks",
    "missing_segments",
    "invalid_characters",
    "language_consistency",
    "provider_integrity",
    "timestamp_coverage",
    "minimum_segments",
    "text_segment_ratio",
]

# ---------------------------------------------------------------------------
# Duplicate detection strategies
# ---------------------------------------------------------------------------


DUPLICATE_STRATEGIES = [
    "exact_line",
    "exact_paragraph",
    "timestamp_block",
    "segment_overlap",
    "sentence_repeat",
    "near_duplicate",
]

# ---------------------------------------------------------------------------
# Silence detection patterns
# ---------------------------------------------------------------------------


SILENCE_PATTERNS = [
    "silent_audio",
    "music_only",
    "long_pauses",
    "empty_captions",
    "placeholder_captions",
    "noise_only",
]

# ---------------------------------------------------------------------------
# Cleaning pipeline stages
# ---------------------------------------------------------------------------


CLEANING_STAGES = [
    "unicode_normalizer",
    "whitespace_normalizer",
    "punctuation_normalizer",
    "number_normalizer",
    "special_char_normalizer",
    "emoji_remover",
    "broken_formatting_fixer",
    "speaker_label_normalizer",
    "sentence_boundary_fixer",
    "ai_ready_formatter",
]

# ---------------------------------------------------------------------------
# Version types
# ---------------------------------------------------------------------------


VERSION_TYPES = [
    "original",
    "cleaned",
    "validated",
    "translated",
    "corrected",
    "ai_optimized",
    "current",
]

# ---------------------------------------------------------------------------
# Default cost per minute (USD) for providers that don't report cost
# ---------------------------------------------------------------------------


PROVIDER_COST_PER_MINUTE: dict[str, float] = {
    "youtube_manual": 0.0,
    "youtube_auto": 0.0,
    "whisper_api": 0.006,
    "whisper_local": 0.0,
    "deepgram": 0.0059,
    "assemblyai": 0.015,
}

# ---------------------------------------------------------------------------
# Performance targets (seconds)
# ---------------------------------------------------------------------------


PERFORMANCE_TARGETS: dict[str, float] = {
    "manual_caption": 3.0,
    "cache_hit": 3.0,
    "auto_caption": 8.0,
    "whisper_api": 20.0,
    "deepgram": 25.0,
    "assemblyai": 30.0,
    "pipeline_recovery": 2.0,
}
