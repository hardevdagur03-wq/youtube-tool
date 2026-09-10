"""Tests for Phase 3 – Fetch All Uploaded Public Videos."""

from unittest.mock import MagicMock, patch

import pytest

from api.video_service import (
    UploadsPlaylistNotFoundError,
    VideoService,
    VideoServiceError,
)
from services.video_discovery import VideoDiscovery, VideoDiscoveryError


# ---------------------------------------------------------------------------
# VideoService – API layer
# ---------------------------------------------------------------------------

class TestVideoServiceGetUploadsPlaylistId:
    """VideoService.get_uploads_playlist_id with mocked YouTubeClient."""

    @patch("api.video_service.YouTubeClient")
    def test_returns_uploads_playlist_id(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "contentDetails": {
                        "relatedPlaylists": {"uploads": "UU_test123"},
                    },
                },
            ],
        }

        svc = VideoService()
        result = svc.get_uploads_playlist_id("UC_channel")
        assert result == "UU_test123"

    @patch("api.video_service.YouTubeClient")
    def test_calls_channels_list_with_correct_args(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_x"}}}],
        }

        svc = VideoService()
        svc.get_uploads_playlist_id("UC_channel")
        mock_service.channels.return_value.list.assert_called_once_with(
            part="contentDetails", id="UC_channel"
        )

    @patch("api.video_service.YouTubeClient")
    def test_channel_not_found_raises_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [],
        }

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="No channel found"):
            svc.get_uploads_playlist_id("UC_ghost")

    @patch("api.video_service.YouTubeClient")
    def test_missing_uploads_playlist_raises_not_found(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"contentDetails": {"relatedPlaylists": {}}}],
        }

        svc = VideoService()
        with pytest.raises(UploadsPlaylistNotFoundError, match="no uploads playlist"):
            svc.get_uploads_playlist_id("UC_empty")


class TestVideoServiceGetPlaylistItems:
    """VideoService.get_playlist_items with mocked YouTubeClient."""

    @patch("api.video_service.YouTubeClient")
    def test_returns_video_ids_from_page(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid1"}}},
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid2"}}},
            ],
            "nextPageToken": "CAUQAA",
        }

        svc = VideoService()
        result = svc.get_playlist_items("UU_playlist")
        assert result["video_ids"] == ["vid1", "vid2"]
        assert result["next_page_token"] == "CAUQAA"
        assert result["page_item_count"] == 2

    @patch("api.video_service.YouTubeClient")
    def test_last_page_no_next_token(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid1"}}},
            ],
        }

        svc = VideoService()
        result = svc.get_playlist_items("UU_playlist", page_token="CAUQAA")
        assert result["video_ids"] == ["vid1"]
        assert result["next_page_token"] is None

    @patch("api.video_service.YouTubeClient")
    def test_skips_non_video_items(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid1"}}},
                {"snippet": {"resourceId": {"kind": "youtube#playlist", "playlistId": "pl1"}}},
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid2"}}},
            ],
        }

        svc = VideoService()
        result = svc.get_playlist_items("UU_playlist")
        assert result["video_ids"] == ["vid1", "vid2"]

    @patch("api.video_service.YouTubeClient")
    def test_skips_items_missing_video_id(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {"snippet": {"resourceId": {"kind": "youtube#video", "videoId": "vid1"}}},
                {"snippet": {"resourceId": {"kind": "youtube#video"}}},
                {},
            ],
        }

        svc = VideoService()
        result = svc.get_playlist_items("UU_playlist")
        assert result["video_ids"] == ["vid1"]

    @patch("api.video_service.YouTubeClient")
    def test_empty_page_returns_empty_list(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [],
        }

        svc = VideoService()
        result = svc.get_playlist_items("UU_playlist")
        assert result["video_ids"] == []
        assert result["next_page_token"] is None

    @patch("api.video_service.YouTubeClient")
    def test_passes_page_token_to_api(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [],
        }

        svc = VideoService()
        svc.get_playlist_items("UU_playlist", page_token="CBQBBQ")
        mock_service.playlistItems.return_value.list.assert_called_once_with(
            part="snippet",
            playlistId="UU_playlist",
            maxResults=50,
            pageToken="CBQBBQ",
        )


# ---------------------------------------------------------------------------
# VideoDiscovery – orchestration layer
# ---------------------------------------------------------------------------

