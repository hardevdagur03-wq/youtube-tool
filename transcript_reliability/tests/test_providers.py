"""Tests for Provider implementations and plugin system."""

from __future__ import annotations

from transcript_reliability.providers import get_default_providers, get_default_provider_map, discover_plugins
from transcript_reliability.providers.youtube_manual import YouTubeManualProvider
from transcript_reliability.providers.youtube_auto import YouTubeAutoProvider
from transcript_reliability.providers.whisper_local import WhisperLocalProvider
from transcript_reliability.providers.whisper_api import WhisperAPIProvider
from transcript_reliability.providers.deepgram import DeepgramProvider
from transcript_reliability.providers.assemblyai import AssemblyAIProvider
from transcript_reliability.providers.plugin import register_external_provider
from transcript_reliability.constants import ProviderCapability
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestDefaultProviders:
    def test_all_providers_loaded(self):
        providers = get_default_providers()
        assert len(providers) == 6

    def test_provider_map(self):
        pmap = get_default_provider_map()
        assert "youtube_manual" in pmap
        assert "youtube_auto" in pmap
        assert "whisper_local" in pmap
        assert "whisper_api" in pmap
        assert "deepgram" in pmap
        assert "assemblyai" in pmap

    def test_all_implement_interface(self):
        for p in get_default_providers():
            assert isinstance(p, TranscriptProvider)

    def test_all_have_unique_ids(self):
        ids = [p.provider_id for p in get_default_providers()]
        assert len(ids) == len(set(ids))

    def test_all_have_names(self):
        for p in get_default_providers():
            assert p.name and len(p.name) > 0

    def test_all_have_capabilities(self):
        for p in get_default_providers():
            caps = p.capabilities()
            assert len(caps) >= 1

    def test_all_have_cost(self):
        for p in get_default_providers():
            assert p.cost_per_minute() >= 0


class TestYouTubeManualProvider:
    def test_provider_metadata(self):
        p = YouTubeManualProvider()
        assert p.provider_id == "youtube_manual"
        assert p.name == "YouTube Manual Captions"
        assert ProviderCapability.CAPTIONS in p.capabilities()

    def test_graceful_degradation(self):
        p = YouTubeManualProvider()
        result = p.get_transcript("dQw4w9WgXcQ")
        assert hasattr(result, 'success')

    def test_info(self):
        p = YouTubeManualProvider()
        info = p.info()
        assert info.provider_id == "youtube_manual"
        assert info.cost_per_minute == 0.0

    def test_supports_language(self):
        p = YouTubeManualProvider()
        assert p.supports_language("en") == True
        assert p.supports_language("hi") == True


class TestYouTubeAutoProvider:
    def test_provider_metadata(self):
        p = YouTubeAutoProvider()
        assert p.provider_id == "youtube_auto"
        assert p.name == "YouTube Auto Captions"
        assert ProviderCapability.CAPTIONS in p.capabilities()

    def test_graceful_degradation(self):
        p = YouTubeAutoProvider()
        result = p.get_transcript("test123")
        assert hasattr(result, 'success')

    def test_supports_language(self):
        p = YouTubeAutoProvider()
        assert p.supports_language("en") == True


class TestWhisperLocalProvider:
    def test_provider_metadata(self):
        p = WhisperLocalProvider()
        assert p.provider_id == "whisper_local"
        assert p.name == "Whisper Local"

    def test_graceful_degradation(self):
        p = WhisperLocalProvider()
        result = p.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert result.error is not None


class TestWhisperAPIProvider:
    def test_provider_metadata(self):
        p = WhisperAPIProvider()
        assert p.provider_id == "whisper_api"
        assert p.name == "Whisper API (OpenAI)"

    def test_graceful_degradation(self):
        p = WhisperAPIProvider()
        result = p.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "API" in (result.error or "")


class TestDeepgramProvider:
    def test_provider_metadata(self):
        p = DeepgramProvider()
        assert p.provider_id == "deepgram"
        assert p.name == "Deepgram"
        assert ProviderCapability.ASYNC in p.capabilities()

    def test_graceful_degradation(self):
        p = DeepgramProvider()
        result = p.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "API key" in (result.error or "")


class TestAssemblyAIProvider:
    def test_provider_metadata(self):
        p = AssemblyAIProvider()
        assert p.provider_id == "assemblyai"
        assert p.name == "AssemblyAI"
        assert ProviderCapability.ASYNC in p.capabilities()

    def test_graceful_degradation(self):
        p = AssemblyAIProvider()
        result = p.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "API key" in (result.error or "")


class TestPluginSystem:
    def test_discover_no_plugins(self):
        plugins = discover_plugins()
        assert len(plugins) == 0

    def test_register_external_provider(self):
        provider = register_external_provider(MockTranscriptProvider)
        assert provider.provider_id == "mock"
        assert provider.name == "Mock Provider"

    def test_register_invalid_provider(self):
        import pytest
        with pytest.raises(TypeError):
            register_external_provider(str)


class TestBaseProvider:
    def test_base_health_check(self):
        from transcript_reliability.providers.base import BaseTranscriptProvider
        p = BaseTranscriptProvider()
        health = p.health_check()
        assert health.provider_id == "base"

    def test_default_language_support(self):
        from transcript_reliability.providers.base import BaseTranscriptProvider
        p = BaseTranscriptProvider()
        assert p.supports_language("en") == True
        assert p.supports_language("fr") == True
