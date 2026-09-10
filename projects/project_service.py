"""Project Service — high-level interface for API controllers.

All existing endpoints continue to work unchanged.
New project-aware endpoints use this service.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from projects.project_manager import ProjectManager
from projects.project_models import (
    ArtifactInfo,
    PipelineStage,
    Project,
    ProjectSettings,
    ProjectSummary,
    ProjectStatus,
    utc_now,
)

logger = logging.getLogger(__name__)


class ProjectService:
    """High-level service for API integration.

    Does NOT modify any existing pipeline code.
    Does NOT replace any existing API endpoints.
    """

    def __init__(self) -> None:
        self._pm = ProjectManager()

    @property
    def manager(self) -> ProjectManager:
        return self._pm

    def create_from_url(self, url: str, video_id: str = "") -> dict[str, Any]:
        project = self._pm.create_project(url=url, video_id=video_id)
        return self._to_api_response(project)

    def get(self, project_id: str) -> dict[str, Any] | None:
        project = self._pm.get_project(project_id)
        if project is None:
            return None
        return self._to_api_response(project)

    def list_all(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        projects = self._pm.list_projects(limit=limit, offset=offset)
        return [self._to_summary(p) for p in projects]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        projects = self._pm.search_projects(query, limit=limit)
        return [self._to_summary(p) for p in projects]

    def delete(self, project_id: str, permanent: bool = False) -> dict[str, Any]:
        success = self._pm.delete_project(project_id, permanent=permanent)
        return {"success": success, "project_id": project_id}

    def resume(self, project_id: str) -> dict[str, Any] | None:
        project = self._pm.resume_project(project_id)
        if project is None:
            return None
        return self._to_api_response(project)

    def pause(self, project_id: str) -> dict[str, Any]:
        success = self._pm.pause_project(project_id)
        return {"success": success, "project_id": project_id}

    def cancel(self, project_id: str) -> dict[str, Any]:
        success = self._pm.cancel_project(project_id)
        return {"success": success, "project_id": project_id}

    def get_history(self, project_id: str, limit: int = 50) -> list[dict[str, Any]]:
        from projects.history_manager import HistoryManager
        hm = HistoryManager(self._pm.storage)
        entries = hm.get_history(project_id, limit=limit)
        return [e.model_dump() for e in entries]

    def get_checkpoints(self, project_id: str) -> list[dict[str, Any]]:
        from projects.checkpoint_manager import CheckpointManager
        cm = CheckpointManager(self._pm.storage)
        checkpoints = cm._load_checkpoints(project_id)
        return checkpoints

    def get_versions(self, project_id: str) -> list[dict[str, Any]]:
        from projects.version_manager import VersionManager
        vm = VersionManager(self._pm.storage)
        versions = vm.get_versions(project_id)
        return [v.model_dump() for v in versions]

    def update_settings(self, project_id: str, settings: dict[str, Any]) -> dict[str, Any] | None:
        project = self._pm.get_project(project_id)
        if project is None:
            return None
        for key, value in settings.items():
            if hasattr(project.settings, key):
                setattr(project.settings, key, value)
        self._pm._save(project)
        return self._to_api_response(project)

    def restore_version(self, project_id: str, version_number: int) -> dict[str, Any] | None:
        from projects.version_manager import VersionManager
        vm = VersionManager(self._pm.storage)
        data = vm.get_rollback_data(project_id, version_number)
        if data is None:
            return None
        project = Project(**data)
        self._pm._save(project)
        return self._to_api_response(project)

    def validate(self, project_id: str) -> list[dict[str, Any]]:
        from projects.recovery_engine import RecoveryEngine
        re = RecoveryEngine(self._pm.storage, self._pm._checkpoint_mgr)
        return re.validate_artifacts(project_id)

    def get_stats(self) -> dict[str, Any]:
        projects = self._pm.list_projects(limit=1000)
        total = len(projects)
        completed = sum(1 for p in projects if p.status == ProjectStatus.COMPLETED)
        failed = sum(1 for p in projects if p.status == ProjectStatus.FAILED)
        running = sum(1 for p in projects if p.status in (
            ProjectStatus.QUEUED, ProjectStatus.FETCHING_METADATA,
            ProjectStatus.FETCHING_TRANSCRIPT, ProjectStatus.AI_ANALYSIS,
            ProjectStatus.OUTLINE_GENERATION, ProjectStatus.BLOG_GENERATION,
            ProjectStatus.BLOG_REVIEW, ProjectStatus.EXPORTING,
        ))
        return {
            "total_projects": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": round(completed / total * 100, 1) if total > 0 else 0,
        }

    # --- Internal helpers ---

    def _to_api_response(self, project: Project) -> dict[str, Any]:
        return {
            "project_id": project.project_id,
            "short_id": project.short_id,
            "name": project.name,
            "url": project.url,
            "video_id": project.video_id,
            "thumbnail": project.thumbnail,
            "channel_title": project.channel_title,
            "channel_id": project.channel_id,
            "status": project.status.value,
            "version": project.version,
            "language": project.language,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "completed_at": project.completed_at,
            "pipeline": project.pipeline.model_dump(),
            "settings": project.settings.model_dump(),
            "statistics": project.statistics.model_dump(),
            "artifacts": [a.model_dump() for a in project.artifacts],
            "error": project.error,
            "warnings": project.warnings,
            "tags": project.tags,
            "notes": project.notes,
        }

    def _to_summary(self, project: Project) -> dict[str, Any]:
        return {
            "project_id": project.project_id,
            "short_id": project.short_id,
            "name": project.name,
            "video_id": project.video_id,
            "url": project.url,
            "thumbnail": project.thumbnail,
            "status": project.status.value,
            "current_stage": project.pipeline.current_stage,
            "overall_progress_pct": round(project.pipeline.overall_progress_pct, 1),
            "version": project.version,
            "language": project.language,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "completed_at": project.completed_at,
            "error": project.error,
            "tags": project.tags,
            "quality_score": project.statistics.quality_score,
            "seo_score": project.statistics.seo_score,
        }
