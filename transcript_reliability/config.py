"""Transcript Reliability Configuration — all settings driven by environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if not val:
        return default
    return val in ("1", "true", "yes", "y")


def _env_list(key: str, default: str) -> list[str]:
    val = os.environ.get(key, default)
    return [v.strip() for v in val.split(",") if v.strip()]


@dataclass
class TranscriptReliabilityConfig:
    """Configuration for the Transcript Reliability Engine.

    All values are driven by environment variables with sensible defaults.
    """

    # Provider priority order (comma-separated provider IDs)
    provider_priority_order: list[str] = field(
        default_factory=lambda: _env_list(
            "TRANSCRIPT_PRIORITY_ORDER",
            "youtube_manual,youtube_auto,whisper_api,whisper_local,deepgram,assemblyai",
        )
    )

    # Disabled providers (comma-separated)
    provider_disabled: list[str] = field(
        default_factory=lambda: _env_list("TRANSCRIPT_PROVIDER_DISABLED", "")
    )

    # Language-specific overrides: e.g. TRANSCRIPT_PRIORITY_LANGUAGE_hi=deepgram,assemblyai
    provider_language_overrides: dict[str, list[str]] = field(default_factory=dict)

    # Retry engine
    retry_max_retries: int = _env_int("TRANSCRIPT_RETRY_MAX_RETRIES", 3)
    retry_base_delay: float = _env_float("TRANSCRIPT_RETRY_BASE_DELAY", 2.0)
    retry_max_delay: float = _env_float("TRANSCRIPT_RETRY_MAX_DELAY", 60.0)
    retry_backoff_factor: float = _env_float("TRANSCRIPT_RETRY_BACKOFF_FACTOR", 2.0)
    retry_jitter: float = _env_float("TRANSCRIPT_RETRY_JITTER", 0.25)

    # Circuit breaker
    circuit_breaker_failure_threshold: int = _env_int("TRANSCRIPT_CB_FAILURE_THRESHOLD", 5)
    circuit_breaker_recovery_timeout: float = _env_float("TRANSCRIPT_CB_RECOVERY_TIMEOUT", 30.0)
    circuit_breaker_half_open_max_probes: int = _env_int("TRANSCRIPT_CB_HALF_OPEN_MAX_PROBES", 3)
    circuit_breaker_success_threshold: int = _env_int("TRANSCRIPT_CB_SUCCESS_THRESHOLD", 2)

    # Health monitor
    health_window_seconds: float = _env_float("TRANSCRIPT_HEALTH_WINDOW_SECONDS", 60.0)
    health_window_max_requests: int = _env_int("TRANSCRIPT_HEALTH_WINDOW_MAX_REQUESTS", 100)
    health_downgrade_threshold: float = _env_float("TRANSCRIPT_HEALTH_DOWNGRADE_THRESHOLD", 0.7)
    health_disable_threshold: float = _env_float("TRANSCRIPT_HEALTH_DISABLE_THRESHOLD", 0.3)
    health_poll_interval: float = _env_float("TRANSCRIPT_HEALTH_POLL_INTERVAL", 15.0)

    # Cache layer
    cache_l1_ttl_seconds: float = _env_float("TRANSCRIPT_CACHE_L1_TTL", 300.0)
    cache_l1_max_entries: int = _env_int("TRANSCRIPT_CACHE_L1_MAX_ENTRIES", 10000)
    cache_l2_ttl_seconds: float = _env_float("TRANSCRIPT_CACHE_L2_TTL", 3600.0)
    cache_l3_ttl_seconds: float = _env_float("TRANSCRIPT_CACHE_L3_TTL", 604800.0)
    cache_l2_enabled: bool = _env_bool("TRANSCRIPT_CACHE_L2_ENABLED", True)
    cache_l3_enabled: bool = _env_bool("TRANSCRIPT_CACHE_L3_ENABLED", True)

    # Validation
    validation_min_word_count: int = _env_int("TRANSCRIPT_VALIDATION_MIN_WORDS", 10)
    validation_min_segments: int = _env_int("TRANSCRIPT_VALIDATION_MIN_SEGMENTS", 3)
    validation_min_coverage_ratio: float = _env_float("TRANSCRIPT_VALIDATION_MIN_COVERAGE", 0.5)
    validation_language_consistency_threshold: float = _env_float("TRANSCRIPT_VALIDATION_LANG_CONSISTENCY", 0.7)
    validation_overall_threshold: float = _env_float("TRANSCRIPT_VALIDATION_OVERALL_THRESHOLD", 0.3)
    validation_max_gap_seconds: float = _env_float("TRANSCRIPT_VALIDATION_MAX_GAP", 30.0)

    # Duplicate removal
    duplicate_similarity_threshold: float = _env_float("TRANSCRIPT_DUPLICATE_SIMILARITY", 0.80)
    duplicate_sentence_repeat_threshold: int = _env_int("TRANSCRIPT_DUPLICATE_SENTENCE_REPEAT", 2)

    # Silence detection
    silence_max_gap_seconds: float = _env_float("TRANSCRIPT_SILENCE_MAX_GAP", 10.0)
    silence_min_speech_ratio: float = _env_float("TRANSCRIPT_SILENCE_MIN_SPEECH_RATIO", 0.1)

    # API keys (providers)
    openai_api_key: str = _env("OPENAI_API_KEY", "")
    deepgram_api_key: str = _env("DEEPGRAM_API_KEY", "")
    assemblyai_api_key: str = _env("ASSEMBLYAI_API_KEY", "")

    @classmethod
    def from_env(cls) -> TranscriptReliabilityConfig:
        """Create config from environment variables, parsing language overrides."""
        config = cls()
        # Parse language-specific overrides: TRANSCRIPT_PRIORITY_LANGUAGE_hi=deepgram,assemblyai
        for key, val in os.environ.items():
            if key.startswith("TRANSCRIPT_PRIORITY_LANGUAGE_"):
                lang = key[len("TRANSCRIPT_PRIORITY_LANGUAGE_"):].lower()
                if lang and val:
                    config.provider_language_overrides[lang] = [
                        v.strip() for v in val.split(",") if v.strip()
                    ]
        return config

    def get_priority_for_language(self, language: str) -> list[str]:
        """Get provider priority order for a specific language."""
        lang_lower = language.lower().split("-")[0] if language else ""
        if lang_lower in self.provider_language_overrides:
            return self.provider_language_overrides[lang_lower]
        return self.provider_priority_order

    def is_provider_enabled(self, provider_id: str) -> bool:
        """Check if a provider is enabled."""
        return provider_id not in self.provider_disabled
