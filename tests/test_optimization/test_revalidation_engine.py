"""Tests for RevalidationEngine."""

from __future__ import annotations
from optimization.revalidation_engine import RevalidationEngine
from optimization.optimization_models import OptimizationType


class TestRevalidationEngine:
    def test_init(self):
        re = RevalidationEngine()
        assert re is not None

    def test_revalidate_seo_improved(self):
        re = RevalidationEngine()
        scores = re.revalidate(
            "Some content without keyword.",
            "Python content with python keyword included.",
            [OptimizationType.SEO],
            primary_keyword="python",
        )
        assert "seo" in scores
        assert scores["seo"] >= 0

    def test_revalidate_grammar(self):
        re = RevalidationEngine()
        scores = re.revalidate(
            "this has definately a error.",
            "This has definitely an error corrected.",
            [OptimizationType.GRAMMAR],
        )
        assert "grammar" in scores

    def test_compute_improvement(self):
        re = RevalidationEngine()
        imp = re.compute_improvement(
            {"seo": 70.0, "grammar": 80.0},
            {"seo": 95.0, "grammar": 85.0},
        )
        assert imp["seo"] == 25.0
        assert imp["grammar"] == 5.0

    def test_has_improved(self):
        re = RevalidationEngine()
        assert re.has_improved({"seo": 70.0}, {"seo": 95.0}, [OptimizationType.SEO]) is True
        assert re.has_improved({"seo": 90.0}, {"seo": 70.0}, [OptimizationType.SEO]) is False

    def test_seo_score(self):
        re = RevalidationEngine()
        score = re._seo_score("Python content about python programming.", "python")
        assert 0 <= score <= 100
        # No keyword
        score2 = re._seo_score("Random content without keyword.", "python")
        assert score2 < score

    def test_grammar_score(self):
        re = RevalidationEngine()
        score = re._grammar_score("This is correct. No errors here.")
        assert score == 100.0

    def test_readability_score(self):
        re = RevalidationEngine()
        # Short sentences
        score = re._readability_score("Short sentences. Very clear. Easy to read.")
        assert score >= 90

    def test_hallucination_score(self):
        re = RevalidationEngine()
        score = re._hallucination_score("According to a 2023 study, this is proven.")
        assert score < 100

    def test_keyword_score(self):
        re = RevalidationEngine()
        score = re._keyword_score("python python python python python", "python")
        assert score < 100  # Stuffing penalized

    def test_score_key(self):
        assert RevalidationEngine._score_key(OptimizationType.SEO) == "seo"
        assert RevalidationEngine._score_key(OptimizationType.GRAMMAR) == "grammar"
        assert RevalidationEngine._score_key(OptimizationType.HALLUCINATION) == "hallucination_risk"
