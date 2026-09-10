"""Tests for Phase 5 – Data Transformation."""

import pytest

from utils.duration import format_duration, parse_duration_to_seconds
from utils.helper import classify_video_type, generate_video_url
from services.data_transformer import DataTransformer, _transform_record


# ---------------------------------------------------------------------------
# utils.duration – ISO 8601 parsing
# ---------------------------------------------------------------------------

class TestParseDurationToSeconds:
    """parse_duration_to_seconds edge cases."""

    @pytest.mark.parametrize(
        ("iso", "expected"),
        [
            ("PT30S", 30),
            ("PT1M", 60),
            ("PT1M1S", 61),
            ("PT12M35S", 755),
            ("PT1H", 3600),
            ("PT1H30M15S", 5415),
            ("PT1H0M0S", 3600),
            ("PT0H0M0S", 0),
            ("PT0S", 0),
            ("PT59S", 59),
            ("PT60S", 60),
            ("PT61S", 61),
            ("PT2H", 7200),
            ("PT2H30M", 9000),
            ("PT1M30S", 90),
        ],
    )
    def test_valid_durations(self, iso, expected):
        assert parse_duration_to_seconds(iso) == expected

    @pytest.mark.parametrize(
        "invalid",
        [
            None,
            "",
            "  ",
            "invalid",
            "P12M35S",
            "T12M35S",
            "PT",
            "PTX",
            123,
            12.5,
            [],
        ],
    )
    def test_invalid_durations_return_none(self, invalid):
        assert parse_duration_to_seconds(invalid) is None


