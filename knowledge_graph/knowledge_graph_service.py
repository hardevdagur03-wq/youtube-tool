"""Knowledge Graph Service — high-level integration layer.

Integrates with Project Manager, Pipeline Orchestrator, and Cache Manager.
No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import KnowledgeGraph
from knowledge_graph.knowledge_graph_engine import KnowledgeGraphEngine
from knowledge_graph.knowledge_graph_validator import KnowledgeGraphValidator
from projects.project_manager import ProjectManager
from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """High-level service for building and managing knowledge graphs."""

    def __init__(
        self,
        project_manager: ProjectManager | None = None,
        cache_manager: CacheManager | None = None,
    ) -> None:
        self._engine = KnowledgeGraphEngine()
        self._validator = KnowledgeGraphValidator()
        self._pm = project_manager
        self._cache = cache_manager or CacheManager()

    def build(
        self,
        project_id: str,
        metadata: dict[str, Any] | None = None,
        transcript: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> KnowledgeGraph:
        video_id = ""
        if self._pm:
            project = self._pm.get_project(project_id)
            if project:
                video_id = project.video_id

        # Check cache
        ctx = type("ctx", (), {"video_id": video_id, "settings": {}})()
        cached = self._cache.get("knowledge_graph", ctx)
        if cached is not None:
            logger.info("Knowledge graph cache HIT for project %s", project_id)
            return KnowledgeGraph(**cached)

        kg = self._engine.build(
            metadata=metadata,
            transcript=transcript,
            analysis=analysis,
            project_id=project_id,
            video_id=video_id,
        )

        self._cache.set("knowledge_graph", ctx, kg.model_dump())

        if self._pm:
            self._pm.store_stage_data(project_id, "knowledge_graph", kg.model_dump())

        return kg

    def get_stored(self, project_id: str) -> KnowledgeGraph | None:
        if self._pm:
            data = self._pm.load_stage_data(project_id, "knowledge_graph")
            if data:
                return KnowledgeGraph(**data)
        return None

    def validate(self, kg: KnowledgeGraph) -> list[str]:
        return self._validator.validate(kg)

    def quality_score(self, kg: KnowledgeGraph) -> float:
        return self._validator.compute_quality_score(kg)

    def to_dict(self, kg: KnowledgeGraph) -> dict[str, Any]:
        return kg.model_dump()

    def summary(self, kg: KnowledgeGraph) -> dict[str, Any]:
        return kg.summary
