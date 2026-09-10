"""Exception hierarchy for the Transcript Reliability Engine."""

from __future__ import annotations


class TranscriptReliabilityError(Exception):
    """Base exception for all Transcript Reliability Engine errors."""
    pass


class ProviderNotFoundError(TranscriptReliabilityError):
    """Requested provider is not registered."""
    pass


class ProviderDisabledError(TranscriptReliabilityError):
    """Requested provider is disabled."""
    pass


class ProviderUnhealthyError(TranscriptReliabilityError):
    """Requested provider is unhealthy."""
    pass


class CircuitBreakerOpenError(TranscriptReliabilityError):
    """Circuit breaker is open for this provider."""
    pass


class AllProvidersFailedError(TranscriptReliabilityError):
    """All available providers failed to produce a transcript."""
    pass


class RetryBudgetExhaustedError(TranscriptReliabilityError):
    """Retry budget has been exhausted for this request."""
    pass


class ValidationRejectedError(TranscriptReliabilityError):
    """Transcript failed validation checks."""
    pass


class DuplicateTranscriptError(TranscriptReliabilityError):
    """Transcript consists entirely of duplicate content."""
    pass


class SilenceDetectedError(TranscriptReliabilityError):
    """Transcript contains only silence, music, or noise."""
    pass


class CacheError(TranscriptReliabilityError):
    """Cache operation failed."""
    pass


class ProviderAuthError(TranscriptReliabilityError):
    """Provider authentication failed (API key missing or invalid)."""
    pass


class ProviderQuotaError(TranscriptReliabilityError):
    """Provider quota exceeded."""
    pass


class ProviderTimeoutError(TranscriptReliabilityError):
    """Provider request timed out."""
    pass


class VersionNotFoundError(TranscriptReliabilityError):
    """Requested version does not exist."""
    pass
