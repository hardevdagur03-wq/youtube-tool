"""Tests for RecommendationEngine."""

from __future__ import annotations
from models.blog_review import QualityReport, GrammarResult, SEOResult, ReadabilityResult, HeadingResult
from review.recommendation_engine import RecommendationEngine
from review.review_models_ext import RecommendationEntry


class TestRecommendationEngine:
    def test_init(self):
        e = RecommendationEngine()
        assert e is not None

    def test_empty_report(self):
        e = RecommendationEngine()
        report = QualityReport()
        recs = e.generate(report)
        assert isinstance(recs, list)

    def test_low_grammar_recommendation(self):
        e = RecommendationEngine()
        report = QualityReport()
        report.grammar = GrammarResult(score=50.0)
        recs = e.generate(report)
        must_fix = [r for r in recs if r.priority == "must_fix"]
        grammar_recs = [r for r in recs if r.category == "grammar"]
        assert len(grammar_recs) > 0

    def test_low_seo_recommendation(self):
        e = RecommendationEngine()
        report = QualityReport()
        report.seo = SEOResult(score=50.0, missing_elements=["keyword in title", "meta description"])
        recs = e.generate(report)
        seo_recs = [r for r in recs if r.category == "seo"]
        assert len(seo_recs) > 0

    def test_low_readability_recommendation(self):
        e = RecommendationEngine()
        report = QualityReport()
        report.readability = ReadabilityResult(score=50.0)
        recs = e.generate(report)
        readability_recs = [r for r in recs if r.category == "readability"]
        assert len(readability_recs) > 0

    def test_priority_sorting(self):
        e = RecommendationEngine()
        report = QualityReport()
        report.grammar = GrammarResult(score=50.0)
        report.seo = SEOResult(score=50.0)
        report.readability = ReadabilityResult(score=50.0)
        recs = e.generate(report)
        priorities = [r.priority for r in recs]
        must_fix_idx = next((i for i, p in enumerate(priorities) if p == "must_fix"), len(priorities))
        should_improve_idx = next((i for i, p in enumerate(priorities) if p == "should_improve"), len(priorities))
        nice_idx = next((i for i, p in enumerate(priorities) if p == "nice_to_have"), len(priorities))
        assert must_fix_idx < should_improve_idx < nice_idx

    def test_recommendation_fields(self):
        e = RecommendationEngine()
        report = QualityReport()
        report.grammar = GrammarResult(score=50.0)
        recs = e.generate(report)
        for rec in recs:
            assert isinstance(rec, RecommendationEntry)
            assert hasattr(rec, 'priority')
            assert hasattr(rec, 'category')
            assert hasattr(rec, 'description')
            assert hasattr(rec, 'impact')
            assert hasattr(rec, 'effort')
