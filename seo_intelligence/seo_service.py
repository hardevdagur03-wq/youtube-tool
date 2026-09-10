"""SEO Service — high-level integration layer for the SEO Intelligence Engine.

Integrates with Project Manager, Pipeline Orchestrator, Cache Manager, and Knowledge Graph.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import SEOPlan
from seo_intelligence.seo_engine import SEOEngine
from seo_intelligence.seo_validator import SEOValidator
from projects.project_manager import ProjectManager
from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class SEOService:
    """High-level service for building and managing SEO plans."""

    def __init__(
        self,
        project_manager: ProjectManager | None = None,
        cache_manager: CacheManager | None = None,
    ) -> None:
        self._engine = SEOEngine()
        self._validator = SEOValidator()
        self._pm = project_manager
        self._cache = cache_manager or CacheManager()

    def build(
        self,
        project_id: str,
        knowledge_graph: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SEOPlan:
        video_id = ""
        if self._pm:
            project = self._pm.get_project(project_id)
            if project:
                video_id = project.video_id

        # Check cache
        ctx = type("ctx", (), {"video_id": video_id, "settings": {}})()
        cached = self._cache.get("seo_plan", ctx)
        if cached is not None:
            logger.info("SEO plan cache HIT for project %s", project_id)
            return SEOPlan(**cached)

        plan = self._engine.build(
            knowledge_graph=knowledge_graph,
            analysis=analysis,
            metadata=metadata,
            project_id=project_id,
            video_id=video_id,
        )

        self._cache.set("seo_plan", ctx, plan.model_dump())

        if self._pm:
            self._pm.store_stage_data(project_id, "seo_plan", plan.model_dump())

        return plan

    def get_stored(self, project_id: str) -> SEOPlan | None:
        if self._pm:
            data = self._pm.load_stage_data(project_id, "seo_plan")
            if data:
                return SEOPlan(**data)
        return None

    def validate(self, plan: SEOPlan) -> list[str]:
        return self._validator.validate(plan)

    def to_dict(self, plan: SEOPlan) -> dict[str, Any]:
        return plan.model_dump()

    def summary(self, plan: SEOPlan) -> dict[str, Any]:
        return plan.summary
