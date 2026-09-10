"""Tests for the Security Layer — payload validation, sanitization, redaction."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.models import JobCreate
from background_processing.security import PayloadValidationError, SecurityManager


class TestSecurityManager:
    @pytest.fixture
    def security(self):
        return SecurityManager()

    def test_validate_valid_job(self, security):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", payload={"video_id": "vid123"})
        validated = security.validate_job(job)
        assert validated.job_type == "pipeline.analysis"

    def test_validate_invalid_job_type(self, security):
        job = JobCreate(job_type="  invalid type!", project_id="p1")
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_validate_unknown_job_type_prefix(self, security):
        job = JobCreate(job_type="malicious.code", project_id="p1")
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_validate_payload_too_large(self, security):
        big_payload = {"data": "x" * (1024 * 1024 + 1)}
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", payload=big_payload)
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_validate_payload_deeply_nested(self, security):
        deep = {}
        current = deep
        for _ in range(15):
            current["nested"] = {}
            current = current["nested"]
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", payload=deep)
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_redact_sensitive_fields(self, security):
        data = {
            "api_key": "sk-1234567890",
            "normal_field": "hello",
            "nested": {"secret": "s3cr3t", "safe": "visible"},
        }
        redacted = security.redact_sensitive(data)
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["normal_field"] == "hello"
        assert redacted["nested"]["secret"] == "***REDACTED***"
        assert redacted["nested"]["safe"] == "visible"

    def test_sanitize_long_strings(self, security):
        long_str = "x" * 20000
        job = JobCreate(
            job_type="pipeline.analysis",
            project_id="p1",
            payload={"data": long_str},
        )
        validated = security.validate_job(job)
        assert len(validated.payload["data"]) == 10000  # truncated

    def test_validate_empty_job_type(self, security):
        job = JobCreate(job_type="", project_id="p1")
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_validate_non_dict_payload(self, security):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1")
        job.payload = "not a dict"  # type: ignore
        with pytest.raises(PayloadValidationError):
            security.validate_job(job)

    def test_allowed_job_types(self, security):
        for prefix in ["pipeline.", "export.", "cleanup.", "system.", "ai.", "email.", "notification."]:
            job = JobCreate(job_type=f"{prefix}test", project_id="p1")
            validated = security.validate_job(job)
            assert validated.job_type == f"{prefix}test"

    def test_redact_no_sensitive_data(self, security):
        data = {"name": "test", "count": 42}
        redacted = security.redact_sensitive(data)
        assert redacted == data
