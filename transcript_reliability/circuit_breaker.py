"""Circuit Breaker — prevents repeated requests to failing providers.

State machine: CLOSED → OPEN → HALF_OPEN → CLOSED (or back to OPEN).
Supports configurable failure threshold, recovery timeout, half-open probes,
and automatic reset.
"""

from __future__ import annotations

import logging
import time
from threading import Lock

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import CircuitState
from transcript_reliability.models import CircuitBreakerState

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker for a single provider.

    Thread-safe state machine that prevents cascading failures
    by short-circuiting requests to failing providers.
    """

    def __init__(
        self,
        provider_id: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_probes: int = 3,
        success_threshold: int = 2,
    ) -> None:
        self._provider_id = provider_id
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_probes = half_open_max_probes
        self._success_threshold = success_threshold
        self._lock = Lock()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_at = 0.0
        self._last_success_at = 0.0
        self._opened_at = 0.0
        self._half_open_probes = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Thread-safe. Automatically transitions to HALF_OPEN
        when recovery timeout has elapsed.

        Returns:
            True if the request should proceed, False if short-circuited.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._opened_at
                if elapsed >= self._recovery_timeout:
                    logger.info(
                        "[%s] Circuit half-open after %.1fs recovery timeout",
                        self._provider_id, elapsed,
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_probes = 0
                    self._success_count = 0
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_probes < self._half_open_max_probes:
                    self._half_open_probes += 1
                    return True
                return False

            return True

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._last_success_at = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    logger.info(
                        "[%s] Circuit closed after %d consecutive successes",
                        self._provider_id, self._success_count,
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_probes = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._last_failure_at = time.time()

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._failure_threshold:
                    logger.warning(
                        "[%s] Circuit opened after %d failures",
                        self._provider_id, self._failure_count,
                    )
                    self._state = CircuitState.OPEN
                    self._opened_at = time.time()
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "[%s] Circuit re-opened after failure in half-open state",
                    self._provider_id,
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._half_open_probes = 0
                self._success_count = 0

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_probes = 0
            logger.info("[%s] Circuit manually reset", self._provider_id)

    def get_state_info(self) -> CircuitBreakerState:
        """Get current state information."""
        with self._lock:
            return CircuitBreakerState(
                provider_id=self._provider_id,
                state=self._state,
                failure_count=self._failure_count,
                success_count=self._success_count,
                last_failure_at=self._last_failure_at,
                last_success_at=self._last_success_at,
                opened_at=self._opened_at,
                half_open_probes=self._half_open_probes,
                recovery_timeout=self._recovery_timeout,
                failure_threshold=self._failure_threshold,
                success_threshold=self._success_threshold,
            )


class CircuitBreakerManager:
    """Manages circuit breakers for all providers.

    Provides a unified interface for checking and recording
    provider status across the system.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(self, provider_id: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a provider."""
        if provider_id not in self._breakers:
            self._breakers[provider_id] = CircuitBreaker(
                provider_id=provider_id,
                failure_threshold=self._config.circuit_breaker_failure_threshold,
                recovery_timeout=self._config.circuit_breaker_recovery_timeout,
                half_open_max_probes=self._config.circuit_breaker_half_open_max_probes,
                success_threshold=self._config.circuit_breaker_success_threshold,
            )
        return self._breakers[provider_id]

    def allow_request(self, provider_id: str) -> bool:
        """Check if a request to this provider should proceed."""
        return self.get_breaker(provider_id).allow_request()

    def record_success(self, provider_id: str) -> None:
        """Record a successful request for a provider."""
        self.get_breaker(provider_id).record_success()

    def record_failure(self, provider_id: str) -> None:
        """Record a failed request for a provider."""
        self.get_breaker(provider_id).record_failure()

    def reset(self, provider_id: str) -> None:
        """Manually reset circuit breaker for a provider."""
        if provider_id in self._breakers:
            self._breakers[provider_id].reset()

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def get_state(self, provider_id: str) -> CircuitBreakerState:
        """Get the current state of a provider's circuit breaker."""
        return self.get_breaker(provider_id).get_state_info()

    def get_all_states(self) -> dict[str, CircuitBreakerState]:
        """Get states for all providers that have been accessed."""
        return {
            pid: breaker.get_state_info()
            for pid, breaker in self._breakers.items()
        }

    def is_open(self, provider_id: str) -> bool:
        """Check if the circuit breaker is open for a provider."""
        return self.get_breaker(provider_id).state == CircuitState.OPEN
