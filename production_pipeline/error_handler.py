"""Global Error Handler — centralized exception handling for the entire pipeline.

Classifies every error into a standard category, maps to retry strategy,
recovery action, and user-facing message. Never exposes stack traces.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from production_pipeline.constants import ErrorClass

logger = logging.getLogger(__name__)

# Error classification patterns: (keyword, ErrorClass, retryable, recoverable)
_ERROR_PATTERNS: list[tuple[list[str], ErrorClass, bool, bool]] = [
    # AI / LLM errors
    (["rate limit", "429", "too many requests"], ErrorClass.AI, True, False),
    (["context length", "maximum context", "token limit", "too long"], ErrorClass.AI, False, False),
    (["timeout", "deadline exceeded", "timed out"], ErrorClass.TIMEOUT, True, True),
    (["authentication", "api key", "unauthorized", "forbidden", "403"], ErrorClass.EXTERNAL_API, False, False),
    (["model not found", "model not supported", "404"], ErrorClass.EXTERNAL_API, False, False),
    # Database errors
    (["database", "db error", "connection refused", "psycopg", "sqlite"], ErrorClass.DATABASE, True, True),
    (["deadlock", "serialization failure"], ErrorClass.DATABASE, True, True),
    # Redis errors
    (["redis", "connection error", "timeout on redis"], ErrorClass.REDIS, True, True),
    # Network errors
    (["connection", "socket", "dns", "name or service not known"], ErrorClass.NETWORK, True, True),
    (["ssl", "certificate", "handshake"], ErrorClass.NETWORK, True, True),
    # Storage errors
    (["disk", "disk full", "no space", "quota exceeded"], ErrorClass.STORAGE, False, False),
    (["file not found", "permission denied", "read-only"], ErrorClass.STORAGE, False, False),
    # Worker errors
    (["worker", "segfault", "oom", "memory"], ErrorClass.WORKER, False, True),
    (["killed", "signal", "exit code"], ErrorClass.WORKER, False, True),
    # Validation errors
    (["validation", "invalid", "malformed", "schema"], ErrorClass.VALIDATION, False, False),
    (["required field", "missing"], ErrorClass.VALIDATION, False, False),
]

_ERROR_CACHE: dict[str, tuple[ErrorClass, bool, bool]] = {}


def classify_error(error: Exception | str) -> tuple[ErrorClass, bool, bool]:
    """Classify an error into ErrorClass with retryable and recoverable flags.

    Args:
        error: Exception instance or error string.

    Returns:
        Tuple of (ErrorClass, is_retryable, is_recoverable).
    """
    error_str = str(error).lower() if isinstance(error, Exception) else error.lower()
    error_type = type(error).__name__ if isinstance(error, Exception) else ""

    # Check cache
    cache_key = f"{error_type}:{error_str[:100]}"
    if cache_key in _ERROR_CACHE:
        return _ERROR_CACHE[cache_key]

    # Check patterns
    for keywords, error_class, retryable, recoverable in _ERROR_PATTERNS:
        for keyword in keywords:
            if keyword in error_str or keyword in error_type.lower():
                result = (error_class, retryable, recoverable)
                _ERROR_CACHE[cache_key] = result
                return result

    # Default: unknown, not retryable, not recoverable
    result = (ErrorClass.UNKNOWN, False, False)
    _ERROR_CACHE[cache_key] = result
    return result


class ErrorHandler:
    """Global error handler for pipeline execution.

    Centralizes error classification, formatting, and logging.
    Never exposes stack traces to external callers.
    """

    @staticmethod
    def handle(
        error: Exception,
        stage_name: str = "",
        execution_id: str = "",
    ) -> dict[str, Any]:
        """Handle an error and return a standardized error response.

        Args:
            error: The exception that occurred.
            stage_name: Stage name where error occurred.
            execution_id: Execution ID.

        Returns:
            Standardized error dict with safe user message.
        """
        error_class, retryable, recoverable = classify_error(error)
        error_str = str(error)
        tb = traceback.format_exc()

        # Log the full error internally
        logger.error(
            "[%s] Stage '%s' error [%s]: %s\n%s",
            execution_id[:8] if execution_id else "????",
            stage_name, error_class.value, error_str[:200], tb[:1000],
        )

        return ErrorHandler._build_response(
            error=error,
            error_class=error_class,
            retryable=retryable,
            recoverable=recoverable,
            stage_name=stage_name,
        )

    @staticmethod
    def _build_response(
        error: Exception,
        error_class: ErrorClass,
        retryable: bool,
        recoverable: bool,
        stage_name: str = "",
    ) -> dict[str, Any]:
        """Build a standardized error response without exposing internals."""
        error_str = str(error)

        return {
            "error_type": error_class.value,
            "message": ErrorHandler._safe_message(error_class, error_str),
            "retryable": retryable,
            "recoverable": recoverable,
            "stage": stage_name,
            "internal_error": error_str[:500],
        }

    @staticmethod
    def _safe_message(error_class: ErrorClass, error_str: str) -> str:
        """Generate a user-safe error message based on error class."""
        messages = {
            ErrorClass.AI: "AI service error. The request will be retried.",
            ErrorClass.VALIDATION: "Input validation failed. Please check your data.",
            ErrorClass.DATABASE: "Database error. The operation will be retried.",
            ErrorClass.REDIS: "Cache service error. Continuing without cache.",
            ErrorClass.TIMEOUT: "Operation timed out. The request will be retried.",
            ErrorClass.NETWORK: "Network error. The request will be retried.",
            ErrorClass.WORKER: "Worker process error. Recovery in progress.",
            ErrorClass.STORAGE: "Storage error. Please contact support.",
            ErrorClass.EXTERNAL_API: "External API error. Please check your configuration.",
            ErrorClass.UNKNOWN: "An unexpected error occurred. Please try again.",
        }
        return messages.get(error_class, "An error occurred. Please try again.")

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Quick check if an error is retryable."""
        _, retryable, _ = classify_error(error)
        return retryable

    @staticmethod
    def is_recoverable(error: Exception) -> bool:
        """Quick check if an error is recoverable."""
        _, _, recoverable = classify_error(error)
        return recoverable

    @staticmethod
    def get_stack_trace(error: Exception) -> str:
        """Get the stack trace for internal logging."""
        return traceback.format_exc()

    @staticmethod
    def clear_cache() -> None:
        """Clear the error classification cache."""
        _ERROR_CACHE.clear()


def classify_error_short(error: Exception) -> str:
    """Quick classification returning just the error class name."""
    cls, _, _ = classify_error(error)
    return cls.value
