"""Review Pipeline — wraps existing validators + new validators, orchestrates full review."""

from __future__ import annotations
import json
import logging
import time
from typing import Any

from models.blog_review import BlogReviewRequest, BlogReviewResponse, QualityReport
from review.engine import ReviewEngine
from review.markdown_validator import MarkdownValidator
from review.keyword_analyzer import KeywordAnalyzer
from review.passive_voice_detector import PassiveVoiceDetector
from review.table_validator import TableValidator
from review.image_validator import ImageValidator
from review.review_models_ext import (
    ReviewReport, GrammarReport, KeywordReport, MarkdownReport,
)
from review.review_report_generator import ReviewReportGenerator

logger = logging.getLogger(__name__)


class ReviewPipeline:
    """Extended review pipeline that wraps existing ReviewEngine and adds new validators."""

    def __init__(self, output_dir: str | None = None):
        self.engine = ReviewEngine()
        self.report_generator = ReviewReportGenerator()
        self.output_dir = output_dir or "output"
        self._extra_validators = [
            MarkdownValidator(),
            KeywordAnalyzer(),
            PassiveVoiceDetector(),
            TableValidator(),
            ImageValidator(),
        ]

    def review(self, request: BlogReviewRequest) -> tuple[BlogReviewResponse, ReviewReport | None]:
        start = time.time()
        logger.info("[ReviewPipeline] Starting extended review pipeline")

        # Run existing engine
        response = self.engine.review(request)
        quality_report = response.report

        if not quality_report:
            logger.error("[ReviewPipeline] No quality report from engine")
            return response, None

        # Run extra validators
        extra_results: dict[str, Any] = {}
        for validator in self._extra_validators:
            try:
                result, elapsed = validator.execute(request)
                extra_results[validator.name()] = result
                logger.info("[ReviewPipeline] %s completed in %.1fms", validator.name(), elapsed)
            except Exception as exc:
                logger.exception("[ReviewPipeline] %s failed: %s", validator.name(), exc)

        # Extract extra results
        keyword_report: KeywordReport | None = None
        markdown_report: MarkdownReport | None = None
        extra_grammar: GrammarReport | None = None

        for name, result in extra_results.items():
            if name == "Keyword Analysis":
                keyword_report = result
            elif name == "Markdown Validation":
                markdown_report = result
            elif name == "Passive Voice Detection":
                extra_grammar = result
            elif name == "Table Validation":
                if markdown_report is None:
                    markdown_report = result
                elif hasattr(markdown_report, 'table_issues') and hasattr(result, 'table_issues'):
                    markdown_report.table_issues.extend(result.table_issues)
                    markdown_report.score = min(markdown_report.score, result.score)
            elif name == "Image Validation":
                if markdown_report is None:
                    markdown_report = result
                elif hasattr(markdown_report, 'image_issues') and hasattr(result, 'image_issues'):
                    markdown_report.image_issues.extend(result.image_issues)
                    markdown_report.images_missing_alt += result.images_missing_alt
                    markdown_report.image_count += result.image_count
                    markdown_report.score = min(markdown_report.score, result.score)

        # Generate comprehensive report
        report = self.report_generator.generate(
            request=request,
            quality_report=quality_report,
            keyword_report=keyword_report,
            markdown_report=markdown_report,
            extra_grammar=extra_grammar,
        )

        elapsed = round((time.time() - start) * 1000, 1)
        logger.info(
            "[ReviewPipeline] Extended review complete: score=%.1f, decision=%s, %.1fms",
            report.publication_status.overall_score,
            report.publication_status.decision,
            elapsed,
        )

        return response, report

    def write_review_report(self, report: ReviewReport, project_id: str = "") -> str:
        filename = "review_report.json"
        if project_id:
            filename = f"review_report_{project_id}.json"
        output_path = f"{self.output_dir}/{filename}"
        return self.report_generator.write_report(report, output_path)