class TestFormatDuration:
    """format_duration edge cases."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0, "0:00"),
            (30, "0:30"),
            (59, "0:59"),
            (60, "1:00"),
            (61, "1:01"),
            (755, "12:35"),
            (3600, "1:00:00"),
            (3661, "1:01:01"),
            (5415, "1:30:15"),
            (7200, "2:00:00"),
            (86399, "23:59:59"),
        ],
    )
    def test_positive_values(self, seconds, expected):
        assert format_duration(seconds) == expected

    @pytest.mark.parametrize("invalid", [None, "abc", 1.5, [], {}])
    def test_invalid_input_returns_none(self, invalid):
        assert format_duration(invalid) is None

    def test_negative_coerces_to_zero(self):
        assert format_duration(-1) == "0:00"
        assert format_duration(-3600) == "0:00"


# ---------------------------------------------------------------------------
# utils.helper – URL generation & classification
# ---------------------------------------------------------------------------

class TestGenerateVideoUrl:
    def test_valid_id(self):
        assert generate_video_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @pytest.mark.parametrize("bad", [None, "", 123, []])
    def test_invalid_input_returns_none(self, bad):
        assert generate_video_url(bad) is None


class TestClassifyVideoType:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0, "Short"),
            (30, "Short"),
            (60, "Short"),
            (61, "Video"),
            (120, "Video"),
            (3600, "Video"),
            (None, "Video"),
        ],
    )
    def test_classification(self, seconds, expected):
        assert classify_video_type(seconds) == expected


# ---------------------------------------------------------------------------
# services.data_transformer – record transformation
# ---------------------------------------------------------------------------

RAW_RECORD = {
    "video_id": "dQw4w9WgXcQ",
    "title": "Test Video",
    "upload_date": "2025-01-12T10:20:00Z",
    "views": 1000,
    "likes": 50,
    "duration": "PT12M35S",
}


class TestTransformRecord:
    """_transform_record single-record logic."""

    def test_full_transform(self):
        result = _transform_record(RAW_RECORD)
        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["title"] == "Test Video"
        assert result["upload_date"] == "2025-01-12T10:20:00Z"
        assert result["views"] == 1000
        assert result["likes"] == 50
        assert result["duration_iso"] == "PT12M35S"
        assert result["duration"] == "12:35"
        assert result["duration_seconds"] == 755
        assert result["video_type"] == "Video"
        assert result["video_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_short_video_detection(self):
        record = {**RAW_RECORD, "duration": "PT30S"}
        result = _transform_record(record)
        assert result["duration"] == "0:30"
        assert result["duration_seconds"] == 30
        assert result["video_type"] == "Short"

    def test_exactly_60_seconds_is_short(self):
        record = {**RAW_RECORD, "duration": "PT60S"}
        result = _transform_record(record)
        assert result["duration_seconds"] == 60
        assert result["video_type"] == "Short"

    def test_null_duration(self):
        record = {**RAW_RECORD, "duration": None}
        result = _transform_record(record)
        assert result["duration_iso"] is None
        assert result["duration"] is None
        assert result["duration_seconds"] is None
        assert result["video_type"] == "Video"

    def test_invalid_duration_string(self):
        record = {**RAW_RECORD, "duration": "bad"}
        result = _transform_record(record)
        assert result["duration_iso"] == "bad"
        assert result["duration"] is None
        assert result["duration_seconds"] is None
        assert result["video_type"] == "Video"

    def test_missing_video_id_skips_record(self):
        result = _transform_record({"title": "No ID"})
        assert result is None

    def test_empty_video_id_skips_record(self):
        result = _transform_record({**RAW_RECORD, "video_id": ""})
        assert result is None

    def test_missing_title_handled_gracefully(self):
        result = _transform_record({**RAW_RECORD, "title": None})
        assert result["title"] is None
        assert result["video_id"] == "dQw4w9WgXcQ"

    def test_zero_views_likes(self):
        record = {**RAW_RECORD, "views": 0, "likes": 0}
        result = _transform_record(record)
        assert result["views"] == 0
        assert result["likes"] == 0

    def test_hour_duration_format(self):
        record = {**RAW_RECORD, "duration": "PT1H30M15S"}
        result = _transform_record(record)
        assert result["duration"] == "1:30:15"
        assert result["duration_seconds"] == 5415
        assert result["video_type"] == "Video"


# ---------------------------------------------------------------------------
# DataTransformer – batch orchestration
# ---------------------------------------------------------------------------

class TestDataTransformer:
    """DataTransformer.transform batch processing."""

    def test_empty_input(self):
        result = DataTransformer.transform([])
        assert result["videos"] == []
        assert result["total_input"] == 0
        assert result["transformed"] == 0
        assert result["skipped"] == 0
        assert result["success"] is True

    def test_single_record(self):
        result = DataTransformer.transform([RAW_RECORD])
        assert result["total_input"] == 1
        assert result["transformed"] == 1
        assert result["skipped"] == 0
        assert len(result["videos"]) == 1

    def test_multiple_records(self):
        records = [
            {**RAW_RECORD, "video_id": "v1", "duration": "PT10S"},
            {**RAW_RECORD, "video_id": "v2", "duration": "PT5M"},
            {**RAW_RECORD, "video_id": "v3", "duration": "PT1H"},
        ]
        result = DataTransformer.transform(records)
        assert result["total_input"] == 3
        assert result["transformed"] == 3
        assert result["videos"][0]["video_type"] == "Short"
        assert result["videos"][1]["video_type"] == "Video"
        assert result["videos"][2]["video_type"] == "Video"

    def test_mixed_valid_and_invalid_records(self):
        records = [
            RAW_RECORD,
            {"title": "no id"},
            {**RAW_RECORD, "video_id": "v2"},
        ]
        result = DataTransformer.transform(records)
        assert result["total_input"] == 3
        assert result["transformed"] == 2
        assert result["skipped"] == 1

    def test_large_batch(self):
        records = [{**RAW_RECORD, "video_id": f"v{i}"} for i in range(1000)]
        result = DataTransformer.transform(records)
        assert result["transformed"] == 1000
        assert result["skipped"] == 0

    def test_all_skipped_records(self):
        records = [
            {"title": "no id 1"},
            {"title": "no id 2"},
        ]
        result = DataTransformer.transform(records)
        assert result["transformed"] == 0
        assert result["skipped"] == 2
        assert result["videos"] == []

    def test_url_generated_for_all(self):
        records = [
            {**RAW_RECORD, "video_id": f"v{i}"} for i in range(5)
        ]
        result = DataTransformer.transform(records)
        for v in result["videos"]:
            assert v["video_url"].startswith("https://www.youtube.com/watch?v=")
            assert v["video_id"] in v["video_url"]
