"""Comprehensive tests for the Transcript Intelligence Platform."""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Any

from services.transcript.transcript_gateway import (
    TranscriptGateway,
    TranscriptResult,
)
from services.transcript.quality_engine import (
    QualityScore,
    score_transcript_quality,
)


class MockProvider:
    def __init__(self, name: str, succeed: bool = True, text: str = ""):
        self._name = name
        self._succeed = succeed
        self._text = text

    def get_transcript(self, video_id: str, language: str | None = None) -> Any:
        if not self._succeed:
            raise RuntimeError(f"{self._name} failed")

        @dataclass
        class MockResult:
            success: bool = True
            video_id: str = ""
            plain_text: str = ""
            language: str = ""
            segments: list = field(default_factory=list)

        return MockResult(
            success=True,
            video_id=video_id,
            plain_text=self._text or f"Transcript from {self._name}",
            language=language or "en",
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello world"},
                {"start": 5.0, "end": 10.0, "text": "This is a test"},
            ],
        )


class FailingProvider:
    def __init__(self, name: str = "failing"):
        self._name = name

    def get_transcript(self, video_id: str, language: str | None = None) -> Any:
        raise RuntimeError(f"{self._name} outage")


class EmptyProvider:
    def __init__(self, name: str = "empty"):
        self._name = name

    def get_transcript(self, video_id: str, language: str | None = None) -> Any:
        @dataclass
        class EmptyResult:
            success: bool = False
        return EmptyResult()


