"""Tests for ReviewReportGenerator."""

from __future__ import annotations
import json
import os
import tempfile
from models.blog_review import BlogReviewRequest, QualityReport, GrammarResult, SEOResult
from review.review_report_generator import ReviewReportGenerator
from review.review_models_ext import (
    ReviewReport, MarkdownReport, KeywordReport, QualityScores,
)


class TestReviewReportGenerator:
    def test_init(self):
        g = ReviewReportGenerator()
        assert g is not None

    def test_generate_minimal(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(content="# Hello\n\nWorld")
        quality_report = QualityReport()
        result = g.generate(request, quality_report)
        assert isinstance(result, ReviewReport)
        assert result.metadata.word_count >= 1

    def test_generate_with_all(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(
            blog_title="Test",
            content="# Test\n\nContent here.",
            primary_keyword="test",
            secondary_keywords=["python"],
        )
        quality_report = QualityReport()
        quality_report.grammar = GrammarResult(score=85.0)
        quality_report.seo = SEOResult(score=90.0)

        keyword_report = KeywordReport(score=80.0, primary_keyword_density=1.5)
        markdown_report = MarkdownReport(score=95.0)
        extra_grammar = GrammarResult(score=90.0, passive_voice_sentences=2)

        result = g.generate(request, quality_report, keyword_report, markdown_report, extra_grammar)
        assert result.grammar.score == 85.0
        assert result.seo.score == 90.0
        assert result.keyword_analysis.score == 80.0
        assert result.markdown.score == 95.0

    def test_scores_built(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(content="Test content")
        quality_report = QualityReport()
        result = g.generate(request, quality_report)
        assert isinstance(result.quality_scores, QualityScores)
        assert result.quality_scores.grammar == 100.0

    def test_publication_status(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(content="Test")
        quality_report = QualityReport()
        result = g.generate(request, quality_report)
        assert result.publication_status.decision == "reject"
        assert result.publication_status.overall_score >= 0

    def test_issues_extracted(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(content="Test")
        quality_report = QualityReport()
        result = g.generate(request, quality_report)
        assert isinstance(result.issues, list)

    def test_write_report(self):
        g = ReviewReportGenerator()
        request = BlogReviewRequest(content="Test")
        quality_report = QualityReport()
        report = g.generate(request, quality_report)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            written = g.write_report(report, path)
            assert written == path
            assert os.path.exists(path)
            with open(path, 'r') as f:
                data = json.load(f)
            assert "metadata" in data
            assert "quality_scores" in data
            assert "publication_status" in data
        finally:
            os.unlink(path)
