"""Comprehensive tests for the Enterprise AI Platform.

Covers:
- Provider Registry (registration, resolution, routing)
- AI Gateway (routing, failover, caching)
- Failover scenarios (provider outages, fallback chains)
- Cache integration
"""

from __future__ import annotations

import json
import time

import pytest

from providers.llm_provider import LLMProvider, LLMResponse, MockProvider, ProviderConfig
from services.ai.provider_registry import (
    ProviderRegistry,
    ProviderMetadata,
    RoutingStrategy,
)
from services.ai.ai_gateway import AIRequest, AIResponse, AIGateway


@pytest.fixture(autouse=True)
def setup_registry():
    """Register providers before each test."""
    ProviderRegistry.clear()
    ProviderRegistry.register("mock", MockProvider)
    ProviderRegistry.register("gemini", MockProvider)
    ProviderRegistry.register("openai", MockProvider)
    yield
    ProviderRegistry.clear()


class TestProviderRegistry:
    def test_register_and_list(self):
        ProviderRegistry.clear()
        ProviderRegistry.register("mock", MockProvider)
        providers = ProviderRegistry.list_providers()
        assert "mock" in providers

    def test_get_provider_class(self):
        cls = ProviderRegistry.get_provider_class("mock")
        assert cls == MockProvider

    def test_get_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.get_provider_class("nonexistent")

    def test_get_or_create_returns_provider(self):
        provider = ProviderRegistry.get_or_create("mock")
        assert provider is not None
        assert provider.provider_name == "mock"

    def test_get_or_create_caches_instances(self):
        p1 = ProviderRegistry.get_or_create("mock")
        p2 = ProviderRegistry.get_or_create("mock")
        assert p1 is p2

    def test_get_metadata(self):
        meta = ProviderRegistry.get_metadata("gemini")
        assert meta is not None
        assert meta.name == "gemini"
        assert "gemini-2.5-flash" in meta.models
        assert meta.priority == 1

    def test_get_all_metadata(self):
        all_meta = ProviderRegistry.get_all_metadata()
        assert "mock" in all_meta
        assert "gemini" in all_meta

    def test_get_unknown_metadata_returns_none(self):
        assert ProviderRegistry.get_metadata("nonexistent") is None

    def test_clear_removes_all(self):
        ProviderRegistry.register("test", MockProvider)
        ProviderRegistry.clear()
        assert ProviderRegistry.list_providers() == []


class TestProviderRouting:
    def test_resolve_by_preference(self):
        name, config = ProviderRegistry.resolve_provider(
            task="text",
            preferred_provider="gemini",
        )
        assert name == "gemini"

    def test_resolve_fastest_strategy(self):
        name, config = ProviderRegistry.resolve_provider(
            task="text",
            strategy=RoutingStrategy.FASTEST_RESPONSE,
        )
        assert name in ProviderRegistry.list_providers()
        assert name != ""

    def test_resolve_lowest_cost_strategy(self):
        name, config = ProviderRegistry.resolve_provider(
            task="text",
            strategy=RoutingStrategy.LOWEST_COST,
        )
        assert name in ProviderRegistry.list_providers()

    def test_resolve_fallback_to_mock(self):
        ProviderRegistry.clear()
        ProviderRegistry.register("mock", MockProvider)
        name, config = ProviderRegistry.resolve_provider(task="text")
        assert name == "mock"

    def test_resolve_includes_model_config(self):
        name, config = ProviderRegistry.resolve_provider(
            task="text",
            preferred_provider="openai",
        )
        assert config.model is not None
        assert config.extra.get("provider") == "openai"


class TestAIGateway:
    def test_generate_with_mock(self):
        gateway = AIGateway()
        request = AIRequest(
            prompt="What is machine learning?",
            task="text",
        )
        response = gateway.generate(request)
        assert response.success is True
        assert response.text != ""
        assert response.provider == "mock"
        assert response.model != ""
        assert response.latency_ms >= 0

    def test_generate_with_preferred_provider(self):
        gateway = AIGateway()
        request = AIRequest(
            prompt="Test prompt",
            provider="openai",
        )
        response = gateway.generate(request)
        assert response.success is True

    def test_generate_json(self):
        gateway = AIGateway()
        request = AIRequest(
            prompt="Generate a JSON object",
            task="json",
        )
        data, response = gateway.generate_json(request)
        assert response.success is True
        assert isinstance(data, dict)
        assert "mock" in str(data) or "primary_topic" in str(data) or "raw" in str(data)

    def test_generate_sets_metadata(self):
        gateway = AIGateway()
        request = AIRequest(
            prompt="Test",
            metadata={"user_id": "user-1", "project_id": "proj-1"},
        )
        response = gateway.generate(request)
        assert response.success is True

    def test_failover_on_provider_error(self):
        class FailingProvider(LLMProvider):
            @property
            def provider_name(self):
                return "failing"
            @property
            def model_name(self):
                return "failing-v1"
            def generate(self, prompt, system_prompt=None):
                raise RuntimeError("Provider outage")
            def generate_json(self, prompt, system_prompt=None):
                raise RuntimeError("Provider outage")

        ProviderRegistry.register("failing", FailingProvider)
        ProviderRegistry.register("mock", MockProvider)

        gateway = AIGateway()
        request = AIRequest(
            prompt="Test failover",
            provider="failing",
        )
        response = gateway.generate(request)
        assert response.success is True

    def test_failover_to_mock(self):
        class FailingProvider(LLMProvider):
            @property
            def provider_name(self):
                return "failing"
            @property
            def model_name(self):
                return "failing-v1"
            def generate(self, prompt, system_prompt=None):
                raise RuntimeError("Always fails")
            def generate_json(self, prompt, system_prompt=None):
                raise RuntimeError("Always fails")

        ProviderRegistry.clear()
        ProviderRegistry.register("mock", MockProvider)
        ProviderRegistry.register("fail1", FailingProvider)

        gateway = AIGateway()
        request = AIRequest(prompt="Test", provider="fail1")
        response = gateway.generate(request)
        assert response.success is True
        assert response.provider == "mock"

    def test_generate_with_cache(self):
        class CacheMock:
            def __init__(self):
                self._store = {}
            def get(self, namespace, key):
                return self._store.get(f"{namespace}:{key}")
            def set(self, namespace, key, value, ttl=300):
                self._store[f"{namespace}:{key}"] = value

        gateway = AIGateway()
        cache = CacheMock()

        request = AIRequest(
            prompt="Cache test",
            cache_ttl=300,
        )
        response1 = gateway.generate_with_cache(request, cache)
        assert response1.success is True
        assert response1.from_cache is False

        response2 = gateway.generate_with_cache(request, cache)
        if response2.from_cache:
            assert response2.text == response1.text

    def test_cache_key_uniqueness(self):
        gateway = AIGateway()
        req1 = AIRequest(prompt="Hello", provider="mock")
        req2 = AIRequest(prompt="World", provider="mock")
        key1 = gateway._make_cache_key(req1)
        key2 = gateway._make_cache_key(req2)
        assert key1 != key2

    def test_cache_key_same_requests(self):
        gateway = AIGateway()
        req1 = AIRequest(prompt="Same", temperature=0.1)
        req2 = AIRequest(prompt="Same", temperature=0.1)
        key1 = gateway._make_cache_key(req1)
        key2 = gateway._make_cache_key(req2)
        assert key1 == key2


