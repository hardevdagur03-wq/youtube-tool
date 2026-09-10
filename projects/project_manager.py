"""Project Manager — orchestrates project lifecycle around existing pipelines.

This is the central orchestration layer.
It does NOT modify any existing pipeline code.
It wraps existing pipelines with project-level lifecycle management.
"""

from __future__ import annotations

import json
import logging
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from projects.project_models import (
    ArtifactInfo,
    Checkpoint,
    HistoryEntry,
    PipelineStage,
    PipelineStatus,
    Project,
    ProjectSettings,
    ProjectStatistics,
    ProjectStatus,
    StageInfo,
    StageStatus,
    Version,
    utc_now,
)
from projects.uuid_manager import UUIDManager
from projects import storage_manager as storage_mod
from projects.progress_tracker import ProgressTracker
from projects.checkpoint_manager import CheckpointManager
from projects.version_manager import VersionManager
from projects.history_manager import HistoryManager
from projects.recovery_engine import RecoveryEngine

logger = logging.getLogger(__name__)


class ProjectManager:
    """Central orchestrator for project lifecycle.

    Wraps existing pipelines without modifying them.
    """

    def __init__(self) -> None:
        self._storage = storage_mod.StorageManager()
        self._checkpoint_mgr = CheckpointManager(self._storage)
        self._version_mgr = VersionManager(self._storage)
        self._history_mgr = HistoryManager(self._storage)
        self._recovery = RecoveryEngine(self._storage, self._checkpoint_mgr)
        self._progress = ProgressTracker()

    @property
    def storage(self) -> storage_mod.StorageManager:
        return self._storage

    def create_project(
        self,
        url: str = "",
        video_id: str = "",
        name: str = "",
        settings: ProjectSettings | None = None,
    ) -> Project:
        project_id = UUIDManager.generate_project_id()
        short_id = UUIDManager.generate_short_id()
        now = utc_now()
        folder = UUIDManager.generate_folder_name(project_id, video_id)

        project = Project(
            project_id=project_id,
            short_id=short_id,
            name=name or video_id or "Untitled Project",
            url=url,
            video_id=video_id,
            status=ProjectStatus.CREATED,
            version=1,
            created_at=now,
            updated_at=now,
            folder_path=folder,
            settings=settings or ProjectSettings(),
        )
        self._init_pipeline_stages(project)
        self._storage.create_project_dir(project_id)
        self._save(project)
        self._history_mgr.record(
            project_id, "project_created", details=f"URL: {url}",
        )
        self._version_mgr.create_version(project_id, project.model_dump(), reason="project_created")
        logger.info("Project created: %s (%s)", project_id, url)
        return project

    def _init_pipeline_stages(self, project: Project) -> None:
        for stage_enum in PipelineStage:
            key = stage_enum.value
            project.pipeline.stages[key] = StageInfo(
                stage=stage_enum,
                status=StageStatus.PENDING,
            )
        project.pipeline.current_stage = PipelineStage.METADATA.value

    def get_project(self, project_id: str) -> Project | None:
        data = self._storage.load_json(project_id, "project.json")
        if data is None:
            return None
        return Project(**data)

    def _save(self, project: Project) -> None:
        project.updated_at = utc_now()
        self._storage.save_json(project.project_id, "project.json", project.model_dump())

    def update_project(self, project_id: str, updates: dict[str, Any]) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for key, value in updates.items():
            if hasattr(project, key) and key not in ("project_id", "created_at"):
                setattr(project, key, value)
        self._save(project)
        return project

    def delete_project(self, project_id: str, permanent: bool = False) -> bool:
        project = self.get_project(project_id)
        if project is None:
            return False
        self._storage.delete_project(project_id, permanent=permanent)
        logger.info("Project deleted: %s (permanent=%s)", project_id, permanent)
        return True

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[Project]:
        ids = self._storage.list_projects()
        ids = ids[offset:offset + limit]
        projects = []
        for pid in ids:
            p = self.get_project(pid)
            if p:
                projects.append(p)
        return projects

    def search_projects(self, query: str, limit: int = 20) -> list[Project]:
        query = query.lower()
        projects = self.list_projects(limit=200)
        results = []
        for p in projects:
            if (query in p.name.lower()
                or query in p.video_id.lower()
                or query in p.project_id.lower()
                or query in p.short_id.lower()
                or any(query in t.lower() for t in p.tags)):
                results.append(p)
        return results[:limit]

    # --- Pipeline Stage Wrappers ---

    def stage_completed(self, project_id: str, stage: PipelineStage | str) -> None:
        project = self.get_project(project_id)
        if project is None:
            return
        key = stage.value if isinstance(stage, PipelineStage) else stage
        if key in project.pipeline.stages:
            project.pipeline.stages[key].status = StageStatus.COMPLETED
            project.pipeline.stages[key].progress_pct = 100.0
            project.pipeline.stages[key].finished_at = utc_now()
        self._advance_pipeline(project)
        self._save(project)
        self._history_mgr.record(project_id, "stage_completed", stage=key)
        self._checkpoint_mgr.create_checkpoint(project_id, key, "stage_completed")

    def stage_failed(self, project_id: str, stage: PipelineStage | str, error: str = "") -> None:
        project = self.get_project(project_id)
        if project is None:
            return
        key = stage.value if isinstance(stage, PipelineStage) else stage
        if key in project.pipeline.stages:
            project.pipeline.stages[key].status = StageStatus.FAILED
            project.pipeline.stages[key].error = error
        project.status = ProjectStatus.FAILED
        project.error = error
        self._save(project)
        self._history_mgr.record(project_id, "stage_failed", stage=key, errors=[error])

    def stage_started(self, project_id: str, stage: PipelineStage | str) -> None:
        project = self.get_project(project_id)
        if project is None:
            return
        key = stage.value if isinstance(stage, PipelineStage) else stage
        if key in project.pipeline.stages:
            project.pipeline.stages[key].status = StageStatus.RUNNING
            project.pipeline.stages[key].started_at = utc_now()
        project.pipeline.current_stage = key
        project.status = self._status_for_stage(key)
        self._save(project)
        self._history_mgr.record(project_id, "stage_started", stage=key)

    def _status_for_stage(self, stage: str) -> ProjectStatus:
        mapping = {
            "metadata": ProjectStatus.FETCHING_METADATA,
            "transcript": ProjectStatus.FETCHING_TRANSCRIPT,
            "analysis": ProjectStatus.AI_ANALYSIS,
            "knowledge_graph": ProjectStatus.AI_ANALYSIS,
            "seo": ProjectStatus.OUTLINE_GENERATION,
            "seo_intelligence": ProjectStatus.OUTLINE_GENERATION,
            "outline": ProjectStatus.OUTLINE_GENERATION,
            "sections": ProjectStatus.BLOG_GENERATION,
            "merge": ProjectStatus.BLOG_GENERATION,
            "blog": ProjectStatus.BLOG_GENERATION,
            "review": ProjectStatus.BLOG_REVIEW,
            "export": ProjectStatus.EXPORTING,
        }
        return mapping.get(stage, ProjectStatus.QUEUED)

    def update_stage_progress(self, project_id: str, stage: PipelineStage | str, progress_pct: float, detail: str = "") -> None:
        project = self.get_project(project_id)
        if project is None:
            return
        key = stage.value if isinstance(stage, PipelineStage) else stage
        if key in project.pipeline.stages:
            project.pipeline.stages[key].progress_pct = progress_pct
        self._update_overall_progress(project)
        self._save(project)

    def _advance_pipeline(self, project: Project) -> None:
        next_stage = self._progress.next_stage(project.pipeline.stages)
        if next_stage:
            project.pipeline.current_stage = next_stage
        else:
            all_complete = all(
                info.status == StageStatus.COMPLETED
                for info in project.pipeline.stages.values()
            )
            if all_complete:
                project.status = ProjectStatus.COMPLETED
                project.completed_at = utc_now()

    def _update_overall_progress(self, project: Project) -> None:
        stages_dict = {k: StageInfo(**v) if isinstance(v, dict) else v
                       for k, v in project.pipeline.stages.items()}
        pct = self._progress.compute_overall_progress(stages_dict)
        project.pipeline.overall_progress_pct = pct

    def complete_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project is None:
            return False
        project.status = ProjectStatus.COMPLETED
        project.completed_at = utc_now()
        for key in project.pipeline.stages:
            if project.pipeline.stages[key].status != StageStatus.COMPLETED:
                project.pipeline.stages[key].status = StageStatus.COMPLETED
        project.pipeline.overall_progress_pct = 100.0
        self._save(project)
        self._history_mgr.record(project_id, "project_completed")
        self._version_mgr.create_version(project_id, project.model_dump(), reason="project_completed")
        logger.info("Project completed: %s", project_id)
        return True

    # --- Artifact Management ---

    def store_artifact(self, project_id: str, artifact: ArtifactInfo) -> None:
        project = self.get_project(project_id)
        if project is None:
            return
        project.artifacts.append(artifact)
        self._save(project)

    def store_stage_data(self, project_id: str, stage: str, data: dict) -> None:
        if hasattr(Project, stage):
            self._storage.save_json(project_id, f"{stage}.json", data)

    def load_stage_data(self, project_id: str, stage: str) -> dict | None:
        return self._storage.load_json(project_id, f"{stage}.json")

    # --- Resume ---

    def resume_project(self, project_id: str) -> Project | None:
        needs_recovery, reason = self._recovery.needs_recovery(project_id)
        project = self.get_project(project_id)
        if project is None:
            return None

        if needs_recovery:
            logger.info("Project %s needs recovery: %s", project_id, reason)
            project = self._recovery.recover(project_id)
            if project is None:
                return None

        project.status = ProjectStatus.RESUMED
        self._save(project)
        self._history_mgr.record(project_id, "project_resumed")
        logger.info("Project resumed: %s", project_id)
        return project

    def pause_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project is None:
            return False
        project.status = ProjectStatus.PAUSED
        project.pipeline.is_paused = True
        self._save(project)
        self._history_mgr.record(project_id, "project_paused")
        logger.info("Project paused: %s", project_id)
        return True

    def cancel_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project is None:
            return False
        project.status = ProjectStatus.CANCELLED
        for key in project.pipeline.stages:
            if project.pipeline.stages[key].status == StageStatus.RUNNING:
                project.pipeline.stages[key].status = StageStatus.PENDING
        self._save(project)
        self._history_mgr.record(project_id, "project_cancelled")
        logger.info("Project cancelled: %s", project_id)
        return True

    # --- Export (legacy support) ---

    def find_or_create_by_video(self, video_id: str, url: str = "") -> Project:
        projects = self.list_projects(limit=200)
        for p in projects:
            if p.video_id == video_id and p.status not in (
                ProjectStatus.FAILED, ProjectStatus.CANCELLED,
            ):
                return p
        name = f"Video {video_id}"
        return self.create_project(url=url, video_id=video_id, name=name)

    def get_summary(self, project_id: str) -> dict[str, Any] | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        return {
            "project_id": project.project_id,
            "short_id": project.short_id,
            "name": project.name,
            "video_id": project.video_id,
            "url": project.url,
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
            "stats": {
                "word_count": project.statistics.word_count,
                "blog_word_count": project.statistics.blog_word_count,
                "total_api_calls": project.statistics.total_api_calls,
                "cache_hits": project.statistics.cache_hits,
            },
        }
