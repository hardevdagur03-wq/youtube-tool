"""Tests for config, models, exceptions, and constants."""

from __future__ import annotations

import os

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import (
    CircuitState,
    ProviderCapability,
    ProviderStatus,
    QualityGrade,
    RetryAction,
    VALIDATION_CHECKS,
    DUPLICATE_STRATEGIES,
    SILENCE_PATTERNS,
    CLEANING_STAGES,
    VERSION_TYPES,
    PROVIDER_COST_PER_MINUTE,
    PERFORMANCE_TARGETS,
)
from transcript_reliability.exceptions import (
    TranscriptReliabilityError,
    ProviderNotFoundError,
    ProviderDisabledError,
    ProviderUnhealthyError,
    CircuitBreakerOpenError,
    AllProvidersFailedError,
    RetryBudgetExhaustedError,
    ValidationRejectedError,
    DuplicateTranscriptError,
    SilenceDetectedError,
    CacheError,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderTimeoutError,
    VersionNotFoundError,
)
from transcript_reliability.models import (
    ProviderInfo,
    ProviderHealth,
    QualityScore,
    LanguageDetectionResult,
    ValidationReport,
    SilenceResult,
    DuplicateReport,
    VersionRecord,
    CacheEntry,
    HealthRecord,
    RetryDecision,
    RetryAttempt,
    RetryPolicy,
    CircuitBreakerState,
    TranscriptMetrics,
    QualityDimension,
)


class TestConfig:
    def test_default_config(self):
        config = TranscriptReliabilityConfig()
        assert len(config.provider_priority_order) == 6
        assert config.provider_priority_order[0] == "youtube_manual"
        assert config.retry_max_retries == 3
        assert config.circuit_breaker_failure_threshold == 5
        assert config.health_window_seconds == 60.0

    def test_from_env(self):
        config = TranscriptReliabilityConfig.from_env()
        assert config.retry_max_retries >= 3
        # Test that env parsing of language overrides works
        os.environ["TRANSCRIPT_PRIORITY_LANGUAGE_HI"] = "deepgram,assemblyai"
        try:
            config2 = TranscriptReliabilityConfig.from_env()
            assert config2.provider_language_overrides.get("hi") == ["deepgram", "assemblyai"]
        finally:
            os.environ.pop("TRANSCRIPT_PRIORITY_LANGUAGE_HI", None)

    def test_get_priority_for_language_default(self):
        config = TranscriptReliabilityConfig()
        priority = config.get_priority_for_language("en")
        assert priority == config.provider_priority_order

    def test_get_priority_for_language_override(self):
        config = TranscriptReliabilityConfig()
        config.provider_language_overrides["hi"] = ["deepgram", "assemblyai"]
        priority = config.get_priority_for_language("hi")
        assert priority == ["deepgram", "assemblyai"]

    def test_is_provider_enabled(self):
        config = TranscriptReliabilityConfig()
        assert config.is_provider_enabled("youtube_manual") == True
        config.provider_disabled = ["youtube_manual"]
        assert config.is_provider_enabled("youtube_manual") == False

    def test_language_short_code(self):
        config = TranscriptReliabilityConfig()
        config.provider_language_overrides["hi"] = ["deepgram"]
        priority = config.get_priority_for_language("hi-IN")
        assert priority == ["deepgram"]


