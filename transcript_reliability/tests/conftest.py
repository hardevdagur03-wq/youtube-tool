"""Test fixtures and mocks for the Transcript Reliability Engine."""

from __future__ import annotations

import time
from typing import Any

import pytest

from models.transcript import (
    TranscriptResult,
    TranscriptSegment,
    TranscriptSource,
    TranscriptProviderName,
)
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import (
    CircuitState,
    ProviderCapability,
    ProviderStatus,
    RetryAction,
    QualityGrade,
)
from transcript_reliability.interfaces.provider import TranscriptProvider


# ---------------------------------------------------------------------------
# Sample transcripts
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="Hello and welcome to this video."),
        TranscriptSegment(start=1.0, end=2.5, duration=1.5, text="Today we are going to discuss an important topic."),
        TranscriptSegment(start=2.5, end=4.0, duration=1.5, text="This technology is changing the way we work."),
        TranscriptSegment(start=4.0, end=5.5, duration=1.5, text="Let me show you how it works in practice."),
        TranscriptSegment(start=5.5, end=7.0, duration=1.5, text="The first step is to understand the core concepts."),
        TranscriptSegment(start=7.0, end=9.0, duration=2.0, text="Once you grasp these ideas, everything becomes clearer."),
        TranscriptSegment(start=9.0, end=10.5, duration=1.5, text="Thank you for watching, and see you in the next video."),
    ]


@pytest.fixture
def sample_transcript(sample_segments) -> TranscriptResult:
    plain_text = " ".join(s.text for s in sample_segments)
    return TranscriptResult(
        success=True,
        video_id="dQw4w9WgXcQ",
        source=TranscriptSource.MANUAL,
        provider=TranscriptProviderName.YOUTUBE_MANUAL,
        language="en",
        segments=sample_segments,
        plain_text=plain_text,
        word_count=len(plain_text.split()),
        character_count=len(plain_text),
        duration_seconds=sample_segments[-1].end if sample_segments else 0,
    )


@pytest.fixture
def empty_transcript() -> TranscriptResult:
    return TranscriptResult(
        success=False,
        video_id="test123",
        error="No transcript available",
    )


@pytest.fixture
def funny_transcript() -> str:
    return (
        "Hello and welcome to this video. "
        "Today we are going to discuss an important topic. "
        "This technology is changing the way we work. "
        "Let me show you how it works in practice. "
        "The first step is to understand the core concepts. "
        "Once you grasp these ideas, everything becomes clearer. "
        "Thank you for watching, and see you in the next video."
    )


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockTranscriptProvider(TranscriptProvider):
    """Mock provider for testing with configurable behavior."""

    def __init__(
        self,
        provider_id: str = "mock",
        name: str = "Mock Provider",
        capabilities: list[ProviderCapability] | None = None,
        cost_per_minute: float = 0.0,
        should_succeed: bool = True,
        latency_ms: float = 10.0,
        fail_on_video_ids: list[str] | None = None,
        supported_languages: list[str] | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._name = name
        self._capabilities = capabilities or [ProviderCapability.CAPTIONS]
        self._cost = cost_per_minute
        self._should_succeed = should_succeed
        self._latency_ms = latency_ms
        self._fail_on_video_ids = fail_on_video_ids or []
        self._supported_languages = supported_languages or ["en", "es", "fr", "de", "hi"]
        self.call_count = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[ProviderCapability]:
        return list(self._capabilities)

    def info(self) -> Any:
        from transcript_reliability.models import ProviderInfo
        return ProviderInfo(
            provider_id=self._provider_id,
            name=self._name,
            capabilities=self.capabilities(),
            cost_per_minute=self._cost,
            enabled=True,
        )

    def cost_per_minute(self) -> float:
        return self._cost

    def health_check(self) -> Any:
        from transcript_reliability.models import ProviderHealth
        return ProviderHealth(
            provider_id=self._provider_id,
            status=ProviderStatus.HEALTHY,
            availability=1.0,
            success_rate=1.0,
        )

    def supports_language(self, language: str | None) -> bool:
        if not language:
            return True
        return language.split("-")[0] in self._supported_languages

    def get_transcript(
        self, video_id: str, language: str | None = None, **options: Any
    ) -> TranscriptResult:
        self.call_count += 1
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

        if video_id in self._fail_on_video_ids:
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error=f"{self._provider_id} failed for {video_id}",
            )

        if not self._should_succeed:
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error=f"{self._provider_id} intentionally failed",
            )

        sample_text = f"This is a sample transcript from {self._name} for video {video_id}."
        return TranscriptResult(
            success=True,
            video_id=video_id,
            source=TranscriptSource.MANUAL,
            provider=TranscriptProviderName.YOUTUBE_MANUAL,
            language=language or "en",
            segments=[TranscriptSegment(start=0.0, end=2.0, duration=2.0, text=sample_text)],
            plain_text=sample_text,
            word_count=len(sample_text.split()),
            duration_seconds=2.0,
        )


@pytest.fixture
def mock_provider() -> MockTranscriptProvider:
    return MockTranscriptProvider()


@pytest.fixture
def mock_providers() -> list[MockTranscriptProvider]:
    return [
        MockTranscriptProvider(
            provider_id="provider_a",
            name="Provider A",
            should_succeed=True,
            latency_ms=5,
        ),
        MockTranscriptProvider(
            provider_id="provider_b",
            name="Provider B",
            should_succeed=True,
            latency_ms=10,
        ),
        MockTranscriptProvider(
            provider_id="provider_c",
            name="Provider C",
            should_succeed=False,
            latency_ms=15,
        ),
    ]


@pytest.fixture
def failing_providers() -> list[MockTranscriptProvider]:
    return [
        MockTranscriptProvider(
            provider_id="fail_a",
            name="Failing A",
            should_succeed=False,
        ),
        MockTranscriptProvider(
            provider_id="fail_b",
            name="Failing B",
            should_succeed=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.fixture
def test_config() -> TranscriptReliabilityConfig:
    config = TranscriptReliabilityConfig()
    config.retry_max_retries = 2
    config.retry_base_delay = 0.01
    config.retry_max_delay = 0.1
    config.retry_backoff_factor = 2.0
    config.retry_jitter = 0.0
    config.circuit_breaker_failure_threshold = 2
    config.circuit_breaker_recovery_timeout = 0.1
    config.circuit_breaker_success_threshold = 1
    config.circuit_breaker_half_open_max_probes = 2
    config.health_window_seconds = 60.0
    config.health_window_max_requests = 100
    config.health_downgrade_threshold = 0.7
    config.health_disable_threshold = 0.3
    config.validation_min_word_count = 2
    config.validation_min_segments = 1
    config.validation_overall_threshold = 0.3
    config.provider_priority_order = ["provider_a", "provider_b", "provider_c"]
    return config
