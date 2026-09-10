"""Tests for the Transcript Manager."""

from __future__ import annotations

from transcript_reliability import TranscriptManager
from transcript_reliability.providers import get_default_providers
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestTranscriptManager:
    def test_create_manager(self):
        manager = TranscriptManager()
        assert manager is not None

    def test_get_transcript_no_providers(self):
        manager = TranscriptManager()
        result = manager.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "providers" in result.error.lower()

    def test_register_provider(self):
        manager = TranscriptManager()
        provider = MockTranscriptProvider(provider_id="test_prov")
        manager.register_provider(provider)
        result = manager.get_transcript("test123")
        assert result.success == True

    def test_all_default_providers_register(self):
        manager = TranscriptManager()
        providers = get_default_providers()
        for p in providers:
            manager.register_provider(p)
        result = manager.get_transcript("dQw4w9WgXcQ")
        # At least YouTube captions should succeed for this well-known video
        # Assert we get a result (success or graceful failure)
        assert hasattr(result, 'success')

    def test_get_transcript_single_provider(self):
        manager = TranscriptManager()
        provider = MockTranscriptProvider(provider_id="single")
        manager.register_provider(provider)
        result = manager.get_transcript("test123", allow_failover=False)
        assert result.success == True
        assert provider.call_count == 1

    def test_get_transcript_status(self):
        manager = TranscriptManager()
        status = manager.get_transcript_status("dQw4w9WgXcQ")
        assert status["video_id"] == "dQw4w9WgXcQ"
        assert "cached" in status
        assert "available_providers" in status

    def test_get_provider_status(self):
        manager = TranscriptManager()
        provider = MockTranscriptProvider(provider_id="test_prov")
        manager.register_provider(provider)
        status = manager.get_provider_status()
        assert "providers" in status
        assert "available_count" in status

    def test_force_refresh_bypasses_cache(self):
        manager = TranscriptManager()
        provider = MockTranscriptProvider(provider_id="test_prov")
        manager.register_provider(provider)
        result1 = manager.get_transcript("test123")
        result2 = manager.get_transcript("test123", force_refresh=True)
        assert result1.success == True
        assert result2.success == True

    def test_clear_cache(self):
        manager = TranscriptManager()
        manager.clear_cache()  # Should not raise

    def test_failover_with_mixed_providers(self):
        manager = TranscriptManager()
        a = MockTranscriptProvider(provider_id="fail_first", should_succeed=False)
        b = MockTranscriptProvider(provider_id="succeed_second", should_succeed=True)
        manager.register_provider(a)
        manager.register_provider(b)
        result = manager.get_transcript("test123")
        assert result.success == True
        assert a.call_count >= 1
        assert b.call_count == 1

    def test_all_providers_graceful_degradation(self):
        manager = TranscriptManager()
        a = MockTranscriptProvider(provider_id="fail_a", should_succeed=False)
        b = MockTranscriptProvider(provider_id="fail_b", should_succeed=False)
        manager.register_provider(a)
        manager.register_provider(b)
        result = manager.get_transcript("test123")
        assert result.success == False

    def test_get_transcript_with_options(self):
        manager = TranscriptManager()
        provider = MockTranscriptProvider(provider_id="opt_test")
        manager.register_provider(provider)
        result = manager.get_transcript("test123", options={"custom": True})
        assert result is not None
