"""Revalidation Engine — automatically reruns validators post-optimization to verify quality improvement."""

from __future__ import annotations
import logging
import re
from typing import Any

from models.blog_review import BlogReviewRequest
from optimization.optimization_models import (
    OptimizationType, OptimizationResult,
)

logger = logging.getLogger(__name__)


class RevalidationEngine:
    """Runs targeted validation on optimized sections and computes quality scores."""

    def revalidate(
        self,
        original_text: str,
        optimized_text: str,
        optimization_types: list[OptimizationType],
        primary_keyword: str = "",
    ) -> dict[str, float]:
        scores: dict[str, float] = {}
        original_scores = self._compute_scores(original_text, optimization_types, primary_keyword)
        optimized_scores = self._compute_scores(optimized_text, optimization_types, primary_keyword)

        for key in original_scores:
            scores[key] = optimized_scores.get(key, original_scores.get(key, 0))

        return scores

    def compute_improvement(
        self,
        scores_before: dict[str, float],
        scores_after: dict[str, float],
    ) -> dict[str, float]:
        improvement: dict[str, float] = {}
        for key in scores_before:
            before = scores_before.get(key, 0)
            after = scores_after.get(key, 0)
            improvement[key] = round(after - before, 1)
        return improvement

    def has_improved(
        self,
        scores_before: dict[str, float],
        scores_after: dict[str, float],
        optimization_types: list[OptimizationType],
    ) -> bool:
        for opt_type in optimization_types:
            key = self._score_key(opt_type)
            before = scores_before.get(key, 0)
            after = scores_after.get(key, 0)
            if after < before - 3:
                return False
        return True

    def _compute_scores(
        self,
        text: str,
        optimization_types: list[OptimizationType],
        primary_keyword: str,
    ) -> dict[str, float]:
        scores: dict[str, float] = {}

        for opt_type in optimization_types:
            key = self._score_key(opt_type)
            score_fn = self._score_functions().get(opt_type)
            if score_fn:
                scores[key] = score_fn(text, primary_keyword)
            else:
                scores[key] = self._compute_generic_score(text, primary_keyword)

        return scores

    def _score_functions(self) -> dict[OptimizationType, callable]:
        return {
            OptimizationType.SEO: self._seo_score,
            OptimizationType.GRAMMAR: self._grammar_score,
            OptimizationType.READABILITY: self._readability_score,
            OptimizationType.HALLUCINATION: self._hallucination_score,
            OptimizationType.KEYWORD: self._keyword_score,
            OptimizationType.PASSIVE_VOICE: self._passive_voice_score,
            OptimizationType.MARKDOWN: self._markdown_score,
        }

    def _seo_score(self, text: str, primary_keyword: str) -> float:
        score = 100.0
        text_lower = text.lower()
        kw = primary_keyword.lower() if primary_keyword else ""

        if kw:
            if kw not in text_lower:
                score -= 30
            words = text.split()
            kw_count = len(re.findall(re.escape(kw), text_lower))
            density = kw_count * len(kw.split()) / len(words) if words else 0
            if density < 0.003:
                score -= 15
            elif density > 0.03:
                score -= 10

        # Check first 100 chars for keyword
        if kw and kw not in text_lower[:200]:
            score -= 10

        # Check last 100 chars for keyword
        if kw and kw not in text_lower[-200:]:
            score -= 5

        return max(0, score)

    def _grammar_score(self, text: str, _kw: str = "") -> float:
        score = 100.0
        text_lower = text.lower()

        misspellings = {
            "recieve", "acheive", "seperate", "definately", "occured",
            "occuring", "occurance", "prefered", "refered", "adress",
        }
        found = [w for w in misspellings if w in text_lower]
        score -= len(found) * 5

        sentences = re.split(r'(?<=[.!?])\s+', text)
        total = len(sentences)
        if total > 0:
            passive = len(re.findall(r'\b(is|are|was|were|be|been|being)\s+\w+ed\b', text_lower))
            passive_ratio = passive / total
            if passive_ratio > 0.3:
                score -= 15

        return max(0, score)

    def _readability_score(self, text: str, _kw: str = "") -> float:
        score = 100.0
        sentences = re.split(r'(?<=[.!?])\s+', text)
        total = len(sentences)
        if total == 0:
            return 100.0

        # Average sentence length
        words = text.split()
        avg_sentence_len = len(words) / total if total else 0
        if avg_sentence_len > 25:
            score -= (avg_sentence_len - 25) * 2
        elif avg_sentence_len > 20:
            score -= (avg_sentence_len - 20)

        # Long sentences
        long_sentences = sum(1 for s in sentences if len(s.split()) > 30)
        if long_sentences > total * 0.2:
            score -= 10

        return max(0, score)

    def _hallucination_score(self, text: str, _kw: str = "") -> float:
        score = 100.0
        text_lower = text.lower()

        patterns = [
            r'\baccording to a \d{4} study\b',
            r'\ba \d{4} (study|report|survey|analysis) (by|from|published)\b',
            r'\bresearch (shows|suggests|indicates|proves)\b',
            r'\bstudies show\b',
            r'\bmany (studies|experts) (have shown|believe|suggest)\b',
            r'\bit is (widely|generally|well) (known|accepted)\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            score -= len(matches) * 10

        return max(0, score)

    def _keyword_score(self, text: str, primary_keyword: str) -> float:
        if not primary_keyword:
            return 100.0
        score = 100.0
        text_lower = text.lower()
        kw = primary_keyword.lower()

        words = text.split()
        kw_count = len(re.findall(re.escape(kw), text_lower))
        density = kw_count * len(kw.split()) / len(words) if words else 0

        if density < 0.005:
            score -= 20
        elif density > 0.03:
            score -= 15

        if kw not in text_lower[:200]:
            score -= 10

        return max(0, score)

    def _passive_voice_score(self, text: str, _kw: str = "") -> float:
        score = 100.0
        sentences = re.split(r'(?<=[.!?])\s+', text)
        total = len(sentences)
        if total == 0:
            return 100.0

        passive = len(re.findall(r'\b(is|are|was|were|be|been|being)\s+\w+ed\b', text.lower()))
        ratio = passive / total
        if ratio > 0.3:
            score -= 20
        elif ratio > 0.2:
            score -= 10
        elif ratio > 0.1:
            score -= 5

        return max(0, score)

    def _markdown_score(self, text: str, _kw: str = "") -> float:
        score = 100.0

        tables = re.findall(r'\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)*', text)
        for table in tables:
            lines = table.strip().split('\n')
            if len(lines) >= 2:
                header_cols = len([c for c in lines[0].split('|') if c.strip()])
                sep_cols = len([c for c in lines[1].split('|') if c.strip()])
                if header_cols != sep_cols:
                    score -= 10

        # Check for broken links
        links = re.findall(r'\[([^\]]*)\]\(([^)]*)\)', text)
        for text_content, url in links:
            if not url.strip():
                score -= 5

        return max(0, score)

    @staticmethod
    def _score_key(opt_type: OptimizationType) -> str:
        mapping = {
            OptimizationType.SEO: "seo",
            OptimizationType.GRAMMAR: "grammar",
            OptimizationType.READABILITY: "readability",
            OptimizationType.HALLUCINATION: "hallucination_risk",
            OptimizationType.KEYWORD: "keyword_optimization",
            OptimizationType.PASSIVE_VOICE: "grammar",
            OptimizationType.MARKDOWN: "markdown_quality",
            OptimizationType.DUPLICATE: "structure",
            OptimizationType.STRUCTURE: "structure",
            OptimizationType.STYLE: "content_quality",
            OptimizationType.COMPLETENESS: "completeness",
            OptimizationType.FAQ: "completeness",
            OptimizationType.CTA: "completeness",
            OptimizationType.SUMMARY: "completeness",
        }
        return mapping.get(opt_type, "overall")
