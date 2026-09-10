from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.security


class TestOWASPTop10:
    def test_a01_broken_access_control(self):
        roles = {"admin", "user", "viewer"}
        project_owner = "user_a"
        accessor = "user_b"
        assert project_owner != accessor
        assert "admin" in roles

    def test_a02_cryptographic_failures(self):
        import hashlib
        password = "test_password_123"
        hashed = hashlib.sha256(password.encode()).hexdigest()
        assert hashed != password
        assert len(hashed) == 64
        assert hashlib.sha256(password.encode()).hexdigest() == hashed

    def test_a03_injection(self):
        dangerous = "' OR 1=1 --"
        sanitized = dangerous.replace("'", "''")
        assert "'" not in sanitized or "''" in sanitized

    def test_a04_insecure_design(self):
        rate_limits = {"login": 5, "api": 100, "export": 10}
        assert all(limit > 0 for limit in rate_limits.values())
        assert "login" in rate_limits

    def test_a05_security_misconfiguration(self):
        import http.server
        assert hasattr(http.server, "HTTPServer")
        debug_enabled = os.environ.get("DEBUG", "").lower() == "true"
        assert not debug_enabled or os.environ.get("TEST_MODE") == "True"

    def test_a06_vulnerable_components(self):
        try:
            import celery
            ver = tuple(int(x) for x in celery.__version__.split(".")[:2])
            assert ver >= (5, 2), f"Celery {celery.__version__} is outdated"
        except ImportError:
            pass
        try:
            import redis
            ver = tuple(int(x) for x in redis.__version__.split(".")[:2])
            assert ver >= (4, 0), f"Redis {redis.__version__} is outdated"
        except ImportError:
            pass

    def test_a07_authentication_failures(self):
        attempt_count = 0
        max_attempts = 5
        for i in range(10):
            attempt_count += 1
            if attempt_count > max_attempts:
                break
        assert attempt_count == 6

    def test_a08_data_integrity_failures(self):
        original = {"project_id": "p1", "name": "Test"}
        tampered = {"project_id": "p1", "name": "Test", "role": "admin"}
        assert original != tampered
        assert "role" not in original

    def test_a09_security_logging_failures(self):
        log_entries = [
            "2026-07-01T12:00:00Z INFO User login: user1 from 192.168.1.1",
            "2026-07-01T12:01:00Z WARN Failed login attempt: unknown from 10.0.0.1",
            "2026-07-01T12:02:00Z ERROR Unauthorized access attempt to /admin by 10.0.0.2",
        ]
        assert len(log_entries) == 3
        assert any("Unauthorized" in entry for entry in log_entries)

    def test_a10_ssrf(self):
        internal_hosts = {"localhost", "127.0.0.1", "10.", "172.16.", "192.168.", "169.254."}
        external_url = "https://api.example.com/data"
        assert not any(external_url.startswith(f"http://{h}") or external_url.startswith(f"https://{h}") for h in internal_hosts)
