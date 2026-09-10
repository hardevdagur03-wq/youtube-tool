"""YouTube Metadata Service — enterprise-grade video metadata retrieval.

Retrieves complete video metadata from the YouTube Data API v3,
normalizes all fields, and returns a structured ``VideoMetadata`` object.
"""

import logging
import re
from typing import Any

from api.video_service import VideoService, VideoServiceError
from api.youtube_client import (
    YouTubeClient,
    YouTubeAPIClientError,
    YouTubeAPISslError,
    YouTubeAPITimeoutError,
)
from models.video_metadata import (
    ChannelInfo,
    DateInfo,
    DescriptionInfo,
    DurationInfo,
    Thumbnails,
    VideoMetadata,
    VideoMetadataResponse,
    VideoStatistics,
)
from utils.cache import TTLCache
from utils.date_formatter import format_date
from utils.duration import format_duration, parse_duration_to_seconds
from utils.number_formatter import format_count
from utils.thumbnail import extract_thumbnails

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s]+")
_HASHTAG_RE = re.compile(r"#[\w]+")
_MENTION_RE = re.compile(r"@[\w]+")

_DURATION_READABLE_RE = re.compile(
    r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
)


def _format_duration_readable(iso: str | None) -> str | None:
    """Convert ISO-8601 duration to a human-readable string like '1 hr 25 min 17 sec'."""
    if not iso:
        return None
    match = _DURATION_READABLE_RE.fullmatch(iso)
    if not match:
        return None
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hr" if hours == 1 else f"{hours} hrs")
    if minutes:
        parts.append(f"{minutes} min" if minutes == 1 else f"{minutes} min")
    if seconds:
        parts.append(f"{seconds} sec" if seconds == 1 else f"{seconds} sec")

    return " ".join(parts) if parts else None


def _parse_description(text: str | None) -> DescriptionInfo:
    """Extract URLs, hashtags, and mentions from a description string."""
    if not text:
        return DescriptionInfo()
    return DescriptionInfo(
        full=text,
        urls=_URL_RE.findall(text),
        hashtags=_HASHTAG_RE.findall(text),
        mentions=_MENTION_RE.findall(text),
    )


def _determine_privacy(item: dict[str, Any]) -> str | None:
    """Extract privacy / status from the video resource."""
    status = item.get("status", {})
    if status.get("privacyStatus"):
        return status["privacyStatus"]
    # Fallback — check if uploadStatus implies availability
    upload = status.get("uploadStatus")
    if upload == "processed":
        return "public"
    if upload == "failed":
        return "unavailable"
    return None


def _determine_live_status(item: dict[str, Any]) -> str | None:
    """Extract live broadcast status."""
    snippet = item.get("snippet", {})
    live = snippet.get("liveBroadcastContent", "none")
    if live and live != "none":
        return live
    return None


