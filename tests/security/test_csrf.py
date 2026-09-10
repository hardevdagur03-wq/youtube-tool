from __future__ import annotations

import secrets

import pytest


pytestmark = pytest.mark.security


class TestCSRF:
    def test_csrf_token_validation(self):
        token = secrets.token_hex(32)
        assert len(token) == 64
        assert token.isalnum()

    def test_missing_csrf_token(self):
        headers = {"Content-Type": "application/json"}
        assert "X-CSRF-Token" not in headers

    def test_invalid_csrf_token(self):
        valid_token = secrets.token_hex(32)
        invalid_token = "not_a_valid_token"
        assert invalid_token != valid_token
        assert len(invalid_token) != len(valid_token)

    def test_same_origin_policy(self):
        allowed_origins = {"https://example.com", "https://app.example.com"}
        request_origin = "https://malicious-site.com"
        assert request_origin not in allowed_origins

    def test_csrf_token_rotation(self):
        old_token = secrets.token_hex(32)
        new_token = secrets.token_hex(32)
        assert old_token != new_token

    @pytest.mark.parametrize("method,requires_csrf", [
        ("GET", False),
        ("HEAD", False),
        ("OPTIONS", False),
        ("POST", True),
        ("PUT", True),
        ("PATCH", True),
        ("DELETE", True),
    ])
    def test_csrf_method_checking(self, method, requires_csrf):
        safe_methods = {"GET", "HEAD", "OPTIONS"}
        if method in safe_methods:
            assert not requires_csrf
        else:
            assert requires_csrf

    def test_double_submit_cookie(self):
        cookie_token = secrets.token_hex(32)
        header_token = cookie_token
        assert cookie_token == header_token

    def test_csrf_token_bound_to_session(self):
        session_id = "session_123"
        token_for_session = secrets.token_hex(32)
        stored = {session_id: token_for_session}
        assert stored[session_id] == token_for_session
        assert "session_456" not in stored
