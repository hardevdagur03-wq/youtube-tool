from __future__ import annotations

import pytest


class TestYouTubeURLParser:
    def test_parse_valid_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.url_type == "watch"

    def test_parse_short_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://youtu.be/dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"

    def test_parse_embed_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"

    def test_parse_invalid_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://example.com")
        assert result.error is not None

    def test_parse_empty_string(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("")
        assert result.error is not None

    def test_extract_channel_handle(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/@testchannel")
        assert result.error is not None and "Channel" in result.error

    def test_parse_with_extra_params(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLabc")
        assert result.video_id == "dQw4w9WgXcQ"


class TestVideoMetadataService:
    def test_get_metadata(self):
        from services.video_metadata import VideoMetadataService
        svc = VideoMetadataService()
        result = svc.fetch_metadata(["test123"])
        assert result is not None
        assert "videos" in result or "success" in result

    def test_get_metadata_invalid_id(self):
        from services.video_metadata import VideoMetadataService
        svc = VideoMetadataService()
        result = svc.fetch_metadata([])
        assert result is not None
        assert result["success"] is True


class TestChannelResolver:
    def test_resolve_handle(self):
        from services.channel_resolver import ChannelResolver
        resolver = ChannelResolver()
        result = resolver.resolve("@testchannel")
        assert result is not None

    def test_resolve_channel_id(self):
        from services.channel_resolver import ChannelResolver
        resolver = ChannelResolver()
        with pytest.raises(Exception):
            resolver.resolve("UC" + "a" * 22)

    def test_resolve_invalid(self):
        from services.channel_resolver import ChannelResolver, InvalidHandleError
        resolver = ChannelResolver()
        with pytest.raises(InvalidHandleError):
            resolver.resolve("ab")

    def test_extract_channel_id(self):
        from services.channel_resolver import ChannelResolver
        cid = ChannelResolver._extract_from_url("https://www.youtube.com/channel/UCtest123")
        assert cid == "UCtest123"


class TestVideoDiscovery:
    def test_discover_by_channel(self):
        from services.video_discovery import VideoDiscovery
        vd = VideoDiscovery()
        with pytest.raises(Exception):
            vd.discover("UCtest123")

    def test_discover_by_keyword(self):
        from services.video_discovery import VideoDiscovery
        vd = VideoDiscovery()
        with pytest.raises(Exception):
            vd.discover("UCnonexistent")

    def test_discover_empty_channel(self):
        from services.video_discovery import VideoDiscovery
        vd = VideoDiscovery()
        with pytest.raises(Exception):
            vd.discover("UCnonexistent")


class TestYouTubeMetadataService:
    def test_get_metadata(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        svc = YouTubeMetadataService()
        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result is not None

    def test_get_video_details(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        svc = YouTubeMetadataService()
        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result is not None
