"""Review Engine — Phase 9 orchestrator.

Runs all validators, aggregates results, and generates a QualityReport.
"""

from __future__ import annotations
import logging
import time
from typing import Any

from models.blog_review import (
    BlogReviewRequest, BlogReviewResponse, QualityReport, Scorecard, CategoryScore,
    PublishDecision, ReviewIssue, IssueSeverity,
)
from review.base import BaseValidator
from review.grammar_validator import GrammarValidator
from review.readability_validator import ReadabilityValidator
from review.seo_validator import SEOValidator
from review.duplicate_validator import DuplicateValidator
from review.heading_validator import HeadingValidator
from review.completeness_validator import CompletenessValidator
from review.hallucination_validator import HallucinationValidator
from review.fact_consistency_validator import FactConsistencyValidator
from review.eeat_validator import EEATValidator
from review.linking_validator import InternalLinkingValidator, ExternalLinkingValidator
from review.accessibility_validator import AccessibilityValidator
from review.content_quality_validator import ContentQualityValidator
from review.ai_detection_validator import AIDetectionValidator
from review.report import ReportGenerator

logger = logging.getLogger(__name__)

# Weight configuration for overall scoring
CATEGORY_WEIGHTS = {
    "grammar": 0.15,
    "readability": 0.15,
    "seo": 0.20,
    "content_quality": 0.20,
    "hallucination_risk": 0.10,
    "eeat": 0.10,
    "structure": 0.05,
    "accessibility": 0.05,
}

SCORE_THRESHOLDS = [
    (95, PublishDecision.ENTERPRISE_READY, "Enterprise Ready"),
    (90, PublishDecision.PUBLISH_READY, "Publish Ready"),
    (80, PublishDecision.MINOR_REVISIONS, "Minor Revisions Needed"),
    (70, PublishDecision.MAJOR_REVISIONS, "Major Revisions Needed"),
]


