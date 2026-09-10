"""Error Handler — centralized error handling for pipeline execution.

No existing code is modified.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineError:
    """Structured pipeline error."""
    stage: str = ""
    message: str = ""
    error_type: str = "unknown"
    recoverable: bool = True
    retryable: bool = True
    traceback: str = ""
    details: dict[str, Any] = field(default_factory=dict)


ERROR_CLASSIFICATIONS: list[dict] = [
    {"keywords": ["quota_exceeded", "quota exceeded", "quota"], "type": "quota_exceeded",
     "recoverable": True, "retryable": True, "message": "API quota exceeded. Try again later."},
    {"keywords": ["channel_not_found", "channel not found", "no channel found"],
     "type": "channel_not_found", "recoverable": False, "retryable": False,
     "message": "YouTube channel not found."},
    {"keywords": ["video_not_found", "video not found"], "type": "video_not_found",
     "recoverable": False, "retryable": False, "message": "Video not found or unavailable."},
    {"keywords": ["transcript_unavailable", "no transcript", "transcript not"],
     "type": "transcript_unavailable", "recoverable": False, "retryable": False,
     "message": "No transcript available for this video."},
    {"keywords": ["llm_error", "llm error", "ai provider"], "type": "llm_error",
     "recoverable": True, "retryable": True, "message": "AI provider returned an error."},
    {"keywords": ["timeout", "timed out"], "type": "timeout",
     "recoverable": True, "retryable": True, "message": "Request timed out."},
    {"keywords": ["network_error", "network error", "connection"], "type": "network_error",
     "recoverable": True, "retryable": True, "message": "Network connection failed."},
    {"keywords": ["invalid_json", "invalid json", "parse error"], "type": "invalid_json",
     "recoverable": True, "retryable": True, "message": "Invalid JSON response from API."},
    {"keywords": ["validation_error", "validation error", "invalid input"],
     "type": "validation_error", "recoverable": False, "retryable": False,
     "message": "Input validation failed."},
]


class ErrorHandler:
    """Centralized error classification and handling."""

    @staticmethod
    def classify(exc: Exception, stage: str = "") -> PipelineError:
        error_str = str(exc).lower()
        tb = traceback.format_exc()

        for classification in ERROR_CLASSIFICATIONS:
            for keyword in classification["keywords"]:
                if keyword in error_str:
                    return PipelineError(
                        stage=stage,
                        message=classification["message"],
                        error_type=classification["type"],
                        recoverable=classification["recoverable"],
                        retryable=classification["retryable"],
                        traceback=tb,
                        details={"original": str(exc)},
                    )

        return PipelineError(
            stage=stage,
            message=str(exc) or "An unexpected error occurred.",
            error_type="unexpected",
            recoverable=False,
            retryable=False,
            traceback=tb,
        )

    @staticmethod
    def should_retry(error: PipelineError) -> bool:
        return error.retryable and error.recoverable

    @staticmethod
    def is_recoverable(error: PipelineError) -> bool:
        return error.recoverable

    @staticmethod
    def user_message(error: PipelineError) -> str:
        if error.error_type == "quota_exceeded":
            return "YouTube API quota exceeded. Please try again later or upgrade your quota."
        if error.error_type == "channel_not_found":
            return "Channel not found. Please check the URL and try again."
        if error.error_type == "transcript_unavailable":
            return "No transcript available for this video. It may be missing captions."
        if error.error_type == "llm_error":
            return "AI generation failed. Please check your API keys and try again."
        if error.error_type == "timeout":
            return "Request timed out. Please check your network and try again."
        if error.error_type == "network_error":
            return "Network error. Please check your internet connection."
        return error.message

    @staticmethod
    def log_error(error: PipelineError) -> None:
        logger.error(
            "Pipeline error [stage=%s, type=%s, recoverable=%s]: %s\n%s",
            error.stage, error.error_type, error.recoverable,
            error.message, error.traceback,
        )
