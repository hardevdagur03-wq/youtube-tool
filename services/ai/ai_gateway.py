"""AI Gateway — intelligent request routing, failover, and caching.

Routes AI requests to the best provider based on strategy,
handles failures with automatic failover, and caches responses.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from providers.llm_provider import LLMResponse, ProviderConfig
from services.ai.provider_registry import ProviderRegistry, RoutingStrategy

logger = logging.getLogger(__name__)


@dataclass
class AIRequest:
    prompt: str = ""
    system_prompt: str = ""
    task: str = "text"
    provider: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    strategy: RoutingStrategy = RoutingStrategy.FASTEST_RESPONSE
    cache_ttl: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    text: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    from_cache: bool = False
    cached_at: str = ""
    error: str = ""
    success: bool = True


class AIGateway:
    """Central AI Gateway with routing, failover, and caching.

    Usage:
        gateway = AIGateway()
        response = await gateway.generate(request)
    """

    def __init__(self, registry: ProviderRegistry | None = None):
        self._registry = registry or ProviderRegistry()

    def generate(self, request: AIRequest) -> AIResponse:
        start = time.time()

        provider_name, config = self._registry.resolve_provider(
            task=request.task,
            preferred_provider=request.provider,
            strategy=request.strategy,
        )

        if request.model:
            config.model = request.model

        config.temperature = request.temperature
        config.max_tokens = request.max_tokens

        provider = self._registry.get_or_create(provider_name, config)

        try:
            llm_response = provider.generate(
                prompt=request.prompt,
                system_prompt=request.system_prompt or None,
            )
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text=llm_response.text,
                model=llm_response.model,
                provider=llm_response.provider,
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                total_tokens=llm_response.total_tokens,
                latency_ms=round(elapsed, 1),
                cost_estimate=llm_response.cost_estimate,
                from_cache=False,
                success=True,
            )
        except Exception as exc:
            logger.warning(
                "Primary provider %s failed: %s. Trying fallback...",
                provider_name, exc,
            )
            return self._fallback(request, start, str(exc))

    def _fallback(
        self, request: AIRequest, start: float, error: str
    ) -> AIResponse:
        strategies = [
            RoutingStrategy.LOWEST_COST,
            RoutingStrategy.PROVIDER_PREFERENCE,
        ]
        errors = [error]

        for strategy in strategies:
            try:
                provider_name, config = self._registry.resolve_provider(
                    task=request.task,
                    strategy=strategy,
                )

                config.temperature = request.temperature
                config.max_tokens = request.max_tokens

                provider = self._registry.get_or_create(provider_name, config)
                llm_response = provider.generate(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt or None,
                )
                elapsed = (time.time() - start) * 1000
                return AIResponse(
                    text=llm_response.text,
                    model=llm_response.model,
                    provider=llm_response.provider,
                    input_tokens=llm_response.input_tokens,
                    output_tokens=llm_response.output_tokens,
                    total_tokens=llm_response.total_tokens,
                    latency_ms=round(elapsed, 1),
                    cost_estimate=llm_response.cost_estimate,
                    from_cache=False,
                    success=True,
                )
            except Exception as exc:
                errors.append(str(exc))
                continue

        return AIResponse(
            error="All providers failed: " + "; ".join(errors),
            success=False,
        )

    def generate_json(
        self, request: AIRequest
    ) -> tuple[dict[str, Any], AIResponse]:
        response = self.generate(request)
        if not response.success:
            return {}, response
        try:
            data = json.loads(response.text)
            return data, response
        except json.JSONDecodeError:
            return {"raw": response.text}, response

    def generate_with_cache(
        self, request: AIRequest, cache_service: Any = None
    ) -> AIResponse:
        if cache_service and request.cache_ttl > 0:
            cache_key = self._make_cache_key(request)
            cached = cache_service.get("ai", cache_key)
            if cached:
                return AIResponse(
                    text=cached.get("text", ""),
                    model=cached.get("model", ""),
                    provider=cached.get("provider", ""),
                    from_cache=True,
                    success=True,
                )

        response = self.generate(request)

        if response.success and cache_service and request.cache_ttl > 0:
            cache_service.set(
                "ai",
                cache_key,
                {
                    "text": response.text,
                    "model": response.model,
                    "provider": response.provider,
                },
                ttl=request.cache_ttl,
            )

        return response

    def _make_cache_key(self, request: AIRequest) -> str:
        raw = f"{request.provider}:{request.model}:{request.temperature}:{request.prompt}:{request.system_prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
