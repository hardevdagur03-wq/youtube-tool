"""AI Content Detection Risk — Phase 9.

Estimates AI-likeness by analyzing repetitive phrasing, sentence structure
predictability, lexical diversity, and generic wording patterns.
"""

from __future__ import annotations
import re
from collections import Counter
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, AIDetectionResult


class AIDetectionValidator(BaseValidator):
    """Detects AI-like writing patterns."""

    AI_PATTERNS = {
        "generic_openers": {
            "in today's digital world", "in today's world", "in the modern world",
            "in the digital age", "in recent years", "in today's fast-paced",
            "when it comes to", "in the realm of", "in the world of",
            "it is important to", "it is crucial to", "it is essential to",
            "it is worth noting", "it is no secret that",
        },
        "ai_transitions": {
            "let's dive in", "dive into", "let's explore", "let's take a look",
            "take a closer look", "let's examine", "let's consider",
            "when we look at", "if we look at", "as we can see",
            "it's worth noting that", "it's important to note that",
            "it should be noted that", "it is worth mentioning that",
        },
        "hedging_language": {
            "arguably", "essentially", "basically", "practically",
            "virtually", "relatively", "comparatively", "fairly",
            "quite", "somewhat", "rather", "slightly", "a bit",
        },
        "ai_conclusions": {
            "in conclusion", "to conclude", "in summary", "to summarize",
            "overall,", "all in all,", "in the end,", "ultimately,",
        },
    }

    def name(self) -> str:
        return "AI Detection Risk"

    def validate(self, request: BlogReviewRequest) -> AIDetectionResult:
        text = request.content
        if not text:
            return AIDetectionResult(score=100.0, risk_level="low")

        words = text.split()
        word_count = len(words)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentence_count = len(sentences) if sentences else 1

        # Count AI patterns
        pattern_counts: Counter = Counter()
        for category, patterns in self.AI_PATTERNS.items():
            for pattern in patterns:
                count = len(re.findall(re.escape(pattern), text.lower()))
                if count > 0:
                    pattern_counts[category] += count

        total_ai_patterns = sum(pattern_counts.values())

        # Repetitive sentence starts
        sentence_starts: list[str] = []
        for sent in sentences:
            first_words = sent.split()[:3]
            if first_words:
                sentence_starts.append(' '.join(first_words).lower().rstrip('('))

        start_counts = Counter(sentence_starts)
        repetitive_starts = [start for start, count in start_counts.most_common(5) if count > 2]

        # Lexical diversity
        unique_words = set(w.lower().strip('.,!?;:()[]{}""\'') for w in words)
        lexical_diversity = len(unique_words) / word_count if word_count else 0

        # Sentence length variety
        sentence_lengths = [len(s.split()) for s in sentences]
        if sentence_lengths:
            avg_len = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((l - avg_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            std_dev = variance ** 0.5
        else:
            std_dev = 0

        # Low variance in sentence length = AI-like
        sentence_variety = min(100, std_dev * 10)

        # Detect repeated phrases (3+ words)
        phrase_counts: Counter = Counter()
        for i in range(len(words) - 3):
            phrase = ' '.join(words[i:i + 3]).lower().strip('.,!?;:')
            if len(phrase) > 10:
                phrase_counts[phrase] += 1

        repeated_phrases = [phrase for phrase, count in phrase_counts.most_common(10) if count > 1]

        # Generic word analysis
        generic_words = {"very", "really", "quite", "actually", "basically", "essentially",
                         "importantly", "significantly", "interestingly", "notably",
                         "specifically", "particularly", "remarkably", "incredibly"}
        generic_count = sum(1 for w in words if w.lower().strip('.,!?;:') in generic_words)
        generic_density = generic_count / word_count if word_count else 0

        # Score calculation
        base_score = 100.0
        base_score -= total_ai_patterns * 3
        base_score -= len(repetitive_starts) * 5
        base_score -= max(0, (0.5 - lexical_diversity) * 50)
        if sentence_variety < 30:
            base_score -= (30 - sentence_variety) * 0.5
        if generic_density > 0.02:
            base_score -= (generic_density - 0.02) * 200
        base_score -= len(repeated_phrases) * 2
        score = max(0, min(100, base_score))

        # Risk level
        score_threshold = score
        if score_threshold < 40:
            risk = "high"
        elif score_threshold < 65:
            risk = "medium"
        else:
            risk = "low"

        # Recommendations
        recommendations: list[str] = []
        if total_ai_patterns > 3:
            recommendations.append(f"Replace {total_ai_patterns} AI-like transitional phrases with varied, natural language")
        if repetitive_starts:
            recommendations.append(f"Vary sentence openings — '{repetitive_starts[0]}' appears {start_counts[repetitive_starts[0]]} times")
        if lexical_diversity < 0.45:
            recommendations.append("Increase lexical diversity by using synonyms and more varied vocabulary")
        if sentence_variety < 30:
            recommendations.append("Mix short and long sentences to create more natural rhythm")
        if generic_density > 0.02:
            recommendations.append(f"Reduce generic intensifiers ({generic_count} found) for more precise language")
        if repeated_phrases:
            recommendations.append(f"Rewrite {len(repeated_phrases)} repeated phrases to add variety")

        return AIDetectionResult(
            score=round(score, 1),
            risk_level=risk,
            repetitive_phrases=repeated_phrases[:10],
            lexical_diversity_score=round(lexical_diversity, 3),
            avg_sentence_length_variety=round(sentence_variety, 1),
            recommendations=recommendations,
        )
