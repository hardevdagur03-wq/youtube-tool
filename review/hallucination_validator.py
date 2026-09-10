"""Hallucination Risk Detection — Phase 9.

Flags unsupported claims, unverifiable statistics, fabricated facts.
Uses heuristic pattern matching to identify risky statements.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, HallucinationResult, HallucinationRisk, ReviewIssue, IssueSeverity


class HallucinationValidator(BaseValidator):
    """Detects statements at risk of hallucination."""

    UNSUPPORTED_CLAIM_PATTERNS = [
        r'(studies show|research shows|studies have shown)\s+(?!that\s+(a|an|the|many|most|some))',
        r'(according to research|according to studies)\s+(?!by|from|published|conducted)',
        r'(experts say|experts agree|experts believe)\s+(?!that\s+(a|an|the|many|most|some|this|it))',
        r'(it is widely known|it is well known|it is common knowledge)\s+(?!that\s+(a|an|the))',
        r'(as everyone knows|as we all know)\s',
    ]

    FABRICATED_REFERENCE_PATTERNS = [
        r'(according to a \d{4} study)',
        r'(a \d{4} (study|survey|report) (by|from|published in))',
        r'(research from \d{4})',
        r'(published in \d{4})',
    ]

    VAGUE_QUANTIFIERS = [
        r'\b(many|most|some|several|various|numerous|countless|multiple)\s+(studies|research|experts|reports)\b',
        r'\b(a lot of|a large number of|a significant number of)\s+(studies|research)\b',
    ]

    def name(self) -> str:
        return "Hallucination Risk Detection"

    def validate(self, request: BlogReviewRequest) -> HallucinationResult:
        text = request.content
        if not text:
            return HallucinationResult(score=100.0)

        flagged: list[dict] = []
        unsupported_count = 0
        unverifiable_stats = 0
        fabricated_refs = 0

        # Check unsupported claim patterns
        for pattern in self.UNSUPPORTED_CLAIM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context = self._get_context(text, match.start())
                unsupported_count += 1
                flagged.append({
                    "statement": match.group(0)[:100],
                    "context": context[:150],
                    "risk": "medium",
                    "reason": "Unsupported claim — no source provided",
                    "position": match.start(),
                })

        # Check fabricated references
        for pattern in self.FABRICATED_REFERENCE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context = self._get_context(text, match.start())
                fabricated_refs += 1
                flagged.append({
                    "statement": match.group(0)[:100],
                    "context": context[:150],
                    "risk": "high",
                    "reason": "Potentially fabricated reference — verify source exists",
                    "position": match.start(),
                })

        # Check vague quantifiers
        for pattern in self.VAGUE_QUANTIFIERS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                unverifiable_stats += 1
                context = self._get_context(text, match.start())
                flagged.append({
                    "statement": match.group(0)[:100],
                    "context": context[:150],
                    "risk": "medium",
                    "reason": "Vague claim without specific evidence or citation",
                    "position": match.start(),
                })

        # Check specific statistics without sources
        stat_pattern = r'(\d+[%]|\d+ out of \d+|\d+ \w+ percent|\d+[–-]fold)'
        for match in re.finditer(stat_pattern, text):
            start = max(0, match.start() - 50)
            before = text[start:match.start()]
            after = text[match.end():match.end() + 80]
            context = before + match.group(0) + after

            # Check if source is mentioned nearby
            has_source = bool(re.search(r'(according to|source:|from|per|based on|by|reported)', before[-80:], re.IGNORECASE))
            if not has_source:
                unverifiable_stats += 1
                flagged.append({
                    "statement": match.group(0)[:100],
                    "context": context[:150],
                    "risk": "medium",
                    "reason": "Unverifiable statistic — no source cited",
                    "position": match.start(),
                })

        # Check for facts with dates that seem suspicious
        date_exact_pattern = r'(in \d{4}|as of \d{4})'
        for match in re.finditer(date_exact_pattern, text):
            context = self._get_context(text, match.start())
            # Check if it's about a current/ongoing topic
            after = text[match.end():match.end() + 100]
            if not re.search(r'(according to|source|published|released|announced)', after, re.IGNORECASE):
                flagged.append({
                    "statement": f"Date claim: '{match.group(0)}'",
                    "context": context[:150],
                    "risk": "low",
                    "reason": "Verify the date is correct and corresponds to the claim",
                    "position": match.start(),
                })

        # Determine overall risk level
        total_flagged = len(flagged)
        high_risk_count = sum(1 for f in flagged if f["risk"] == "high")

        if high_risk_count > 2 or total_flagged > 8:
            risk_level = HallucinationRisk.HIGH
        elif total_flagged > 3:
            risk_level = HallucinationRisk.MEDIUM
        else:
            risk_level = HallucinationRisk.LOW

        # Calculate score
        penalty = min(total_flagged * 5 + high_risk_count * 10, 80)
        score = max(0, 100 - penalty)

        recs = []
        if high_risk_count > 0:
            recs.append(f"Verify {high_risk_count} high-risk statements with reliable sources")
        if unsupported_count > 0:
            recs.append(f"Add citations for {unsupported_count} unsupported claims")
        if unverifiable_stats > 0:
            recs.append(f"Provide sources for {unverifiable_stats} statistics")
        if total_flagged > 0:
            recs.append("Review all flagged statements and either add sources or remove unverifiable claims")

        return HallucinationResult(
            score=round(score, 1),
            risk_level=risk_level,
            flagged_statements=flagged[:20],
            unsupported_claims=unsupported_count,
            unverifiable_statistics=unverifiable_stats,
            fabricated_references=fabricated_refs,
            recommendations=recs,
        )

    def _get_context(self, text: str, position: int, window: int = 100) -> str:
        start = max(0, position - window)
        end = min(len(text), position + window)
        ctx = text[start:end]
        if start > 0:
            ctx = "..." + ctx
        if end < len(text):
            ctx = ctx + "..."
        return ctx
