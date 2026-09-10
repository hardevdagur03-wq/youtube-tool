"""Tests for ReviewPipeline."""

from __future__ import annotations
import os
import pytest
from models.blog_review import BlogReviewRequest
from review.review_pipeline import ReviewPipeline


SAMPLE_CONTENT = """# Python Testing Guide

## Introduction

Testing is important for software quality.

## Methods

Unit tests verify individual components. Integration tests check how components work together.

| Type | Scope | Speed |
|------|-------|-------|
| Unit | Function | Fast |
| Integration | Module | Medium |

![Diagram](/img/diagram.png)

## Conclusion

Testing is essential.
"""


class TestReviewPipeline:
    def test_init(self):
        p = ReviewPipeline()
        assert p is not None

    def test_review_with_content(self):
        p = ReviewPipeline()
        req = BlogReviewRequest(
            blog_title="Python Testing Guide",
            primary_keyword="testing",
            secondary_keywords=["unit", "integration"],
            content=SAMPLE_CONTENT,
        )
        response, report = p.review(req)
        assert response.success is True
        assert report is not None
        assert report.metadata.word_count > 0
        assert report.quality_scores.overall > 0

    def test_review_empty_content(self):
        p = ReviewPipeline()
        req = BlogReviewRequest(content="")
        response, report = p.review(req)
        assert report is not None

    def test_review_with_extra_validators(self):
        p = ReviewPipeline()
        req = BlogReviewRequest(
            blog_title="Test",
            primary_keyword="python",
            content=SAMPLE_CONTENT,
        )
        _, report = p.review(req)
        assert report is not None
        assert report.keyword_analysis.score >= 0
        assert report.markdown.score >= 0
        assert report.markdown.table_count >= 1
        assert report.markdown.image_count >= 1

    def test_write_review_report(self):
        p = ReviewPipeline(output_dir="test_output")
        req = BlogReviewRequest(content="# Hello\n\nWorld.")
        _, report = p.review(req)
        assert report is not None
        path = p.write_review_report(report, project_id="test123")
        assert os.path.exists(path)
        assert "test123" in path
        os.unlink(path)
        try:
            os.rmdir("test_output")
        except OSError:
            pass

    def test_pipeline_no_output_dir(self):
        p = ReviewPipeline()
        assert p.output_dir == "output"
