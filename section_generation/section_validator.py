"""Section Validator — validates each section independently.

Checks grammar, SEO coverage, keyword usage, heading alignment,
word count, fact consistency, outline compliance, duplicate content,
readability, and hallucination risk.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from section_generation.section_models import (
    SectionOutput,
    SectionContext,
    SectionValidation,
    SectionType,
    utc_now,
)

logger = logging.getLogger(__name__)


class SectionValidator:
    """Validates a single generated section."""

    WORD_COUNT_TOLERANCE = 0.5

    def validate(
        self,
        output: SectionOutput,
        context: SectionContext | None = None,
    ) -> SectionValidation:
        if not output.content.strip():
            return SectionValidation(
                section_id=output.section_id,
                validated_at=utc_now(),
                valid=False,
                score=0.0,
                issues=["Section content is empty"],
            )

        validation = SectionValidation(
            section_id=output.section_id,
            validated_at=utc_now(),
        )

        grammar_score = self._check_grammar(output.content)
        seo_score = self._check_seo_coverage(output, context)
        keyword_score = self._check_keyword_usage(output, context)
        heading_score = self._check_heading_alignment(output)
        word_count_valid = self._check_word_count(output, context)
        fact_score = self._check_fact_consistency(output, context)
        outline_score = self._check_outline_compliance(output, context)
        duplicate_score = self._check_duplicate_content(output)
        readability_score = self._check_readability(output.content)
        hallucination_score = self._check_hallucination_risk(output, context)

        validation.grammar_score = grammar_score
        validation.seo_coverage_score = seo_score
        validation.keyword_usage_score = keyword_score
        validation.heading_alignment_score = heading_score
        validation.word_count_valid = word_count_valid
        validation.fact_consistency_score = fact_score
        validation.outline_compliance_score = outline_score
        validation.duplicate_content_score = duplicate_score
        validation.readability_score = readability_score
        validation.hallucination_risk_score = hallucination_score

        weights = {
            "grammar": 0.10,
            "seo": 0.15,
            "keyword": 0.15,
            "heading": 0.10,
            "word_count": 0.05,
            "fact": 0.15,
            "outline": 0.10,
            "duplicate": 0.05,
            "readability": 0.05,
            "hallucination": 0.10,
        }

        weighted = (
            grammar_score * weights["grammar"]
            + seo_score * weights["seo"]
            + keyword_score * weights["keyword"]
            + heading_score * weights["heading"]
            + (1.0 if word_count_valid else 0.3) * weights["word_count"]
            + fact_score * weights["fact"]
            + outline_score * weights["outline"]
            + duplicate_score * weights["duplicate"]
            + readability_score * weights["readability"]
            + hallucination_score * weights["hallucination"]
        )
        validation.score = round(weighted * 100, 1)
        validation.valid = validation.score >= 60.0

        self._collect_issues(validation, output, context)
        self._collect_warnings(validation)

        return validation

    def _check_grammar(self, content: str) -> float:
        issues = 0
        sentences = re.split(r"[.!?]+", content)
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            words = s.split()
            if len(words) > 40:
                issues += 1
            if s[0].islower():
                issues += 1
        repeated = re.findall(r"\b(\w+)\s+\1\b", content, re.IGNORECASE)
        issues += len(repeated)
        score = max(0.0, 1.0 - (issues * 0.05))
        return round(score, 2)

    def _check_seo_coverage(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> float:
        if not context:
            return 0.7
        content_lower = output.content.lower()
        keywords = context.keywords or []
        if not keywords and context.primary_keyword:
            keywords = [context.primary_keyword]
        if not keywords:
            return 0.7
        found = sum(1 for kw in keywords if kw.lower() in content_lower)
        ratio = found / len(keywords)
        return round(min(1.0, ratio + 0.3), 2)

    def _check_keyword_usage(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> float:
        if not context or not context.primary_keyword:
            return 0.7
        content_lower = output.content.lower()
        pk = context.primary_keyword.lower()
        if pk not in content_lower:
            return 0.0
        count = content_lower.count(pk)
        if count < 1:
            return 0.0
        if count > 10:
            return max(0.0, 1.0 - (count - 10) * 0.05)
        return 1.0

    def _check_heading_alignment(self, output: SectionOutput) -> float:
        if not output.heading:
            return 0.7
        content_lower = output.content.lower()
        heading_lower = output.heading.lower()
        heading_words = set(heading_lower.split())
        if not heading_words:
            return 0.7
        found = sum(1 for w in heading_words if len(w) > 3 and w in content_lower)
        ratio = found / max(len([w for w in heading_words if len(w) > 3]), 1)
        return round(min(1.0, ratio + 0.2), 2)

    def _check_word_count(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> bool:
        word_count = len(output.content.split())
        target = (context or SectionContext()).target_word_count
        if word_count == 0:
            return False
        lower = target * (1 - self.WORD_COUNT_TOLERANCE)
        upper = target * (1 + self.WORD_COUNT_TOLERANCE * 3)
        return lower <= word_count <= upper

    def _check_fact_consistency(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> float:
        if not context:
            return 0.7
        facts = context.facts or []
        if not facts:
            return 0.7
        content_lower = output.content.lower()
        found = 0
        for fact in facts:
            key_terms = [t for t in fact.split() if len(t) > 4]
            if not key_terms:
                continue
            matches = sum(1 for t in key_terms[:5] if t.lower() in content_lower)
            if matches >= min(2, len(key_terms[:5])):
                found += 1
        ratio = found / len(facts)
        return round(min(1.0, ratio + 0.2), 2)

    def _check_outline_compliance(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> float:
        if not context:
            return 0.7
        score = 1.0
        if context.goal:
            goal_terms = [t for t in context.goal.split() if len(t) > 4]
            if goal_terms:
                matches = sum(1 for t in goal_terms if t.lower() in output.content.lower())
                if matches < len(goal_terms) * 0.3:
                    score -= 0.3
        return round(max(0.0, score), 2)

    def _check_duplicate_content(self, output: SectionOutput) -> float:
        sentences = re.split(r"[.!?]+", output.content)
        seen = set()
        duplicates = 0
        for s in sentences:
            s = s.strip().lower()
            if len(s) > 20:
                if s in seen:
                    duplicates += 1
                seen.add(s)
        if duplicates > 0:
            return round(max(0.0, 1.0 - duplicates * 0.1), 2)
        return 1.0

    def _check_readability(self, content: str) -> float:
        sentences = re.split(r"[.!?]+", content)
        total_sentences = max(len(sentences), 1)
        total_words = len(content.split())
        if total_words == 0:
            return 0.5
        avg_words_per_sentence = total_words / total_sentences
        if avg_words_per_sentence < 8:
            return 0.7
        if avg_words_per_sentence < 15:
            return 0.9
        if avg_words_per_sentence < 22:
            return 0.7
        return round(max(0.0, 1.0 - (avg_words_per_sentence - 22) * 0.02), 2)

    def _check_hallucination_risk(
        self,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> float:
        risk_indicators = [
            r"according to (research|studies|experts)\b",
            r"statistics show\b",
            r"studies (show|indicate|suggest)\b",
            r"research (shows|indicates|suggests)\b",
            r"\d+% of\b",
        ]
        content_lower = output.content.lower()
        flags = 0
        for pattern in risk_indicators:
            if re.search(pattern, content_lower):
                flags += 1
        if flags == 0:
            return 1.0
        return round(max(0.0, 1.0 - flags * 0.15), 2)

    def _collect_issues(
        self,
        validation: SectionValidation,
        output: SectionOutput,
        context: SectionContext | None,
    ) -> None:
        if validation.grammar_score < 0.7:
            validation.issues.append("Grammar issues detected")
        if validation.seo_coverage_score < 0.5:
            validation.issues.append("Poor SEO keyword coverage")
        if validation.keyword_usage_score < 0.3:
            validation.issues.append("Primary keyword missing from section")
        if validation.heading_alignment_score < 0.5:
            validation.issues.append("Section content does not align with heading")
        if not validation.word_count_valid:
            target = (context or SectionContext()).target_word_count
            actual = len(output.content.split())
            validation.issues.append(
                f"Word count {actual} outside expected range for target {target}"
            )
        if validation.fact_consistency_score < 0.4:
            validation.issues.append("Low fact consistency with knowledge graph")
        if validation.hallucination_risk_score < 0.6:
            validation.issues.append("Potential hallucination risk detected")

    def _collect_warnings(self, validation: SectionValidation) -> None:
        if validation.seo_coverage_score < 0.8:
            validation.warnings.append("SEO coverage could be improved")
        if validation.keyword_usage_score < 0.7:
            validation.warnings.append("Keyword usage could be improved")
        if validation.readability_score < 0.6:
            validation.warnings.append("Readability could be improved")
        if validation.duplicate_content_score < 0.9:
            validation.warnings.append("Duplicate sentences detected")
