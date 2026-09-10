from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from pathlib import Path

from publishing.models import DownloadInfo

logger = logging.getLogger(__name__)

TOKENS_FILE = "download_tokens.json"
DEFAULT_EXPIRY = 3600


class DownloadManager:
    def __init__(self, tokens_file: str | Path = TOKENS_FILE,
                 expiry: int = DEFAULT_EXPIRY):
        self.tokens_file = Path(tokens_file)
        self.expiry = expiry
        self._tokens: dict[str, dict] = {}
        self._load_tokens()

    def create_token(self, file_path: str | Path, export_id: str,
                     format_name: str, filename: str | None = None) -> DownloadInfo:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        now = time.time()

        entry = {
            "token_hash": token_hash,
            "token": token,
            "file_path": str(file_path),
            "export_id": export_id,
            "format": format_name,
            "filename": filename or Path(str(file_path)).name,
            "created_at": now,
            "expires_at": now + self.expiry,
            "download_count": 0,
        }

        self._tokens[token_hash] = entry
        self._save_tokens()

        return DownloadInfo(
            token=token,
            token_hash=token_hash,
            file_path=str(file_path),
            export_id=export_id,
            format=format_name,
            filename=entry["filename"],
            expires_at=entry["expires_at"],
            download_count=0,
        )

    def validate_token(self, token: str) -> DownloadInfo | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        entry = self._tokens.get(token_hash)

        if not entry:
            return None

        if time.time() > entry["expires_at"]:
            del self._tokens[token_hash]
            self._save_tokens()
            return None

        entry["download_count"] += 1
        self._save_tokens()

        return DownloadInfo(
            token=entry["token"],
            token_hash=token_hash,
            file_path=entry["file_path"],
            export_id=entry["export_id"],
            format=entry["format"],
            filename=entry["filename"],
            expires_at=entry["expires_at"],
            download_count=entry["download_count"],
        )

    def revoke_token(self, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        if token_hash in self._tokens:
            del self._tokens[token_hash]
            self._save_tokens()
            return True
        return False

    def clean_expired(self) -> int:
        now = time.time()
        expired = [h for h, e in self._tokens.items() if now > e["expires_at"]]
        for h in expired:
            del self._tokens[h]
        if expired:
            self._save_tokens()
        return len(expired)

    def get_token_info(self, token: str) -> DownloadInfo | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        entry = self._tokens.get(token_hash)
        if not entry:
            return None
        return DownloadInfo(
            token=entry["token"],
            token_hash=token_hash,
            file_path=entry["file_path"],
            export_id=entry["export_id"],
            format=entry["format"],
            filename=entry["filename"],
            expires_at=entry["expires_at"],
            download_count=entry["download_count"],
        )

    def _load_tokens(self) -> None:
        if self.tokens_file.exists():
            try:
                data = json.loads(self.tokens_file.read_text(encoding="utf-8"))
                self._tokens = data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load tokens: %s", e)
                self._tokens = {}

    def _save_tokens(self) -> None:
        try:
            self.tokens_file.write_text(
                json.dumps(self._tokens, indent=2), encoding="utf-8"
            )
        except IOError as e:
            logger.warning("Failed to save tokens: %s", e)
