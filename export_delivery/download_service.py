"""Download Service — signed URL generation and download management.

Creates secure download links with token-based authentication.
Supports direct downloads, signed URLs, temporary access, and streaming.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from export_delivery.config import ExportDeliveryConfig
from export_delivery.constants import DOWNLOAD_TOKEN_EXPIRY_DEFAULT, DOWNLOAD_TOKEN_BYTES
from export_delivery.models import DownloadLink

logger = logging.getLogger(__name__)


class DownloadService:
    """Manages download tokens and signed URLs for exported files.

    Usage::

        svc = DownloadService()
        link = svc.create_download_link("export123", "markdown", "/path/to/file.md")
        validated = svc.validate_download_token(link.token)
    """

    def __init__(self, config: ExportDeliveryConfig | None = None) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._tokens: dict[str, dict[str, Any]] = {}
        self._token_ttl = self._config.download_token_expiry

    def create_download_link(
        self, export_id: str, format_key: str,
        file_path: str, filename: str | None = None,
        expires_in: int | None = None,
    ) -> DownloadLink:
        """Create a signed download link for an exported file.

        Args:
            export_id: Export job ID.
            format_key: Format key (e.g. 'markdown').
            file_path: Path to the exported file.
            filename: Optional display filename.
            expires_in: Link expiry in seconds (default: config value).

        Returns:
            ``DownloadLink`` with URL, token, and metadata.
        """
        expires_in = expires_in or self._token_ttl
        token = self._generate_token()
        display_name = filename or os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        base_url = self._config.download_base_url or ""

        # Compute mime type from format
        from export_delivery.constants import FORMATS
        fmt_info = FORMATS.get(format_key, {})
        mime_type = fmt_info.get("mime", "application/octet-stream")

        # Store token
        self._tokens[token] = {
            "export_id": export_id,
            "format": format_key,
            "file_path": file_path,
            "filename": display_name,
            "expires_at": expires_at.timestamp(),
            "created_at": time.time(),
            "download_count": 0,
            "max_downloads": 10,
        }

        url = f"{base_url}/api/v3/downloads/{token}"
        if not base_url:
            url = f"/api/v3/downloads/{token}"

        link = DownloadLink(
            url=url,
            token=token,
            filename=display_name,
            format_key=format_key,
            expires_at=expires_at.isoformat(),
            size_bytes=file_size,
            mime_type=mime_type,
        )

        logger.info(
            "Download link created: export=%s format=%s token=%s",
            export_id[:8] if len(export_id) > 8 else export_id,
            format_key, token[:8],
        )

        return link

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """Validate a download token and return file info.

        Args:
            token: Download token string.

        Returns:
            Dict with file info if valid, None if invalid/expired.
        """
        entry = self._tokens.get(token)
        if entry is None:
            return None

        # Check expiry
        if time.time() > entry["expires_at"]:
            del self._tokens[token]
            logger.warning("Download token expired: %s", token[:8])
            return None

        # Check download limit
        if entry["download_count"] >= entry.get("max_downloads", 10):
            logger.warning("Download limit reached: %s", token[:8])
            return None

        # Check file exists
        if not os.path.isfile(entry["file_path"]):
            logger.warning("Download file not found: %s", entry["file_path"])
            return None

        # Increment download count
        entry["download_count"] += 1

        return {
            "file_path": entry["file_path"],
            "filename": entry["filename"],
            "format": entry["format"],
            "export_id": entry["export_id"],
            "download_count": entry["download_count"],
        }

    def revoke_token(self, token: str) -> bool:
        """Revoke a download token.

        Args:
            token: Download token to revoke.

        Returns:
            True if revoked, False if not found.
        """
        if token in self._tokens:
            del self._tokens[token]
            logger.info("Download token revoked: %s", token[:8])
            return True
        return False

    def clean_expired(self) -> int:
        """Remove all expired tokens.

        Returns:
            Number of tokens removed.
        """
        now = time.time()
        expired = [t for t, e in self._tokens.items() if now > e["expires_at"]]
        for t in expired:
            del self._tokens[t]
        if expired:
            logger.info("Cleaned %d expired download tokens", len(expired))
        return len(expired)

    def get_stats(self) -> dict[str, Any]:
        """Get download service statistics.

        Returns:
            Dict with token count, active links, etc.
        """
        now = time.time()
        active = sum(1 for e in self._tokens.values() if now <= e["expires_at"])
        total_downloads = sum(e.get("download_count", 0) for e in self._tokens.values())
        return {
            "total_tokens": len(self._tokens),
            "active_tokens": active,
            "expired_tokens": len(self._tokens) - active,
            "total_downloads": total_downloads,
        }

    @staticmethod
    def _generate_token() -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(DOWNLOAD_TOKEN_BYTES)
