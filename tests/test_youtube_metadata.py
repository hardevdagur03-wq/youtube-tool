"""Tests for Phase 3 — YouTube Metadata Engine.

Tests the utility modules (number_formatter, date_formatter, thumbnail, cache)
and the YouTubeMetadataService.
"""

from datetime import datetime, timezone

import pytest

from utils.number_formatter import format_count
from utils.date_formatter import format_date
from utils.thumbnail import extract_thumbnails, best_thumbnail
from utils.cache import TTLCache
from models.video_metadata import VideoMetadataResponse


# ===========================================================================
# Number Formatter Tests
# ===========================================================================


class TestFormatCount:
    def test_zero(self):
        assert format_count(0) == "0"

    def test_under_thousand(self):
        assert format_count(999) == "999"
        assert format_count(1) == "1"
        assert format_count(500) == "500"

    def test_thousands(self):
        assert format_count(1000) == "1.0K"
        assert format_count(1523) == "1.5K"
        assert format_count(9999) == "10.0K"
        assert format_count(10500) == "10K"
        assert format_count(999999) == "1000K"

    def test_millions(self):
        assert format_count(1000000) == "1.0M"
        assert format_count(1580000) == "1.6M"
        assert format_count(25000000) == "25M"
        assert format_count(999999999) == "1000M"

    def test_billions(self):
        assert format_count(1000000000) == "1.0B"
        assert format_count(1500000000) == "1.5B"

    def test_negative_coerces_to_zero(self):
        assert format_count(-100) == "0"

    def test_string_input(self):
        assert format_count("1523") == "1.5K"
        assert format_count("abc") == "0"

    def test_none_input(self):
        assert format_count(None) == "0"  # type: ignore


# ===========================================================================
# Date Formatter Tests
# ===========================================================================


class TestFormatDate:
    def test_valid_iso(self):
        result = format_date("2024-03-18T12:30:11Z")
        assert result["iso"] == "2024-03-18T12:30:11Z"
        assert result["localized"] == "March 18, 2024"
        assert result["relative"] is not None

    def test_none_input(self):
        result = format_date(None)
        assert result["iso"] is None
        assert result["localized"] is None
        assert result["relative"] is None

    def test_empty_string(self):
        result = format_date("")
        assert result["iso"] is None

    def test_invalid_string(self):
        result = format_date("not-a-date")
        assert result["iso"] == "not-a-date"
        assert result["localized"] is None

    def test_recent_date_returns_just_now(self):
        now = datetime.now(timezone.utc)
        iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert result["relative"] == "just now"

    def test_minutes_ago(self):
        from datetime import timedelta
        past = (datetime.now(timezone.utc) - timedelta(minutes=5))
        iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert "minute" in (result["relative"] or "")

    def test_hours_ago(self):
        from datetime import timedelta
        past = (datetime.now(timezone.utc) - timedelta(hours=3))
        iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert "hour" in (result["relative"] or "")

    def test_days_ago(self):
        from datetime import timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=10))
        iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert "day" in (result["relative"] or "")

    def test_months_ago(self):
        from datetime import timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=100))
        iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert "month" in (result["relative"] or "")

    def test_years_ago(self):
        from datetime import timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=800))
        iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_date(iso)
        assert "year" in (result["relative"] or "")


# ===========================================================================
# Thumbnail Tests
# ===========================================================================


class TestExtractThumbnails:
    def test_all_thumbnails(self):
        data = {
            "default": {"url": "https://img.youtube.com/vi/abc/default.jpg"},
            "medium": {"url": "https://img.youtube.com/vi/abc/mqdefault.jpg"},
            "high": {"url": "https://img.youtube.com/vi/abc/hqdefault.jpg"},
            "standard": {"url": "https://img.youtube.com/vi/abc/sddefault.jpg"},
            "maxres": {"url": "https://img.youtube.com/vi/abc/maxresdefault.jpg"},
        }
        result = extract_thumbnails(data)
        assert result["default"] == "https://img.youtube.com/vi/abc/default.jpg"
        assert result["maxres"] == "https://img.youtube.com/vi/abc/maxresdefault.jpg"

    def test_partial_thumbnails(self):
        data = {
            "default": {"url": "https://img.youtube.com/vi/abc/default.jpg"},
            "high": {"url": "https://img.youtube.com/vi/abc/hqdefault.jpg"},
        }
        result = extract_thumbnails(data)
        assert result["default"] is not None
        assert result["medium"] is None
        assert result["high"] is not None
        assert result["standard"] is None
        assert result["maxres"] is None

    def test_empty_data(self):
        result = extract_thumbnails({})
        assert all(v is None for v in result.values())

    def test_none_data(self):
        result = extract_thumbnails(None)
        assert all(v is None for v in result.values())

    def test_non_dict_data(self):
        result = extract_thumbnails("invalid")
        assert all(v is None for v in result.values())


class TestBestThumbnail:
    def test_returns_maxres_when_available(self):
        thumbs = {
            "default": "url_default",
            "medium": "url_medium",
            "high": "url_high",
            "standard": "url_standard",
            "maxres": "url_maxres",
        }
        assert best_thumbnail(thumbs) == "url_maxres"

    def test_falls_back_to_lower(self):
        thumbs = {"default": "url_default", "high": "url_high"}
        assert best_thumbnail(thumbs) == "url_high"

    def test_returns_none_when_empty(self):
        assert best_thumbnail({}) is None
        assert best_thumbnail({"default": None}) is None


