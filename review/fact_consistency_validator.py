"""Fact Consistency Review — Phase 9.

Validates number usage, dates, terminology, and detects contradictions.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, FactConsistencyResult


class FactConsistencyValidator(BaseValidator):
    """Detects internal contradictions and inconsistencies."""

    def name(self) -> str:
        return "Fact Consistency Review"

    def validate(self, request: BlogReviewRequest) -> FactConsistencyResult:
        text = request.content
        if not text:
            return FactConsistencyResult(score=100.0)

        conflicting: list[str] = []
        timeline_issues: list[str] = []
        number_issues: list[str] = []

        # Check for contradictory statements
        contradiction_pairs = [
            (r'\bmust\b', r'\b(optional|not required|unnecessary)\b'),
            (r'\balways\b', r'\b(never|sometimes|occasionally)\b'),
            (r'\ball\b', r'\b(none|no)\b'),
            (r'\bincreases?\b', r'\b(decreases?|reduces?)\b'),
            (r'\b(cheaper|less expensive|lower cost)\b', r'\b(more expensive|costly|expensive)\b'),
            (r'\b(easier|simpler)\b', r'\b(harder|more difficult|complex)\b'),
            (r'\bfast(er)?\b', r'\b(slow(er)?)\b'),
        ]

        sentences = re.split(r'(?<=[.!?])\s+', text)
        for i, s1 in enumerate(sentences):
            for j, s2 in enumerate(sentences):
                if i >= j:
                    continue
                s1_lower = s1.lower()
                s2_lower = s2.lower()
                for pos_pattern, neg_pattern in contradiction_pairs:
                    has_pos1 = bool(re.search(pos_pattern, s1_lower))
                    has_neg1 = bool(re.search(neg_pattern, s1_lower))
                    has_pos2 = bool(re.search(pos_pattern, s2_lower))
                    has_neg2 = bool(re.search(neg_pattern, s2_lower))
                    if (has_pos1 and has_neg2) or (has_neg1 and has_pos2):
                        conflicting.append(
                            f"Possible contradiction between sentences {i + 1} and {j + 1}: "
                            f"'{s1[:80]}...' vs '{s2[:80]}...'"
                        )

        # Check number inconsistencies within reasonable range
        numbers = []
        for match in re.finditer(r'\b(\d+)\b', text):
            num = int(match.group(1))
            if 1 <= num <= 100000:
                numbers.append((num, match.start()))

        # Check for same number used in different contexts that seem wrong
        number_counts = {}
        for num, pos in numbers:
            context = text[max(0, pos - 30):pos + 30]
            if num not in number_counts:
                number_counts[num] = []
            number_counts[num].append(context)

        # Check for contradictory percentages
        percentages = re.findall(r'(\d+)\s*%', text)
        if len(percentages) >= 2:
            for i, p1 in enumerate(percentages):
                for j, p2 in enumerate(percentages):
                    if i < j and p1 == p2:
                        idx1 = text.index(f"{p1}%")
                        idx2 = text.index(f"{p2}%", idx1 + 1)
                        ctx1 = text[max(0, idx1 - 40):idx1 + 40]
                        ctx2 = text[max(0, idx2 - 40):idx2 + 40]
                        # Only flag if contexts are different (same % in different contexts could be fine)
                        if abs(idx1 - idx2) > 200:
                            number_issues.append(
                                f"Same percentage '{p1}%' used in different contexts — verify consistency: "
                                f"'{ctx1.strip()[:60]}' and '{ctx2.strip()[:60]}'"
                            )

        # Check timeline/date consistency
        years = list(set(int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', text) if 1900 <= int(y) <= 2100))
        if len(years) >= 2:
            # For tutorial content, check if years are consistent
            if max(years) > 2024 and min(years) < 2020:
                timeline_issues.append(
                    f"Timeline spans {min(years)}-{max(years)}. "
                    "Verify that all dates are current and consistent with the topic."
                )

        # Calculate score
        penalty = len(conflicting) * 10 + len(timeline_issues) * 8 + len(number_issues) * 5
        score = max(0, min(100, 100 - penalty))

        return FactConsistencyResult(
            score=round(score, 1),
            conflicting_statements=conflicting[:10],
            timeline_inconsistencies=timeline_issues[:5],
            number_inconsistencies=number_issues[:5],
        )
