"""Merge stage — uses DraftAssemblyEngine to assemble complete drafts.

Consumes: outline.json, seo_plan.json, knowledge_graph.json, sections/
Produces: draft/draft.md with version history, metadata, and merge log.

No content generation occurs here — only intelligent assembly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from draft.draft_assembly_engine import DraftAssemblyEngine
from draft.draft_models import AssemblyConfig, MergeStatus
from draft.draft_service import DraftService

logger = logging.getLogger(__name__)


class MergeStage(StageExecutor):
    """Assembles independently generated sections into a complete, versioned draft."""

    def __init__(self) -> None:
        self._engine = DraftAssemblyEngine()
        self._service = DraftService(engine=self._engine)

    @property
    def name(self) -> str:
        return "merge"

    @property
    def dependencies(self) -> list[str]:
        return ["sections", "outline", "seo_intelligence"]

    @property
    def is_cacheable(self) -> bool:
        return False

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        sections = ctx.get_stage_input("sections")
        if not sections:
            errors.append("sections data required for merge stage")
        outline = ctx.get_stage_input("outline")
        if not outline:
            errors.append("outline data required for merge stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        project_id = ctx.project_id
        sections_data = ctx.get_stage_input("sections")
        outline = ctx.get_stage_input("outline")
        seo = ctx.get_stage_input("seo_intelligence") or ctx.get_stage_input("seo")

        logger.info("Draft Assembly: assembling draft for project %s", project_id)

        pm = ctx.project_manager
        sections_path = None
        if pm:
            sections_path = (
                Path(pm.storage.root)
                / project_id
                / "sections"
            )

        section_list = []
        if isinstance(sections_data, dict):
            section_list = sections_data.get("sections", [])
        elif isinstance(sections_data, list):
            section_list = sections_data

        config = AssemblyConfig(
            generate_toc=True,
            add_horizontal_rules=True,
            normalize_headings=True,
            resolve_references=True,
            fail_on_validation_error=False,
            fail_on_missing_section=False,
        )

        try:
            document = self._service.assemble_draft(
                project_id=project_id,
                sections_path=sections_path if sections_path and sections_path.exists() else None,
                sections_data=section_list if not (sections_path and sections_path.exists()) else None,
                outline=outline,
                seo_plan=seo,
                analysis=ctx.get_stage_input("analysis"),
                config=config,
            )

            if pm:
                self._service.publish_to_project(project_id, document)

            metadata = self._engine.get_metadata(project_id)
            status = metadata.status.value if metadata else "completed"

            return StageResult(
                success=status != MergeStatus.FAILED.value,
                stage=self.name,
                data={
                    "version": metadata.draft_version if metadata else 1,
                    "word_count": document.word_count,
                    "reading_time_minutes": document.reading_time_minutes,
                    "section_count": document.section_count,
                    "content": document.content,
                    "toc": [e.model_dump() for e in document.toc],
                    "metadata": metadata.model_dump() if metadata else {},
                    "status": status,
                },
                warnings=metadata.warnings if metadata else [],
            )

        except Exception as exc:
            logger.error("Draft assembly failed for project %s: %s", project_id, exc)
            return StageResult(
                success=False,
                stage=self.name,
                data={},
                error=str(exc),
            )
