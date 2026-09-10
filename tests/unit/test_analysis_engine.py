from __future__ import annotations

import pytest
from providers.llm_provider import MockProvider, ProviderConfig


class TestContentAnalysisService:
    def _make_service(self):
        """Create a ContentAnalysisService with a MockProvider to avoid real API calls."""
        from services.content_analysis_service import ContentAnalysisService
        return ContentAnalysisService(provider=MockProvider(ProviderConfig()))

    def test_analyze(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result is not None
        assert result.primary_topic

    def test_analyze_empty_text(self):
        svc = self._make_service()
        result = svc.analyze("", "vtest001234")
        assert result.success is False
        assert result.error is not None

    def test_analyze_invalid_video_id(self):
        svc = self._make_service()
        result = svc.analyze("some transcript text", "bad-id")
        assert result.success is False
        assert result.error is not None

    def test_analyze_result_has_summary(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.summary is not None

    def test_analyze_result_has_keywords(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.keywords is not None

    def test_analyze_result_has_entities(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.entities is not None

    def test_analyze_result_has_quality_scores(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.quality is not None
        assert 0 <= result.quality.confidence <= 1

    def test_analyze_result_has_outline(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.outline is not None
        assert isinstance(result.outline.sections, list)

    def test_analyze_search_intent_default(self, sample_transcript):
        svc = self._make_service()
        result = svc.analyze(sample_transcript["plain_text"], "vtest001234")
        assert result.search_intent is not None
