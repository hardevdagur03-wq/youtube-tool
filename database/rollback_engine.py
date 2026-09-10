from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

ROLLBACKABLE_ENTITIES = {
    "project": "projects",
    "section": "sections",
    "draft": "drafts",
    "review": "reviews",
    "seo": "seo",
    "outline": "outlines",
    "knowledge_graph": "knowledge_graphs",
    "optimization": "optimizations",
}


class RollbackEngine:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def rollback(
        self,
        entity_type: str,
        entity_uuid: str,
        target_version: int,
        actor: str = "system",
        reason: str = "",
    ) -> dict[str, Any]:
        if entity_type not in ROLLBACKABLE_ENTITIES:
            raise ValueError(f"Entity type '{entity_type}' is not rollbackable")

        version = await self.uow.version_history.get_version(
            entity_type, entity_uuid, target_version
        )
        if version is None:
            raise ValueError(
                f"Version {target_version} not found for "
                f"{entity_type} {entity_uuid[:8]}"
            )

        snapshot = version.snapshot
        if not snapshot:
            raise ValueError(f"Version {target_version} has no snapshot data")

        current_version = await self.uow.version_manager.get_latest_version(
            entity_type, entity_uuid
        )
        current_snapshot = await self.get_current_snapshot(entity_type, entity_uuid)

        restore_data = {
            "entity_type": entity_type,
            "entity_uuid": entity_uuid,
            "target_version": target_version,
            "previous_version": current_version,
            "restored_fields": list(snapshot.keys()),
            "actor": actor,
            "reason": reason,
        }

        if entity_type == "project":
            await self._rollback_project(entity_uuid, snapshot)
        elif entity_type == "section":
            await self._rollback_section(entity_uuid, snapshot)
        elif entity_type == "draft":
            await self._rollback_draft(entity_uuid, snapshot)
        elif entity_type == "review":
            await self._rollback_review(entity_uuid, snapshot)
        elif entity_type == "seo":
            await self._rollback_seo(entity_uuid, snapshot)
        elif entity_type == "outline":
            await self._rollback_outline(entity_uuid, snapshot)
        elif entity_type == "knowledge_graph":
            await self._rollback_kg(entity_uuid, snapshot)
        elif entity_type == "optimization":
            await self._rollback_optimization(entity_uuid, snapshot)

        await self.uow.version_manager.create_version(
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            project_uuid=snapshot.get("project_uuid", ""),
            snapshot=current_snapshot or {},
            changed_by=actor,
            pipeline_stage="rollback",
        )

        await self.uow.history.log_event(
            action=f"{entity_type}.rolled_back",
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            project_uuid=snapshot.get("project_uuid", ""),
            actor_id=actor,
            changes={
                "from_version": current_version,
                "to_version": target_version,
                "reason": reason,
            },
        )

        logger.info(
            "Rolled back %s %s to version %d (was v%d)",
            entity_type, entity_uuid[:8], target_version, current_version,
        )

        return restore_data

    async def rollback_project(
        self, project_uuid: str, target_version: int, actor: str = "system"
    ) -> dict[str, Any]:
        result = await self.rollback(
            "project", project_uuid, target_version, actor,
            reason="Project rollback requested",
        )
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project:
            project.updated_at = datetime.now(timezone.utc)
        return result

    async def get_current_snapshot(
        self, entity_type: str, entity_uuid: str
    ) -> dict[str, Any] | None:
        if entity_type == "project":
            obj = await self.uow.projects.get_by_uuid(entity_uuid)
        elif entity_type == "section":
            obj = await self.uow.sections.get_by_uuid(entity_uuid)
        elif entity_type == "draft":
            obj = await self.uow.drafts.get_by_uuid(entity_uuid)
        elif entity_type == "review":
            obj = await self.uow.reviews.get_by_uuid(entity_uuid)
        elif entity_type == "seo":
            obj = await self.uow.seo.get_by_uuid(entity_uuid)
        elif entity_type == "outline":
            obj = await self.uow.outlines.get_by_uuid(entity_uuid)
        elif entity_type == "knowledge_graph":
            obj = await self.uow.knowledge_graphs.get_by_uuid(entity_uuid)
        elif entity_type == "optimization":
            obj = await self.uow.optimizations.get_by_uuid(entity_uuid)
        else:
            return None
        return obj.to_json_safe() if obj else None

    async def _rollback_project(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, ProjectModelFields)
        await self.uow.projects.update(uuid, **safe)

    async def _rollback_section(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, SectionModelFields)
        await self.uow.sections.update(uuid, **safe)

    async def _rollback_draft(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, DraftModelFields)
        await self.uow.drafts.update(uuid, **safe)

    async def _rollback_review(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, ReviewModelFields)
        await self.uow.reviews.update(uuid, **safe)

    async def _rollback_seo(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, SEOModelFields)
        await self.uow.seo.update(uuid, **safe)

    async def _rollback_outline(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, OutlineModelFields)
        await self.uow.outlines.update(uuid, **safe)

    async def _rollback_kg(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, KGModelFields)
        await self.uow.knowledge_graphs.update(uuid, **safe)

    async def _rollback_optimization(
        self, uuid: str, snapshot: dict[str, Any]
    ) -> None:
        safe = self._safe_snapshot(snapshot, OptimizationModelFields)
        await self.uow.optimizations.update(uuid, **safe)

    @staticmethod
    def _safe_snapshot(
        snapshot: dict[str, Any], allowed_fields: set[str]
    ) -> dict[str, Any]:
        return {
            k: v for k, v in snapshot.items()
            if k in allowed_fields and k not in {"uuid", "created_at", "is_deleted"}
        }


