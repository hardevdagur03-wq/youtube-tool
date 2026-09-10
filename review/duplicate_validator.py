"""Duplicate Content Detection — Phase 9."""

from __future__ import annotations
import re
from collections import Counter
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, DuplicateResult


class DuplicateValidator(BaseValidator):
    """Detects duplicate content: paragraphs, headings, FAQs, lists."""

    def name(self) -> str:
        return "Duplicate Content Detection"

    def validate(self, request: BlogReviewRequest) -> DuplicateResult:
        text = request.content
        if not text:
            return DuplicateResult(score=100.0)

        issues: list[str] = []
        recommendations: list[str] = []

        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

        # Check duplicate paragraphs
        para_counts: Counter = Counter()
        normalized_paras = [re.sub(r'\s+', ' ', p).lower() for p in paragraphs]
        for np in normalized_paras:
            para_counts[np] += 1

        dup_paras = sum(1 for c in para_counts.values() if c > 1)
        dup_heading_count = 0

        # Check duplicate headings
        headings = re.findall(r'^#{1,3}\s+(.+)$', text, re.MULTILINE)
        heading_counts: Counter = Counter(h.lower().strip() for h in headings)
        dup_headings = sum(1 for c in heading_counts.values() if c > 1)
        dup_heading_count = dup_headings

        if dup_headings > 0:
            for h, count in heading_counts.most_common(3):
                if count > 1:
                    issues.append(f"Duplicate heading: '{h}' appears {count} times")
            recommendations.append("Rename duplicate headings to be more specific and descriptive")

        # Find near-duplicate paragraphs
        near_duplicates: list[str] = []
        for i, p1 in enumerate(normalized_paras):
            for j, p2 in enumerate(normalized_paras):
                if i < j and len(p1) > 20:
                    similarity = self._jaccard_similarity(set(p1.split()), set(p2.split()))
                    if similarity > 0.8:
                        near_duplicates.append(f"Paragraph {i + 1} and {j + 1} are near-identical ({similarity:.0%} similarity)")

        if near_duplicates:
            issues.extend(near_duplicates[:3])
            recommendations.append("Merge near-duplicate paragraphs or rewrite to add unique value")

        # Check repeated FAQ questions
        if request.faq:
            faq_questions = [f.get("question", "").lower().strip() for f in request.faq if f.get("question")]
            faq_counts: Counter = Counter(faq_questions)
            dup_faqs = sum(1 for c in faq_counts.values() if c > 1)
            if dup_faqs > 0:
                issues.append(f"{dup_faqs} duplicate FAQ questions found")
                recommendations.append("Remove duplicate FAQ questions")

        # Check repeated examples (e.g., "For example")
        example_count = len(re.findall(r'\b(for example|for instance|such as)\b', text.lower()))
        if example_count > 5:
            recommendations.append(f"'{example_count}' examples found. Vary example language to avoid repetition.")

        # Calculate score
        score = 100.0
        score -= dup_paras * 5
        score -= dup_heading_count * 8
        score -= len(near_duplicates) * 5
        score = max(0, min(100, score))

        return DuplicateResult(
            score=round(score, 1),
            duplicate_paragraphs=dup_paras,
            duplicate_headings=dup_heading_count,
            repeated_sections=issues,
            merge_recommendations=recommendations,
        )

    def _jaccard_similarity(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)
