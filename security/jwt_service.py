from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from jose.constants import ALGORITHMS

from security.security_models import (
    AuthenticationError, InvalidTokenError, TokenExpiredError, User,
)


@dataclass
class JWTConfig:
    secret_key: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "change-me-in-production-32-chars!")
    )
    algorithm: str = ALGORITHMS.HS256
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    refresh_token_expire_days: int = field(
        default_factory=lambda: int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    )
    issuer: str = field(
        default_factory=lambda: os.getenv("JWT_ISSUER", "youtube-seo-platform")
    )
    audience: str = field(
        default_factory=lambda: os.getenv("JWT_AUDIENCE", "youtube-seo-api")
    )


class JWTService:
    def __init__(self, config: JWTConfig | None = None):
        self._config = config or JWTConfig()

    def create_access_token(self, user: User, extra_claims: dict[str, Any] | None = None) -> str:
        now = datetime.now(timezone.utc)
        user_id = getattr(user, "uuid", None) or getattr(user, "id", "")
        user_email = getattr(user, "email", "")
        user_role = getattr(user, "role", "viewer")
        if hasattr(user_role, "value"):
            user_role = user_role.value
        user_org = getattr(user, "organization_id", "")
        payload = {
            "sub": user_id,
            "email": user_email,
            "role": user_role,
            "org_id": user_org,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self._config.access_token_expire_minutes),
            "iss": self._config.issuer,
            "aud": self._config.audience,
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._config.secret_key, algorithm=self._config.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self._config.refresh_token_expire_days),
            "iss": self._config.issuer,
            "aud": self._config.audience,
        }
        return jwt.encode(payload, self._config.secret_key, algorithm=self._config.algorithm)

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self._config.secret_key,
                algorithms=[self._config.algorithm],
                audience=self._config.audience,
                issuer=self._config.issuer,
            )
            if payload.get("type") != expected_type:
                raise InvalidTokenError(f"Invalid token type: expected {expected_type}")
            return payload
        except JWTError as e:
            msg = str(e)
            if "expired" in msg.lower():
                raise TokenExpiredError("Token has expired")
            raise InvalidTokenError(f"Invalid token: {msg}")

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._config.secret_key,
                              algorithms=[self._config.algorithm],
                              audience=self._config.audience)
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {e}")

    def refresh_access_token(self, refresh_token: str) -> str:
        payload = self.verify_token(refresh_token, expected_type="refresh")
        user_id = payload.get("sub", "")
        user = User(id=user_id, email="", username="", organization_id="")
        return self.create_access_token(user)

    def get_user_id_from_token(self, token: str) -> str:
        payload = self.decode_token(token)
        return payload.get("sub", "")

    def get_claims(self, token: str) -> dict[str, Any]:
        return self.decode_token(token)
