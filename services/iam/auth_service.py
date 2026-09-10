"""Authentication service — login, registration, OAuth, MFA, session management.

Bridges the security layer with the database layer.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from database.base import utcnow
from database.models import UserModel, OrganizationMemberModel, OrganizationModel
from database.repositories.base import BaseRepository
from security.jwt_service import JWTService, JWTConfig
from security.oauth_service import OAuthService
from security.security_models import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    Permission,
    TokenExpiredError,
    UserRole,
    ThreatType,
)
from services.iam.password_service import PasswordService


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


@dataclass
class AuthResult:
    success: bool
    user: Any = None
    tokens: TokenPair | None = None
    error: str = ""
    error_code: str = ""


class AuthService:
    """Primary authentication service.

    Handles registration, login, OAuth, token management, MFA.
    Uses repository pattern for database access.
    """

    def __init__(
        self,
        user_repo: BaseRepository,
        jwt_service: JWTService | None = None,
        oauth_service: OAuthService | None = None,
    ):
        self._user_repo = user_repo
        self._jwt = jwt_service or JWTService()
        self._oauth = oauth_service or OAuthService()
        self._password = PasswordService()

    # --- Email/Password Registration ---

    async def register(
        self,
        email: str,
        password: str,
        username: str,
        display_name: str = "",
    ) -> AuthResult:
        email = email.strip().lower()
        existing = await self._user_repo.get_by_field("email", email)
        if existing:
            return AuthResult(
                success=False, error="Email already registered",
                error_code="EMAIL_EXISTS",
            )

        valid, msg = PasswordService.validate_password_strength(password)
        if not valid:
            return AuthResult(success=False, error=msg, error_code="WEAK_PASSWORD")

        password_hash = PasswordService.hash_password(password)
        user = UserModel(
            email=email,
            username=username,
            password_hash=password_hash,
            display_name=display_name or username,
        )
        saved = await self._user_repo.create(user)

        tokens = self._create_token_pair(saved)
        return AuthResult(success=True, user=saved, tokens=tokens)

    # --- Email/Password Login ---

    async def login(self, email: str, password: str) -> AuthResult:
        email = email.strip().lower()
        user = await self._user_repo.get_by_field("email", email)
        if not user:
            return AuthResult(
                success=False, error="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )

        if user.is_deleted:
            return AuthResult(
                success=False, error="Account not found",
                error_code="ACCOUNT_NOT_FOUND",
            )

        if not PasswordService.verify_password(password, user.password_hash):
            return AuthResult(
                success=False, error="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )

        if not user.is_active:
            return AuthResult(
                success=False, error="Account is deactivated",
                error_code="ACCOUNT_INACTIVE",
            )

        user.last_login_at = utcnow()
        await self._user_repo.update(user)

        tokens = self._create_token_pair(user)
        return AuthResult(success=True, user=user, tokens=tokens)

    # --- OAuth Login ---

    async def oauth_login(
        self, provider: str, code: str
    ) -> AuthResult:
        try:
            oauth_user = await self._oauth.authenticate(provider, code)
        except AuthenticationError as e:
            return AuthResult(
                success=False, error=str(e), error_code="OAUTH_FAILED",
            )

        provider_id = f"{provider}_{oauth_user.id}"
        identifier = f"oauth:{provider}:{oauth_user.id}"

        user = await self._user_repo.get_by_field("email", oauth_user.email)
        if not user:
            user = UserModel(
                email=oauth_user.email or f"{provider_id}@oauth.local",
                username=oauth_user.username or provider_id,
                password_hash=PasswordService.hash_password(secrets.token_urlsafe(32)),
                is_verified=True,
            )
            user = await self._user_repo.create(user)

        user.last_login_at = utcnow()
        await self._user_repo.update(user)

        tokens = self._create_token_pair(user)
        return AuthResult(success=True, user=user, tokens=tokens)

    # --- Token Management ---

    def _create_token_pair(self, user: Any) -> TokenPair:
        user_id = getattr(user, "uuid", None) or getattr(user, "id", "")
        role = getattr(user, "role", "viewer")
        if hasattr(role, "value"):
            role = role.value
        access_token = self._jwt.create_access_token(user)
        refresh_token = self._jwt.create_refresh_token(user_id)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,
        )

    def refresh_access_token(self, refresh_token: str) -> AuthResult:
        try:
            payload = self._jwt.verify_token(refresh_token, expected_type="refresh")
            user_id = payload.get("sub", "")
            if not user_id:
                return AuthResult(
                    success=False, error="Invalid refresh token",
                    error_code="INVALID_TOKEN",
                )
            new_access = self._jwt.create_access_token(
                type("obj", (), {"uuid": user_id, "email": "", "role": ""})()
            )
            return AuthResult(
                success=True,
                tokens=TokenPair(
                    access_token=new_access,
                    refresh_token=refresh_token,
                    expires_in=1800,
                ),
            )
        except TokenExpiredError:
            return AuthResult(
                success=False, error="Refresh token expired",
                error_code="TOKEN_EXPIRED",
            )
        except InvalidTokenError:
            return AuthResult(
                success=False, error="Invalid refresh token",
                error_code="INVALID_TOKEN",
            )

    def validate_access_token(self, token: str) -> dict[str, Any]:
        try:
            return self._jwt.verify_token(token, expected_type="access")
        except TokenExpiredError:
            raise
        except InvalidTokenError:
            raise
