"""Outline Service — high-level integration layer for the Outline Generator.

Integrates with Project Manager, Pipeline Orchestrator, and Cache Manager.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ContentOutline
from outline_generator.outline_engine import OutlineEngine
from outline_generator.outline_validator import OutlineValidator
from projects.project_manager import ProjectManager
from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class OutlineService:
    """High-level service for building and managing content outlines."""

    def __init__(
        self,
        project_manager: ProjectManager | None = None,
        cache_manager: CacheManager | None = None,
    ) -> None:
        self._engine = OutlineEngine()
        self._validator = OutlineValidator()
        self._pm = project_manager
        self._cache = cache_manager or CacheManager()

    def build(
        self,
        project_id: str,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContentOutline:
        video_id = ""
        if self._pm:
            project = self._pm.get_project(project_id)
            if project:
                video_id = project.video_id

        ctx = type("ctx", (), {"video_id": video_id, "settings": {}})()
        cached = self._cache.get("outline", ctx)
        if cached is not None:
            logger.info("Outline cache HIT for project %s", project_id)
            return ContentOutline(**cached)

        outline = self._engine.build(
            knowledge_graph=knowledge_graph,
            seo_plan=seo_plan,
            analysis=analysis,
            metadata=metadata,
            project_id=project_id,
            video_id=video_id,
        )

        self._cache.set("outline", ctx, outline.model_dump())

        if self._pm:
            self._pm.store_stage_data(project_id, "outline", outline.model_dump())

        return outline

    def get_stored(self, project_id: str) -> ContentOutline | None:
        if self._pm:
            data = self._pm.load_stage_data(project_id, "outline")
            if data:
                return ContentOutline(**data)
        return None

    def validate(self, outline: ContentOutline) -> list[str]:
        return self._validator.validate(outline)

    def to_dict(self, outline: ContentOutline) -> dict[str, Any]:
        return outline.model_dump()

    def summary(self, outline: ContentOutline) -> dict[str, Any]:
        return outline.summary
