"""Transcript Manager — top-level orchestrator for the Transcript Reliability Engine.

Replaces TranscriptService as the single entry point for transcript retrieval.
Coordinates provider selection, failover, caching, validation, cleaning,
quality scoring, versioning, and observability.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from models.transcript import TranscriptResult
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.priority_manager import PriorityManager
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.retry_engine import RetryEngine
from transcript_reliability.failover_engine import FailoverEngine

logger = logging.getLogger(__name__)


class TranscriptManager:
    """Top-level orchestrator for all transcript retrieval.

    This is the single entry point that replaces TranscriptService.
    It coordinates provider failover, caching, validation, cleaning,
    quality scoring, and versioning.

    Usage::

        manager = TranscriptManager()
        result = manager.get_transcript("dQw4w9WgXcQ")
        if result.success:
            print(result.plain_text[:200])
    """

    def __init__(
        self,
        config: TranscriptReliabilityConfig | None = None,
        registry: ProviderRegistry | None = None,
        health_monitor: HealthMonitor | None = None,
        circuit_breaker: CircuitBreakerManager | None = None,
        retry_engine: RetryEngine | None = None,
        priority_manager: PriorityManager | None = None,
        failover_engine: FailoverEngine | None = None,
    ) -> None:
        self._config = config or TranscriptReliabilityConfig.from_env()

        # Core components
        self._registry = registry or ProviderRegistry(self._config)
        self._health = health_monitor or HealthMonitor(self._config)
        self._circuit_breaker = circuit_breaker or CircuitBreakerManager(self._config)
        self._retry = retry_engine or RetryEngine(self._config)

        # Priority and failover
        if priority_manager:
            self._priority = priority_manager
        else:
            self._priority = PriorityManager(
                self._registry, self._health, self._circuit_breaker, self._config,
            )

        if failover_engine:
            self._failover = failover_engine
        else:
            self._failover = FailoverEngine(
                self._registry, self._priority, self._health,
                self._circuit_breaker, self._retry, self._config,
            )

        # Lazy-loaded optional components (wired in later waves)
        self._cache = None
        self._validator = None
        self._cleaner = None
        self._deduplicator = None
        self._silence_detector = None
        self._quality_scorer = None
        self._version_manager = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_transcript(
        self,
        video_id: str,
        language: str | None = None,
        force_refresh: bool = False,
        allow_failover: bool = True,
        options: dict[str, Any] | None = None,
    ) -> TranscriptResult:
        """Retrieve the best available transcript for a video.

        Orchestrates the full pipeline:
        1. Check cache (L1 → L2 → L3) if not force_refresh
        2. Failover through providers if cache miss
        3. Validate transcript quality
        4. Clean and normalize text
        5. Score quality
        6. Cache the result
        7. Return

        Args:
            video_id: 11-character YouTube video ID.
            language: Preferred language code (e.g. 'en', 'hi').
            force_refresh: If True, bypass all cache levels.
            allow_failover: If False, only try the first available provider.
            options: Provider-specific options.

        Returns:
            ``TranscriptResult`` — always returns, never raises.
            Check ``result.success`` to determine availability.
        """
        start_time = time.time()
        options = options or {}

        # Step 1: Check cache (when implemented in Wave 5)
        if not force_refresh and self._cache is not None:
            cached = self._cache.get(video_id, language=language)
            if cached is not None:
                logger.info(
                    "[%s] Cache hit for video %s (language=%s)",
                    video_id[:8], video_id, language or "any",
                )
                return cached

        # Step 2: Failover through providers
        if allow_failover:
            result = self._failover.get_transcript(video_id, language=language, options=options)
        else:
            result = self._get_single_provider(video_id, language, options)

        # Step 3: Validate (when implemented in Wave 4)
        if result.success and self._validator is not None:
            validation = self._validator.validate(result)
            if not validation.passed:
                logger.warning(
                    "[%s] Transcript validation failed (score=%.2f): %s",
                    video_id[:8], validation.overall_score,
                    validation.failed_checks,
                )
                result.success = False
                result.error = f"Validation failed: {', '.join(validation.failed_checks)}"

        # Step 4: Clean (when implemented in Wave 4)
        if result.success and self._cleaner is not None:
            result = self._cleaner.clean(result)

        # Step 5: Score quality (when implemented in Wave 5)
        if result.success and self._quality_scorer is not None:
            quality = self._quality_scorer.score(result)

        # Step 6: Cache result (when implemented in Wave 5)
        if result.success and self._cache is not None:
            self._cache.set(video_id, result, language=language)

        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        logger.info(
            "[%s] Transcript %s for video %s in %.1fms (words=%d, lang=%s)",
            video_id[:8],
            "obtained" if result.success else "FAILED",
            video_id, elapsed_ms,
            result.word_count if result.success else 0,
            result.language,
        )

        return result

    def get_transcript_status(self, video_id: str) -> dict[str, Any]:
        """Check transcript availability without full retrieval.

        Returns info about what providers can serve this video
        and whether a cached version exists.

        Args:
            video_id: 11-character YouTube video ID.

        Returns:
            Dict with availability information.
        """
        result: dict[str, Any] = {
            "video_id": video_id,
            "cached": False,
            "available_providers": [],
            "provider_count": 0,
        }

        # Check cache
        if self._cache is not None:
            cached = self._cache.get(video_id)
            if cached is not None:
                result["cached"] = True
                result["source"] = cached.source
                result["language"] = cached.language

        # List available providers
        providers = self._registry.list_enabled()
        result["available_providers"] = [
            {
                "provider_id": p.provider_id,
                "name": p.name,
                "capabilities": [c.value for c in p.capabilities()],
            }
            for p in providers
        ]
        result["provider_count"] = len(providers)

        return result

    def register_provider(self, provider: Any) -> None:
        """Register a new transcript provider.

        Args:
            provider: A TranscriptProvider implementation.
        """
        self._registry.register(provider)
        logger.info("Provider registered with TranscriptManager: %s", provider.provider_id)

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of all registered providers.

        Returns:
            Dict with provider health, circuit breaker states, and counts.
        """
        return self._failover.get_failover_summary()

    def clear_cache(self) -> None:
        """Clear all cached transcripts."""
        if self._cache is not None:
            self._cache.clear()
        logger.info("TranscriptManager cache cleared")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_single_provider(
        self,
        video_id: str,
        language: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> TranscriptResult:
        """Get transcript from the first available provider only."""
        options = options or {}
        providers = self._priority.get_providers_in_order(
            language=language,
            skip_unhealthy=True,
            skip_open_circuit=True,
        )

        if not providers:
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error="No providers available",
            )

        provider = providers[0]
        pid = provider.provider_id

        if not self._circuit_breaker.allow_request(pid):
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error=f"Circuit breaker open for {pid}",
            )

        try:
            result = provider.get_transcript(video_id, language=language, **options)
            if result.success:
                self._circuit_breaker.record_success(pid)
                self._health.record_success(pid)
            else:
                self._circuit_breaker.record_failure(pid)
                self._health.record_failure(pid)
            return result
        except Exception as exc:
            self._circuit_breaker.record_failure(pid)
            self._health.record_failure(pid, error_type=type(exc).__name__)
            return TranscriptResult(
                success=False,
                video_id=video_id,
                error=f"{pid} failed: {exc}",
            )
