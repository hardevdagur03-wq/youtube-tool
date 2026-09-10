"""DatabaseService — high-level service layer bridging database to pipeline.

Provides a comprehensive API that mirrors the existing ProjectManager/PipelineManager
interface but backed by the SQL database instead of file-based JSON persistence.

Usage:
    service = DatabaseService()
    project = await service.create_project(url="...", video_id="abc123")
    await service.store_stage_data(project.project_id, "transcript", {...})
    data = await service.load_stage_data(project.project_id, "transcript")
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Sequence

from database.models import (
    AnalysisModel, DraftModel, ExportModel, KnowledgeGraphModel,
    OptimizationModel, OutlineModel, PipelineStateModel, ProjectModel,
    ReviewModel, SEOModel, SectionModel, TranscriptModel, VersionModel,
    VideoModel,
)
from database.session import DatabaseSessionManager, db_manager
from database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_STAGE_TO_TABLE = frozenset({
    "videos", "transcripts", "analyses", "knowledge_graphs",
    "seo", "seo_intelligence", "outlines", "sections", "drafts",
    "reviews", "optimizations", "exports",
})


class DatabaseService:
    """Database-backed persistence layer for pipeline artifacts.

    Every public method creates its own UnitOfWork transaction.
    For callers that need transactional grouping across multiple calls,
    use `transaction()` context manager for manual control.

    Thread-safe: each call gets a fresh async session.
    """

    def __init__(
        self,
        session_manager: DatabaseSessionManager | None = None,
    ) -> None:
        self._session_mgr = session_manager or db_manager
        if self._session_mgr._engine is None:
            self._session_mgr.initialize()

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _uow(self):
        """Create and manage a UnitOfWork bound to this service's session."""
        session = self._session_mgr.session_factory()
        uow = UnitOfWork.__new__(UnitOfWork)
        UnitOfWork.__init__(uow, session=session)
        uow._is_owned_session = True
        try:
            await uow.__aenter__()
            yield uow
            await uow.__aexit__(None, None, None)
        except Exception as exc:
            await uow.__aexit__(type(exc), exc, exc.__traceback__)
            raise

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        url: str = "",
        video_id: str = "",
        name: str = "",
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new project and return its full representation."""
        import uuid
        now = _utc_now()
        project_id = str(uuid.uuid4())
        short_id = uuid.uuid4().hex[:8]

        pipeline_state = {
            "stages": {},
            "current_stage": "",
            "overall_progress_pct": 0.0,
            "elapsed_seconds": 0.0,
            "is_paused": False,
        }

        async with self._uow() as uow:
            model = await uow.projects.create(
                uuid=project_id,
                short_id=short_id,
                name=name or video_id or "Untitled Project",
                url=url,
                video_id=video_id,
                status="created",
                language="en",
                folder_path=f"projects/{project_id}",
                pipeline_state=pipeline_state,
                settings=settings or {},
                statistics={},
                stage_data={},
            )
            await uow.history.log_event(
                action="project.created",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
                extra_data={"url": url, "video_id": video_id},
            )
            result = await self._project_to_dict(model)

        logger.info("DB project created: %s (%s)", project_id, url)
        return result

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None or model.is_deleted:
                return None
            return await self._project_to_dict(model)

    async def update_project(
        self, project_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        safe_updates = {
            k: v for k, v in updates.items()
            if k not in ("uuid", "created_at", "is_deleted")
        }
        async with self._uow() as uow:
            model = await uow.projects.update(project_id, **safe_updates)
            if model is None:
                return None
            return await self._project_to_dict(model)

    async def delete_project(
        self, project_id: str, permanent: bool = False
    ) -> bool:
        async with self._uow() as uow:
            if permanent:
                model = await uow.projects.hard_delete(project_id)
            else:
                model = await uow.projects.soft_delete(project_id)
            if model is None:
                return False
            await uow.history.log_event(
                action="project.deleted",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
                extra_data={"permanent": permanent},
            )
            return True

    async def list_projects(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        async with self._uow() as uow:
            projects = await uow.projects.list_all(
                order_by="updated_at", descending=True, limit=limit, offset=offset
            )
            return [await self._project_to_summary(p) for p in projects]

    async def search_projects(
        self, query: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        async with self._uow() as uow:
            result = await uow.projects.search_projects(query, page=1, page_size=limit)
            return [await self._project_to_summary(p) for p in result.items]

    async def find_or_create_by_video(
        self, video_id: str, url: str = ""
    ) -> dict[str, Any]:
        async with self._uow() as uow:
            model = await uow.projects.get_by_video_id(video_id)
            if model is not None and not model.is_deleted:
                return await self._project_to_dict(model)
        return await self.create_project(url=url, video_id=video_id, name=f"Video {video_id}")

    async def get_summary(self, project_id: str) -> dict[str, Any] | None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None or model.is_deleted:
                return None
            return await self._project_to_summary(model)

    async def get_project_stats(self) -> dict[str, Any]:
        async with self._uow() as uow:
            return await uow.projects.get_project_stats()

    async def project_exists(self, project_id: str) -> bool:
        async with self._uow() as uow:
            return await uow.projects.exists(uuid=project_id)

    # ------------------------------------------------------------------
    # Pipeline Stage Management
    # ------------------------------------------------------------------

    async def stage_started(self, project_id: str, stage: str) -> None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return
            ps = dict(model.pipeline_state or {})
            stages = dict(ps.get("stages", {}))
            stages[stage] = {
                "status": "running",
                "progress_pct": 0.0,
                "started_at": _utc_now(),
            }
            ps["stages"] = stages
            ps["current_stage"] = stage
            ps["is_paused"] = False
            await uow.projects.update(project_id, pipeline_state=ps, status=_status_for_stage(stage))
            await uow.history.log_event(
                action="stage.started",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
                extra_data={"stage": stage},
            )

    async def stage_completed(self, project_id: str, stage: str) -> None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return
            ps = dict(model.pipeline_state or {})
            stages = dict(ps.get("stages", {}))
            stages[stage] = dict(stages.get(stage, {}))
            stages[stage].update({
                "status": "completed",
                "progress_pct": 100.0,
                "finished_at": _utc_now(),
            })
            ps["stages"] = stages
            await uow.projects.update(project_id, pipeline_state=ps)
            await uow.history.log_event(
                action="stage.completed",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
                extra_data={"stage": stage},
            )

    async def stage_failed(
        self, project_id: str, stage: str, error: str = ""
    ) -> None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return
            ps = dict(model.pipeline_state or {})
            stages = dict(ps.get("stages", {}))
            stages[stage] = dict(stages.get(stage, {}))
            stages[stage].update({
                "status": "failed",
                "error": error,
            })
            ps["stages"] = stages
            await uow.projects.update(
                project_id, pipeline_state=ps, status="failed", error=error
            )
            await uow.history.log_event(
                action="stage.failed",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
                extra_data={"stage": stage, "error": error},
            )

    async def complete_project(self, project_id: str) -> bool:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return False
            now = _utc_now()
            ps = dict(model.pipeline_state or {})
            stages = dict(ps.get("stages", {}))
            for s in stages:
                if stages[s].get("status") != "completed":
                    stages[s] = dict(stages.get(s, {}))
                    stages[s]["status"] = "completed"
            ps["stages"] = stages
            ps["overall_progress_pct"] = 100.0
            await uow.projects.update(
                project_id,
                pipeline_state=ps,
                status="completed",
                completed_at=now,
            )
            await uow.history.log_event(
                action="project.completed",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
            )
            return True

    async def pause_project(self, project_id: str) -> bool:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return False
            ps = dict(model.pipeline_state or {})
            ps["is_paused"] = True
            await uow.projects.update(project_id, pipeline_state=ps, status="paused")
            await uow.history.log_event(
                action="project.paused",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
            )
            return True

    async def resume_project(self, project_id: str) -> dict[str, Any] | None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return None
            ps = dict(model.pipeline_state or {})
            ps["is_paused"] = False
            await uow.projects.update(project_id, pipeline_state=ps, status="resumed")
            await uow.history.log_event(
                action="project.resumed",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
            )
            return await self._project_to_dict(model)

    async def cancel_project(self, project_id: str) -> bool:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return False
            await uow.projects.update(project_id, status="cancelled")
            await uow.history.log_event(
                action="project.cancelled",
                entity_type="project",
                entity_uuid=project_id,
                project_uuid=project_id,
                actor_id="system",
            )
            return True

    # ------------------------------------------------------------------
    # Stage Data Operations (generic store/load by stage name)
    # ------------------------------------------------------------------

    async def store_stage_data(
        self, project_id: str, stage: str, data: dict[str, Any]
    ) -> None:
        """Store stage data, routing to dedicated table or JSON fallback."""
        handler = _STAGE_HANDLERS.get(stage)
        if handler is not None:
            await handler(self, project_id, data)
            return

        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return
            sd = dict(model.stage_data or {})
            sd[stage] = data
            await uow.projects.update(project_id, stage_data=sd)

    async def load_stage_data(
        self, project_id: str, stage: str
    ) -> dict[str, Any] | None:
        """Load stage data from dedicated table or JSON fallback."""
        loader = _STAGE_LOADERS.get(stage)
        if loader is not None:
            return await loader(self, project_id)

        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return None
            sd = model.stage_data or {}
            return sd.get(stage)

    # ------------------------------------------------------------------
    # Per-Entity Operations (dedicated tables)
    # ------------------------------------------------------------------

    async def save_video(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, VideoModel,
            field_map={"title": "title", "duration_seconds": "duration_seconds",
                       "view_count": "view_count", "description": "description",
                       "channel_title": "channel_title", "channel_id": "channel_id"},
        )

    async def get_video(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "videos")

    async def save_transcript(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, TranscriptModel,
            field_map={"plain_text": "plain_text", "content": "plain_text",
                       "language": "language", "word_count": "word_count",
                       "duration_seconds": "duration_seconds"},
        )

    async def get_transcript(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "transcripts")

    async def save_analysis(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, AnalysisModel,
            field_map={"summary": "summary", "key_topics": "topics",
                       "topics": "topics", "key_points": "key_points",
                       "sentiment": "sentiment", "readability_score": "readability_score"},
        )

    async def get_analysis(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "analyses")

    async def save_knowledge_graph(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, KnowledgeGraphModel,
            field_map={"entities": "entities", "relationships": "relationships",
                       "quality_score": "quality_score", "summary": "summary"},
        )

    async def get_knowledge_graph(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "knowledge_graphs")

    async def save_seo(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, SEOModel,
            field_map={"seo_score": "seo_score", "keywords": "primary_keyword",
                       "primary_keyword": "primary_keyword",
                       "meta_description": "meta_description",
                       "search_intent": "search_intent"},
        )

    async def get_seo(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "seo")

    async def save_outline(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        kw = {"raw_data": data}
        if "title" in data:
            t = data["title"]
            kw["title"] = t.get("primary_title", "") if isinstance(t, dict) else str(t)
        if "sections" in data:
            kw["sections"] = data["sections"]
        async with self._uow() as uow:
            existing = await uow.outlines.get_by_field("project_uuid", project_id)
            if existing:
                model = await uow.outlines.update(existing.uuid, **kw)
            else:
                model = await uow.outlines.create(project_uuid=project_id, **kw)
            return self._model_to_dict(model)

    async def get_outline(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "outlines")

    async def save_sections(
        self, project_id: str, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        async with self._uow() as uow:
            existing = await uow.sections.get_by_field("project_uuid", project_id, unique=False)
            if isinstance(existing, list):
                for sec in existing:
                    await uow.sections.hard_delete(sec.uuid)
            results = []
            for sec in sections:
                model = await uow.sections.create(project_uuid=project_id, **sec)
                results.append(self._model_to_dict(model))
            return results

    async def get_sections(self, project_id: str) -> list[dict[str, Any]]:
        async with self._uow() as uow:
            models = await uow.sections.get_by_field("project_uuid", project_id, unique=False)
            if isinstance(models, list):
                return [self._model_to_dict(m) for m in models]
            return [self._model_to_dict(models)] if models else []

    async def save_draft(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._uow() as uow:
            existing = await uow.drafts.get_by_project(project_id)
            draft_number = 1
            if existing:
                draft_number = (existing.draft_number or 1) + 1
            kw: dict[str, Any] = {"project_uuid": project_id, "draft_number": draft_number}
            for col in ("markdown_content", "html_content", "word_count",
                        "reading_time_minutes", "section_count", "toc", "extra_data"):
                if col in data:
                    kw[col] = data[col]
            model = await uow.drafts.create(**kw)
            return self._model_to_dict(model)

    async def get_draft(
        self, project_id: str, draft_number: int | None = None
    ) -> dict[str, Any] | None:
        async with self._uow() as uow:
            if draft_number:
                model = await uow.drafts.get_by_field("draft_number", draft_number)
            else:
                model = await uow.drafts.get_latest_by_project(project_id)
            return self._model_to_dict(model) if model else None

    async def save_review(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, ReviewModel,
            field_map={"score": "overall_score", "overall_score": "overall_score",
                       "status": "publication_status",
                       "publication_status": "publication_status",
                       "issues": "issues", "summary": "summary",
                       "recommendations": "recommendations"},
        )

    async def get_review(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "reviews")

    async def save_optimization(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, OptimizationModel,
            field_map={"optimization_round": "optimization_round",
                       "score_before": "pre_optimization_scores",
                       "score_after": "post_optimization_scores",
                       "changes": "changes_applied",
                       "changes_applied": "changes_applied",
                       "summary": "summary"},
        )

    async def get_optimization(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "optimizations")

    async def save_export(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._upsert_entity_data(
            project_id, data, ExportModel,
            field_map={"format": "export_format", "export_format": "export_format",
                       "file_path": "file_path", "file_size": "file_size_bytes",
                       "file_size_bytes": "file_size_bytes",
                       "filename": "filename"},
        )

    async def get_export(self, project_id: str) -> dict[str, Any] | None:
        return await self._get_entity_data(project_id, "exports")

    # ------------------------------------------------------------------
    # Pipeline State
    # ------------------------------------------------------------------

    async def save_pipeline_state(
        self, project_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._uow() as uow:
            existing = await uow.projects.get_by_uuid(project_id)
            if existing is None:
                return {}
            await uow.projects.update(project_id, pipeline_state=state)
            return state

    async def get_pipeline_state(
        self, project_id: str
    ) -> dict[str, Any] | None:
        async with self._uow() as uow:
            model = await uow.projects.get_by_uuid(project_id)
            if model is None:
                return None
            return dict(model.pipeline_state or {})

    async def update_stage_data(
        self, project_id: str, stage: str, data: dict[str, Any]
    ) -> None:
        async with self._uow() as uow:
            await uow.projects.update_stage_data(project_id, stage, data)

    # ------------------------------------------------------------------
    # Audit Operations
    # ------------------------------------------------------------------

    async def log_event(
        self,
        project_id: str,
        action: str,
        entity_type: str = "project",
        entity_uuid: str | None = None,
        actor_id: str = "system",
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        async with self._uow() as uow:
            await uow.history.log_event(
                action=action,
                entity_type=entity_type,
                entity_uuid=entity_uuid or project_id,
                project_uuid=project_id,
                actor_id=actor_id,
                extra_data=extra_data or {},
            )

    async def get_audit_trail(
        self,
        project_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        from database.audit import AuditService
        async with self._uow() as uow:
            audit = AuditService(uow)
            return await audit.get_project_history(project_id, limit=limit)

    async def get_recent_activity(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        from database.audit import AuditService
        async with self._uow() as uow:
            audit = AuditService(uow)
            return await audit.get_recent_activity(limit=limit)

    # ------------------------------------------------------------------
    # Version Operations
    # ------------------------------------------------------------------

    async def create_version(
        self,
        entity_type: str,
        entity_uuid: str,
        project_uuid: str,
        snapshot: dict[str, Any],
        changed_fields: list[str] | None = None,
        changed_by: str = "system",
        pipeline_stage: str = "",
    ) -> int:
        async with self._uow() as uow:
            return await uow.version_manager.create_version(
                entity_type=entity_type,
                entity_uuid=entity_uuid,
                project_uuid=project_uuid,
                snapshot=snapshot,
                changed_fields=changed_fields,
                changed_by=changed_by,
                pipeline_stage=pipeline_stage,
            )

    async def list_versions(
        self, entity_type: str, entity_uuid: str
    ) -> list[dict[str, Any]]:
        async with self._uow() as uow:
            versions = await uow.version_history.list_by_entity(
                entity_type, entity_uuid
            )
            return [self._model_to_dict(v) for v in versions]

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        try:
            async with self._uow() as uow:
                count = await uow.projects.count()
                return {
                    "healthy": True,
                    "project_count": count,
                    "driver": (
                        self._session_mgr._config.driver
                        if self._session_mgr._config
                        else "unknown"
                    ),
                }
        except Exception as exc:
            return {
                "healthy": False,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Transaction Grouping
    # ------------------------------------------------------------------

    def transaction(self):
        """Return a UnitOfWork context manager for manual transaction control.

        Example:
            service = DatabaseService()
            async with service.transaction() as uow:
                await uow.projects.create(...)
                await uow.history.log_event(...)
        """
        return self._uow()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _project_to_dict(self, model: ProjectModel) -> dict[str, Any]:
        return {
            "project_id": model.uuid,
            "short_id": model.short_id,
            "name": model.name,
            "description": model.description,
            "url": model.url,
            "video_id": model.video_id,
            "thumbnail": model.thumbnail,
            "channel_title": model.channel_title,
            "channel_id": model.channel_id,
            "status": model.status,
            "version": 1,
            "language": model.language,
            "folder_path": model.folder_path,
            "created_at": model.created_at.isoformat() if hasattr(model.created_at, "isoformat") else str(model.created_at),
            "updated_at": model.updated_at.isoformat() if hasattr(model.updated_at, "isoformat") else str(model.updated_at),
            "completed_at": model.completed_at,
            "pipeline": model.pipeline_state or {},
            "settings": model.settings or {},
            "statistics": model.statistics or {},
            "stage_data": model.stage_data or {},
            "checkpoints": model.checkpoints or [],
            "artifacts": model.artifacts or [],
            "history": model.history or [],
            "error": model.error,
            "warnings": model.warnings or [],
            "tags": model.tags or [],
            "notes": model.notes,
            "progress": model.progress,
        }

    async def _project_to_summary(self, model: ProjectModel) -> dict[str, Any]:
        ps = model.pipeline_state or {}
        stages = ps.get("stages", {})
        stats = model.statistics or {}
        return {
            "project_id": model.uuid,
            "short_id": model.short_id,
            "name": model.name,
            "video_id": model.video_id,
            "url": model.url,
            "thumbnail": model.thumbnail,
            "status": model.status,
            "current_stage": ps.get("current_stage", ""),
            "overall_progress_pct": round(ps.get("overall_progress_pct", 0.0), 1),
            "version": 1,
            "language": model.language,
            "created_at": model.created_at.isoformat() if hasattr(model.created_at, "isoformat") else str(model.created_at),
            "updated_at": model.updated_at.isoformat() if hasattr(model.updated_at, "isoformat") else str(model.updated_at),
            "completed_at": model.completed_at,
            "error": model.error,
            "tags": model.tags or [],
            "quality_score": stats.get("quality_score", 0.0),
            "seo_score": stats.get("seo_score", 0.0),
        }

    def _model_to_dict(self, model: Any) -> dict[str, Any]:
        if model is None:
            return {}
        result = {}
        for col in model.__table__.columns:
            val = getattr(model, col.name, None)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            result[col.name] = val
        return result

    async def _get_entity_data(
        self, project_id: str, repo_attr: str
    ) -> dict[str, Any] | None:
        """Load entity data from a dedicated table by project_uuid."""
        async with self._uow() as uow:
            repo = getattr(uow, repo_attr, None)
            if repo is None:
                return None
            model = await repo.get_by_field("project_uuid", project_id)
            return self._model_to_dict(model) if model else None

    async def _upsert_entity_data(
        self,
        project_id: str,
        data: dict[str, Any],
        model_class: type,
        field_map: dict[str, str],
    ) -> dict[str, Any]:
        """Create or update entity data. Maps arbitrary data keys to model columns,
        and stores everything else in raw_data (if the model has that column)."""
        from database.repositories.base import BaseRepository
        repo_attr = model_class.__tablename__
        model_cols = {c.name for c in model_class.__table__.columns}
        kw: dict[str, Any] = {}
        if "raw_data" in model_cols:
            kw["raw_data"] = data
        for data_key, col_name in field_map.items():
            if data_key in data and col_name in model_cols:
                val = data[data_key]
                col_type = getattr(model_class, col_name, None)
                if col_type is not None and isinstance(val, (list, dict)) and hasattr(col_type, "type"):
                    from sqlalchemy import String
                    if isinstance(col_type.type, String):
                        import json
                        val = json.dumps(val)
                kw[col_name] = val
        async with self._uow() as uow:
            repo: BaseRepository = getattr(uow, repo_attr, None)
            if repo is None:
                return {}
            existing = await repo.get_by_field("project_uuid", project_id)
            if existing:
                model = await repo.update(existing.uuid, **kw)
            else:
                model = await repo.create(project_uuid=project_id, **kw)
            return self._model_to_dict(model)


# ------------------------------------------------------------------
# Stage Routing — maps pipeline stage names to dedicated tables
# ------------------------------------------------------------------

_STAGE_HANDLERS: dict[str, Any] = {}
_STAGE_LOADERS: dict[str, Any] = {}


def _register_stage(
    stage_name: str,
    service: DatabaseService,
    save_method: str,
    load_method: str,
) -> None:
    _STAGE_HANDLERS[stage_name] = lambda svc, pid, data: getattr(svc, save_method)(pid, data)
    _STAGE_LOADERS[stage_name] = lambda svc, pid: getattr(svc, load_method)(pid)


# Register the standard pipeline stages
_STAGE_ROUTING = [
    ("metadata", "save_video", "get_video"),
    ("video", "save_video", "get_video"),
    ("transcript", "save_transcript", "get_transcript"),
    ("analysis", "save_analysis", "get_analysis"),
    ("knowledge_graph", "save_knowledge_graph", "get_knowledge_graph"),
    ("seo", "save_seo", "get_seo"),
    ("seo_intelligence", "save_seo", "get_seo"),
    ("outline", "save_outline", "get_outline"),
    ("sections", "save_sections", "get_sections"),
    ("draft", "save_draft", "get_draft"),
    ("review", "save_review", "get_review"),
    ("optimization", "save_optimization", "get_optimization"),
    ("export", "save_export", "get_export"),
]


def _init_routing():
    if _STAGE_HANDLERS:
        return
    dummy = DatabaseService.__new__(DatabaseService)
    for stage, save_method, load_method in _STAGE_ROUTING:
        _register_stage(stage, dummy, save_method, load_method)


_init_routing()


def _status_for_stage(stage: str) -> str:
    mapping = {
        "metadata": "fetching_metadata",
        "transcript": "fetching_transcript",
        "analysis": "ai_analysis",
        "knowledge_graph": "ai_analysis",
        "seo": "outline_generation",
        "seo_intelligence": "outline_generation",
        "outline": "outline_generation",
        "sections": "blog_generation",
        "merge": "blog_generation",
        "draft": "blog_generation",
        "review": "blog_review",
        "export": "exporting",
    }
    return mapping.get(stage, "queued")
