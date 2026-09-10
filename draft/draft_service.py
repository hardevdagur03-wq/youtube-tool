"""Draft Service — service layer for external integration with the platform.

Provides a clean API for:
- Project Manager integration
- Pipeline Orchestrator integration
- Cache integration
- Checkpoint integration
- Direct draft assembly
- Draft querying and management
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from draft.draft_assembly_engine import DraftAssemblyEngine
from draft.draft_models import (
    AssemblyConfig,
    DraftDocument,
    DraftMetadata,
    DraftVersion,
    MergeLogEntry,
    MergeStatus,
    utc_now,
)
from draft.draft_storage import DraftStorage

logger = logging.getLogger(__name__)


class DraftService:
    """Service layer for the Draft Assembly Engine.

    Integrates with the project manager, pipeline orchestrator,
    cache, and checkpoint systems.
    """

    def __init__(
        self,
        engine: DraftAssemblyEngine | None = None,
        project_manager: Any | None = None,
    ) -> None:
        self._engine = engine or DraftAssemblyEngine()
        self._pm = project_manager

    @property
    def engine(self) -> DraftAssemblyEngine:
        return self._engine

    def assemble_draft(
        self,
        project_id: str,
        sections_path: Path | None = None,
        sections_data: list[dict[str, Any]] | None = None,
        outline: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        config: AssemblyConfig | None = None,
    ) -> DraftDocument:
        title = ""
        seo_title = ""
        meta_description = ""

        if outline:
            title_obj = outline.get("title", {})
            if isinstance(title_obj, dict):
                title = title_obj.get("primary_title", "")
                seo_title = title_obj.get("seo_title", title)
            elif isinstance(title_obj, str):
                title = title_obj

        if seo_plan:
            meta = seo_plan.get("meta", {})
            if isinstance(meta, dict):
                if not seo_title:
                    seo_title = meta.get("meta_title", title)
                meta_description = meta.get("meta_description", "")

        if analysis:
            if not title:
                title = analysis.get("primary_topic", "") or analysis.get("title", "")
            if not meta_description:
                meta_description = analysis.get("summary", "")

        document = self._engine.assemble(
            project_id=project_id,
            title=title,
            seo_title=seo_title,
            meta_description=meta_description,
            sections_path=sections_path,
            sections_data=sections_data,
            outline_data=outline,
            seo_data=seo_plan,
            config=config,
        )

        return document

    def publish_to_project(
        self,
        project_id: str,
        document: DraftDocument,
    ) -> None:
        if self._pm is None:
            logger.warning("No project manager available, cannot publish draft")
            return

        project = self._pm.get_project(project_id)
        if project is None:
            logger.warning("Project %s not found, cannot publish draft", project_id)
            return

        project.blog = {
            "draft_version": document.word_count,
            "word_count": document.word_count,
            "reading_time_minutes": document.reading_time_minutes,
            "section_count": document.section_count,
            "content": document.content,
            "status": "draft_assembled",
            "updated_at": utc_now(),
        }

        project.statistics.blog_word_count = document.word_count
        self._pm._save(project)

        logger.info(
            "Published draft to project %s (%d words, %d sections)",
            project_id, document.word_count, document.section_count,
        )

    def get_draft(self, project_id: str, version: int | None = None) -> str | None:
        return self._engine.get_draft(project_id, version)

    def get_metadata(self, project_id: str) -> DraftMetadata | None:
        return self._engine.get_metadata(project_id)

    def get_merge_log(self, project_id: str) -> list[MergeLogEntry]:
        return self._engine.get_merge_log(project_id)

    def get_versions(self, project_id: str) -> list[DraftVersion]:
        return self._engine.get_versions(project_id)

    def list_versions(self, project_id: str) -> list[int]:
        return self._engine.list_draft_versions(project_id)

    def rollback(self, project_id: str, target_version: int) -> str | None:
        return self._engine.rollback(project_id, target_version)

    def prune_versions(self, project_id: str, keep: int = 10) -> int:
        return self._engine.prune_versions(project_id, keep)

    def get_statistics(self, project_id: str) -> dict[str, Any]:
        return self._engine.compute_statistics(project_id)

    def has_draft(self, project_id: str) -> bool:
        return self._engine.draft_exists(project_id)
