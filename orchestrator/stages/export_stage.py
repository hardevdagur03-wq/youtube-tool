"""Export stage — wraps existing ExportEngine.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from export.engine import ExportEngine
from models.blog_export import ExportRequest

logger = logging.getLogger(__name__)


class ExportStage(StageExecutor):
    """Exports blog using the existing ExportEngine."""

    @property
    def name(self) -> str:
        return "export"

    @property
    def dependencies(self) -> list[str]:
        return ["review"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        merged = ctx.get_stage_input("merge")
        if not merged or not merged.get("content"):
            errors.append("blog content required for export")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        merged = ctx.get_stage_input("merge")
        analysis = ctx.get_stage_input("analysis")

        content = merged.get("content", "") if isinstance(merged, dict) else ""
        title = merged.get("title", "Blog Post") if isinstance(merged, dict) else "Blog Post"

        try:
            export_req = ExportRequest(
                title=title,
                content=content,
                formats=["markdown", "html"],
                video_id=ctx.video_id,
            )
            engine = ExportEngine()
            result = engine.export(export_req)
            data = json.loads(result.model_dump_json()) if hasattr(result, "model_dump_json") else {}
            return StageResult(
                success=True,
                stage=self.name,
                data=data,
            )
        except Exception as exc:
            return StageResult(
                success=False,
                stage=self.name,
                error=f"Export failed: {exc}",
            )
