from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class SecretManagerConfig:
    encryption_key: str = field(
        default_factory=lambda: os.getenv("SECRETS_ENCRYPTION_KEY", "")
    )
    salt: str = field(
        default_factory=lambda: os.getenv("SECRETS_SALT", "youtube-seo-salt")
    )


class SecretManager:
    def __init__(self, config: SecretManagerConfig | None = None):
        self._config = config or SecretManagerConfig()
        self._fernet: Fernet | None = None
        self._cache: dict[str, str] = {}

    def _get_fernet(self) -> Fernet:
        if self._fernet is not None:
            return self._fernet
        if self._config.encryption_key:
            key = base64.urlsafe_b64encode(
                PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=self._config.salt.encode(),
                    iterations=100000,
                ).derive(self._config.encryption_key.encode())
            )
        else:
            key = Fernet.generate_key()
        self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        fernet = self._get_fernet()
        return fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        fernet = self._get_fernet()
        return fernet.decrypt(ciphertext.encode()).decode()

    def cache_secret(self, key: str, value: str) -> None:
        self._cache[key] = self.encrypt(value)

    def get_cached_secret(self, key: str) -> str | None:
        encrypted = self._cache.get(key)
        if encrypted is None:
            return None
        return self.decrypt(encrypted)

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def generate_encryption_key() -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def get_config_value(self, key: str, default: str = "") -> str:
        encrypted = os.getenv(f"SECRET_{key}", "")
        if encrypted:
            try:
                return self.decrypt(encrypted)
            except Exception:
                pass
        return os.getenv(key, default)
