"""Tests for the Provider Registry."""

from __future__ import annotations

import pytest

from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.exceptions import ProviderNotFoundError, ProviderDisabledError
from transcript_reliability.constants import ProviderCapability
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestProviderRegistry:
    def test_register_and_get(self, mock_provider):
        registry = ProviderRegistry()
        registry.register(mock_provider)
        retrieved = registry.get("mock")
        assert retrieved.provider_id == "mock"

    def test_get_not_found(self):
        registry = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            registry.get("nonexistent")

    def test_unregister(self, mock_provider):
        registry = ProviderRegistry()
        registry.register(mock_provider)
        registry.unregister("mock")
        with pytest.raises(ProviderNotFoundError):
            registry.get("mock")

    def test_count(self, mock_providers):
        registry = ProviderRegistry()
        for p in mock_providers:
            registry.register(p)
        assert registry.count == 3

    def test_list_all(self, mock_providers):
        registry = ProviderRegistry()
        for p in mock_providers:
            registry.register(p)
        all_p = registry.list_all()
        assert len(all_p) == 3

    def test_list_enabled(self, mock_providers, test_config):
        registry = ProviderRegistry(test_config)
        for p in mock_providers:
            registry.register(p)
        enabled = registry.list_enabled()
        assert len(enabled) == 3

    def test_list_enabled_with_disabled(self, mock_providers, test_config):
        test_config.provider_disabled = ["provider_c"]
        registry = ProviderRegistry(test_config)
        for p in mock_providers:
            registry.register(p)
        enabled = registry.list_enabled()
        assert len(enabled) == 2
        assert all(p.provider_id != "provider_c" for p in enabled)

    def test_list_enabled_with_language(self, mock_providers, test_config):
        provider_no_hi = MockTranscriptProvider(
            provider_id="no_hi", name="No Hindi",
            supported_languages=["en", "es"],
        )
        provider_has_hi = MockTranscriptProvider(
            provider_id="has_hi", name="Has Hindi",
            supported_languages=["en", "hi"],
        )
        registry = ProviderRegistry(test_config)
        registry.register(provider_no_hi)
        registry.register(provider_has_hi)
        enabled = registry.list_enabled(language="hi")
        assert len(enabled) == 1
        assert enabled[0].provider_id == "has_hi"

    def test_list_by_capability(self, mock_providers):
        stt_provider = MockTranscriptProvider(
            provider_id="stt_only", name="STT Only",
            capabilities=[ProviderCapability.STT],
        )
        registry = ProviderRegistry()
        for p in mock_providers:
            registry.register(p)
        registry.register(stt_provider)
        stt_providers = registry.list_by_capability(ProviderCapability.STT)
        assert len(stt_providers) == 1
        assert stt_providers[0].provider_id == "stt_only"

    def test_get_info(self, mock_provider):
        registry = ProviderRegistry()
        registry.register(mock_provider)
        info = registry.get_info("mock")
        assert info.provider_id == "mock"
        assert info.name == "Mock Provider"

    def test_list_info(self, mock_providers):
        registry = ProviderRegistry()
        for p in mock_providers:
            registry.register(p)
        infos = registry.list_info()
        assert len(infos) == 3

    def test_provider_ids(self, mock_providers):
        registry = ProviderRegistry()
        for p in mock_providers:
            registry.register(p)
        assert set(registry.provider_ids) == {"provider_a", "provider_b", "provider_c"}

    def test_get_enabled(self, mock_provider, test_config):
        registry = ProviderRegistry(test_config)
        registry.register(mock_provider)
        provider = registry.get_enabled("mock")
        assert provider.provider_id == "mock"

    def test_get_enabled_disabled(self, mock_provider, test_config):
        test_config.provider_disabled = ["mock"]
        registry = ProviderRegistry(test_config)
        registry.register(mock_provider)
        with pytest.raises(ProviderDisabledError):
            registry.get_enabled("mock")

    def test_get_enabled_language_not_supported(self, test_config):
        provider = MockTranscriptProvider(
            provider_id="en_only", name="English Only",
            supported_languages=["en"],
        )
        registry = ProviderRegistry(test_config)
        registry.register(provider)
        with pytest.raises(ProviderDisabledError):
            registry.get_enabled("en_only", language="hi")

    def test_overwrite_provider(self, mock_provider):
        registry = ProviderRegistry()
        registry.register(mock_provider)
        registry.register(mock_provider)  # Should not raise
        assert registry.count == 1