ProjectModelFields = {
    "name", "short_id", "description", "url", "video_id", "thumbnail",
    "channel_title", "channel_id", "status", "language", "folder_path",
    "completed_at", "error", "warnings", "retry_count", "tags", "notes",
    "pipeline_state", "settings", "statistics", "checkpoints", "artifacts",
    "history", "stage_data", "progress", "updated_at", "version",
}

SectionModelFields = {
    "project_uuid", "heading", "heading_tag", "content", "content_plain",
    "word_count", "order", "status", "validation_score", "generated_at",
    "generation_time_ms", "llm_model", "prompt_template", "iterations",
    "extra_metadata", "subsections", "updated_at", "version",
}

DraftModelFields = {
    "project_uuid", "draft_number", "markdown_content", "html_content",
    "word_count", "reading_time_minutes", "section_count", "heading_count",
    "image_count", "table_count", "code_block_count", "link_count",
    "editor_version", "toc", "extra_data", "updated_at", "version",
}

ReviewModelFields = {
    "project_uuid", "draft_uuid", "grammar_score", "seo_score",
    "readability_score", "hallucination_score", "eeat_score",
    "accessibility_score", "duplication_score", "overall_score",
    "issues", "recommendations", "strengths", "weaknesses",
    "publication_status", "summary", "raw_data", "updated_at", "version",
}

SEOModelFields = {
    "project_uuid", "primary_keyword", "secondary_keywords", "lsi_keywords",
    "search_intent", "meta_title", "meta_description", "url_slug",
    "target_audience", "content_structure", "faq_schema", "schema_markup",
    "featured_snippet_target", "internal_links", "external_links",
    "competitor_keywords", "seo_score", "readability_score",
    "keyword_difficulty", "raw_data", "updated_at", "version",
}

OutlineModelFields = {
    "project_uuid", "title", "title_variants", "sections", "hierarchy",
    "planned_word_count", "introduction_plan", "conclusion_plan", "cta_plan",
    "faq_plan", "image_placeholders", "table_plans", "example_plans",
    "keywords_per_section", "raw_data", "updated_at", "version",
}

KGModelFields = {
    "project_uuid", "video_id", "entities", "relationships", "facts", "topics",
    "keywords", "summary", "timeline", "pain_points", "solutions", "quotes",
    "definitions", "clusters", "statistics", "raw_data", "updated_at", "version",
}

OptimizationModelFields = {
    "project_uuid", "draft_uuid", "review_uuid", "original_draft",
    "optimized_draft", "changes_applied", "score_improvements",
    "pre_optimization_scores", "post_optimization_scores", "gates_passed",
    "gates_failed", "optimization_round", "summary", "raw_data",
    "updated_at", "version",
}
