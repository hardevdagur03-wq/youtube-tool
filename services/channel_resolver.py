"""Business logic for validating and resolving YouTube channel identifiers.

Supports three input formats:
1. **Handle**: ``@handle`` or ``handle``
2. **Channel ID**: ``UC...``
3. **Channel URL**: ``https://youtube.com/@handle`` or ``https://youtube.com/channel/UC...``
"""

import logging
import re
from urllib.parse import urlparse

from api.channel_service import (
    ChannelService,
    ChannelNotFoundError,
    ChannelServiceError,
)

logger = logging.getLogger(__name__)

HANDLE_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,30}$")
CHANNEL_ID_PATTERN = re.compile(r"^UC[\w-]{22,}$")
YOUTUBE_DOMAINS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "music.youtube.com", "youtube-nocookie.com",
}


class ChannelResolverError(Exception):
    """Base exception for channel resolution errors."""
    pass


class InvalidHandleError(ChannelResolverError):
    """Raised when the provided identifier fails format validation."""
    pass


class ChannelResolver:
    """Orchestrates channel identifier parsing and ID resolution.

    Accepts a YouTube handle, channel ID, or channel URL and resolves
    it to a channel ID and title via the YouTube Data API.
    """

    def __init__(self, channel_service: ChannelService | None = None) -> None:
        self._channel_service = channel_service or ChannelService()

    @staticmethod
    def _is_channel_id(value: str) -> bool:
        return bool(CHANNEL_ID_PATTERN.match(value))

    @staticmethod
    def _is_youtube_url(value: str) -> bool:
        try:
            parsed = urlparse(value.strip())
            return parsed.netloc.lower() in YOUTUBE_DOMAINS and parsed.scheme in ("http", "https")
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _extract_from_url(value: str) -> str:
        """Extract a handle or channel ID from a YouTube URL."""
        parsed = urlparse(value.strip())
        path = parsed.path.rstrip("/")

        # https://youtube.com/@handle
        at_match = re.search(r"/@([A-Za-z0-9._-]+)", path)
        if at_match:
            return at_match.group(1)

        # https://youtube.com/channel/UC...
        channel_match = re.search(r"/channel/(UC[\w-]+)", path)
        if channel_match:
            return channel_match.group(1)

        # https://youtube.com/c/... or /user/...
        raise InvalidHandleError(
            "Channel URL format not recognized. "
            "Please use a handle like @handle or a channel ID (UC...). "
            "Custom /c/ and /user/ URLs are not supported by the YouTube API."
        )

    @staticmethod
    def validate_handle(handle: str) -> str:
        """Validate and normalize a YouTube channel handle.

        Rules:
        - Must not be empty or whitespace-only.
        - Must be 3–30 characters (after stripping ``@``).
        - May contain letters, digits, dots, hyphens, and underscores.

        Args:
            handle: Raw input string.

        Returns:
            Normalized handle with ``@`` prefix.

        Raises:
            InvalidHandleError: If validation fails.
        """
        cleaned = handle.strip()
        if not cleaned:
            raise InvalidHandleError("Channel identifier cannot be empty.")

        stripped = cleaned.lstrip("@")
        if not HANDLE_PATTERN.match(stripped):
            raise InvalidHandleError(
                f"Invalid channel handle: '{handle}'. "
                "A handle must be 3–30 characters and may contain letters, "
                "digits, dots, hyphens, or underscores."
            )
        return f"@{stripped}"

    def resolve(self, raw: str) -> dict:
        """Full resolution pipeline: detect input type → resolve → parse response.

        Args:
            raw: User-provided channel identifier.
                 Can be a handle (``@channel`` / ``channel``),
                 a channel ID (``UC...``), or a YouTube channel URL.

        Returns:
            Dictionary with keys:
            - ``channel_id``: Resolved YouTube channel ID.
            - ``title``: Channel display name.
            - ``handle``: Normalized handle (with ``@``).

        Raises:
            InvalidHandleError: If input format is invalid.
            ChannelResolverError: If API resolution fails.
        """
        logger.info("Channel lookup started for input: %s", raw)
        raw_stripped = raw.strip()

        # Step 1: Detect input type and extract the identifier
        if self._is_youtube_url(raw_stripped):
            identifier = self._extract_from_url(raw_stripped)
            logger.info("Input is a YouTube URL; extracted identifier: %s", identifier)
        else:
            identifier = raw_stripped

        # Step 2: Determine resolution strategy
        resolved_handle: str = ""
        if self._is_channel_id(identifier):
            logger.info("Input identified as channel ID: %s", identifier)
            resolved_handle = identifier
            try:
                item = self._channel_service.get_channel_by_id(identifier)
            except ChannelNotFoundError as exc:
                logger.error("Channel not found: %s", exc)
                raise ChannelResolverError(str(exc)) from exc
            except ChannelServiceError as exc:
                logger.error("Channel service error: %s", exc)
                raise ChannelResolverError(str(exc)) from exc
        else:
            normalized = self.validate_handle(identifier)
            resolved_handle = normalized
            logger.info("Input validated, normalized handle: %s", normalized)
            try:
                item = self._channel_service.resolve_handle(normalized)
            except ChannelNotFoundError as exc:
                logger.error("Channel not found: %s", exc)
                raise ChannelResolverError(str(exc)) from exc
            except ChannelServiceError as exc:
                logger.error("Channel service error: %s", exc)
                raise ChannelResolverError(str(exc)) from exc

        channel_id = item["id"]
        title = item.get("snippet", {}).get("title", "Unknown")

        logger.info(
            "Channel resolved: ID=%s, Title='%s'",
            channel_id,
            title,
        )

        return {
            "channel_id": channel_id,
            "title": title,
            "handle": resolved_handle,
        }
