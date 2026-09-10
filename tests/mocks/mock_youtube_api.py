from __future__ import annotations

from typing import Any


class MockYouTubeClient:
    def __init__(
        self,
        videos: dict[str, dict[str, Any]] | None = None,
        channels: dict[str, dict[str, Any]] | None = None,
    ):
        self._videos: dict[str, dict[str, Any]] = videos or {}
        self._channels: dict[str, dict[str, Any]] = channels or {}
        self._call_history: list[dict[str, Any]] = []
        self._rate_limit_active: bool = False
        self._error_status: int | None = None
        self._search_results: list[dict[str, Any]] = []

    def get_video_metadata(self, video_id: str) -> dict[str, Any]:
        self._call_history.append({"method": "get_video_metadata", "video_id": video_id})

        if self._rate_limit_active:
            raise Exception("YouTube API rate limit exceeded")

        if self._error_status is not None:
            raise Exception(f"YouTube API error: status {self._error_status}")

        if video_id in self._videos:
            return dict(self._videos[video_id])

        raise KeyError(f"Video not found: {video_id}")

    def get_channel_info(self, channel_id: str) -> dict[str, Any]:
        self._call_history.append({"method": "get_channel_info", "channel_id": channel_id})

        if self._rate_limit_active:
            raise Exception("YouTube API rate limit exceeded")

        if self._error_status is not None:
            raise Exception(f"YouTube API error: status {self._error_status}")

        if channel_id in self._channels:
            return dict(self._channels[channel_id])

        raise KeyError(f"Channel not found: {channel_id}")

    def search_videos(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        self._call_history.append({
            "method": "search_videos",
            "query": query,
            "max_results": max_results,
        })

        if self._rate_limit_active:
            raise Exception("YouTube API rate limit exceeded")

        if self._error_status is not None:
            raise Exception(f"YouTube API error: status {self._error_status}")

        return list(self._search_results[:max_results])

    def register_video(self, video_id: str, metadata: dict[str, Any]) -> None:
        self._videos[video_id] = dict(metadata)

    def register_search_results(self, results: list[dict[str, Any]]) -> None:
        self._search_results = list(results)

    def simulate_rate_limit(self) -> None:
        self._rate_limit_active = True

    def simulate_api_error(self, status_code: int = 403) -> None:
        self._error_status = status_code

    def reset(self) -> None:
        self._videos.clear()
        self._channels.clear()
        self._call_history.clear()
        self._rate_limit_active = False
        self._error_status = None
        self._search_results.clear()


class MockYouTubeTranscriptAPI:
    def __init__(self):
        self._transcripts: dict[str, list[dict[str, Any]]] = {}
        self._call_history: list[dict[str, Any]] = []
        self._unavailable: set[str] = set()
        self._disabled: set[str] = set()

    def get_transcript(self, video_id: str, languages: list[str] | None = None) -> list[dict[str, Any]]:
        self._call_history.append({
            "method": "get_transcript",
            "video_id": video_id,
            "languages": languages,
        })

        if video_id in self._disabled:
            raise Exception("Transcripts are disabled for this video")

        if video_id in self._unavailable:
            raise Exception("No transcript available for this video")

        if video_id in self._transcripts:
            return list(self._transcripts[video_id])

        raise KeyError(f"No transcript registered for video: {video_id}")

    def register_transcript(self, video_id: str, transcript: list[dict[str, Any]]) -> None:
        self._transcripts[video_id] = list(transcript)

    def simulate_unavailable(self) -> None:
        self._unavailable.add("*")

    def simulate_unavailable_for(self, video_id: str) -> None:
        self._unavailable.add(video_id)

    def simulate_disabled(self) -> None:
        self._disabled.add("*")

    def simulate_disabled_for(self, video_id: str) -> None:
        self._disabled.add(video_id)

    def reset(self) -> None:
        self._transcripts.clear()
        self._call_history.clear()
        self._unavailable.clear()
        self._disabled.clear()
