"""Passive Voice Detector — standalone passive voice and weak sentence detection."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest
from review.review_models_ext import GrammarReport


PASSIVE_PATTERNS = [
    (r'\b(am|is|are)\s+\w+ed\b', "present simple passive"),
    (r'\b(was|were)\s+\w+ed\b', "past simple passive"),
    (r'\b(has|have)\s+been\s+\w+ed\b', "present perfect passive"),
    (r'\bhad\s+been\s+\w+ed\b', "past perfect passive"),
    (r'\b(will|shall|would|should|can|could|may|might|must)\s+be\s+\w+ed\b', "modal passive"),
    (r'\b(is|are|was|were)\s+being\s+\w+ed\b', "continuous passive"),
    (r'\b(has|have|had)\s+been\s+being\s+\w+ed\b', "perfect continuous passive"),
]

WEAK_VERB_PATTERNS = [
    r'\bthere\s+(is|are|was|were|has|have|had)\b',
    r'\bit\s+(is|was)\s+\w+\s+(that|to)\b',
    r'\b(this|that)\s+(is|was)\s+\w+\s+(that|to)\b',
    r'\bthe\s+\w+\s+of\s+\w+\s+(is|was|are|were)\b',
]

WEAK_ADVERB_PATTERNS = [
    r'\bvery\b',
    r'\breally\b',
    r'\bquite\b',
    r'\bbasically\b',
    r'\bactually\b',
    r'\bsimply\b',
    r'\bjust\b(?!\s+like\b)',
    r'\bso\b',
    r'\breally\b',
]

NOMINALIZATION_PATTERNS = [
    r'\w+tion\b',
    r'\w+ment\b',
    r'\w+ance\b',
    r'\w+ence\b',
    r'\w+ity\b',
]


class PassiveVoiceDetector(BaseValidator):
    """Detects passive voice, weak verbs, weak adverbs, and nominalizations."""

    def name(self) -> str:
        return "Passive Voice Detection"

    def validate(self, request: BlogReviewRequest) -> GrammarReport:
        text = request.content
        if not text:
            return GrammarReport(score=100.0)

        sentences = self._split_sentences(text)
        total_sentences = len(sentences) if sentences else 1

        issues: list[dict] = []
        passive_count = 0
        weak_verb_count = 0
        weak_adverb_count = 0
        nominalization_count = 0

        # Check each sentence for passive voice
        for i, sent in enumerate(sentences):
            sent_lower = sent.lower().strip()

            for pattern, pattern_name in PASSIVE_PATTERNS:
                if re.search(pattern, sent_lower):
                    passive_count += 1
                    issues.append({
                        "description": f"Passive voice ({pattern_name})",
                        "location": f"Sentence {i + 1}",
                        "text": sent[:100],
                        "fix": "Consider rewriting in active voice",
                    })
                    break

        # Check for weak verb constructions
        for pattern in WEAK_VERB_PATTERNS:
            matches = re.findall(pattern, text.lower())
            weak_verb_count += len(matches)
            for match in re.finditer(pattern, text.lower()):
                issues.append({
                    "description": f"Weak verb construction: '{match.group().strip()}'",
                    "location": "General content",
                    "text": text[max(0, match.start()-20):match.end()+20].strip()[:100],
                    "fix": "Replace with a stronger verb",
                })

        # Check for weak adverbs
        for pattern in WEAK_ADVERB_PATTERNS:
            matches = re.findall(pattern, text.lower())
            weak_adverb_count += len(matches)
            for match in re.finditer(pattern, text.lower()):
                issues.append({
                    "description": f"Weak adverb: '{match.group().strip()}'",
                    "location": "General content",
                    "text": text[max(0, match.start()-20):match.end()+20].strip()[:100],
                    "fix": "Use more precise language instead of weak adverbs",
                })

        # Check for nominalizations
        for pattern in NOMINALIZATION_PATTERNS:
            matches = re.findall(pattern, text.lower())
            nominalization_count += len(matches)

        # Score calculation
        passive_ratio = passive_count / total_sentences if total_sentences else 0
        score = 100.0

        if passive_ratio > 0.4:
            score -= 20
        elif passive_ratio > 0.3:
            score -= 15
        elif passive_ratio > 0.2:
            score -= 10
        elif passive_ratio > 0.1:
            score -= 5

        if weak_verb_count > total_sentences * 0.1:
            score -= 10

        if weak_adverb_count > total_sentences * 0.15:
            score -= 5

        score = max(0, min(100, score))

        return GrammarReport(
            score=round(score, 1),
            passive_voice_sentences=passive_count,
            issues=[{
                "description": i["description"],
                "location": i["location"],
                "severity": "medium",
                "why_it_matters": "Excessive passive voice and weak constructions reduce writing impact",
                "recommended_fix": i["fix"],
            } for i in issues[:20]],
            grammar_errors=weak_verb_count,
            run_on_sentences=weak_adverb_count,
            sentence_fragments=nominalization_count,
        )

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
