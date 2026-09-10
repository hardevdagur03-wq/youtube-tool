"""Review Report Generator — assembles and writes review_report.json."""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from models.blog_review import (
    BlogReviewRequest, QualityReport, PublishDecision, IssueSeverity,
)
from review.review_models_ext import (
    ReviewReport, ReviewMetadata, GrammarReport, SEOReport, ReadabilityReport,
    StructureReport, KeywordReport, DuplicateReport, HallucinationReport,
    MarkdownReport, CompletenessReport, QualityScores, IssueEntry,
    RecommendationEntry, PublicationStatus,
)
from review.review_scorer import ReviewScorer
from review.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class ReviewReportGenerator:
    """Assembles comprehensive ReviewReport from existing QualityReport + extra validators."""

    def __init__(self):
        self.scorer = ReviewScorer()
        self.recommendation_engine = RecommendationEngine()

    def generate(
        self,
        request: BlogReviewRequest,
        quality_report: QualityReport,
        keyword_report: KeywordReport | None = None,
        markdown_report: MarkdownReport | None = None,
        extra_grammar: GrammarReport | None = None,
    ) -> ReviewReport:
        metadata = self._build_metadata(request, quality_report)
        grammar = self._build_grammar(quality_report, extra_grammar)
        seo = self._build_seo(quality_report)
        readability = self._build_readability(quality_report)
        structure = self._build_structure(quality_report)
        keyword = keyword_report or KeywordReport()
        duplicate = self._build_duplicate(quality_report)
        hallucination = self._build_hallucination(quality_report)
        markdown = markdown_report or MarkdownReport()
        completeness = self._build_completeness(quality_report)

        # Build quality scores
        scores = self._build_scores(quality_report, keyword, markdown)
        overall = self.scorer.compute(scores)

        # Build issues
        issues = self._build_issues(quality_report)

        # Build recommendations
        recommendations = self.recommendation_engine.generate(quality_report)

        # Build publication status
        pub_status = self._build_publication_status(quality_report, scores, overall)

        return ReviewReport(
            metadata=metadata,
            grammar=grammar,
            seo=seo,
            readability=readability,
            structure=structure,
            keyword_analysis=keyword,
            duplicate_content=duplicate,
            hallucination_risk=hallucination,
            markdown=markdown,
            completeness=completeness,
            quality_scores=scores,
            issues=issues,
            recommendations=recommendations,
            publication_status=pub_status,
        )

    def _build_metadata(self, request: BlogReviewRequest, quality_report: QualityReport) -> ReviewMetadata:
        word_count = quality_report.word_count or (len(request.content.split()) if request.content else 0)
        estimated_reading_time = quality_report.estimated_reading_time or f"{max(1, word_count // 200)} min"
        return ReviewMetadata(
            blog_title=request.blog_title or quality_report.blog_title,
            word_count=word_count,
            estimated_reading_time=estimated_reading_time,
            project_id=getattr(request, 'project_id', ""),
            url=getattr(request, 'url', ""),
            generated_at=quality_report.generated_at or datetime.now(timezone.utc).isoformat(),
            execution_time_ms=quality_report.execution_time_ms,
            primary_keyword=request.primary_keyword,
            secondary_keywords=request.secondary_keywords,
            target_audience=request.target_audience,
            search_intent=request.search_intent,
        )

    def _build_grammar(self, quality_report: QualityReport, extra: GrammarReport | None) -> GrammarReport:
        g = quality_report.grammar
        issues = []
        if hasattr(g, 'issues'):
            for issue in g.issues:
                issues.append({
                    "description": issue.description,
                    "location": issue.location,
                    "severity": issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                    "why_it_matters": issue.why_it_matters,
                    "recommended_fix": issue.recommended_fix,
                })
        extra_passive = extra.passive_voice_sentences if extra else 0
        return GrammarReport(
            score=round(g.score, 1) if hasattr(g, 'score') else 100.0,
            spelling_errors=getattr(g, 'spelling_errors', 0),
            grammar_errors=getattr(g, 'grammar_errors', 0),
            punctuation_errors=getattr(g, 'punctuation_errors', 0),
            passive_voice_sentences=max(getattr(g, 'passive_voice_sentences', 0), extra_passive),
            run_on_sentences=getattr(g, 'run_on_sentences', 0),
            sentence_fragments=getattr(g, 'sentence_fragments', 0),
            issues=issues,
        )

    def _build_seo(self, quality_report: QualityReport) -> SEOReport:
        s = quality_report.seo
        return SEOReport(
            score=round(s.score, 1) if hasattr(s, 'score') else 100.0,
            title_length=getattr(s, 'title_length', 0),
            meta_title_length=getattr(s, 'meta_title_length', 0),
            meta_description_length=getattr(s, 'meta_description_length', 0),
            primary_keyword_in_title=getattr(s, 'primary_keyword_in_title', False),
            primary_keyword_in_meta_title=getattr(s, 'primary_keyword_in_meta_title', False),
            primary_keyword_in_meta_description=getattr(s, 'primary_keyword_in_meta_description', False),
            primary_keyword_in_introduction=getattr(s, 'primary_keyword_in_introduction', False),
            primary_keyword_in_h1=getattr(s, 'primary_keyword_in_h1', False),
            primary_keyword_in_h2=getattr(s, 'primary_keyword_in_h2', False),
            primary_keyword_in_conclusion=getattr(s, 'primary_keyword_in_conclusion', False),
            keyword_stuffing_detected=getattr(s, 'keyword_stuffing_detected', False),
            missing_elements=getattr(s, 'missing_elements', []),
            recommendations=getattr(s, 'recommendations', []),
        )

    def _build_readability(self, quality_report: QualityReport) -> ReadabilityReport:
        r = quality_report.readability
        return ReadabilityReport(
            score=round(r.score, 1) if hasattr(r, 'score') else 100.0,
            flesch_reading_ease=getattr(r, 'flesch_reading_ease', 0.0),
            flesch_kincaid_grade=getattr(r, 'flesch_kincaid_grade', 0.0),
            avg_sentence_length=getattr(r, 'avg_sentence_length', 0.0),
            avg_paragraph_length=getattr(r, 'avg_paragraph_length', 0.0),
            complex_sentence_ratio=getattr(r, 'complex_sentence_ratio', 0.0),
            passive_voice_percentage=getattr(r, 'passive_voice_percentage', 0.0),
            reading_time_minutes=getattr(r, 'reading_time_minutes', 0.0),
            difficulty_level=getattr(r, 'difficulty_level', ""),
            improvement_suggestions=getattr(r, 'improvement_suggestions', []),
        )

    def _build_structure(self, quality_report: QualityReport) -> StructureReport:
        h = quality_report.headings
        d = quality_report.duplicate
        c = quality_report.completeness
        return StructureReport(
            score=round((getattr(h, 'score', 100) + getattr(d, 'score', 100) + getattr(c, 'score', 100)) / 3, 1),
            h1_count=getattr(h, 'h1_count', 0),
            hierarchy_issues=getattr(h, 'hierarchy_issues', []),
            missing_headings=getattr(h, 'missing_headings', []),
            skipped_levels=getattr(h, 'skipped_levels', []),
            duplicate_paragraphs=getattr(d, 'duplicate_paragraphs', 0),
            duplicate_headings=getattr(d, 'duplicate_headings', 0),
            repeated_sections=getattr(d, 'repeated_sections', []),
            missing_sections=getattr(c, 'missing_sections', []),
        )

    def _build_duplicate(self, quality_report: QualityReport) -> DuplicateReport:
        d = quality_report.duplicate
        return DuplicateReport(
            score=round(d.score, 1) if hasattr(d, 'score') else 100.0,
            duplicate_paragraphs=getattr(d, 'duplicate_paragraphs', 0),
            duplicate_headings=getattr(d, 'duplicate_headings', 0),
            repeated_sections=getattr(d, 'repeated_sections', []),
            merge_recommendations=getattr(d, 'merge_recommendations', []),
        )

    def _build_hallucination(self, quality_report: QualityReport) -> HallucinationReport:
        h = quality_report.hallucination
        risk = getattr(h, 'risk_level', "low")
        if hasattr(risk, 'value'):
            risk = risk.value
        return HallucinationReport(
            score=round(h.score, 1) if hasattr(h, 'score') else 100.0,
            risk_level=risk,
            unsupported_claims=getattr(h, 'unsupported_claims', 0),
            unverifiable_statistics=getattr(h, 'unverifiable_statistics', 0),
            fabricated_references=getattr(h, 'fabricated_references', 0),
        )

    def _build_completeness(self, quality_report: QualityReport) -> CompletenessReport:
        c = quality_report.completeness
        return CompletenessReport(
            score=round(c.score, 1) if hasattr(c, 'score') else 100.0,
            has_introduction=getattr(c, 'has_introduction', False),
            has_core_explanation=getattr(c, 'has_core_explanation', False),
            has_examples=getattr(c, 'has_examples', False),
            has_best_practices=getattr(c, 'has_best_practices', False),
            has_benefits=getattr(c, 'has_benefits', False),
            has_limitations=getattr(c, 'has_limitations', False),
            has_faq=getattr(c, 'has_faq', False),
            has_summary=getattr(c, 'has_summary', False),
            has_call_to_action=getattr(c, 'has_call_to_action', False),
            missing_sections=getattr(c, 'missing_sections', []),
        )

    def _build_scores(
        self,
        quality_report: QualityReport,
        keyword_report: KeywordReport,
        markdown_report: MarkdownReport,
    ) -> QualityScores:
        return QualityScores(
            overall=quality_report.overall_score,
            grammar=quality_report.grammar.score if hasattr(quality_report.grammar, 'score') else 100.0,
            seo=quality_report.seo.score if hasattr(quality_report.seo, 'score') else 100.0,
            readability=quality_report.readability.score if hasattr(quality_report.readability, 'score') else 100.0,
            structure=self._avg_score([
                getattr(quality_report.headings, 'score', 100),
                getattr(quality_report.duplicate, 'score', 100),
                getattr(quality_report.completeness, 'score', 100),
            ]),
            completeness=quality_report.completeness.score if hasattr(quality_report.completeness, 'score') else 100.0,
            keyword_optimization=keyword_report.score,
            markdown_quality=markdown_report.score,
            content_quality=quality_report.content_quality.score if hasattr(quality_report.content_quality, 'score') else 100.0,
            hallucination_risk=quality_report.hallucination.score if hasattr(quality_report.hallucination, 'score') else 100.0,
            fact_consistency=quality_report.fact_consistency.score if hasattr(quality_report.fact_consistency, 'score') else 100.0,
            eeat=quality_report.eeat.score if hasattr(quality_report.eeat, 'score') else 100.0,
            accessibility=quality_report.accessibility.score if hasattr(quality_report.accessibility, 'score') else 100.0,
            ai_detection=quality_report.ai_detection.score if hasattr(quality_report.ai_detection, 'score') else 100.0,
            linking=self._avg_score([
                getattr(quality_report.internal_linking, 'score', 100),
                getattr(quality_report.external_linking, 'score', 100),
            ]),
        )

    def _build_issues(self, quality_report: QualityReport) -> list[IssueEntry]:
        issues: list[IssueEntry] = []
        severity_map = {
            IssueSeverity.CRITICAL: "critical",
            IssueSeverity.HIGH: "high",
            IssueSeverity.MEDIUM: "medium",
            IssueSeverity.LOW: "low",
        }
        for issue in quality_report.all_issues:
            sev = severity_map.get(issue.severity, "low") if hasattr(issue.severity, 'value') else str(issue.severity)
            issues.append(IssueEntry(
                category="general",
                severity=sev,
                description=issue.description,
                location=issue.location,
                why_it_matters=issue.why_it_matters,
                recommended_fix=issue.recommended_fix,
            ))
        return issues

    def _build_publication_status(
        self,
        quality_report: QualityReport,
        scores: QualityScores,
        overall: float,
    ) -> PublicationStatus:
        decision = quality_report.publish_decision
        if hasattr(decision, 'value'):
            decision = decision.value
        return PublicationStatus(
            decision=decision,
            overall_score=overall,
            score_breakdown=self.scorer.score_breakdown(scores),
            critical_issues=len(quality_report.critical_issues),
            high_issues=len(quality_report.high_issues),
            medium_issues=len(quality_report.medium_issues),
            low_issues=len(quality_report.low_issues),
        )

    def _avg_score(self, scores: list[float]) -> float:
        return round(sum(scores) / len(scores), 1) if scores else 100.0

    def write_report(self, report: ReviewReport, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        data = json.loads(report.model_dump_json())
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("[ReviewReportGenerator] Report written to %s", output_path)
        return output_path
