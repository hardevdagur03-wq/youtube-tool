"""E-E-A-T Evaluation — Phase 9.

Evaluates Experience, Expertise, Authoritativeness, Trustworthiness.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, EEATResult


class EEATValidator(BaseValidator):
    """Evaluates Experience, Expertise, Authoritativeness, Trustworthiness."""

    EXPERIENCE_INDICATORS = [
        r'\b(I have|we have|our team|in my experience|I\'ve found|we\'ve built|personally|hands-on|practical)\b',
        r'\b(implemented|built|developed|designed|created|managed|led)\b',
        r'\b(real(-| )world|practical|actual|case study|customer story)\b',
        r'\b(benchmark|tested|measured|evaluated|validated)\b',
    ]

    EXPERTISE_INDICATORS = [
        r'\b(expert|specialist|professional|senior|principal|lead)\b',
        r'\b(certified|qualified|trained|experienced|skilled)\b',
        r'\b(years of experience|background in|deep understanding|domain expertise)\b',
        r'\b(technical|advanced|in-depth|comprehensive|detailed)\b',
    ]

    AUTHORITY_INDICATORS = [
        r'\b(cited|referenced|recognized|acknowledged|featured)\b',
        r'\b(contributed|published|spoke|presented|interviewed)\b',
        r'\b(industry leader|thought leader|authority|influential)\b',
        r'\b(according to|referenced from|based on research)\b',
    ]

    TRUST_INDICATORS = [
        r'\b(transparent|honest|accurate|reliable|verified)\b',
        r'\b(limitation|caveat|drawback|challenge|consideration)\b',
        r'\b(reference|citation|source|study|research|report)\b',
        r'\b(updated|as of|current|latest|recent)\b',
    ]

    def name(self) -> str:
        return "E-E-A-T Evaluation"

    def validate(self, request: BlogReviewRequest) -> EEATResult:
        text = request.content
        if not text:
            return EEATResult(score=0)

        words = text.split()
        word_count = len(words)

        # Count indicators
        exp_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in self.EXPERIENCE_INDICATORS)
        expert_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in self.EXPERTISE_INDICATORS)
        auth_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in self.AUTHORITY_INDICATORS)
        trust_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in self.TRUST_INDICATORS)

        # Normalize by content length
        factor = max(1, word_count / 500)

        experience_score = min(100, (exp_count / factor) * 20)
        expertise_score = min(100, (expert_count / factor) * 20)
        authority_score = min(100, (auth_count / factor) * 20)
        trust_score = min(100, (trust_count / factor) * 20)

        weak_areas: list[str] = []
        recommendations: list[str] = []

        if experience_score < 40:
            weak_areas.append("Limited evidence of practical experience")
            recommendations.append("Add personal experience, case studies, or practical implementation examples")
        if expertise_score < 40:
            weak_areas.append("Insufficient demonstration of expertise")
            recommendations.append("Include technical depth, specialized terminology, and authoritative explanations")
        if authority_score < 40:
            weak_areas.append("Low authoritativeness signals")
            recommendations.append("Cite industry sources, reference research, or include expert opinions")
        if trust_score < 50:
            weak_areas.append("Trustworthiness could be improved")
            recommendations.append("Acknowledge limitations, include citations, and maintain balanced viewpoints")

        # Check for references/citations presence
        has_references = bool(re.search(r'\b(reference|source|citation|bibliography|further reading)\b', text, re.IGNORECASE))
        if not has_references and trust_score < 60:
            recommendations.append("Add a references or sources section to improve trustworthiness")

        # Check for balanced viewpoints
        has_balanced = bool(
            re.search(r'\b(however|on the other hand|alternatively|another approach|some may argue)\b', text, re.IGNORECASE)
        )
        if not has_balanced:
            recommendations.append("Present balanced viewpoints and acknowledge alternative approaches")

        # Overall score (weighted)
        overall = (experience_score * 0.25 + expertise_score * 0.30 +
                   authority_score * 0.20 + trust_score * 0.25)

        return EEATResult(
            score=round(overall, 1),
            experience_score=round(experience_score, 1),
            expertise_score=round(expertise_score, 1),
            authoritativeness_score=round(authority_score, 1),
            trustworthiness_score=round(trust_score, 1),
            weak_areas=weak_areas,
            recommendations=recommendations,
        )