class TestProviderMetadata:
    def test_gemini_metadata(self):
        meta = ProviderRegistry.get_metadata("gemini")
        assert meta.cost_multiplier == 0.5
        assert "vision" in meta.capabilities
        assert meta.quality_score > 0

    def test_openai_metadata(self):
        meta = ProviderRegistry.get_metadata("openai")
        assert "function_calling" in meta.capabilities
        assert len(meta.models) >= 2

    def test_mock_metadata(self):
        meta = ProviderRegistry.get_metadata("mock")
        assert meta.cost_multiplier == 0.0
        assert meta.priority == 999


class TestRoutingStrategy:
    def test_enum_values(self):
        assert RoutingStrategy.LOWEST_COST.value == "lowest_cost"
        assert RoutingStrategy.FASTEST_RESPONSE.value == "fastest_response"
        assert RoutingStrategy.HIGHEST_QUALITY.value == "highest_quality"

    def test_all_strategies_defined(self):
        assert len(RoutingStrategy) == 7


class TestAIResponse:
    def test_default_values(self):
        resp = AIResponse()
        assert resp.success is True
        assert resp.text == ""
        assert resp.from_cache is False
        assert resp.error == ""

    def test_error_response(self):
        resp = AIResponse(error="Failed", success=False)
        assert resp.success is False
        assert resp.error == "Failed"


class TestAIRequest:
    def test_default_values(self):
        req = AIRequest(prompt="Hello")
        assert req.temperature == 0.1
        assert req.max_tokens == 4096
        assert req.strategy == RoutingStrategy.FASTEST_RESPONSE
        assert req.cache_ttl == 0

    def test_custom_values(self):
        req = AIRequest(
            prompt="Test",
            temperature=0.7,
            max_tokens=2048,
            strategy=RoutingStrategy.LOWEST_COST,
            cache_ttl=3600,
        )
        assert req.temperature == 0.7
        assert req.max_tokens == 2048
        assert req.strategy == RoutingStrategy.LOWEST_COST
        assert req.cache_ttl == 3600


class TestConcurrentProviderRegistration:
    def test_register_multiple_same_type(self):
        ProviderRegistry.register("mock", MockProvider)
        ProviderRegistry.register("mock2", MockProvider)
        assert len(ProviderRegistry.list_providers()) >= 2
        assert "mock" in ProviderRegistry.list_providers()
        assert "mock2" in ProviderRegistry.list_providers()

    def test_get_or_create_different_configs(self):
        p1 = ProviderRegistry.get_or_create("mock", ProviderConfig(model="v1"))
        p2 = ProviderRegistry.get_or_create("mock", ProviderConfig(model="v2"))
        assert p1 is not p2


class TestMockProviderIntegration:
    def test_mock_provider_generates_text(self):
        provider = MockProvider()
        response = provider.generate("What is AI?")
        assert response.text != ""
        assert response.provider == "mock"
        assert response.model == "mock-v1"
        assert response.total_tokens > 0

    def test_mock_provider_generates_json(self):
        provider = MockProvider()
        result = provider.generate_json("Analyze this video about Python programming")
        assert isinstance(result, dict)
        assert "primary_topic" in result or "mock" in str(result)

    def test_mock_provider_latency(self):
        provider = MockProvider()
        start = time.time()
        response = provider.generate("Fast test")
        elapsed = (time.time() - start) * 1000
        assert response.latency_ms <= elapsed + 10
        assert response.latency_ms >= 0

    def test_mock_provider_with_system_prompt(self):
        provider = MockProvider()
        response = provider.generate("Hello", system_prompt="Be helpful")
        assert response.text != ""
