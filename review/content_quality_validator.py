"""Content Quality Review — Phase 9.

Evaluates clarity, logical flow, actionability, originality, engagement, tone.
"""

from __future__ import annotations
import re
from collections import Counter
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, ContentQualityResult, ReviewIssue, IssueSeverity


class ContentQualityValidator(BaseValidator):
    """Evaluates overall content quality."""

    def name(self) -> str:
        return "Content Quality Review"

    def validate(self, request: BlogReviewRequest) -> ContentQualityResult:
        text = request.content
        if not text:
            return ContentQualityResult(score=0)

        words = text.split()
        word_count = len(words)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentence_count = len(sentences)

        issues: list[ReviewIssue] = []

        # Clarity score
        clarity = 100.0
        # Penalty for very long sentences
        long_sentences = sum(1 for s in sentences if len(s.split()) > 30)
        if long_sentences > sentence_count * 0.1:
            clarity -= (long_sentences / sentence_count) * 20
            issues.append(ReviewIssue(
                description=f"{long_sentences} sentences exceed 30 words ({long_sentences * 100 // sentence_count}%)",
                location="General content",
                severity=IssueSeverity.MEDIUM,
                why_it_matters="Long sentences reduce clarity and reader comprehension.",
                recommended_fix="Break long sentences into shorter ones (aim for 15-20 words).",
            ))

        # Penalty for jargon without explanation
        jargon = {"synergy", "leverage", "paradigm", "ecosystem", "holistic", "optimize",
                  "utilize", "facilitate", "implement", "streamline", "actionable"}
        jargon_count = sum(1 for w in words if w.lower().strip('.,!?;:') in jargon)
        if jargon_count > 3:
            clarity -= min(jargon_count * 3, 20)
            issues.append(ReviewIssue(
                description=f"Excessive jargon ({jargon_count} instances). Terms like '{', '.join(list(jargon)[:3])}' overused.",
                location="General content",
                severity=IssueSeverity.LOW,
                why_it_matters="Jargon can alienate readers and reduce clarity.",
                recommended_fix="Replace jargon with plain language where possible, or explain terms on first use.",
            ))
        clarity = max(0, clarity)

        # Logical flow score
        flow = 100.0
        # Transition word density
        transitions = {"however", "therefore", "furthermore", "moreover", "nevertheless",
                       "consequently", "additionally", "meanwhile", "subsequently", "hence",
                       "thus", "accordingly", "besides", "indeed", "notably", "specifically"}
        transition_count = sum(1 for w in words if w.lower().strip('.,!?;:') in transitions)
        expected_transitions = max(2, sentence_count * 0.05)
        if transition_count < expected_transitions:
            flow -= 15
            issues.append(ReviewIssue(
                description=f"Low transition word usage ({transition_count} in {sentence_count} sentences). Expected ~{int(expected_transitions)}.",
                location="General content",
                severity=IssueSeverity.MEDIUM,
                why_it_matters="Transitions guide readers through arguments and improve flow.",
                recommended_fix=f"Add transition words like 'however', 'furthermore', 'consequently' to improve logical flow.",
            ))
        flow = max(0, flow)

        # Actionability score
        actionable = 100.0
        action_phrases = {"you can", "you should", "you need to", "try", "use", "implement",
                          "apply", "follow", "start", "create", "build", "set up"}
        action_count = sum(1 for phrase in action_phrases if phrase in text.lower())
        if action_count < 3 and word_count > 300:
            actionable -= 20
            issues.append(ReviewIssue(
                description="Limited actionable guidance for readers",
                location="General content",
                severity=IssueSeverity.MEDIUM,
                why_it_matters="Readers expect practical, actionable advice they can implement.",
                recommended_fix="Add concrete steps, recommendations, or implementation guidance.",
            ))
        actionable = max(0, actionable)

        # Originality score (based on lexical diversity)
        unique_words = set(w.lower().strip('.,!?;:()[]{}""\'') for w in words)
        lexical_diversity = len(unique_words) / word_count if word_count else 0
        originality = min(100, lexical_diversity * 150)
        if lexical_diversity < 0.4:
            issues.append(ReviewIssue(
                description=f"Low lexical diversity ({lexical_diversity:.1%}). Repetitive word choice limits engagement.",
                location="General content",
                severity=IssueSeverity.MEDIUM,
                why_it_matters="Low vocabulary variety makes content feel repetitive and reduces reader engagement.",
                recommended_fix="Use synonyms and varied vocabulary. Replace frequently repeated words with alternatives.",
            ))

        # Engagement score
        engagement = 100.0
        # Questions engage readers
        question_count = text.count('?')
        if question_count < 2 and word_count > 400:
            engagement -= 10
            issues.append(ReviewIssue(
                description="No rhetorical or engaging questions found",
                location="General content",
                severity=IssueSeverity.LOW,
                why_it_matters="Questions engage readers and maintain interest.",
                recommended_fix="Add rhetorical questions or thought-provoking queries to engage readers.",
            ))

        # Direct address
        if "you" not in text.lower().split()[:100]:
            engagement -= 10
        engagement = max(0, engagement)

        # Tone consistency
        tone = 100.0
        # Check for inconsistent formality
        informal_markers = {"gonna", "wanna", "ain't", "y'all", "dunno", "kinda", "sorta", "cuz"}
        informal_count = sum(1 for m in informal_markers if m in text.lower().split())
        if informal_count > 2:
            tone -= informal_count * 5
            issues.append(ReviewIssue(
                description=f"Inconsistent tone — {informal_count} informal expressions found in otherwise formal content",
                location="General content",
                severity=IssueSeverity.LOW,
                why_it_matters="Mixed formality levels can confuse readers about the content's authority.",
                recommended_fix="Maintain consistent tone throughout. Replace informal expressions with standard language.",
            ))
        tone = max(0, tone)

        # Overall
        overall = (clarity * 0.25 + flow * 0.20 + actionable * 0.20 +
                   originality * 0.15 + engagement * 0.10 + tone * 0.10)

        return ContentQualityResult(
            score=round(overall, 1),
            clarity_score=round(clarity, 1),
            logical_flow_score=round(flow, 1),
            actionability_score=round(actionable, 1),
            originality_score=round(originality, 1),
            engagement_score=round(engagement, 1),
            tone_consistency_score=round(tone, 1),
            issues=issues,
        )