# ===========================================================================
# Cache Tests
# ===========================================================================


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_missing_key(self):
        cache = TTLCache[str]()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = TTLCache[str]()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self):
        cache = TTLCache[str]()
        cache.set("a", "1")
        cache.set("b", "2")
        cache.clear()
        assert cache.size == 0

    def test_expiry(self):
        cache = TTLCache[str](ttl_seconds=0)
        cache.set("key", "value")
        import time
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_size_tracking(self):
        cache = TTLCache[str]()
        assert cache.size == 0
        cache.set("a", "1")
        assert cache.size == 1
        cache.set("b", "2")
        assert cache.size == 2
        cache.delete("a")
        assert cache.size == 1


# ===========================================================================
# YouTubeMetadataService Tests (mocked)
# ===========================================================================


class TestYouTubeMetadataService:
    """Test YouTubeMetadataService with a mocked VideoService."""

    def _make_mock_item(self, video_id: str = "dQw4w9WgXcQ", **overrides) -> dict:
        """Build a mock YouTube API response item."""
        item = {
            "snippet": {
                "title": "Test Video",
                "description": "This is a test video #test @channel",
                "channelId": "UC_test123",
                "channelTitle": "Test Channel",
                "publishedAt": "2024-03-18T12:30:11Z",
                "thumbnails": {
                    "default": {"url": f"https://img.youtube.com/vi/{video_id}/default.jpg"},
                    "medium": {"url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"},
                    "high": {"url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"},
                },
                "tags": ["tag1", "tag2"],
                "categoryId": "22",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
                "liveBroadcastContent": "none",
            },
            "contentDetails": {
                "duration": "PT12M35S",
                "license": "youtube",
                "caption": "true",
                "embed": {"embeddable": True},
            },
            "statistics": {
                "viewCount": "1523",
                "likeCount": "45000",
                "commentCount": "230",
            },
            "status": {
                "privacyStatus": "public",
            },
        }
        # Apply overrides
        self._deep_merge(item, overrides)
        return item

    def _deep_merge(self, base: dict, overrides: dict) -> None:
        """Recursively merge overrides into base dict."""
        for key, value in overrides.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def test_valid_video_returns_metadata(self, monkeypatch):
        from services.youtube_metadata_service import YouTubeMetadataService

        mock_item = self._make_mock_item()
        svc = YouTubeMetadataService()

        def mock_get_videos_batch(video_ids):
            return [mock_item]

        svc._video_service.get_videos_batch = mock_get_videos_batch

        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result.success is True
        assert result.video is not None
        assert result.video.video_id == "dQw4w9WgXcQ"
        assert result.video.title == "Test Video"
        assert result.video.statistics.views == 1523
        assert result.video.statistics.views_formatted == "1.5K"
        assert result.video.statistics.likes == 45000
        assert result.video.statistics.likes_formatted == "45K"
        assert result.video.statistics.comments_formatted == "230"
        assert result.video.duration.compact == "12:35"
        assert result.video.duration.seconds == 755
        assert result.video.channel.name == "Test Channel"
        assert result.video.channel.id == "UC_test123"
        assert result.video.privacy == "public"
        assert len(result.video.tags) == 2

    def test_video_not_found_returns_error(self):
        from services.youtube_metadata_service import YouTubeMetadataService

        svc = YouTubeMetadataService()

        def mock_get_videos_batch(video_ids):
            return []

        svc._video_service.get_videos_batch = mock_get_videos_batch

        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_invalid_video_id(self):
        from services.youtube_metadata_service import YouTubeMetadataService

        svc = YouTubeMetadataService()
        result = svc.get_metadata("short")
        assert result.success is False
        assert "invalid" in (result.error or "").lower()

        result = svc.get_metadata("")
        assert result.success is False

    def test_cache_hit(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        from utils.cache import TTLCache

        call_count = [0]
        svc = YouTubeMetadataService(cache=TTLCache(ttl_seconds=60))

        def mock_get_videos_batch(video_ids):
            call_count[0] += 1
            return [self._make_mock_item()]

        svc._video_service.get_videos_batch = mock_get_videos_batch

        # First call — hits API
        r1 = svc.get_metadata("dQw4w9WgXcQ")
        assert r1.success is True
        assert call_count[0] == 1

        # Second call — should hit cache
        r2 = svc.get_metadata("dQw4w9WgXcQ")
        assert r2.success is True
        assert call_count[0] == 1  # Not incremented

    def test_description_parsing(self):
        from services.youtube_metadata_service import YouTubeMetadataService

        svc = YouTubeMetadataService()

        def mock_get_videos_batch(video_ids):
            return [self._make_mock_item(**{"snippet": {"description": "#hello world https://example.com @user"}})]

        svc._video_service.get_videos_batch = mock_get_videos_batch

        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result.success is True
        desc = result.video.description
        assert desc.full is not None
        assert "#hello" in desc.hashtags
        assert "https://example.com" in desc.urls
        assert "@user" in desc.mentions

    def test_api_error_returns_friendly_message(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        from api.video_service import VideoServiceError

        svc = YouTubeMetadataService()

        def mock_get_videos_batch(video_ids):
            raise VideoServiceError("API quota exceeded")

        svc._video_service.get_videos_batch = mock_get_videos_batch

        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result.success is False
        assert "quota" in (result.error or "").lower()

    def test_model_serialization(self):
        result = VideoMetadataResponse(
            success=True,
            error=None,
        )
        dumped = result.model_dump()
        assert dumped["success"] is True
        assert dumped["error"] is None
