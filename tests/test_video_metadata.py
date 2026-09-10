"""Tests for Phase 4 – Fetch Video Metadata."""

from unittest.mock import MagicMock, patch

import googleapiclient.errors as api_errors
import pytest

from api.video_service import VideoService, VideoServiceError
from services.video_metadata import VideoMetadataService, VideoMetadataError


# ---------------------------------------------------------------------------
# VideoService.get_videos_batch – API layer
# ---------------------------------------------------------------------------

class TestVideoServiceGetVideosBatch:
    """VideoService.get_videos_batch with mocked YouTubeClient."""

    @patch("api.video_service.YouTubeClient")
    def test_returns_items_for_valid_ids(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "vid1",
                    "snippet": {"title": "First", "publishedAt": "2025-01-10T00:00:00Z"},
                    "contentDetails": {"duration": "PT10M"},
                    "statistics": {"viewCount": "100", "likeCount": "10"},
                },
            ],
        }

        svc = VideoService()
        result = svc.get_videos_batch(["vid1"])
        assert len(result) == 1
        assert result[0]["id"] == "vid1"

    @patch("api.video_service.YouTubeClient")
    def test_correct_api_call(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.videos.return_value.list.return_value.execute.return_value = {
            "items": [],
        }

        svc = VideoService()
        svc.get_videos_batch(["v1", "v2"])
        mock_service.videos.return_value.list.assert_called_once_with(
            part="snippet,contentDetails,statistics",
            id="v1,v2",
        )

    @patch("api.video_service.YouTubeClient")
    def test_empty_input_returns_empty_list(self, mock_client_cls):
        svc = VideoService()
        result = svc.get_videos_batch([])
        assert result == []

    @patch("api.video_service.YouTubeClient")
    def test_deleted_videos_omitted_from_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {"id": "vid1", "snippet": {}, "contentDetails": {}, "statistics": {}},
            ],
        }

        svc = VideoService()
        result = svc.get_videos_batch(["vid1", "vid_deleted"])
        assert len(result) == 1
        assert result[0]["id"] == "vid1"

    @patch("api.video_service.YouTubeClient")
    def test_quota_exceeded(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 403
        error = api_errors.HttpError(resp, b'"quotaExceeded"')
        mock_service.videos.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="API quota exceeded"):
            svc.get_videos_batch(["vid1"])

    @patch("api.video_service.YouTubeClient")
    def test_http_400(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status = 400
        error = api_errors.HttpError(resp, b"bad request")
        mock_service.videos.return_value.list.return_value.execute.side_effect = error

        svc = VideoService()
        with pytest.raises(VideoServiceError, match="Bad request"):
            svc.get_videos_batch(["bad_id"])


# ---------------------------------------------------------------------------
# VideoMetadataService – orchestration layer
# ---------------------------------------------------------------------------

class TestVideoMetadataService:
    """VideoMetadataService.fetch_metadata with mocked VideoService."""

    def _make_fake_item(self, vid: str, **overrides) -> dict:
        item = {
            "id": vid,
            "snippet": {"title": f"Video {vid}", "publishedAt": "2025-01-10T00:00:00Z"},
            "contentDetails": {"duration": "PT10M"},
            "statistics": {"viewCount": "1000", "likeCount": "50"},
        }
        item.update(overrides)
        return item

    def test_single_video(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [self._make_fake_item("v1")]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1"])

        assert result["total_input"] == 1
        assert result["total_retrieved"] == 1
        assert result["total_requests"] == 1
        assert len(result["videos"]) == 1
        assert result["videos"][0]["video_id"] == "v1"
        assert result["videos"][0]["title"] == "Video v1"
        assert result["videos"][0]["views"] == 1000
        assert result["videos"][0]["likes"] == 50
        assert result["videos"][0]["duration"] == "PT10M"

    def test_multiple_videos_batched(self):
        mock_svc = MagicMock(spec=VideoService)
        batch1 = [self._make_fake_item(f"v{i}") for i in range(50)]
        batch2 = [self._make_fake_item(f"v{i}") for i in range(50, 75)]
        mock_svc.get_videos_batch.side_effect = [batch1, batch2]

        all_ids = [f"v{i}" for i in range(75)]
        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(all_ids)

        assert result["total_input"] == 75
        assert result["total_retrieved"] == 75
        assert result["total_requests"] == 2
        assert mock_svc.get_videos_batch.call_count == 2

    def test_empty_input(self):
        mds = VideoMetadataService()
        result = mds.fetch_metadata([])

        assert result["videos"] == []
        assert result["total_input"] == 0
        assert result["total_retrieved"] == 0
        assert result["total_requests"] == 0
        assert result["success"] is True

    def test_duplicates_deduplicated(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [self._make_fake_item("v1")]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1", "v1", "v1"])

        assert result["total_input"] == 1
        assert result["deduplicated"] == 2
        assert result["total_retrieved"] == 1
        assert mock_svc.get_videos_batch.call_count == 1

    def test_invalid_ids_skipped(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [self._make_fake_item("v1")]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1", "bad_id"])

        assert result["total_input"] == 2
        assert result["total_retrieved"] == 1
        assert result["videos"][0]["video_id"] == "v1"

    def test_order_preserved(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [
            self._make_fake_item("z"),
            self._make_fake_item("a"),
            self._make_fake_item("m"),
        ]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["z", "a", "m"])

        assert [v["video_id"] for v in result["videos"]] == ["z", "a", "m"]

    def test_missing_statistics_defaults_to_zero(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [
            {
                "id": "v1",
                "snippet": {"title": "No Stats", "publishedAt": "2025-01-10T00:00:00Z"},
                "contentDetails": {"duration": "PT5M"},
            },
        ]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1"])

        assert result["videos"][0]["views"] == 0
        assert result["videos"][0]["likes"] == 0

    def test_missing_likes_only(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [
            {
                "id": "v1",
                "snippet": {"title": "Likes Hidden", "publishedAt": "2025-01-10T00:00:00Z"},
                "contentDetails": {"duration": "PT5M"},
                "statistics": {"viewCount": "500"},
            },
        ]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1"])

        assert result["videos"][0]["views"] == 500
        assert result["videos"][0]["likes"] == 0

    def test_quota_exceeded_raises_metadata_error(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.side_effect = VideoServiceError("API quota exceeded")

        mds = VideoMetadataService(video_service=mock_svc)
        with pytest.raises(VideoMetadataError, match="API quota exceeded"):
            mds.fetch_metadata(["v1", "v2"])

    def test_network_failure_during_batch(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.side_effect = [
            [self._make_fake_item("v1")],
            VideoServiceError("Network timeout"),
        ]

        mds = VideoMetadataService(video_service=mock_svc)
        with pytest.raises(VideoMetadataError, match="Network timeout"):
            mds.fetch_metadata([f"v{i}" for i in range(60)])

    def test_stats_are_integers(self):
        mock_svc = MagicMock(spec=VideoService)
        mock_svc.get_videos_batch.return_value = [
            {
                "id": "v1",
                "snippet": {"title": "T", "publishedAt": "2025-01-10T00:00:00Z"},
                "contentDetails": {"duration": "PT1M"},
                "statistics": {"viewCount": "999999999", "likeCount": "88888888"},
            },
        ]

        mds = VideoMetadataService(video_service=mock_svc)
        result = mds.fetch_metadata(["v1"])

        assert isinstance(result["videos"][0]["views"], int)
        assert isinstance(result["videos"][0]["likes"], int)
        assert result["videos"][0]["views"] == 999999999
