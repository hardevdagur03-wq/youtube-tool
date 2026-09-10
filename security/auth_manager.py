from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from security.api_key_manager import APIKeyManager
from security.audit_logger import SecurityAuditLogger
from security.jwt_service import JWTService
from security.oauth_service import OAuthProvider, OAuthService
from security.permission_service import PermissionService
from security.rbac import RBACManager
from security.rate_limiter import SecurityRateLimiter
from security.security_models import (
    APIKey, AlertSeverity, AuthenticationError, AuthorizationError,
    AuthProvider, InvalidTokenError, Permission, SecurityEvent,
    Session, SessionStatus, TokenExpiredError, User, UserRole,
)
from security.threat_detector import ThreatDetector


class AuthManager:
    def __init__(
        self,
        jwt_service: JWTService | None = None,
        oauth_service: OAuthService | None = None,
        rbac: RBACManager | None = None,
        permission_service: PermissionService | None = None,
        api_key_manager: APIKeyManager | None = None,
        rate_limiter: SecurityRateLimiter | None = None,
        threat_detector: ThreatDetector | None = None,
        audit_logger: SecurityAuditLogger | None = None,
        get_user_by_id: Callable[[str], User | None] | None = None,
        get_user_by_email: Callable[[str], User | None] | None = None,
    ):
        self._jwt = jwt_service or JWTService()
        self._oauth = oauth_service or OAuthService()
        self._rbac = rbac or RBACManager()
        self._permission_service = permission_service or PermissionService(self._rbac)
        self._api_key_manager = api_key_manager or APIKeyManager()
        self._rate_limiter = rate_limiter or SecurityRateLimiter()
        self._threat_detector = threat_detector or ThreatDetector()
        self._audit_logger = audit_logger or SecurityAuditLogger()
        self._get_user_by_id = get_user_by_id or (lambda uid: None)
        self._get_user_by_email = get_user_by_email or (lambda email: None)
        self._sessions: dict[str, Session] = {}
        self._users: dict[str, User] = {}

    def register_user(self, user: User) -> User:
        self._users[user.id] = user
        self._audit_logger.log_event(
            event_type="user.created",
            actor_id=user.id,
            action="register",
            resource_type="user",
            resource_id=user.id,
        )
        return user

    def _find_user_by_email(self, email: str) -> User | None:
        user = self._get_user_by_email(email)
        if user:
            return user
        for u in self._users.values():
            if u.email == email:
                return u
        return None

    def authenticate(self, identifier: str, password: str) -> dict[str, Any]:
        self._rate_limiter.check(f"auth:{identifier}")
        try:
            self._threat_detector.check_brute_force(identifier)
        except Exception:
            self._audit_logger.log_event(
                event_type="threat.detected",
                actor_id=identifier,
                action="brute_force_blocked",
                severity="high",
            )
            raise
        user = self._find_user_by_email(identifier)
        if not user:
            user = self._users.get(identifier)
        if not user or not self._verify_password(password, user.password_hash):
            self._threat_detector.record_failed_attempt(identifier)
            self._audit_logger.log_event(
                event_type="auth.failed",
                actor_id=identifier,
                action="login_failed",
                severity="medium",
            )
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        self._threat_detector.reset_attempts(identifier)
        access_token = self._jwt.create_access_token(user)
        refresh_token = self._jwt.create_refresh_token(user.id)
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
        )
        self._sessions[session.id] = session
        self._audit_logger.log_event(
            event_type="auth.login",
            actor_id=user.id,
            action="login",
            resource_type="session",
            resource_id=session.id,
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.to_dict(),
        }

    def authenticate_with_api_key(self, api_key: str) -> dict[str, Any]:
        self._rate_limiter.check(f"api:{api_key[:8]}")
        key_data = self._api_key_manager.validate(api_key)
        user = self._get_user_by_id(key_data.user_id)
        if not user:
            user = self._users.get(key_data.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return {
            "user": user,
            "api_key": key_data,
        }

    def authenticate_oauth(self, provider: AuthProvider, code: str, redirect_uri: str) -> dict[str, Any]:
        self._rate_limiter.check(f"auth:oauth:{provider.value}")
        oauth_provider = OAuthProvider(
            name=provider.value,
            client_id="",
            client_secret="",
            authorize_url="",
            token_url="",
            userinfo_url="",
            scopes=["openid", "email", "profile"],
        )
        token_data = self._oauth.exchange_code(oauth_provider, code, redirect_uri)
        user_info = self._oauth.get_user_info(oauth_provider, token_data["access_token"])
        email = user_info.get("email", "")
        user = self._get_user_by_email(email)
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                username=user_info.get("name", email.split("@")[0]),
                auth_provider=provider,
            )
            self.register_user(user)
        access_token = self._jwt.create_access_token(user)
        refresh_token = self._jwt.create_refresh_token(user.id)
        self._audit_logger.log_event(
            event_type="auth.login",
            actor_id=user.id,
            action="oauth_login",
            resource_type="session",
            details={"provider": provider.value},
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.to_dict(),
        }

    def verify_token(self, token: str) -> User:
        payload = self._jwt.verify_token(token)
        user_id = payload.get("sub", "")
        user = self._get_user_by_id(user_id)
        if not user:
            user = self._users.get(user_id)
        if not user:
            raise InvalidTokenError("User not found")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        return user

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        payload = self._jwt.verify_token(refresh_token, expected_type="refresh")
        user_id = payload.get("sub", "")
        user = self._get_user_by_id(user_id)
        if not user:
            user = self._users.get(user_id)
        if not user:
            raise InvalidTokenError("User not found")
        new_access = self._jwt.create_access_token(user)
        new_refresh = self._jwt.create_refresh_token(user.id)
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }

    def check_permission(self, user: User, permission: Permission) -> bool:
        return self._permission_service.can(user, permission)

    def require_permission(self, user: User, permission: Permission) -> None:
        if not self.check_permission(user, permission):
            self._audit_logger.log_event(
                event_type="permission.denied",
                actor_id=user.id,
                action="permission_check",
                resource_type="permission",
                resource_id=permission.value,
                severity="medium",
            )
            raise AuthorizationError(f"Missing permission: {permission.value}")

    def logout(self, user_id: str) -> None:
        for sid, session in list(self._sessions.items()):
            if session.user_id == user_id:
                session.status = SessionStatus.REVOKED
        self._audit_logger.log_event(
            event_type="auth.logout",
            actor_id=user_id,
            action="logout",
        )

    def get_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values() if s.user_id == user_id]

    def revoke_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.REVOKED
            self._audit_logger.log_event(
                event_type="session.revoked",
                actor_id=session.user_id,
                action="revoke_session",
                resource_type="session",
                resource_id=session_id,
            )

    def _verify_password(self, password: str, password_hash: str) -> bool:
        from hashlib import sha256
        return sha256(password.encode()).hexdigest() == password_hash