class TestEnums:
    def test_circuit_state_values(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_provider_status_values(self):
        assert ProviderStatus.HEALTHY.value == "healthy"
        assert ProviderStatus.DEGRADED.value == "degraded"
        assert ProviderStatus.UNHEALTHY.value == "unhealthy"

    def test_quality_grade_values(self):
        assert QualityGrade.EXCELLENT.value == "excellent"
        assert QualityGrade.GOOD.value == "good"
        assert QualityGrade.REJECT.value == "reject"

    def test_retry_action_values(self):
        assert RetryAction.RETRY.value == "retry"
        assert RetryAction.FAILOVER.value == "failover"
        assert RetryAction.ABORT.value == "abort"

    def test_provider_capability_values(self):
        assert ProviderCapability.CAPTIONS.value == "captions"
        assert ProviderCapability.STT.value == "stt"


class TestConstants:
    def test_validation_checks_count(self):
        assert len(VALIDATION_CHECKS) == 12

    def test_duplicate_strategies_count(self):
        assert len(DUPLICATE_STRATEGIES) == 6

    def test_silence_patterns_count(self):
        assert len(SILENCE_PATTERNS) == 6

    def test_cleaning_stages_count(self):
        assert len(CLEANING_STAGES) == 10

    def test_version_types_count(self):
        assert len(VERSION_TYPES) == 7

    def test_provider_cost_present(self):
        assert "youtube_manual" in PROVIDER_COST_PER_MINUTE
        assert "deepgram" in PROVIDER_COST_PER_MINUTE
        assert PROVIDER_COST_PER_MINUTE["youtube_manual"] == 0.0
        assert PROVIDER_COST_PER_MINUTE["deepgram"] > 0

    def test_performance_targets_present(self):
        assert "manual_caption" in PERFORMANCE_TARGETS
        assert "cache_hit" in PERFORMANCE_TARGETS


class TestExceptions:
    def test_base_exception(self):
        assert issubclass(TranscriptReliabilityError, Exception)

    def test_provider_not_found(self):
        exc = ProviderNotFoundError("test")
        assert str(exc) == "test"
        assert isinstance(exc, TranscriptReliabilityError)

    def test_all_exception_types(self):
        for exc_cls in [
            ProviderNotFoundError,
            ProviderDisabledError,
            ProviderUnhealthyError,
            CircuitBreakerOpenError,
            AllProvidersFailedError,
            RetryBudgetExhaustedError,
            ValidationRejectedError,
            DuplicateTranscriptError,
            SilenceDetectedError,
            CacheError,
            ProviderAuthError,
            ProviderQuotaError,
            ProviderTimeoutError,
            VersionNotFoundError,
        ]:
            instance = exc_cls("test message")
            assert str(instance) == "test message"
            assert isinstance(instance, TranscriptReliabilityError)


class TestModels:
    def test_provider_info_defaults(self):
        pi = ProviderInfo(provider_id="test", name="Test")
        assert pi.provider_id == "test"
        assert pi.name == "Test"
        assert pi.enabled == True
        assert pi.cost_per_minute == 0.0

    def test_provider_health(self):
        ph = ProviderHealth(provider_id="p1")
        assert ph.provider_id == "p1"
        assert ph.status == ProviderStatus.UNKNOWN
        assert ph.success_rate == 1.0

    def test_quality_score(self):
        qs = QualityScore(overall=0.85, grade=QualityGrade.GOOD)
        assert qs.overall == 0.85
        assert qs.grade == QualityGrade.GOOD
        assert qs.generated_at is not None

    def test_language_detection_result(self):
        ld = LanguageDetectionResult(primary="en", confidence=0.95)
        assert ld.primary == "en"
        assert ld.confidence == 0.95
        assert ld.detection_source == "heuristic"

    def test_validation_report(self):
        vr = ValidationReport(passed=True, overall_score=0.9)
        assert vr.passed == True
        assert vr.overall_score == 0.9

    def test_silence_result(self):
        sr = SilenceResult(is_silent=False)
        assert sr.is_silent == False
        assert sr.confidence == 0.0

    def test_duplicate_report(self):
        dr = DuplicateReport(total_duplicates_found=5, total_duplicates_removed=3)
        assert dr.total_duplicates_found == 5
        assert dr.total_duplicates_removed == 3

    def test_version_record(self):
        vr = VersionRecord(version_id="v1", transcript_id="t1", version_type="original")
        assert vr.version_id == "v1"
        assert vr.version_number == 1

    def test_cache_entry(self):
        ce = CacheEntry(cache_key="k1", video_id="v1")
        assert ce.cache_key == "k1"
        assert ce.hit_count == 0

    def test_health_record(self):
        hr = HealthRecord(timestamp=100.0, success=True, latency_ms=50.0)
        assert hr.success == True
        assert hr.latency_ms == 50.0

    def test_retry_decision(self):
        rd = RetryDecision(action=RetryAction.RETRY, delay_seconds=2.0)
        assert rd.action == RetryAction.RETRY
        assert rd.delay_seconds == 2.0

    def test_retry_policy_defaults(self):
        rp = RetryPolicy()
        assert rp.max_retries == 3
        assert rp.retry_on_auth_error == False

    def test_circuit_breaker_state(self):
        cbs = CircuitBreakerState(provider_id="p1")
        assert cbs.state == CircuitState.CLOSED

    def test_transcript_metrics(self):
        tm = TranscriptMetrics(video_id="v1")
        assert tm.video_id == "v1"
        assert tm.cache_hit == False
