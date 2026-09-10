from __future__ import annotations

import uuid

import pytest

from security.auth_manager import AuthManager
from security.security_models import (
    AuthenticationError, AuthorizationError, InvalidTokenError,
    Permission, User, UserRole,
)


class TestAuthManager:
    def setup_method(self):
        self.manager = AuthManager()
        self.user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            role=UserRole.EDITOR,
            is_active=True,
            password_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        )
        self.manager.register_user(self.user)

    def test_register_user(self):
        new_user = User(
            id=str(uuid.uuid4()), email="new@example.com", username="newuser", role=UserRole.VIEWER,
        )
        result = self.manager.register_user(new_user)
        assert result.id == new_user.id

    def test_authenticate_success(self):
        result = self.manager.authenticate(self.user.email, "test")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == self.user.email

    def test_authenticate_failure_wrong_password(self):
        with pytest.raises(AuthenticationError):
            self.manager.authenticate(self.user.email, "wrong")

    def test_authenticate_failure_unknown_user(self):
        with pytest.raises(AuthenticationError):
            self.manager.authenticate("unknown@example.com", "password")

    def test_authenticate_inactive_user(self):
        inactive = User(
            id=str(uuid.uuid4()), email="inactive@example.com", username="inactive",
            is_active=False,
        )
        self.manager.register_user(inactive)
        with pytest.raises(AuthenticationError):
            self.manager.authenticate(inactive.email, "test")

    def test_verify_token_valid(self):
        result = self.manager.authenticate(self.user.email, "test")
        user = self.manager.verify_token(result["access_token"])
        assert user.id == self.user.id

    def test_verify_token_invalid(self):
        with pytest.raises(InvalidTokenError):
            self.manager.verify_token("invalid-token")

    def test_refresh_token(self):
        result = self.manager.authenticate(self.user.email, "test")
        refreshed = self.manager.refresh_token(result["refresh_token"])
        assert "access_token" in refreshed
        assert "refresh_token" in refreshed

    def test_check_permission_allowed(self):
        result = self.manager.check_permission(self.user, Permission.PROJECT_READ)
        assert result is True

    def test_check_permission_denied(self):
        result = self.manager.check_permission(self.user, Permission.ADMIN_ACCESS)
        assert result is False

    def test_require_permission_allowed(self):
        self.manager.require_permission(self.user, Permission.PROJECT_CREATE)

    def test_require_permission_denied(self):
        with pytest.raises(AuthorizationError):
            self.manager.require_permission(self.user, Permission.ADMIN_ACCESS)

    def test_logout_revokes_sessions(self):
        result = self.manager.authenticate(self.user.email, "test")
        self.manager.logout(self.user.id)
        sessions = self.manager.get_user_sessions(self.user.id)
        assert all(s["status"] == "revoked" for s in sessions)

    def test_revoke_session(self):
        result = self.manager.authenticate(self.user.email, "test")
        sessions = self.manager.get_user_sessions(self.user.id)
        session_id = sessions[0]["id"]
        self.manager.revoke_session(session_id)
        updated = self.manager.get_user_sessions(self.user.id)
        assert updated[0]["status"] == "revoked"

    def test_authenticate_brute_force_lockout(self):
        from security.security_models import ThreatDetectedError
        for _ in range(5):
            try:
                self.manager.authenticate(self.user.email, "wrong")
            except AuthenticationError:
                pass
        with pytest.raises(ThreatDetectedError):
            self.manager.authenticate(self.user.email, "wrong")

    def test_authenticate_tracks_failed_attempts(self):
        for _ in range(3):
            try:
                self.manager.authenticate(self.user.email, "wrong")
            except AuthenticationError:
                pass
        summary = self.manager._threat_detector.get_threat_summary()
        assert summary["failed_logins_total"] >= 3

    def test_authenticate_api_key_with_key_manager(self):
        api_key_obj, raw_key = self.manager._api_key_manager.generate(
            user_id=self.user.id, name="test-key"
        )
        result = self.manager.authenticate_with_api_key(raw_key)
        assert result["user"].email == self.user.email

    def test_authenticate_api_key_invalid(self):
        with pytest.raises(Exception):
            self.manager.authenticate_with_api_key("invalid-key-12345")