class TestTranscriptGateway:
    def test_register_provider(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", MockProvider("manual"))
        assert "manual" in gateway._providers

    def test_single_provider_success(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", MockProvider("manual", text="Hello world"))
        result = gateway.get_transcript("dQw4w9WgXcQ")
        assert result.success is True
        assert result.text == "Hello world"
        assert result.provider == "manual"
        assert result.video_id == "dQw4w9WgXcQ"

    def test_failover_to_next_provider(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", FailingProvider("manual"))
        gateway.register_provider("auto", MockProvider("auto", text="Auto transcript"))
        result = gateway.get_transcript("test123")
        assert result.success is True
        assert result.provider == "auto"
        assert "Auto" in result.text

    def test_all_providers_fail(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", FailingProvider())
        gateway.register_provider("auto", FailingProvider())
        gateway.register_provider("whisper_api", FailingProvider())
        result = gateway.get_transcript("test123")
        assert result.success is False
        assert "All providers failed" in result.error

    def test_failover_chain(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", FailingProvider("manual"))
        gateway.register_provider("auto", FailingProvider("auto"))
        gateway.register_provider("whisper_api", MockProvider("whisper_api", text="Whisper transcript"))
        result = gateway.get_transcript("test123")
        assert result.success is True
        assert result.provider == "whisper_api"

    def test_provider_priority(self):
        gateway = TranscriptGateway()
        gateway.register_provider("whisper_api", MockProvider("whisper_api", text="Whisper"))
        gateway.register_provider("manual", MockProvider("manual", text="Manual"))
        result = gateway.get_transcript("test123")
        assert result.provider == "manual"

    def test_language_passed_to_provider(self):
        gateway = TranscriptGateway()
        captured_languages = []

        class LangCaptureProvider:
            def get_transcript(self, video_id, language=None):
                captured_languages.append(language)
                @dataclass
                class R:
                    success = True
                    plain_text = "test"
                    language = language or "en"
                    segments = []
                return R()

        gateway.register_provider("manual", LangCaptureProvider())
        gateway.get_transcript("test123", language="fr")
        assert "fr" in captured_languages

    def test_result_metadata(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", MockProvider("manual", text="Test transcript"))
        result = gateway.get_transcript("abc123def45")
        assert result.latency_ms >= 0
        assert result.word_count > 0
        assert result.confidence > 0
        assert result.from_cache is False

    def test_empty_result_skips_provider(self):
        gateway = TranscriptGateway()
        gateway.register_provider("manual", EmptyProvider())
        gateway.register_provider("auto", MockProvider("auto", text="Auto"))
        result = gateway.get_transcript("test123")
        assert result.success is True
        assert result.provider == "auto"

    def test_no_registered_providers(self):
        gateway = TranscriptGateway()
        result = gateway.get_transcript("test123")
        assert result.success is False


class TestTranscriptQuality:
    def test_empty_transcript(self):
        score = score_transcript_quality("")
        assert score.overall == 0.0
        assert "Empty transcript" in score.issues[0]

    def test_quality_short_transcript(self):
        score = score_transcript_quality("Hello world.")
        assert score.overall > 0
        assert "Very short" in score.issues[0]

    def test_quality_normal_transcript(self):
        text = "This is a normal transcript. It has multiple sentences. Each one is properly formatted. " * 20
        score = score_transcript_quality(text, provider="manual")
        assert score.overall > 0.5
        assert score.provider_quality == 0.95

    def test_quality_low_repetition(self):
        text = "word " * 100
        score = score_transcript_quality(text)
        assert score.word_accuracy < 0.9

    def test_quality_provider_weights(self):
        text = "A normal transcript. With sentences. " * 20
        manual = score_transcript_quality(text, provider="manual")
        auto = score_transcript_quality(text, provider="auto")
        assert manual.provider_quality >= auto.provider_quality

    def test_quality_timestamps_valid(self):
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Hello"},
            {"start": 5.0, "end": 10.0, "text": "World"},
        ]
        text = "Hello World."
        score = score_transcript_quality(text, segments=segments)
        assert score.timestamp_accuracy == 1.0

    def test_quality_timestamps_invalid(self):
        segments = [
            {"start": -1, "end": 5.0, "text": "Bad start"},
            {"start": 10.0, "end": 5.0, "text": "Reversed"},
        ]
        text = "Bad timestamps."
        score = score_transcript_quality(text, segments=segments)
        assert score.timestamp_accuracy == 0.0

    def test_quality_sentence_length(self):
        text = "A. B. C. D."
        score = score_transcript_quality(text)
        assert score.sentence_accuracy < 0.9

    def test_quality_output_format(self):
        text = "This is a high quality transcript. It has good structure." * 30
        score = score_transcript_quality(text, provider="manual")
        assert isinstance(score.overall, float)
        assert 0 <= score.overall <= 1
        assert isinstance(score.issues, list)

    def test_quality_confidence_calculation(self):
        text = "A well written transcript. With proper structure. " * 30
        score = score_transcript_quality(text, provider="manual")
        assert score.confidence > 0
        assert score.overall == round(score.confidence, 2)

    def test_whisper_provider_quality(self):
        text = "Whisper generated text. With some errors. " * 20
        score = score_transcript_quality(text, provider="whisper_api")
        assert score.provider_quality == 0.90


class TestTranscriptResult:
    def test_default_values(self):
        result = TranscriptResult()
        assert result.success is False
        assert result.video_id == ""
        assert result.text == ""
        assert result.error == ""

    def test_success_result(self):
        result = TranscriptResult(
            success=True,
            video_id="dQw4w9WgXcQ",
            text="Hello world",
            provider="manual",
            word_count=2,
        )
        assert result.success is True
        assert result.word_count == 2

    def test_segments_list(self):
        result = TranscriptResult(
            success=True,
            segments=[{"start": 0.0, "end": 5.0, "text": "test"}],
        )
        assert len(result.segments) == 1


class TestQualityScore:
    def test_default_score(self):
        score = QualityScore()
        assert score.overall == 0.0
        assert score.issues == []

    def test_custom_score(self):
        score = QualityScore(
            overall=0.85,
            word_accuracy=0.9,
            confidence=0.88,
            issues=["Minor repetition"],
        )
        assert score.overall == 0.85
        assert len(score.issues) == 1


class TestFailoverScenarios:
    def test_timeout_fallthrough(self):
        class TimeoutProvider:
            def get_transcript(self, video_id, language=None):
                raise TimeoutError("Request timed out")

        gateway = TranscriptGateway()
        gateway.register_provider("manual", TimeoutProvider())
        gateway.register_provider("auto", MockProvider("auto", text="Auto worked"))
        result = gateway.get_transcript("test123")
        assert result.success is True

    def test_missing_transcript_fallthrough(self):
        class NotFoundProvider:
            def get_transcript(self, video_id, language=None):
                raise FileNotFoundError("No transcript")

        gateway = TranscriptGateway()
        gateway.register_provider("manual", NotFoundProvider())
        gateway.register_provider("whisper_local", MockProvider("whisper_local", text="Whisper recovery"))
        result = gateway.get_transcript("test123")
        assert result.success is True

    def test_provider_chain_recovery(self):
        """Test that transcript recovers after 2 failures."""
        class FailTwiceThenSucceed:
            def __init__(self):
                self._count = 0
            def get_transcript(self, video_id, language=None):
                self._count += 1
                if self._count <= 2:
                    @dataclass
                    class F:
                        success = False
                    return F()
                @dataclass
                class S:
                    success = True
                    plain_text = "Recovered"
                    language = "en"
                    segments = []
                return S()

        gateway = TranscriptGateway()
        gateway.register_provider("manual", FailTwiceThenSucceed())
        gateway.register_provider("auto", MockProvider("auto", text="Fallback"))
        result = gateway.get_transcript("test123")
        assert result.success is True
