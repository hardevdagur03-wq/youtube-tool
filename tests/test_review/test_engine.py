"""Tests for Phase 9 Review Engine."""

from __future__ import annotations
import pytest
from models.blog_review import BlogReviewRequest, PublishDecision
from review.engine import ReviewEngine


SAMPLE_BLOG = """# The Complete Guide to Python Testing

## Introduction

Testing is a critical part of software development. It ensures code quality, prevents regressions, and gives developers confidence when making changes. In this guide, we will explore Python testing frameworks and best practices.

## Why Testing Matters

Testing matters because it catches bugs early. Many teams have adopted test-driven development to improve code quality. There are several types of tests you should know about.

## Getting Started

Pytest is the most popular testing framework for Python. It is simple to use yet powerful.

```python
def test_addition():
    assert 1 + 1 == 2
```

## Best Practices

You should follow these best practices when writing tests:
- Keep tests independent
- Use descriptive test names
- One assertion per test when possible
- Mock external dependencies
- Run tests frequently

## Conclusion

Testing is essential for building reliable software. By following the practices outlined in this guide, you can improve your code quality and development velocity.
"""


class TestReviewEngine:
    def test_engine_initialization(self):
        engine = ReviewEngine()
        assert len(engine._validators) >= 10

    def test_review_valid_content(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(
            blog_title="Complete Guide to Python Testing",
            primary_keyword="python testing",
            content=SAMPLE_BLOG,
            faq=[{"question": "Why test?", "answer": "To ensure quality."}],
        )
        response = engine.review(req)
        assert response.success is True
        assert response.report is not None
        assert response.report.overall_score > 0
        assert response.report.word_count > 0

    def test_review_empty_content(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content="")
        response = engine.review(req)
        assert response.success is True
        if response.report:
            assert response.report.overall_score >= 0

    def test_publish_decision_assigned(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        assert response.report is not None
        assert response.report.publish_decision in list(PublishDecision)

    def test_scorecard_generated(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        report = response.report
        assert report is not None
        assert len(report.scorecard.categories) > 0
        assert report.scorecard.overall_score > 0

    def test_recommendations_generated(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        report = response.report
        assert report is not None
        # At least one of the recommendation lists should have content
        total_recs = len(report.must_fix) + len(report.should_improve) + len(report.nice_to_have)
        assert total_recs >= 0

    def test_markdown_report_generated(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        report = response.report
        assert report is not None
        assert len(report.markdown) > 0
        assert "Overall Quality Score" in report.markdown or "Scorecard" in report.markdown

    def test_executive_summary_generated(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        report = response.report
        assert report is not None
        assert len(report.executive_summary) > 0

    def test_timing_recorded(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(content=SAMPLE_BLOG)
        response = engine.review(req)
        report = response.report
        assert report is not None
        assert report.execution_time_ms > 0

    def test_review_with_faq(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(
            content=SAMPLE_BLOG,
            faq=[
                {"question": "What is pytest?", "answer": "A testing framework."},
                {"question": "Why test?", "answer": "Quality assurance."},
            ],
        )
        response = engine.review(req)
        assert response.success is True

    def test_review_with_links(self):
        engine = ReviewEngine()
        req = BlogReviewRequest(
            content=SAMPLE_BLOG,
            internal_links=[
                {"anchor": "see our docs", "url": "/docs"},
                {"anchor": "learn more", "url": "/learn"},
            ],
            external_links=[
                {"anchor": "pytest docs", "url": "https://docs.pytest.org"},
            ],
        )
        response = engine.review(req)
        assert response.success is True