class YouTubeMetadataService:
    """Service for retrieving and normalizing YouTube video metadata.

    This is a stateless service that wraps the YouTube Data API v3
    and returns structured, normalized metadata.

    Usage::

        service = YouTubeMetadataService()
        response = service.get_metadata("dQw4w9WgXcQ")
        if response.success:
            print(response.video.title)
    """

    def __init__(
        self,
        video_service: VideoService | None = None,
        cache: TTLCache[dict[str, Any]] | None = None,
    ) -> None:
        self._video_service = video_service or VideoService()
        self._cache = cache or TTLCache[dict[str, Any]](ttl_seconds=600)

    def get_metadata(self, video_id: str) -> VideoMetadataResponse:
        """Retrieve complete metadata for a single video.

        Args:
            video_id: An 11-character YouTube video ID.

        Returns:
            ``VideoMetadataResponse`` with ``success``, ``video``, and ``error``.
        """
        if not video_id or not isinstance(video_id, str) or len(video_id) != 11:
            return VideoMetadataResponse(
                success=False,
                error="Invalid video ID. Must be an 11-character YouTube video ID.",
            )

        # Check cache
        cache_key = f"metadata:{video_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for video %s", video_id)
            return VideoMetadataResponse(success=True, video=VideoMetadata(**cached))

        logger.info("Fetching metadata for video %s", video_id)

        try:
            items = self._video_service.get_videos_batch([video_id])
        except VideoServiceError as exc:
            logger.error("VideoService error for %s: %s", video_id, exc)
            return VideoMetadataResponse(
                success=False,
                error=_user_friendly_error(str(exc)),
            )
        except YouTubeAPISslError as exc:
            logger.error("YouTube SSL error for %s: %s", video_id, exc)
            return VideoMetadataResponse(
                success=False,
                error="Unable to connect securely to the video metadata service. "
                       "Please try again in a few moments.",
            )
        except YouTubeAPITimeoutError as exc:
            logger.error("YouTube timeout for %s: %s", video_id, exc)
            return VideoMetadataResponse(
                success=False,
                error="Connection to the video metadata service timed out. "
                       "Please check your network and try again.",
            )
        except YouTubeAPIClientError as exc:
            logger.error("YouTubeClient error for %s: %s", video_id, exc)
            return VideoMetadataResponse(
                success=False,
                error="YouTube API client error. Please check your API key.",
            )
        except Exception as exc:
            logger.exception("Unexpected error fetching metadata for %s", video_id)
            return VideoMetadataResponse(
                success=False,
                error="An unexpected error occurred. Please try again.",
            )

        if not items:
            return VideoMetadataResponse(
                success=False,
                error="Video not found. The video may be deleted or the ID is invalid.",
            )

        item = items[0]
        try:
            metadata = self._build_metadata(video_id, item)
        except Exception as exc:
            logger.exception("Failed to parse metadata for video %s", video_id)
            return VideoMetadataResponse(
                success=False,
                error="Failed to parse video metadata. The API response may be malformed.",
            )

        # Store in cache
        self._cache.set(cache_key, metadata.model_dump())

        return VideoMetadataResponse(success=True, video=metadata)

    def _build_metadata(self, video_id: str, item: dict[str, Any]) -> VideoMetadata:
        """Build a ``VideoMetadata`` object from a raw YouTube API item."""
        snippet: dict[str, Any] = item.get("snippet", {}) or {}
        content: dict[str, Any] = item.get("contentDetails", {}) or {}
        statistics: dict[str, Any] = item.get("statistics", {}) or {}

        # Duration
        iso_duration = content.get("duration")
        seconds = parse_duration_to_seconds(iso_duration)

        # Statistics
        raw_views = statistics.get("viewCount", 0)
        raw_likes = statistics.get("likeCount", 0)
        raw_comments = statistics.get("commentCount", 0)

        # Channel
        channel_name = snippet.get("channelTitle")
        channel_id = snippet.get("channelId")

        # Thumbnails
        thumbnails = extract_thumbnails(snippet.get("thumbnails"))

        # Description
        desc_raw = snippet.get("description")

        # Published date
        pub_date = format_date(snippet.get("publishedAt"))

        # Privacy
        privacy = _determine_privacy(item)

        # Live status
        live_status = _determine_live_status(item)

        return VideoMetadata(
            video_id=video_id,
            title=snippet.get("title"),
            description=_parse_description(desc_raw),
            channel=ChannelInfo(
                name=channel_name,
                id=channel_id,
                url=f"https://www.youtube.com/channel/{channel_id}" if channel_id else None,
            ),
            published_at=DateInfo(**pub_date),
            duration=DurationInfo(
                iso=iso_duration,
                readable=_format_duration_readable(iso_duration),
                compact=format_duration(seconds),
                seconds=seconds,
            ),
            statistics=VideoStatistics(
                views=_safe_int(raw_views),
                likes=_safe_int(raw_likes),
                comments=_safe_int(raw_comments),
                views_formatted=format_count(raw_views),
                likes_formatted=format_count(raw_likes),
                comments_formatted=format_count(raw_comments),
            ),
            thumbnails=Thumbnails(**thumbnails),
            tags=snippet.get("tags", []),
            category_id=snippet.get("categoryId"),
            language=snippet.get("defaultLanguage"),
            license=content.get("license"),
            embeddable=_safe_bool(content.get("embed", {}).get("embeddable")),
            caption=_safe_bool(content.get("caption")),
            privacy=privacy,
            live_status=live_status,
            default_audio_language=snippet.get("defaultAudioLanguage"),
        )


def _safe_int(value: Any) -> int:
    """Safely convert a value to int, defaulting to 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool | None:
    """Safely convert a value to bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def _user_friendly_error(error: str) -> str:
    """Convert API error messages to user-friendly messages."""
    error_lower = error.lower()
    if "quota" in error_lower:
        return "API quota exceeded. Please try again later."
    if "not found" in error_lower or "404" in error:
        return "Video not found. It may have been deleted or the ID is invalid."
    if "forbidden" in error_lower or "403" in error:
        return "Access forbidden. Please check your API key configuration."
    if "bad request" in error_lower:
        return "Invalid request. Please verify the video ID."
    return error
