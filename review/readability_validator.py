"""Readability Analysis — Phase 9.

Calculates Flesch Reading Ease, Flesch-Kincaid Grade, sentence/paragraph stats.
"""

from __future__ import annotations
import re
import math
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, ReadabilityResult


class ReadabilityValidator(BaseValidator):
    """Analyzes readability metrics."""

    TRANSITION_WORDS = {
        "addition": {"also", "and", "besides", "furthermore", "moreover", "additionally", "plus", "similarly"},
        "contrast": {"but", "however", "although", "though", "yet", "still", "nevertheless", "nonetheless", "on the other hand", "conversely", "whereas", "while"},
        "cause": {"because", "since", "as", "due to", "therefore", "thus", "consequently", "as a result", "hence", "accordingly"},
        "sequence": {"first", "second", "third", "next", "then", "finally", "lastly", "subsequently", "previously", "meanwhile", "afterward", "before"},
        "emphasis": {"indeed", "certainly", "surely", "importantly", "notably", "significantly", "especially", "particularly", "above all"},
        "example": {"for example", "for instance", "such as", "including", "like", "namely", "specifically", "to illustrate"},
        "conclusion": {"in conclusion", "to conclude", "in summary", "overall", "ultimately", "in short", "in brief", "to summarize"},
    }

    def name(self) -> str:
        return "Readability Analysis"

    def validate(self, request: BlogReviewRequest) -> ReadabilityResult:
        text = request.content
        if not text:
            return ReadabilityResult(score=100.0)

        sentences = self._split_sentences(text)
        paragraphs = self._split_paragraphs(text)

        if not sentences:
            return ReadabilityResult(score=100.0)

        words = text.split()
        word_count = len(words)
        sentence_count = len(sentences)
        paragraph_count = len(paragraphs) if paragraphs else 1

        # Average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count else 0

        # Average paragraph length (in sentences)
        total_sentences_in_paras = sum(len(self._split_sentences(p)) for p in paragraphs) if paragraphs else sentence_count
        avg_paragraph_length = total_sentences_in_paras / paragraph_count if paragraph_count else 0

        # Syllable count (approximate)
        total_syllables = sum(self._count_syllables(w) for w in words)

        # Complex words (3+ syllables)
        complex_words = sum(1 for w in words if self._count_syllables(w) >= 3)
        complex_ratio = complex_words / word_count if word_count else 0

        # Flesch Reading Ease
        if sentence_count > 0 and word_count > 0:
            flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (total_syllables / word_count)
        else:
            flesch = 100.0

        # Flesch-Kincaid Grade
        if sentence_count > 0 and word_count > 0:
            fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (total_syllables / word_count) - 15.59
        else:
            fk_grade = 0.0

        flesch = max(0, min(100, flesch))
        fk_grade = max(0, fk_grade)

        # Complex sentence ratio
        complex_sentences = sum(1 for s in sentences if len(s.split()) > 25)
        complex_sentence_ratio = complex_sentences / sentence_count if sentence_count else 0

        # Transition word usage
        transition_count = self._count_transitions(text)
        transition_ratio = transition_count / sentence_count if sentence_count else 0

        # Passive voice estimate (via was/were + past participle heuristic)
        passive_count = len(re.findall(r'\b(was|were)\s+\w+ed\b', text, re.IGNORECASE))
        passive_percentage = (passive_count / sentence_count * 100) if sentence_count else 0

        # Reading time
        reading_time = max(1, word_count / 200)

        # Difficulty level
        if flesch >= 90:
            difficulty = "Very Easy"
        elif flesch >= 80:
            difficulty = "Easy"
        elif flesch >= 70:
            difficulty = "Fairly Easy"
        elif flesch >= 60:
            difficulty = "Standard"
        elif flesch >= 50:
            difficulty = "Fairly Difficult"
        elif flesch >= 30:
            difficulty = "Difficult"
        else:
            difficulty = "Very Difficult"

        # Score calculation
        readability_score = flesch
        if fk_grade > 12:
            readability_score -= (fk_grade - 12) * 2
        if complex_ratio > 0.15:
            readability_score -= (complex_ratio - 0.15) * 50
        if transition_ratio < 0.05:
            readability_score -= 5
        readability_score = max(0, min(100, readability_score))

        suggestions = []
        if avg_sentence_length > 20:
            suggestions.append(f"Average sentence length is {avg_sentence_length:.0f} words. Aim for 15-18 words for better readability.")
        if fk_grade > 10:
            suggestions.append(f"Flesch-Kincaid Grade {fk_grade:.1f} may be too high for general audiences. Consider simplifying language.")
        if complex_ratio > 0.15:
            suggestions.append(f"{complex_ratio * 100:.0f}% of words are complex (3+ syllables). Consider using simpler alternatives.")
        if transition_ratio < 0.05:
            suggestions.append("Low transition word usage. Add transitions to improve flow between ideas.")
        if passive_percentage > 20:
            suggestions.append(f"{passive_percentage:.0f}% of sentences use passive voice. Reduce to under 15% for more direct writing.")

        return ReadabilityResult(
            score=round(readability_score, 1),
            flesch_reading_ease=round(flesch, 1),
            flesch_kincaid_grade=round(fk_grade, 1),
            avg_sentence_length=round(avg_sentence_length, 1),
            avg_paragraph_length=round(avg_paragraph_length, 1),
            complex_sentence_ratio=round(complex_sentence_ratio, 2),
            transition_word_ratio=round(transition_ratio, 2),
            passive_voice_percentage=round(passive_percentage, 1),
            reading_time_minutes=round(reading_time, 1),
            difficulty_level=difficulty,
            improvement_suggestions=suggestions,
        )

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    def _split_paragraphs(self, text: str) -> list[str]:
        return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    def _count_syllables(self, word: str) -> int:
        word = word.lower().strip('.,!?;:()[]{}""\'')
        if not word:
            return 0
        if len(word) <= 3:
            return 1
        vowels = 'aeiouy'
        count = 0
        prev_vowel = False
        for ch in word:
            is_vowel = ch in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e'):
            count = max(1, count - 1)
        if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
            count += 1
        return max(1, count)

    def _count_transitions(self, text: str) -> int:
        text_lower = text.lower()
        count = 0
        for category, words in self.TRANSITION_WORDS.items():
            for word in words:
                count += len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
        return count
