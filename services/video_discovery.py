"""Business logic for discovering all uploaded videos from a YouTube channel."""

import logging

from api.video_service import (
    VideoService,
    VideoServiceError,
    UploadsPlaylistNotFoundError,
)

logger = logging.getLogger(__name__)


class VideoDiscoveryError(Exception):
    """Base exception for video discovery errors."""
    pass


class VideoDiscovery:
    """Orchestrates the full video discovery pipeline.

    1. Retrieve the channel's uploads playlist ID.
    2. Paginate through all playlist items.
    3. Collect all unique video IDs preserving upload order.
    4. Return a summary with counts and status.
    """

    def __init__(self, video_service: VideoService | None = None) -> None:
        self._video_service = video_service or VideoService()

    def discover(self, channel_id: str) -> dict:
        """Retrieve all uploaded public video IDs for a channel.

        Args:
            channel_id: The YouTube channel ID (``UC...``).

        Returns:
            Dictionary with keys:
            - ``channel_id``: The requested channel ID.
            - ``video_ids``: List of all video IDs in upload order.
            - ``total_videos``: Total number of videos found.
            - ``total_requests``: Total API requests made.
            - ``success``: ``True`` if completed successfully.

        Raises:
            VideoDiscoveryError: On any API or resolution failure.
        """
        logger.info("Video discovery started for channel: %s", channel_id)

        try:
            playlist_id = self._video_service.get_uploads_playlist_id(channel_id)
        except UploadsPlaylistNotFoundError as exc:
            logger.error("Uploads playlist missing: %s", exc)
            raise VideoDiscoveryError(str(exc)) from exc
        except VideoServiceError as exc:
            logger.error("Video service error (get uploads): %s", exc)
            raise VideoDiscoveryError(str(exc)) from exc

        all_video_ids: list[str] = []
        page_token: str | None = None
        request_count = 0

        logger.info(
            "Starting pagination for playlist: %s (channel: %s)",
            playlist_id,
            channel_id,
        )

        while True:
            try:
                result = self._video_service.get_playlist_items(
                    playlist_id,
                    page_token=page_token,
                )
            except VideoServiceError as exc:
                logger.error(
                    "Video service error at page %d: %s",
                    request_count + 1,
                    exc,
                )
                raise VideoDiscoveryError(str(exc)) from exc

            request_count += 1
            page_video_ids = result["video_ids"]
            all_video_ids.extend(page_video_ids)

            logger.info(
                "Page %d: %d videos (running total: %d)",
                request_count,
                len(page_video_ids),
                len(all_video_ids),
            )

            page_token = result.get("next_page_token")
            if not page_token:
                break

        logger.info(
            "Video discovery complete: %d videos in %d requests",
            len(all_video_ids),
            request_count,
        )

        return {
            "channel_id": channel_id,
            "video_ids": all_video_ids,
            "total_videos": len(all_video_ids),
            "total_requests": request_count,
            "success": True,
        }
