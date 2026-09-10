"""Async YouTube Data API v3 client using httpx with HTTP/2, connection pooling, keep-alive.

Eliminates httplib2 + googleapiclient overhead entirely.
Provides true async I/O with configurable connection pooling.

Usage:
    client = AsyncYouTubeClient()
    channel = await client.get_channel_by_handle("@test")
    videos = await client.get_videos_batch(["id1", "id2", ...])
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_CONNECTIONS = 10
REQUEST_TIMEOUT = 20.0

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class AsyncYouTubeClientError(Exception):
    pass


class AsyncYouTubeQuotaError(AsyncYouTubeClientError):
    pass


class AsyncYouTubeNotFoundError(AsyncYouTubeClientError):
    pass


class AsyncYouTubeTimeoutError(AsyncYouTubeClientError):
    pass


class AsyncYouTubeClient:
    """Async HTTP/2 client for YouTube Data API v3 with connection pooling."""

    def __init__(
        self,
        api_key: str | None = None,
        max_connections: int = MAX_CONNECTIONS,
        request_timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self._api_key = api_key or settings.youtube_api_key
        self._max_connections = max_connections
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(max_connections)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_connections=self._max_connections,
                max_keepalive_connections=self._max_connections,
                keepalive_expiry=60.0,
            )
            try:
                import h2  # noqa: F401
                http2 = True
            except ImportError:
                http2 = False
            self._client = httpx.AsyncClient(
                http2=http2,
                limits=limits,
                timeout=httpx.Timeout(self._request_timeout, connect=10.0),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "YouTubeExportEngine/3.0",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = dict(params or {})
        params["key"] = self._api_key

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self._semaphore:
                    response = await client.get(
                        f"{YOUTUBE_API_BASE}/{endpoint}",
                        params=params,
                    )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 403:
                    body = response.text
                    if "quotaExceeded" in body or "quota" in body.lower():
                        raise AsyncYouTubeQuotaError(
                            "YouTube API quota exceeded."
                        )
                    raise AsyncYouTubeClientError(
                        f"Forbidden: {response.text[:200]}"
                    )

                if response.status_code == 404:
                    raise AsyncYouTubeNotFoundError(
                        f"Resource not found: {endpoint}"
                    )

                if response.status_code in RETRYABLE_STATUSES:
                    if attempt < MAX_RETRIES:
                        delay = BASE_DELAY * (2 ** (attempt - 1))
                        logger.warning(
                            "YouTube API %d on %s (attempt %d/%d), retrying in %.1fs",
                            response.status_code, endpoint, attempt, MAX_RETRIES, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise AsyncYouTubeClientError(
                        f"HTTP {response.status_code} after {MAX_RETRIES} retries: {response.text[:200]}"
                    )

                raise AsyncYouTubeClientError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Timeout on %s (attempt %d/%d), retrying in %.1fs",
                        endpoint, attempt, MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise AsyncYouTubeTimeoutError(
                    f"Request timed out after {MAX_RETRIES} retries: {endpoint}"
                ) from exc

            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "HTTP error on %s (attempt %d/%d): %s, retrying in %.1fs",
                        endpoint, attempt, MAX_RETRIES, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise AsyncYouTubeClientError(
                    f"HTTP error after {MAX_RETRIES} retries: {exc}"
                ) from exc

        raise AsyncYouTubeClientError(
            f"Request failed after {MAX_RETRIES} retries: {last_error}"
        ) from last_error

    async def get_channel_by_handle(self, handle: str) -> dict[str, Any]:
        clean = handle.lstrip("@")
        data = await self._request("channels", {
            "part": "id,snippet",
            "forHandle": clean,
        })
        items = data.get("items", [])
        if not items:
            raise AsyncYouTubeNotFoundError(f"No channel found for handle: {handle}")
        return items[0]

    async def get_channel_by_id(self, channel_id: str) -> dict[str, Any]:
        data = await self._request("channels", {
            "part": "id,snippet,contentDetails",
            "id": channel_id,
        })
        items = data.get("items", [])
        if not items:
            raise AsyncYouTubeNotFoundError(f"No channel found for ID: {channel_id}")
        return items[0]

    async def get_uploads_playlist_id(self, channel_id: str) -> str:
        data = await self._request("channels", {
            "part": "contentDetails",
            "id": channel_id,
        })
        items = data.get("items", [])
        if not items:
            raise AsyncYouTubeNotFoundError(f"No channel found for ID: {channel_id}")
        uploads = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads:
            raise AsyncYouTubeClientError(
                f"Channel {channel_id} has no uploads playlist."
            )
        return uploads

    async def get_playlist_items(
        self,
        playlist_id: str,
        page_token: str | None = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max_results,
        }
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("playlistItems", params)
        items = data.get("items", [])
        video_ids: list[str] = []
        for item in items:
            rid = item.get("snippet", {}).get("resourceId", {})
            if rid.get("kind") == "youtube#video" and rid.get("videoId"):
                video_ids.append(rid["videoId"])

        return {
            "video_ids": video_ids,
            "next_page_token": data.get("nextPageToken"),
            "page_item_count": len(video_ids),
        }

    async def get_videos_batch(
        self, video_ids: list[str]
    ) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        joined = ",".join(video_ids)
        data = await self._request("videos", {
            "part": "snippet,contentDetails,statistics",
            "id": joined,
            "maxResults": 50,
        })
        return data.get("items", [])
