"""Tests for ReviewScorer."""

from __future__ import annotations
from review.review_scorer import ReviewScorer, CATEGORY_WEIGHTS
from review.review_models_ext import QualityScores


class TestReviewScorer:
    def test_init(self):
        s = ReviewScorer()
        assert s is not None

    def test_compute_perfect(self):
        s = ReviewScorer()
        scores = QualityScores(
            overall=100, grammar=100, seo=100, readability=100, structure=100,
            completeness=100, keyword_optimization=100, markdown_quality=100,
            content_quality=100, hallucination_risk=100, fact_consistency=100,
            eeat=100, accessibility=100, ai_detection=100, linking=100,
        )
        result = s.compute(scores)
        assert result == 100.0

    def test_compute_zero(self):
        s = ReviewScorer()
        scores = QualityScores(
            overall=0, grammar=0, seo=0, readability=0, structure=0,
            completeness=0, keyword_optimization=0, markdown_quality=0,
            content_quality=0, hallucination_risk=0, fact_consistency=0,
            eeat=0, accessibility=0, ai_detection=0, linking=0,
        )
        result = s.compute(scores)
        assert result == 0.0

    def test_compute_mid(self):
        s = ReviewScorer()
        scores = QualityScores(
            overall=80, grammar=80, seo=80, readability=80, structure=80,
            completeness=80, keyword_optimization=80, markdown_quality=80,
            content_quality=80, hallucination_risk=80, fact_consistency=80,
            eeat=80, accessibility=80, ai_detection=80, linking=80,
        )
        result = s.compute(scores)
        assert 75 <= result <= 85

    def test_score_status(self):
        s = ReviewScorer()
        assert s.score_status(95) == "excellent"
        assert s.score_status(85) == "good"
        assert s.score_status(75) == "fair"
        assert s.score_status(65) == "poor"
        assert s.score_status(50) == "fail"

    def test_score_breakdown(self):
        s = ReviewScorer()
        scores = QualityScores(grammar=90.0, seo=80.0, readability=70.0)
        breakdown = s.score_breakdown(scores)
        assert "grammar" in breakdown
        assert "seo" in breakdown
        assert "readability" in breakdown
        assert breakdown["grammar"] == 90.0
        assert breakdown["seo"] == 80.0
        assert breakdown["readability"] == 70.0

    def test_category_weights_defined(self):
        assert sum(CATEGORY_WEIGHTS.values()) > 0.9


class TestCategoryWeights:
    def test_all_categories_present(self):
        required = [
            "grammar", "seo", "readability", "structure", "completeness",
            "keyword_optimization", "markdown_quality", "content_quality",
            "hallucination_risk", "fact_consistency", "eeat", "accessibility",
            "ai_detection", "linking",
        ]
        for cat in required:
            assert cat in CATEGORY_WEIGHTS, f"Missing category weight: {cat}"
