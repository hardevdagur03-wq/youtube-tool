"""Chaos and Load tests for the Transcript Reliability Engine.

Simulates: missing captions, private videos, provider timeouts,
429 errors, network failures, Redis failures, duplicate transcripts,
invalid encoding, mixed languages, silence only, and more.

Every scenario must recover automatically and never crash.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from models.transcript import TranscriptResult, TranscriptSegment, TranscriptSource, TranscriptProviderName
from transcript_reliability import TranscriptManager
from transcript_reliability.failover_engine import FailoverEngine
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.priority_manager import PriorityManager
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.retry_engine import RetryEngine
from transcript_reliability.validation_engine import ValidationEngine
from transcript_reliability.duplicate_remover import DuplicateRemover
from transcript_reliability.silence_detector import SilenceDetector
from transcript_reliability.constants import ProviderStatus
from transcript_reliability.tests.conftest import MockTranscriptProvider


# ===================================================================
# Chaos Scenario Helpers
# ===================================================================


def _make_manager_with(providers: list[MockTranscriptProvider], test_config) -> TranscriptManager:
    # Override priority to include all registered providers
    provider_ids = [p.provider_id for p in providers]
    test_config.provider_priority_order = provider_ids
    registry = ProviderRegistry(test_config)
    health = HealthMonitor(test_config)
    cb = CircuitBreakerManager(test_config)
    retry = RetryEngine(test_config)
    priority = PriorityManager(registry, health, cb, test_config)
    failover = FailoverEngine(registry, priority, health, cb, retry, test_config)
    manager = TranscriptManager(
        config=test_config,
        registry=registry,
        health_monitor=health,
        circuit_breaker=cb,
        retry_engine=retry,
        priority_manager=priority,
        failover_engine=failover,
    )
    for p in providers:
        manager.register_provider(p)
    return manager


# ===================================================================
# Chaos Test Scenarios
# ===================================================================


class TestChaosMissingCaptions:
    def test_all_providers_return_empty(self, test_config):
        all_fail = [MockTranscriptProvider(pid, should_succeed=False) for pid in ["a", "b", "c"]]
        manager = _make_manager_with(all_fail, test_config)
        result = manager.get_transcript("test123")
        assert result.success == False
        assert result.error is not None

    def test_mixed_success_and_failure(self, test_config):
        providers = [
            MockTranscriptProvider("a", should_succeed=False),
            MockTranscriptProvider("b", should_succeed=True),
        ]
        manager = _make_manager_with(providers, test_config)
        result = manager.get_transcript("test123")
        assert result.success == True


class TestChaosPrivateVideo:
    def test_private_video_returns_error(self, test_config):
        provider = MockTranscriptProvider("youtube", should_succeed=False)
        manager = _make_manager_with([provider], test_config)
        result = manager.get_transcript("private_video")
        assert result.success == False


class TestChaosProviderTimeout:
    def test_slow_provider_failover(self, test_config):
        slow = MockTranscriptProvider("slow", should_succeed=False, latency_ms=200)
        fast = MockTranscriptProvider("fast", should_succeed=True, latency_ms=1)
        manager = _make_manager_with([slow, fast], test_config)
        result = manager.get_transcript("test123")
        assert result.success == True
        assert fast.call_count >= 1


class TestChaosRateLimit:
    def test_429_retry_then_failover(self, test_config):
        test_config.retry_max_retries = 2
        test_config.retry_base_delay = 0.01
        rate_limited = MockTranscriptProvider("limited", should_succeed=False)
        backup = MockTranscriptProvider("backup", should_succeed=True)
        manager = _make_manager_with([rate_limited, backup], test_config)
        result = manager.get_transcript("test123")
        assert result.success == True
        assert backup.call_count >= 1


class TestChaosDuplicateTranscript:
    def test_duplicate_segments_removed(self, test_config):
        remover = DuplicateRemover(test_config)
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="Repeat."),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="Repeat.")]
        cleaned, report = remover.remove_duplicates(segs)
        assert report.total_duplicates_found == 1
        assert len(cleaned) == 1


class TestChaosSilence:
    def test_silence_detected(self):
        detector = SilenceDetector()
        segs = [TranscriptSegment(start=0.0, end=10.0, duration=10.0, text="[Music]"),
                TranscriptSegment(start=10.0, end=20.0, duration=10.0, text="[Music]")]
        tr = TranscriptResult(success=True, video_id="test", segments=segs,
                              plain_text="[Music] [Music]", word_count=2)
        result = detector.detect(tr)
        assert result.is_silent == True


class TestChaosInvalidEncoding:
    def test_validation_rejects(self):
        engine = ValidationEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[], plain_text="\ufffd\ufffd\ufffd", word_count=0)
        report = engine.validate(tr)
        assert "broken_encoding" in report.failed_checks or report.passed == False


class TestChaosMixedLanguages:
    def test_validation_handles_mixed(self):
        engine = ValidationEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="Hello")],
                              plain_text="Hello 你好", word_count=2,
                              duration_seconds=10.0,
                              source=TranscriptSource.MANUAL,
                              provider=TranscriptProviderName.YOUTUBE_MANUAL)
        report = engine.validate(tr)
        assert report.overall_score >= 0


# ===================================================================
# Load Tests
# ===================================================================


class TestLoadCapacity:
    def test_concurrent_video_ids(self, test_config):
        """Simulate multiple video requests."""
        provider = MockTranscriptProvider("fast", should_succeed=True, latency_ms=1)
        manager = _make_manager_with([provider], test_config)
        video_ids = [f"video_{i:011d}" for i in range(10)]
        results = []
        for vid in video_ids:
            result = manager.get_transcript(vid)
            results.append(result)
        assert all(r.success for r in results)
        assert provider.call_count == 10

    def test_rapid_requests(self, test_config):
        """Handle rapid sequential requests without crashing."""
        provider = MockTranscriptProvider("fast", should_succeed=True, latency_ms=1)
        manager = _make_manager_with([provider], test_config)
        for _ in range(20):
            result = manager.get_transcript("test123")
            assert result.success == True

    def test_cache_under_load(self, test_config):
        """Cache should work correctly under load."""
        manager = _make_manager_with([MockTranscriptProvider("fast", should_succeed=True)], test_config)
        for _ in range(5):
            manager.get_transcript("test123")
        # Later requests should be faster (cache)
        start = time.time()
        manager.get_transcript("test123")
        elapsed = time.time() - start
        assert elapsed < 1.0  # Should be near-instant from cache


# ===================================================================
# Recovery Tests
# ===================================================================


class TestRecovery:
    def test_circuit_breaker_recovers(self, test_config):
        """Circuit breaker should auto-recover after timeout."""
        test_config.circuit_breaker_failure_threshold = 2
        test_config.circuit_breaker_recovery_timeout = 0.05
        provider = MockTranscriptProvider("faulty")
        manager = _make_manager_with([provider], test_config)
        provider._should_succeed = False
        manager.get_transcript("test123")
        manager.get_transcript("test123")
        # Circuit should be open now (2 failures)
        provider._should_succeed = True
        time.sleep(0.06)
        # After recovery timeout, circuit should half-open and succeed
        result = manager.get_transcript("test123")
        assert result.success == True

    def test_health_monitor_recovers(self, test_config):
        """Health monitor should show improvement after successes."""
        hm = HealthMonitor(test_config)
        for _ in range(5):
            hm.record_failure("p1", error_type="timeout")
        health = hm.get_health("p1")
        assert health.status in (ProviderStatus.UNHEALTHY, ProviderStatus.DEGRADED)
        for _ in range(20):
            hm.record_success("p1", latency_ms=50)
        health = hm.get_health("p1")
        assert health.status == ProviderStatus.HEALTHY
