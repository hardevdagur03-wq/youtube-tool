"""Review stage — wraps existing ReviewEngine + extended ReviewPipeline.

Backward-compatible: StageResult output remains the same.
No existing code is modified. Adds review_report.json persistence.
"""

from __future__ import annotations

import json
import logging
import os

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from review.review_pipeline import ReviewPipeline
from models.blog_review import BlogReviewRequest

logger = logging.getLogger(__name__)


class ReviewStage(StageExecutor):
    """Runs quality review using the extended ReviewPipeline."""

    @property
    def name(self) -> str:
        return "review"

    @property
    def dependencies(self) -> list[str]:
        return ["merge"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        merged = ctx.get_stage_input("merge")
        if not merged or not merged.get("content"):
            errors.append("merged blog content required for review")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        merged = ctx.get_stage_input("merge")
        analysis = ctx.get_stage_input("analysis")

        content = merged.get("content", "") if isinstance(merged, dict) else ""

        try:
            # Build request
            review_request = BlogReviewRequest(
                content=content,
                blog_title=merged.get("title", ""),
                primary_keyword=analysis.get("keywords", {}).get("primary", "") if isinstance(analysis, dict) else "",
            )

            # Run extended pipeline
            output_dir = ctx.config.get("output_dir", "output") if hasattr(ctx, 'config') else "output"
            pipeline = ReviewPipeline(output_dir=output_dir)
            response, review_report = pipeline.review(review_request)

            # Persist review_report.json
            if review_report:
                project_id = merged.get("project_id", "") if isinstance(merged, dict) else ""
                report_path = pipeline.write_review_report(review_report, project_id=project_id)
                logger.info("[ReviewStage] review_report.json written to %s", report_path)

            # Backward-compatible StageResult
            data = json.loads(response.model_dump_json()) if hasattr(response, "model_dump_json") else {}
            return StageResult(
                success=True,
                stage=self.name,
                data=data,
            )
        except Exception as exc:
            logger.exception("[ReviewStage] Review failed: %s", exc)
            return StageResult(
                success=False,
                stage=self.name,
                error=f"Review failed: {exc}",
            )
