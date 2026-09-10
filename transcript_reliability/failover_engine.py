"""Failover Engine — coordinates retry, circuit breaker, and priority for provider failover.

Intelligently routes transcript requests through available providers,
handling failures gracefully without ever crashing the pipeline.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from models.transcript import TranscriptResult
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import CircuitState, RetryAction
from transcript_reliability.exceptions import AllProvidersFailedError
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.models import RetryPolicy
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.retry_engine import RetryEngine
from transcript_reliability.priority_manager import PriorityManager

logger = logging.getLogger(__name__)


class FailoverEngine:
    """Coordinates provider failover with retry, circuit breaker, and priority.

    Attempts providers in priority order, retries on transient failures,
    skips providers with open circuit breakers, and ensures the pipeline
    never crashes due to transcript failures.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        priority_manager: PriorityManager,
        health_monitor: HealthMonitor,
        circuit_breaker: CircuitBreakerManager,
        retry_engine: RetryEngine,
        config: TranscriptReliabilityConfig | None = None,
    ) -> None:
        self._registry = registry
        self._priority = priority_manager
        self._health = health_monitor
        self._circuit_breaker = circuit_breaker
        self._retry = retry_engine
        self._config = config or TranscriptReliabilityConfig()

    def get_transcript(
        self,
        video_id: str,
        language: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> TranscriptResult:
        """Retrieve a transcript by failing over through available providers.

        Args:
            video_id: 11-character YouTube video ID.
            language: Optional language code hint.
            options: Provider-specific options.

        Returns:
            ``TranscriptResult`` — always returns a result, never raises.
            Check ``result.success`` to determine if a transcript was found.
        """
        options = options or {}
        start_time = time.time()
        fallback_chain: list[str] = []
        errors: list[str] = []
        total_retries = 0

        providers = self._priority.get_providers_in_order(
            language=language,
            skip_unhealthy=True,
            skip_open_circuit=True,
        )

        if not providers:
            # Fallback: try ALL enabled providers even if unhealthy
            providers = self._priority.get_providers_in_order(
                language=language,
                skip_unhealthy=False,
                skip_open_circuit=False,
            )

        if not providers:
            logger.error("No providers available for video %s (language=%s)", video_id, language)
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error="No transcript providers are available. All providers are disabled or unhealthy.",
            )

        for provider in providers:
            pid = provider.provider_id
            fallback_chain.append(pid)

            # Skip if circuit breaker is open
            if not self._circuit_breaker.allow_request(pid):
                logger.warning(
                    "[%s] Circuit breaker OPEN, skipping provider %s",
                    video_id[:8], pid,
                )
                errors.append(f"{pid}: circuit breaker open")
                continue

            logger.info(
                "[%s] Attempting provider: %s (language=%s)",
                video_id[:8], pid, language or "auto",
            )

            # Attempt with retry
            success, result_data, error, attempts = self._retry.execute_with_retry(
                lambda p=provider: self._execute_provider(p, video_id, language, options),
                provider_id=pid,
            )

            total_retries += attempts - 1  # subtract first attempt

            if success and result_data is not None:
                transcript = result_data
                if isinstance(transcript, TranscriptResult) and transcript.success:
                    # Record success in health monitor and circuit breaker
                    self._health.record_success(pid, latency_ms=(time.time() - start_time) * 1000)
                    self._circuit_breaker.record_success(pid)
                    logger.info(
                        "[%s] Transcript obtained from %s "
                        "(word_count=%d, language=%s, retries=%d)",
                        video_id[:8], pid,
                        transcript.word_count, transcript.language,
                        attempts - 1,
                    )
                    transcript.pipeline_steps = transcript.pipeline_steps or []
                    transcript.pipeline_steps.append({
                        "name": "failover",
                        "status": "ok",
                        "detail": f"Provider: {pid}, retries: {attempts - 1}",
                    })
                    return transcript

            # Record failure
            self._health.record_failure(pid, error_type=error or "unknown")
            self._circuit_breaker.record_failure(pid)
            errors.append(f"{pid}: {error or 'unknown error'}")

            logger.warning(
                "[%s] Provider %s failed after %d attempts: %s",
                video_id[:8], pid, attempts, error,
            )

        # All providers failed — return best-effort error result
        elapsed = round(time.time() - start_time, 2)
        logger.error(
            "[%s] All providers failed after %.1fs. Chain: %s. Errors: %s",
            video_id[:8], elapsed, fallback_chain, errors,
        )

        return TranscriptResult(
            success=False,
            video_id=video_id,
            error=f"All {len(fallback_chain)} provider(s) failed: {'; '.join(errors[:3])}",
            language=language or "en",
        )

    def _execute_provider(
        self,
        provider: TranscriptProvider,
        video_id: str,
        language: str | None,
        options: dict[str, Any],
    ) -> TranscriptResult:
        """Execute a single provider call and return the result.

        Separated from the main loop to allow clean retry semantics.
        """
        result = provider.get_transcript(video_id, language=language, **options)
        return result

    def get_failover_summary(self) -> dict[str, Any]:
        """Get a summary of failover statistics."""
        all_health = self._health.get_all_health()
        cb_states = self._circuit_breaker.get_all_states()
        return {
            "providers": {
                pid: {
                    "health_status": h.status.value,
                    "circuit_state": cb_states[pid].state.value if pid in cb_states else "unknown",
                    "success_rate": round(h.success_rate, 3),
                    "avg_latency_ms": h.avg_latency_ms,
                }
                for pid, h in all_health.items()
            },
            "available_count": len(self._priority.get_providers_in_order()),
        }
