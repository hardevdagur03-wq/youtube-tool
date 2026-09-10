"""Tests for Phase 6 – Export to CSV."""

import csv
import os
import tempfile
from pathlib import Path

import pytest

from services.exporter import CSVExporter, CSVExporterError

TRANSFORMED_RECORD = {
    "video_id": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "upload_date": "2009-10-25T06:57:33Z",
    "views": 1500000000,
    "likes": 45000000,
    "duration": "3:32",
    "video_type": "Video",
}


@pytest.fixture
def tmp_output():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# CSVExporter
# ---------------------------------------------------------------------------

class TestCSVExporter:
    """CSVExporter.export with temporary output directories."""

    def test_single_record(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export([TRANSFORMED_RECORD], filename="test.csv")

        assert result["total_input"] == 1
        assert result["exported"] == 1
        assert result["skipped"] == 0
        assert result["success"] is True
        assert Path(result["filepath"]).exists()
        assert result["file_size_bytes"] > 0

    def test_csv_content_structure(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)
        exporter.export([TRANSFORMED_RECORD], filename="test.csv")

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["video_id"] == "dQw4w9WgXcQ"
        assert row["title"] == "Never Gonna Give You Up"
        assert row["upload_date"] == "2009-10-25T06:57:33Z"
        assert row["views"] == "1500000000"
        assert row["likes"] == "45000000"
        assert row["duration"] == "3:32"
        assert row["video_type"] == "Video"

    def test_column_order(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)
        exporter.export([TRANSFORMED_RECORD], filename="test.csv")

        expected = ["video_id", "title", "upload_date", "views", "likes", "duration", "video_type", "video_url"]
        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == expected

    def test_multiple_records(self, tmp_output):
        records = [
            {**TRANSFORMED_RECORD, "video_id": "v1", "title": "First"},
            {**TRANSFORMED_RECORD, "video_id": "v2", "title": "Second"},
            {**TRANSFORMED_RECORD, "video_id": "v3", "title": "Third"},
        ]
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export(records, filename="test.csv")

        assert result["exported"] == 3

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3
        assert rows[0]["video_id"] == "v1"
        assert rows[2]["video_id"] == "v3"

    def test_empty_dataset(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export([], filename="test.csv")

        assert result["exported"] == 0
        assert result["skipped"] == 0
        assert result["success"] is True

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows == []

    def test_skips_records_missing_required_fields(self, tmp_output):
        records = [
            TRANSFORMED_RECORD,
            {"video_id": "v2", "title": "No Type"},
            {"video_id": "v3", "title": "T", "duration": "1:00", "video_type": "Video"},
        ]
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export(records, filename="test.csv")

        assert result["exported"] == 2
        assert result["skipped"] == 1

    def test_skips_empty_video_id(self, tmp_output):
        records = [
            TRANSFORMED_RECORD,
            {**TRANSFORMED_RECORD, "video_id": ""},
        ]
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export(records, filename="test.csv")

        assert result["exported"] == 1
        assert result["skipped"] == 1

    def test_overwrites_existing_file(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)

        exporter.export([TRANSFORMED_RECORD], filename="test.csv")
        first_size = (tmp_output / "test.csv").stat().st_size

        # Write again with different data
        exporter.export(
            [{**TRANSFORMED_RECORD, "video_id": "v2"}],
            filename="test.csv",
        )
        second_size = (tmp_output / "test.csv").stat().st_size

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["video_id"] == "v2"

    def test_special_characters(self, tmp_output):
        record = {
            **TRANSFORMED_RECORD,
            "title": 'Title with "quotes", commas, and\nnewlines',
        }
        exporter = CSVExporter(output_dir=tmp_output)
        exporter.export([record], filename="test.csv")

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["title"] == record["title"]

    def test_large_dataset(self, tmp_output):
        records = [
            {**TRANSFORMED_RECORD, "video_id": f"v{i:06d}", "title": f"Video {i}"}
            for i in range(5000)
        ]
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export(records, filename="test.csv")

        assert result["exported"] == 5000
        assert result["file_size_bytes"] > 0

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 5000

    def test_utf8_encoding(self, tmp_output):
        record = {
            **TRANSFORMED_RECORD,
            "title": "Çağatay Öztürk — 日本語のタイトル",
        }
        exporter = CSVExporter(output_dir=tmp_output)
        exporter.export([record], filename="test.csv")

        raw = (tmp_output / "test.csv").read_bytes()
        raw.decode("utf-8")

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["title"] == record["title"]

    def test_creates_output_directory(self, tmp_output):
        nested = tmp_output / "subdir" / "nested"
        exporter = CSVExporter(output_dir=nested)
        result = exporter.export([TRANSFORMED_RECORD], filename="test.csv")

        assert nested.exists()
        assert Path(result["filepath"]).exists()

    def test_missing_views_likes_exported_as_empty(self, tmp_output):
        record = {
            "video_id": "v1",
            "title": "No Stats",
            "upload_date": "2025-01-01T00:00:00Z",
            "duration": "5:00",
            "video_type": "Video",
        }
        exporter = CSVExporter(output_dir=tmp_output)
        exporter.export([record], filename="test.csv")

        with open(tmp_output / "test.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["views"] == ""
        assert rows[0]["likes"] == ""

    def test_default_filename_is_videos_csv(self, tmp_output):
        exporter = CSVExporter(output_dir=tmp_output)
        result = exporter.export([TRANSFORMED_RECORD])

        assert result["filepath"].endswith("videos.csv")
        assert Path(result["filepath"]).exists()
