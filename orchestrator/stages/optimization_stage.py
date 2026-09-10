"""Optimization Stage — pipeline stage for the Optimization Engine.

Consumes merge/review stage outputs.
Produces optimized draft and optimization report.
Backward-compatible: StageResult output.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from optimization.optimization_service import OptimizationService
from optimization.optimization_models import OptimizationConfig

logger = logging.getLogger(__name__)


class OptimizationStage(StageExecutor):
    """Runs targeted content optimization based on review report quality scores."""

    @property
    def name(self) -> str:
        return "optimization"

    @property
    def dependencies(self) -> list[str]:
        return ["merge", "review"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        merged = ctx.get_stage_input("merge")
        review = ctx.get_stage_input("review")

        if not merged or not merged.get("content"):
            errors.append("merged content required for optimization")

        if not review:
            errors.append("review report required for optimization")

        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        merged = ctx.get_stage_input("merge")
        review_data = ctx.get_stage_input("review")
        analysis = ctx.get_stage_input("analysis")

        content = merged.get("content", "") if isinstance(merged, dict) else ""
        review_report = review_data.get("report", {}) if isinstance(review_data, dict) else review_data

        # Load artifacts from project directory
        project = ctx.project
        project_dir = ""
        if project and hasattr(project, 'project_dir'):
            project_dir = project.project_dir
        elif project and isinstance(project, dict):
            project_dir = project.get("project_dir", "")

        outline = {}
        seo_plan = {}
        knowledge_graph = {}
        project_data = {}

        if project_dir:
            def _load_json(filename: str) -> dict:
                path = os.path.join(project_dir, filename)
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception:
                        return {}
                return {}

            outline = _load_json("outline.json")
            seo_plan = _load_json("seo_plan.json")
            knowledge_graph = _load_json("knowledge_graph.json")
            project_data = _load_json("project.json")
        else:
            outline = ctx.get_stage_input("outline") or {}
            seo_plan = ctx.get_stage_input("seo_intelligence") or {}
            if isinstance(analysis, dict):
                knowledge_graph = analysis

        try:
            service = OptimizationService()

            if project_dir:
                optimized_draft, report = service.optimize_from_project(
                    project_dir=project_dir,
                )
            else:
                optimized_draft, report = service.optimize_from_artifacts(
                    draft_md=content,
                    review_report=review_report if isinstance(review_report, dict) else {},
                    outline=outline if isinstance(outline, dict) else {},
                    seo_plan=seo_plan if isinstance(seo_plan, dict) else {},
                    knowledge_graph=knowledge_graph if isinstance(knowledge_graph, dict) else {},
                    project=project_data if isinstance(project_data, dict) else None,
                )

            if not report:
                return StageResult(
                    success=False,
                    stage=self.name,
                    error="Optimization engine returned no report",
                )

            # Return backward-compatible StageResult
            report_dict = json.loads(report.model_dump_json()) if hasattr(report, "model_dump_json") else {}

            data = {
                "optimized_content": optimized_draft or content,
                "optimization_report": report_dict,
                "sections_optimized": report.sections_optimized,
                "quality_gates_passed": report.quality_gates_passed,
            }

            return StageResult(
                success=True,
                stage=self.name,
                data=data,
                artifacts={
                    "optimized_draft": f"optimized_draft_{project_data.get('project_id', '')}.md",
                    "optimization_report": f"optimization_report_{project_data.get('project_id', '')}.json",
                },
            )

        except Exception as exc:
            logger.exception("[OptimizationStage] Optimization failed: %s", exc)
            return StageResult(
                success=False,
                stage=self.name,
                error=f"Optimization failed: {exc}",
            )
