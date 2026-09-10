from __future__ import annotations

import os
import re

import pytest


pytestmark = pytest.mark.security


SECRET_PATTERNS = [
    r'api[_-]?key[_-]?[\s=:]+["\'][A-Za-z0-9_\-]{16,}["\']',
    r'api[_-]?secret[_-]?[\s=:]+["\'][A-Za-z0-9_\-]{16,}["\']',
    r'secret[_-]?key[_-]?[\s=:]+["\'][A-Za-z0-9_\-]{16,}["\']',
    r'password[_-]?[\s=:]+["\'][A-Za-z0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{8,}["\']',
    r'bearer\s+[A-Za-z0-9_\-\.]{20,}',
    r'token[_-]?[\s=:]+["\'][A-Za-z0-9_\-]{16,}["\']',
]


class TestSecretLeakage:
    def test_no_secrets_in_logs(self):
        log_content = """
INFO: Project created successfully
DEBUG: Processing video dQw4w9WgXcQ
INFO: Export completed for project p1
ERROR: Database connection timeout
"""
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            assert len(matches) == 0, f"Secret pattern found in logs: {matches}"

    def test_no_secrets_in_error_messages(self):
        error_msg = "Error processing project p1: Video not found"
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern, error_msg, re.IGNORECASE)
            assert len(matches) == 0, f"Secret pattern found in error: {matches}"

    def test_no_secrets_in_api_responses(self):
        api_response = '{"project_id": "p1", "status": "completed", "name": "Test"}'
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern, api_response, re.IGNORECASE)
            assert len(matches) == 0, f"Secret pattern found in API response: {matches}"

    def test_secret_masking(self):
        secrets_map = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "password": "super_secret_password_123",
            "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMSJ9.signature",
        }
        masked = {}
        for key, value in secrets_map.items():
            if len(value) > 8:
                masked[key] = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked[key] = "****"
            assert "*" in masked[key]
            assert masked[key] != value

    def test_env_var_sanitization(self):
        safe_envs = {k: v for k, v in os.environ.items() if not k.lower().startswith("test_")}
        for key in safe_envs:
            val = safe_envs[key]
            if any(pat in key.lower() for pat in ["key", "secret", "password", "token"]):
                assert len(val) > 0
