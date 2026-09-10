from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


@pytest.fixture
def baseline_metrics():
    return {
        "pipeline_duration_seconds": 120.0,
        "seo_score": 85.0,
        "readability_score": 75.0,
        "grammar_score": 90.0,
        "overall_quality_score": 82.0,
        "word_count": 1500,
        "entity_count": 8,
        "keyword_count": 12,
        "section_count": 6,
        "output_hash": "abc123def456",
    }


@pytest.fixture
def regression_engine():
    return {
        "name": "pipeline_regression",
        "version": "1.0.0",
        "thresholds": {
            "seo_score_min": 70.0,
            "readability_min": 60.0,
            "grammar_min": 75.0,
            "quality_min": 70.0,
            "word_count_min": 800,
            "word_count_max": 3000,
            "duration_max_seconds": 300.0,
            "entity_count_min": 3,
            "section_count_min": 4,
        },
    }


@pytest.fixture
def golden_dataset():
    return {
        "project": {
            "url": "https://youtube.com/watch?v=golden123",
            "video_id": "golden123",
            "name": "Golden Regression Project",
        },
        "metadata": {
            "title": "Golden Video Title",
            "channel_title": "Golden Channel",
        },
        "analysis": {
            "primary_topic": "Regression Testing",
            "sentiment": "positive",
        },
        "seo": {
            "primary_keyword": "regression testing",
            "seo_score": 85.0,
        },
        "outline": {
            "section_count": 6,
        },
    }


@pytest.fixture
def sample_transcript_text():
    return (
        "Regression testing is a type of software testing that ensures existing "
        "features still work after changes. It is crucial for maintaining quality. "
        "Automated regression tests save time and improve reliability. "
        "Test suites should be run after every code change to catch regressions early. "
        "Continuous integration pipelines often include regression test suites."
    )
