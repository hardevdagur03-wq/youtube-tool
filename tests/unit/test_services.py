from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

import pytest


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
            resolver.resolve("UCtest12345678901234567890")

    def test_resolve_url(self):
        from services.channel_resolver import ChannelResolver
        resolver = ChannelResolver()
        result = resolver.resolve("https://youtube.com/@testchannel")
        assert result is not None

    def test_resolve_invalid(self):
        from services.channel_resolver import ChannelResolver
        resolver = ChannelResolver()
        with pytest.raises(Exception):
            resolver.resolve("")


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

    def test_discover_empty(self):
        from services.video_discovery import VideoDiscovery
        vd = VideoDiscovery()
        with pytest.raises(Exception):
            vd.discover("UCnonexistent")


class TestVideoMetadataService:
    def test_get_metadata(self):
        from services.video_metadata import VideoMetadataService
        svc = VideoMetadataService()
        result = svc.fetch_metadata(["test123"])
        assert result is not None

    def test_get_metadata_invalid_id(self):
        from services.video_metadata import VideoMetadataService
        svc = VideoMetadataService()
        result = svc.fetch_metadata([])
        assert result["total_input"] == 0

    def test_format_metadata(self):
        from services.video_metadata import _parse_video_item
        raw = {"id": "test", "snippet": {"title": "Test", "channelTitle": "C"}, "statistics": {"viewCount": "100"}, "contentDetails": {"duration": "PT5M"}}
        formatted = _parse_video_item(raw)
        assert formatted["title"] == "Test"
        assert formatted["views"] == 100


class TestYouTubeMetadataService:
    def test_get_channel_metadata(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        svc = YouTubeMetadataService()
        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result is not None

    def test_get_video_details(self):
        from services.youtube_metadata_service import YouTubeMetadataService
        svc = YouTubeMetadataService()
        result = svc.get_metadata("dQw4w9WgXcQ")
        assert result is not None

    def test_parse_duration(self):
        from utils.duration import parse_duration_to_seconds
        assert parse_duration_to_seconds("PT1H30M15S") == 5415
        assert parse_duration_to_seconds("PT10M") == 600
        assert parse_duration_to_seconds("PT0S") == 0


class TestTranscriptService:
    def test_get_transcript(self):
        from services.transcript_service import TranscriptService
        svc = TranscriptService()
        result = svc.get_transcript("dQw4w9WgXcQ")
        assert result is not None

    def test_get_transcript_not_found(self):
        from services.transcript_service import TranscriptService
        svc = TranscriptService()
        result = svc.get_transcript("nonexistent")
        assert result is not None

    def test_get_transcript_languages(self):
        from services.transcript_service import TranscriptService
        svc = TranscriptService()
        result = svc.get_transcript("dQw4w9WgXcQ", language="en")
        assert result is not None


class TestTranscriptProcessor:
    def test_process(self):
        from services.transcript_processor import TranscriptProcessor
        processor = TranscriptProcessor()
        result = processor.process(
            [{"text": "hello world", "start": 0.0, "duration": 1.0}],
            video_id="dQw4w9WgXcQ",
        )
        assert result is not None

    def test_process_empty(self):
        from services.transcript_processor import TranscriptProcessor
        processor = TranscriptProcessor()
        result = processor.process([], video_id="dQw4w9WgXcQ")
        assert result is not None


class TestContentAnalysisService:
    def test_analyze(self):
        from services.content_analysis_service import ContentAnalysisService
        svc = ContentAnalysisService()
        result = svc.analyze(
            "Python is a programming language used for data science",
            video_id="dQw4w9WgXcQ",
        )
        assert result is not None

    def test_analyze_empty_transcript(self):
        from services.content_analysis_service import ContentAnalysisService
        svc = ContentAnalysisService()
        result = svc.analyze("", video_id="dQw4w9WgXcQ")
        assert result is not None


class TestDataTransformer:
    def test_transform_video_data(self):
        from services.data_transformer import DataTransformer
        raw = [{"video_id": "v1", "title": "Test", "views": 100, "likes": 10, "duration": "PT5M"}]
        result = DataTransformer.transform(raw)
        assert result is not None
        assert result["total_input"] == 1

    def test_transform_channel_data(self):
        from services.data_transformer import DataTransformer
        record = {"video_id": "v1", "title": "Test", "duration": "PT5M"}
        result = DataTransformer.transform([record])
        assert result is not None

    def test_transform_empty(self):
        from services.data_transformer import DataTransformer
        result = DataTransformer.transform([])
        assert result is not None


class TestCSVExporter:
    def test_export_videos(self):
        from services.exporter import CSVExporter
        exporter = CSVExporter(output_dir=Path(gettempdir()))
        videos = [{"video_id": "v1", "title": "Test", "duration": "PT5M", "video_type": "short"}]
        result = exporter.export(videos)
        assert result is not None

    def test_export_empty(self):
        from services.exporter import CSVExporter
        exporter = CSVExporter(output_dir=Path(gettempdir()))
        result = exporter.export([])
        assert result is not None
        assert result["exported"] == 0


class TestYouTubeURLParser:
    def test_parse_video_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"

    def test_parse_channel_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://www.youtube.com/@testchannel")
        assert result is not None

    def test_parse_invalid(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("not a url")
        assert result.error is not None

    def test_parse_short_url(self):
        from services.youtube_url_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        result = parser.parse("https://youtu.be/dQw4w9WgXcQ")
        assert result.video_id == "dQw4w9WgXcQ"


class TestURLValidator:
    def test_valid_handle(self):
        from services.url_validator import URLValidator
        r = URLValidator.validate("@test")
        assert r["valid"] is True
        assert r["input_type"] == "handle"

    def test_valid_channel_id(self):
        from services.url_validator import URLValidator
        r = URLValidator.validate("UC" + "a" * 22)
        assert r["valid"] is True

    def test_valid_url(self):
        from services.url_validator import URLValidator
        r = URLValidator.validate("https://youtube.com/@test")
        assert r["valid"] is True

    def test_empty_input(self):
        from services.url_validator import URLValidator
        r = URLValidator.validate("")
        assert r["valid"] is False

    def test_video_id_validation(self):
        from services.url_validator import URLValidator
        assert URLValidator.validate_video_id("dQw4w9WgXcQ") is True
        assert URLValidator.validate_video_id("") is False

    def test_sanitize_url(self):
        from services.url_validator import URLValidator
        sanitized = URLValidator.sanitize_url("<script>alert('xss')</script>")
        assert "<script>" not in sanitized
