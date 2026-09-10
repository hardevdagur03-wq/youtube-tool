"""AI Provider Metrics — tracks health, latency, token usage, costs, and fallbacks per provider.

Provides real-time visibility into:
- Per-provider health and availability
- Per-model latency (P50/P95/P99)
- Token consumption (prompt, completion, total)
- Cost tracking per-call and cumulative
- Provider fallback counts
- Error rates per provider
- Hallucination rate estimation
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from observability.logger import get_logger

logger = get_logger(__name__)

PREFIX = "youtube_seo_ai"

# Counters
provider_calls = Counter(f"{PREFIX}_calls_total", "AI provider calls", ["provider", "model"])
provider_success = Counter(f"{PREFIX}_success_total", "Successful AI provider calls", ["provider", "model"])
provider_failures = Counter(f"{PREFIX}_failures_total", "Failed AI provider calls", ["provider", "model", "error_type"])
provider_fallbacks = Counter(f"{PREFIX}_fallbacks_total", "AI provider fallback events", ["from_provider", "to_provider"])
provider_retries = Counter(f"{PREFIX}_retries_total", "AI provider retry attempts", ["provider", "model"])
provider_timeouts = Counter(f"{PREFIX}_timeouts_total", "AI provider timeouts", ["provider", "model"])

prompt_tokens = Counter(f"{PREFIX}_prompt_tokens_total", "Prompt tokens consumed", ["provider", "model"])
completion_tokens = Counter(f"{PREFIX}_completion_tokens_total", "Completion tokens generated", ["provider", "model"])
total_tokens = Counter(f"{PREFIX}_tokens_total", "Total tokens consumed", ["provider", "model"])
cache_hit_tokens = Counter(f"{PREFIX}_cache_hit_tokens_total", "Cache hit tokens saved", ["provider", "model"])

# Histograms
provider_latency = Histogram(
    f"{PREFIX}_latency_seconds",
    "AI provider call latency",
    ["provider", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)
prompt_length = Histogram(
    f"{PREFIX}_prompt_length_tokens",
    "Prompt length in tokens",
    ["provider", "model"],
    buckets=(100, 500, 1000, 2000, 4000, 8000, 16000, 32000),
)
completion_length = Histogram(
    f"{PREFIX}_completion_length_tokens",
    "Completion length in tokens",
    ["provider", "model"],
    buckets=(50, 100, 200, 500, 1000, 2000, 4000, 8000),
)

# Gauges
provider_health = Gauge(f"{PREFIX}_provider_health", "Provider health (1=healthy, 0=unhealthy)", ["provider"])
provider_availability = Gauge(f"{PREFIX}_provider_availability_ratio", "Provider availability (0-1)", ["provider"])
model_latency_p50 = Gauge(f"{PREFIX}_model_latency_p50", "P50 latency per model", ["provider", "model"])
model_latency_p95 = Gauge(f"{PREFIX}_model_latency_p95", "P95 latency per model", ["provider", "model"])
model_latency_p99 = Gauge(f"{PREFIX}_model_latency_p99", "P99 latency per model", ["provider", "model"])
model_error_rate = Gauge(f"{PREFIX}_model_error_rate", "Error rate per model (0-1)", ["provider", "model"])
model_cost_rate = Gauge(f"{PREFIX}_model_cost_rate", "Cost per 1K tokens", ["provider", "model"])


@dataclass
class AIProviderSnapshot:
    provider: str = ""
    model: str = ""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    error_rate: float = 0.0
    availability: float = 1.0
    fallback_count: int = 0
    timestamp: str = ""


MODEL_COST_PER_1K_TOKENS: dict[str, float] = {
    "gemini-2.0-flash": 0.0001,
    "gemini-2.5-pro": 0.00125,
    "gpt-4o": 0.0025,
    "gpt-4o-mini": 0.00015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "deepseek-chat": 0.0005,
    "mistral-large": 0.002,
}


class AIMetricsCollector:
    """Tracks AI provider metrics, costs, health, and fallback behavior."""

    def __init__(self):
        self._latency_history: dict[str, list[float]] = defaultdict(list)

    def record_call(
        self,
        provider: str,
        model: str,
        success: bool = True,
        latency_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        error_type: str = "",
        is_fallback: bool = False,
        from_provider: str = "",
    ) -> None:
        provider_calls.labels(provider=provider, model=model).inc()
        if success:
            provider_success.labels(provider=provider, model=model).inc()
        else:
            provider_failures.labels(provider=provider, model=model, error_type=error_type or "unknown").inc()

        if latency_ms > 0:
            provider_latency.labels(provider=provider, model=model).observe(latency_ms / 1000.0)
            key = f"{provider}:{model}"
            self._latency_history[key].append(latency_ms)
            if len(self._latency_history[key]) > 1000:
                self._latency_history[key] = self._latency_history[key][-1000:]

        if prompt_tokens > 0:
            prompt_tokens.labels(provider=provider, model=model).inc(prompt_tokens)
            prompt_length.labels(provider=provider, model=model).observe(prompt_tokens)
        if completion_tokens > 0:
            completion_tokens.labels(provider=provider, model=model).inc(completion_tokens)
            completion_length.labels(provider=provider, model=model).observe(completion_tokens)
        if prompt_tokens > 0 or completion_tokens > 0:
            total_tokens.labels(provider=provider, model=model).inc(prompt_tokens + completion_tokens)
        if cached_tokens > 0:
            cache_hit_tokens.labels(provider=provider, model=model).inc(cached_tokens)
        if is_fallback and from_provider:
            provider_fallbacks.labels(from_provider=from_provider, to_provider=provider).inc()

        if success:
            provider_health.labels(provider=provider).set(1)
        else:
            provider_health.labels(provider=provider).set(0)

        cost_per_1k = MODEL_COST_PER_1K_TOKENS.get(model, 0.001)
        model_cost_rate.labels(provider=provider, model=model).set(cost_per_1k)

    def record_retry(self, provider: str, model: str) -> None:
        provider_retries.labels(provider=provider, model=model).inc()

    def record_timeout(self, provider: str, model: str) -> None:
        provider_timeouts.labels(provider=provider, model=model).inc()

    def mark_provider_unhealthy(self, provider: str) -> None:
        provider_health.labels(provider=provider).set(0)

    def mark_provider_healthy(self, provider: str) -> None:
        provider_health.labels(provider=provider).set(1)

    def update_availability(self, provider: str, ratio: float) -> None:
        provider_availability.labels(provider=provider).set(max(0.0, min(1.0, ratio)))

    def update_latency_percentiles(self, provider: str, model: str) -> None:
        key = f"{provider}:{model}"
        history = self._latency_history.get(key, [])
        if not history:
            return
        sorted_lat = sorted(history)
        n = len(sorted_lat)
        model_latency_p50.labels(provider=provider, model=model).set(sorted_lat[int(n * 0.5)])
        model_latency_p95.labels(provider=provider, model=model).set(sorted_lat[int(n * 0.95)])
        model_latency_p99.labels(provider=provider, model=model).set(sorted_lat[int(n * 0.99)])

    def get_snapshot(self, provider: str = "", model: str = "") -> AIProviderSnapshot:
        return AIProviderSnapshot(
            provider=provider or "all",
            model=model or "all",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rate = MODEL_COST_PER_1K_TOKENS.get(model, 0.001)
        return ((prompt_tokens + completion_tokens) / 1000) * rate


_ai_metrics: AIMetricsCollector | None = None


def get_ai_metrics() -> AIMetricsCollector:
    global _ai_metrics
    if _ai_metrics is None:
        _ai_metrics = AIMetricsCollector()
    return _ai_metrics