class ReviewEngine:
    """Orchestrates the full review pipeline."""

    def __init__(self, validators: list[BaseValidator] | None = None):
        self._validators = validators or self._default_validators()
        self._report_gen = ReportGenerator()

    def _default_validators(self) -> list[BaseValidator]:
        return [
            GrammarValidator(),
            ReadabilityValidator(),
            SEOValidator(),
            DuplicateValidator(),
            HeadingValidator(),
            CompletenessValidator(),
            HallucinationValidator(),
            FactConsistencyValidator(),
            EEATValidator(),
            InternalLinkingValidator(),
            ExternalLinkingValidator(),
            AccessibilityValidator(),
            ContentQualityValidator(),
            AIDetectionValidator(),
        ]

    def review(self, request: BlogReviewRequest) -> BlogReviewResponse:
        start = time.time()
        logger.info("[ReviewEngine] Starting review pipeline with %d validators", len(self._validators))

        # Run all validators
        results: dict[str, Any] = {}
        timings: dict[str, float] = {}
        errors: list[str] = []

        for validator in self._validators:
            try:
                result, elapsed = validator.execute(request)
                key = validator.name().lower().replace(" ", "_").replace("-", "_")
                results[key] = result
                timings[key] = elapsed
            except Exception as exc:
                logger.exception("[ReviewEngine] Validator '%s' failed: %s", validator.name(), exc)
                errors.append(f"{validator.name()}: {exc}")

        # Build quality report
        report = self._build_report(request, results, timings, errors, start)
        elapsed = round((time.time() - start) * 1000, 1)
        report.execution_time_ms = elapsed

        logger.info(
            "[ReviewEngine] Review complete: score=%.1f, decision=%s, %.1fms",
            report.overall_score, report.publish_decision.value, elapsed,
        )

        return BlogReviewResponse(success=len(errors) < len(self._validators), report=report)

    def _build_report(
        self,
        request: BlogReviewRequest,
        results: dict[str, Any],
        timings: dict[str, float],
        errors: list[str],
        start: float,
    ) -> QualityReport:
        report = QualityReport()
        report.blog_title = request.blog_title
        report.word_count = len(request.content.split()) if request.content else 0
        report.estimated_reading_time = f"{max(1, report.word_count // 200)} min"

        # Map results to report fields
        field_map = {
            "grammar": "grammar",
            "readability_analysis": "readability",
            "seo_audit": "seo",
            "duplicate_content_detection": "duplicate",
            "heading_validation": "headings",
            "content_completeness": "completeness",
            "hallucination_risk_detection": "hallucination",
            "fact_consistency_review": "fact_consistency",
            "e-e-a-t_evaluation": "eeat",
            "internal_linking_audit": "internal_linking",
            "external_linking_audit": "external_linking",
            "accessibility_review": "accessibility",
            "content_quality_review": "content_quality",
            "ai_detection_risk": "ai_detection",
        }

        for result_key, report_field in field_map.items():
            if result_key in results:
                setattr(report, report_field, results[result_key])

        # Build scorecard
        category_scores: list[tuple[str, float, float]] = []
        weights = CATEGORY_WEIGHTS

        # Grammar
        if hasattr(report.grammar, 'score'):
            category_scores.append(("Grammar", report.grammar.score, weights["grammar"]))

        # Readability
        if hasattr(report.readability, 'score'):
            category_scores.append(("Readability", report.readability.score, weights["readability"]))

        # SEO
        if hasattr(report.seo, 'score'):
            category_scores.append(("SEO", report.seo.score, weights["seo"]))

        # Structure (headings + duplicate + completeness avg)
        struct_scores = []
        if hasattr(report.headings, 'score'):
            struct_scores.append(report.headings.score)
        if hasattr(report.duplicate, 'score'):
            struct_scores.append(report.duplicate.score)
        if hasattr(report.completeness, 'score'):
            struct_scores.append(report.completeness.score)
        struct_avg = sum(struct_scores) / len(struct_scores) if struct_scores else 0
        category_scores.append(("Structure", struct_avg, weights["structure"]))

        # EEAT
        if hasattr(report.eeat, 'score'):
            category_scores.append(("EEAT", report.eeat.score, weights["eeat"]))

        # Content Quality
        if hasattr(report.content_quality, 'score'):
            category_scores.append(("Content Quality", report.content_quality.score, weights["content_quality"]))

        # Accessibility
        if hasattr(report.accessibility, 'score'):
            category_scores.append(("Accessibility", report.accessibility.score, weights["accessibility"]))

        # Hallucination Risk
        if hasattr(report.hallucination, 'score'):
            category_scores.append(("Hallucination Risk", report.hallucination.score, weights["hallucination_risk"]))

        # Build scorecard
        scorecard_categories = []
        for category, score, weight in category_scores:
            status = self._score_status(score)
            scorecard_categories.append(CategoryScore(
                category=category,
                score=round(score, 1),
                weight=weight,
                status=status,
            ))

        # Weighted overall
        total_weight = sum(w for _, _, w in category_scores)
        overall = sum(s * w for _, s, w in category_scores) / total_weight if total_weight else 0
        report.overall_score = round(overall, 1)

        # Deductions for hallucination risk and critical errors
        if hasattr(report.hallucination, 'risk_level'):
            if report.hallucination.risk_level.value == "high":
                report.overall_score = max(0, report.overall_score - 15)
            elif report.hallucination.risk_level.value == "medium":
                report.overall_score = max(0, report.overall_score - 5)

        report.scorecard = Scorecard(categories=scorecard_categories, overall_score=report.overall_score)

        # Gather all issues
        all_issues: list[ReviewIssue] = []
        for field in ["grammar", "content_quality"]:
            obj = getattr(report, field, None)
            if obj and hasattr(obj, 'issues'):
                for issue in obj.issues:
                    all_issues.append(issue)

        report.all_issues = all_issues
        report.critical_issues = [i for i in all_issues if i.severity == IssueSeverity.CRITICAL]
        report.high_issues = [i for i in all_issues if i.severity == IssueSeverity.HIGH]
        report.medium_issues = [i for i in all_issues if i.severity == IssueSeverity.MEDIUM]
        report.low_issues = [i for i in all_issues if i.severity == IssueSeverity.LOW]

        # Publish decision
        decision = PublishDecision.REJECT
        for item in sorted(SCORE_THRESHOLDS, reverse=True):
            threshold = item[0]
            dec = item[1]
            if report.overall_score >= threshold:
                decision = dec
                break
        report.publish_decision = decision

        # Check for hallucination override
        if hasattr(report.hallucination, 'risk_level'):
            if report.hallucination.risk_level.value == "high" and decision in [
                PublishDecision.ENTERPRISE_READY, PublishDecision.PUBLISH_READY
            ]:
                decision = PublishDecision.MAJOR_REVISIONS
                report.publish_decision = decision

        # Generate recommendations
        report = self._generate_recommendations(report, results)

        # Executive summary
        report.executive_summary = self._generate_executive_summary(report, errors)

        # Generate markdown
        report.markdown = self._report_gen.generate(report)

        return report

    def _generate_recommendations(self, report: QualityReport, results: dict[str, Any]) -> QualityReport:
        must_fix: list[str] = []
        should_improve: list[str] = []
        nice_to_have: list[str] = []

        # Check hallucination
        if hasattr(report.hallucination, 'risk_level'):
            if report.hallucination.risk_level.value == "high":
                must_fix.append("High hallucination risk — review all flagged statements and add citations")
            elif report.hallucination.risk_level.value == "medium":
                should_improve.append("Review medium-risk hallucination flags and add supporting evidence")

        # Check SEO
        if hasattr(report.seo, 'score'):
            if report.seo.score < 70:
                must_fix.append(f"Low SEO score ({report.seo.score:.0f}) — address missing elements: {', '.join(report.seo.missing_elements[:3])}")
            elif report.seo.score < 85:
                should_improve.append(f"SEO score {report.seo.score:.0f} — optimize keyword placement and meta data")

        # Check grammar
        if hasattr(report.grammar, 'score'):
            if report.grammar.score < 80:
                must_fix.append(f"Grammar issues found (score: {report.grammar.score:.0f}) — review and fix errors")
            elif report.grammar.score < 90:
                should_improve.append(f"Minor grammar improvements needed (score: {report.grammar.score:.0f})")

        # Check heading structure
        if hasattr(report.headings, 'score'):
            if report.headings.score < 70:
                must_fix.append("Fix heading hierarchy issues for SEO and accessibility")

        # Check readability
        if hasattr(report.readability, 'score'):
            if report.readability.score < 60:
                should_improve.append(f"Improve readability (score: {report.readability.score:.0f}) — simplify language and sentence structure")
            elif report.readability.score < 80:
                nice_to_have.append(f"Consider readability improvements (score: {report.readability.score:.0f})")

        # Check EEAT
        if hasattr(report.eeat, 'score') and report.eeat.score < 60:
            must_fix.append(f"Low EEAT score ({report.eeat.score:.0f}) — add expertise signals and authoritative references")

        # Check AI detection
        if hasattr(report.ai_detection, 'risk_level'):
            if report.ai_detection.risk_level == "high":
                must_fix.append("High AI detection risk — revise to sound more natural and human-written")
            elif report.ai_detection.risk_level == "medium":
                should_improve.append("Medium AI detection risk — vary sentence structure and vocabulary")

        # Check accessibility
        if hasattr(report.accessibility, 'score') and report.accessibility.score < 70:
            should_improve.append(f"Improve accessibility (score: {report.accessibility.score:.0f})")

        report.must_fix = must_fix[:5]
        report.should_improve = should_improve[:5]
        report.nice_to_have = nice_to_have[:5]

        return report

    def _generate_executive_summary(self, report: QualityReport, errors: list[str]) -> str:
        parts: list[str] = []

        parts.append(f"**Overall Quality Score: {report.overall_score:.0f}/100**")
        parts.append(f"**Decision: {report.publish_decision.value.replace('_', ' ').title()}**")
        parts.append(f"**Word Count: {report.word_count}**")
        parts.append(f"**Reading Time: {report.estimated_reading_time}**")

        # SEO readiness
        seo_score = report.seo.score if hasattr(report.seo, 'score') else 0
        parts.append(f"**SEO Readiness: {seo_score:.0f}/100**")

        # Hallucination risk
        if hasattr(report.hallucination, 'risk_level'):
            parts.append(f"**Hallucination Risk: {report.hallucination.risk_level.value.title()}**")

        # Key strengths
        strengths = []
        for cat in report.scorecard.categories:
            if cat.score >= 85:
                strengths.append(f"{cat.category} ({cat.score:.0f})")
        if strengths:
            parts.append(f"**Strengths:** {', '.join(strengths[:3])}")

        # Key weaknesses
        weaknesses = []
        for cat in report.scorecard.categories:
            if cat.score < 70:
                weaknesses.append(f"{cat.category} ({cat.score:.0f})")
        if weaknesses:
            parts.append(f"**Needs Improvement:** {', '.join(weaknesses[:3])}")

        if errors:
            parts.append(f"**Warnings:** {len(errors)} validator(s) encountered errors: {'; '.join(errors[:2])}")

        return "\n\n".join(parts)

    @staticmethod
    def _score_status(score: float) -> str:
        if score >= 90:
            return "excellent"
        if score >= 80:
            return "good"
        if score >= 70:
            return "fair"
        if score >= 60:
            return "poor"
        return "fail"