class TestVideoDiscovery:
    """VideoDiscovery.discover with mocked VideoService."""

    def test_small_channel_single_page(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"
        mock_svc.get_playlist_items.return_value = {
            "video_ids": ["vid1", "vid2", "vid3"],
            "next_page_token": None,
            "page_item_count": 3,
        }

        discovery = VideoDiscovery(video_service=mock_svc)
        result = discovery.discover("UC_channel")

        assert result["channel_id"] == "UC_channel"
        assert result["video_ids"] == ["vid1", "vid2", "vid3"]
        assert result["total_videos"] == 3
        assert result["total_requests"] == 1
        assert result["success"] is True

    def test_large_channel_multi_page(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"

        page1 = {"video_ids": ["v1"] * 50, "next_page_token": "tok2", "page_item_count": 50}
        page2 = {"video_ids": ["v2"] * 50, "next_page_token": "tok3", "page_item_count": 50}
        page3 = {"video_ids": ["v3"] * 30, "next_page_token": None, "page_item_count": 30}
        mock_svc.get_playlist_items.side_effect = [page1, page2, page3]

        discovery = VideoDiscovery(video_service=mock_svc)
        result = discovery.discover("UC_channel")

        assert result["total_videos"] == 130
        assert result["total_requests"] == 3
        assert result["success"] is True

    def test_empty_playlist(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_empty"
        mock_svc.get_playlist_items.return_value = {
            "video_ids": [],
            "next_page_token": None,
            "page_item_count": 0,
        }

        discovery = VideoDiscovery(video_service=mock_svc)
        result = discovery.discover("UC_empty_channel")

        assert result["video_ids"] == []
        assert result["total_videos"] == 0
        assert result["total_requests"] == 1
        assert result["success"] is True

    def test_invalid_channel_id(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.side_effect = VideoServiceError(
            "No channel found for ID: UC_ghost"
        )

        discovery = VideoDiscovery(video_service=mock_svc)
        with pytest.raises(VideoDiscoveryError, match="No channel found"):
            discovery.discover("UC_ghost")

    def test_missing_uploads_playlist(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.side_effect = UploadsPlaylistNotFoundError(
            "no uploads playlist"
        )

        discovery = VideoDiscovery(video_service=mock_svc)
        with pytest.raises(VideoDiscoveryError, match="no uploads playlist"):
            discovery.discover("UC_no_uploads")

    def test_quota_exceeded_during_pagination(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"
        mock_svc.get_playlist_items.side_effect = VideoServiceError(
            "API quota exceeded"
        )

        discovery = VideoDiscovery(video_service=mock_svc)
        with pytest.raises(VideoDiscoveryError, match="API quota exceeded"):
            discovery.discover("UC_channel")

    def test_network_failure_during_pagination(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"

        def fail_on_second_call(playlist_id, page_token=None):
            if page_token:
                raise VideoServiceError("Network timeout")
            return {"video_ids": ["v1"], "next_page_token": "tok2", "page_item_count": 1}

        mock_svc.get_playlist_items.side_effect = fail_on_second_call

        discovery = VideoDiscovery(video_service=mock_svc)
        with pytest.raises(VideoDiscoveryError, match="Network timeout"):
            discovery.discover("UC_channel")

    def test_duplicate_prevention_order_preserved(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"

        mock_svc.get_playlist_items.return_value = {
            "video_ids": ["a", "b", "c"],
            "next_page_token": None,
            "page_item_count": 3,
        }

        discovery = VideoDiscovery(video_service=mock_svc)
        result = discovery.discover("UC_channel")
        assert result["video_ids"] == ["a", "b", "c"]

    def test_pagination_completes_all_pages(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_uploads_playlist_id.return_value = "UU_playlist"

        tokens = iter(["tok2", "tok3", "tok4", None])
        call_count = 0

        def paginate(playlist_id, page_token=None):
            nonlocal call_count
            call_count += 1
            next_tok = next(tokens)
            return {
                "video_ids": [f"vid_{call_count}_{i}" for i in range(2)],
                "next_page_token": next_tok,
                "page_item_count": 2,
            }

        mock_svc.get_playlist_items.side_effect = paginate

        discovery = VideoDiscovery(video_service=mock_svc)
        result = discovery.discover("UC_channel")

        assert result["total_videos"] == 8
        assert result["total_requests"] == 4
        assert result["success"] is True


class TestVideoServiceHttpErrors:
    """VideoService error classification for HTTP failures."""

    @patch("api.video_service.YouTubeClient")
    def test_quota_exceeded_during_playlist_id(self, mock_client_cls):
        import googleapiclient.errors as api_errors
        from googleapiclient.http import HttpMock

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 403
        error = api_errors.HttpError(resp, b'"quotaExceeded"', uri="https://youtube.googleapis.com")
        mock_service.channels.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="API quota exceeded"):
            svc.get_uploads_playlist_id("UC_test")

    @patch("api.video_service.YouTubeClient")
    def test_quota_exceeded_during_playlist_items(self, mock_client_cls):
        import googleapiclient.errors as api_errors

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 403
        error = api_errors.HttpError(resp, b'"quotaExceeded"', uri="https://youtube.googleapis.com")
        mock_service.playlistItems.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="API quota exceeded"):
            svc.get_playlist_items("UU_playlist")

    @patch("api.video_service.YouTubeClient")
    def test_forbidden_during_playlist_id(self, mock_client_cls):
        import googleapiclient.errors as api_errors

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 403
        error = api_errors.HttpError(resp, b'"forbidden"', uri="https://youtube.googleapis.com")
        mock_service.channels.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="forbidden"):
            svc.get_uploads_playlist_id("UC_test")

    @patch("api.video_service.YouTubeClient")
    def test_not_found_during_playlist_items(self, mock_client_cls):
        import googleapiclient.errors as api_errors

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 404
        error = api_errors.HttpError(resp, b'"notFound"', uri="https://youtube.googleapis.com")
        mock_service.playlistItems.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="Resource not found"):
            svc.get_playlist_items("UU_bad")
