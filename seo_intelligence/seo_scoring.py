"""SEO Scoring — comprehensive SEO quality assessment.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import SEOScore, KeywordStrategy, ContentStrategy

logger = logging.getLogger(__name__)


class SEOScoring:
    """Computes comprehensive SEO scores for the SEO plan."""

    def compute(
        self,
        keyword_strategy: KeywordStrategy,
        content_strategy: ContentStrategy,
    ) -> SEOScore:
        score = SEOScore()

        # Keyword score (0-100)
        kw_score = 0.0
        if keyword_strategy.primary_keyword:
            kw_score += 30
        kw_score += min(30, len(keyword_strategy.secondary_keywords) * 3)
        kw_score += min(20, len(keyword_strategy.lsi_keywords) * 2)
        kw_score += min(10, len(keyword_strategy.long_tail_keywords) * 1.5)
        kw_score += min(10, len(keyword_strategy.question_keywords) * 2)
        score.keyword_score = min(100, kw_score)

        # Intent match score
        intent_score = 0.0
        if keyword_strategy.primary_intent:
            intent_score += 50
        if keyword_strategy.primary_difficulty < 0.7:
            intent_score += 25
        score.intent_match_score = min(100, intent_score + (kw_score * 0.25))

        # Topic authority score
        entity_count = len(keyword_strategy.entity_keywords)
        topic_score = min(40, entity_count * 4) + min(60, kw_score * 0.6)
        score.topic_authority_score = min(100, topic_score)

        # Keyword coverage
        total_secondary = len(keyword_strategy.secondary_keywords)
        coverage = min(100, total_secondary * 8)
        score.keyword_coverage_score = min(100, coverage)

        # Semantic coverage
        semantic_count = len(keyword_strategy.semantic_keywords) + len(keyword_strategy.lsi_keywords)
        score.semantic_coverage_score = min(100, semantic_count * 5)

        # Content readability (estimate based on structure)
        readability = 0.0
        if keyword_strategy.primary_keyword:
            readability = 50.0
        if content_strategy.recommended_word_count >= 1500:
            readability += 15
        if content_strategy.recommended_headings >= 6:
            readability += 15
        if content_strategy.recommended_examples >= 3:
            readability += 10
        if content_strategy.recommended_statistics >= 2:
            readability += 10
        score.readability_score = min(100, readability)

        # CTR prediction
        ctr = 0.0
        if keyword_strategy.primary_keyword:
            ctr = 40.0
        if len(keyword_strategy.secondary_keywords) >= 5:
            ctr += 10
        if len(keyword_strategy.long_tail_keywords) >= 3:
            ctr += 10
        if keyword_strategy.primary_difficulty < 0.6:
            ctr += 10
        score.ctr_prediction = min(100, ctr)

        # Completeness score
        completeness = 0.0
        if keyword_strategy.primary_keyword:
            completeness += 20
        if len(keyword_strategy.secondary_keywords) >= 3:
            completeness += 20
        if len(keyword_strategy.lsi_keywords) >= 3:
            completeness += 15
        if len(keyword_strategy.long_tail_keywords) >= 2:
            completeness += 15
        if len(keyword_strategy.question_keywords) >= 1:
            completeness += 15
        if len(keyword_strategy.entity_keywords) >= 3:
            completeness += 15
        score.completeness_score = min(100, completeness)

        # Content opportunity score
        opportunity = (score.keyword_score * 0.3 +
                       score.semantic_coverage_score * 0.2 +
                       score.completeness_score * 0.3 +
                       score.topic_authority_score * 0.2)
        score.content_opportunity_score = min(100, opportunity)

        # Overall score (weighted average)
        if keyword_strategy.primary_keyword:
            score.overall_score = (
                score.keyword_score * 0.20 +
                score.intent_match_score * 0.10 +
                score.topic_authority_score * 0.15 +
                score.keyword_coverage_score * 0.10 +
                score.semantic_coverage_score * 0.10 +
                score.readability_score * 0.10 +
                score.completeness_score * 0.15 +
                score.content_opportunity_score * 0.10
            )

        return score
