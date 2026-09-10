from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from security.security_models import APIKey, APIKeyError, Permission


class APIKeyManager:
    def __init__(self):
        self._keys: dict[str, APIKey] = {}

    def generate(
        self,
        name: str,
        user_id: str,
        organization_id: str = "",
        permissions: list[Permission] | None = None,
        expires_in_days: int | None = None,
        allowed_ips: list[str] | None = None,
        allowed_origins: list[str] | None = None,
    ) -> tuple[APIKey, str]:
        key_id = secrets.token_hex(16)
        raw_key = f"ysk_{secrets.token_hex(32)}"
        key_hash = self._hash_key(raw_key)
        key_prefix = raw_key[:10]
        api_key = APIKey(
            id=key_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            user_id=user_id,
            organization_id=organization_id,
            permissions=permissions or [p for p in Permission],
            allowed_ips=allowed_ips or [],
            allowed_origins=allowed_origins or [],
        )
        if expires_in_days:
            api_key.expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
        self._keys[key_id] = api_key
        return api_key, raw_key

    def validate(self, raw_key: str) -> APIKey:
        prefix = raw_key[:10]
        for api_key in self._keys.values():
            if api_key.key_prefix == prefix:
                if not api_key.is_active:
                    raise APIKeyError("API key is inactive")
                if api_key.is_expired():
                    raise APIKeyError("API key has expired")
                if hmac.compare_digest(api_key.key_hash, self._hash_key(raw_key)):
                    api_key.last_used_at = datetime.now(timezone.utc).isoformat()
                    return api_key
        raise APIKeyError("Invalid API key")

    def revoke(self, key_id: str) -> None:
        if key_id in self._keys:
            self._keys[key_id].is_active = False

    def delete(self, key_id: str) -> None:
        self._keys.pop(key_id, None)

    def get(self, key_id: str) -> APIKey | None:
        return self._keys.get(key_id)

    def list_keys(self, user_id: str | None = None) -> list[APIKey]:
        if user_id:
            return [k for k in self._keys.values() if k.user_id == user_id]
        return list(self._keys.values())

    def update_permissions(self, key_id: str, permissions: list[Permission]) -> None:
        if key_id not in self._keys:
            raise APIKeyError("API key not found")
        self._keys[key_id].permissions = permissions

    def _hash_key(self, raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def validate_request(self, raw_key: str, ip_address: str = "", origin: str = "") -> APIKey:
        api_key = self.validate(raw_key)
        if api_key.allowed_ips and ip_address not in api_key.allowed_ips:
            raise APIKeyError("IP address not allowed for this API key")
        if api_key.allowed_origins and origin not in api_key.allowed_origins:
            raise APIKeyError("Origin not allowed for this API key")
        return api_key
