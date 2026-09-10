"""Comprehensive quality scoring engine — computes weighted scores across all categories."""

from __future__ import annotations
from review.review_models_ext import QualityScores


CATEGORY_WEIGHTS = {
    "grammar": 0.12,
    "seo": 0.12,
    "readability": 0.12,
    "structure": 0.08,
    "completeness": 0.08,
    "keyword_optimization": 0.10,
    "markdown_quality": 0.05,
    "content_quality": 0.12,
    "hallucination_risk": 0.06,
    "fact_consistency": 0.04,
    "eeat": 0.05,
    "accessibility": 0.03,
    "ai_detection": 0.02,
    "linking": 0.01,
}


class ReviewScorer:
    """Computes comprehensive weighted quality scores."""

    def compute(self, scores: QualityScores) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for category, weight in CATEGORY_WEIGHTS.items():
            score = getattr(scores, category, 0.0)
            weighted_sum += score * weight
            total_weight += weight

        overall = weighted_sum / total_weight if total_weight else 0.0
        return round(overall, 1)

    def score_status(self, score: float) -> str:
        if score >= 90:
            return "excellent"
        if score >= 80:
            return "good"
        if score >= 70:
            return "fair"
        if score >= 60:
            return "poor"
        return "fail"

    def score_breakdown(self, scores: QualityScores) -> dict[str, float]:
        return {
            "grammar": scores.grammar,
            "seo": scores.seo,
            "readability": scores.readability,
            "structure": scores.structure,
            "completeness": scores.completeness,
            "keyword_optimization": scores.keyword_optimization,
            "markdown_quality": scores.markdown_quality,
            "content_quality": scores.content_quality,
            "hallucination_risk": scores.hallucination_risk,
            "fact_consistency": scores.fact_consistency,
            "eeat": scores.eeat,
            "accessibility": scores.accessibility,
            "ai_detection": scores.ai_detection,
            "linking": scores.linking,
        }
