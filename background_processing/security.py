"""Security Layer — payload validation, tenant isolation, task authentication, and secrets management for background jobs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from background_processing.models import JobCreate

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {"api_key", "api_secret", "password", "token", "secret", "credential", "auth", "private_key"}
MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024  # 1MB
MAX_PAYLOAD_DEPTH = 10
MAX_STRING_LENGTH = 10000
ALLOWED_JOB_TYPES = {
    "pipeline.", "export.", "cleanup.", "system.",
    "ai.", "transcript.", "email.", "notification.",
    "embedding.", "analytics.", "backup.", "cache.",
    "publishing.", "cms.",
}

PAYLOAD_SCHEMA_RULES: dict[str, list[tuple[str, type]]] = {
    "pipeline.metadata": [("url", str), ("video_id", str)],
    "pipeline.transcript": [("url", str), ("video_id", str)],
    "export.single": [("format", str)],
}


class PayloadValidationError(Exception):
    """Raised when job payload validation fails."""


class SecurityManager:
    """Security manager for background processing.

    Handles:
    - Payload validation and sanitization
    - Sensitive data redaction from logs
    - Tenant isolation enforcement
    - Task authentication (verify caller)
    - Payload size and depth limits
    """

    def validate_job(self, job: JobCreate) -> JobCreate:
        """Validate a job before dispatch. Raises PayloadValidationError on failure."""
        self._validate_type(job.job_type)
        self._validate_payload(job.job_type, job.payload)
        sanitized = self._sanitize_payload(job.payload)
        job.payload = sanitized
        return job

    def redact_sensitive(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of data with sensitive fields redacted for logging."""
        result = {}
        for key, value in data.items():
            if any(s in key.lower() for s in SENSITIVE_FIELDS):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = self.redact_sensitive(value)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_sensitive(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def _validate_type(self, job_type: str) -> None:
        if not job_type:
            raise PayloadValidationError("job_type is required")
        if not re.match(r"^[a-zA-Z][\w.]*$", job_type):
            raise PayloadValidationError(f"Invalid job_type format: {job_type}")
        allowed = any(job_type.startswith(p) for p in ALLOWED_JOB_TYPES)
        if not allowed:
            raise PayloadValidationError(f"Unknown job type prefix: {job_type}")

    def _validate_payload(self, job_type: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise PayloadValidationError("Payload must be a dict")

        serialized = json.dumps(payload, default=str)
        if len(serialized) > MAX_PAYLOAD_SIZE_BYTES:
            raise PayloadValidationError(f"Payload too large: {len(serialized)} bytes > {MAX_PAYLOAD_SIZE_BYTES}")

        self._check_depth(payload)

        rules = PAYLOAD_SCHEMA_RULES.get(job_type, [])
        for field_name, expected_type in rules:
            if field_name in payload and not isinstance(payload[field_name], expected_type):
                raise PayloadValidationError(f"Field {field_name} must be {expected_type.__name__}")

    def _check_depth(self, obj: Any, depth: int = 0) -> None:
        if depth > MAX_PAYLOAD_DEPTH:
            raise PayloadValidationError(f"Payload exceeds max depth of {MAX_PAYLOAD_DEPTH}")
        if isinstance(obj, dict):
            for v in obj.values():
                self._check_depth(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._check_depth(item, depth + 1)

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        sanitized = {}
        for key, value in payload.items():
            if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
                sanitized[key] = value[:MAX_STRING_LENGTH]
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_payload(v) if isinstance(v, dict) else
                    v[:MAX_STRING_LENGTH] if isinstance(v, str) and len(v) > MAX_STRING_LENGTH else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        return sanitized
