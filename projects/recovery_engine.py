"""Recovery Engine — validates artifacts, recovers state after crashes.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from projects.checkpoint_manager import CheckpointManager
from projects.storage_manager import StorageManager
from projects.project_models import (
    Checkpoint,
    PipelineStage,
    StageInfo,
    StageStatus,
    Project,
    utc_now,
)

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """Validates project state and recovers from crashes."""

    def __init__(self, storage: StorageManager, checkpoint_mgr: CheckpointManager) -> None:
        self._storage = storage
        self._checkpoint_mgr = checkpoint_mgr

    def needs_recovery(self, project_id: str) -> tuple[bool, str]:
        """Check if a project needs recovery after a crash."""
        project_data = self._storage.load_json(project_id, "project.json")
        if project_data is None:
            return False, "no_project"

        status = project_data.get("status", "")
        if status in ("completed", "failed", "cancelled"):
            return False, "terminal_state"

        pipeline = project_data.get("pipeline", {})
        current = pipeline.get("current_stage", "")
        if not current:
            return False, "no_pipeline"

        stages = pipeline.get("stages", {})
        running_stages = [
            k for k, v in stages.items()
            if v.get("status") in ("running", "pending")
        ]
        if not running_stages:
            return False, "all_complete"

        return True, f"unfinished_stages:{','.join(running_stages)}"

    def recover(self, project_id: str) -> Project | None:
        """Attempt to recover a project after a crash."""
        project_data = self._storage.load_json(project_id, "project.json")
        if project_data is None:
            logger.error("Cannot recover project %s: project.json missing", project_id)
            return None

        project = Project(**project_data)
        latest_cp = self._checkpoint_mgr.get_latest_checkpoint(project_id)

        if latest_cp and self._checkpoint_mgr.validate_checkpoint(project_id, latest_cp):
            logger.info(
                "Recovering project %s from checkpoint %s (stage: %s)",
                project_id, latest_cp.checkpoint_id, latest_cp.stage,
            )
            project = self._restore_from_checkpoint(project_id, latest_cp, project)
        else:
            logger.info(
                "Recovering project %s from last known state (no valid checkpoint)",
                project_id,
            )
            project = self._recover_from_state(project)

        self._storage.save_json(project_id, "project.json", project.model_dump())
        return project

    def _restore_from_checkpoint(self, project_id: str, cp: Checkpoint, project: Project) -> Project:
        for stage_enum in PipelineStage:
            key = stage_enum.value
            if key in cp.state_snapshot.get("completed_stages", []):
                if key in project.pipeline.stages:
                    project.pipeline.stages[key].status = StageStatus.COMPLETED
            elif key == cp.stage:
                if key in project.pipeline.stages:
                    project.pipeline.stages[key].status = StageStatus.PENDING
            else:
                stage_order = [s.value for s in PipelineStage]
                cp_idx = stage_order.index(cp.stage) if cp.stage in stage_order else -1
                curr_idx = stage_order.index(key) if key in stage_order else -1
                if curr_idx > cp_idx:
                    if key in project.pipeline.stages:
                        project.pipeline.stages[key].status = StageStatus.PENDING
        project.pipeline.current_stage = cp.stage
        project.status = project.status
        project.error = ""
        return project

    def _recover_from_state(self, project: Project) -> Project:
        running_found = False
        for stage_enum in PipelineStage:
            key = stage_enum.value
            info = project.pipeline.stages.get(key)
            if info is None:
                continue
            if info.status == StageStatus.RUNNING:
                info.status = StageStatus.PENDING
                if not running_found:
                    project.pipeline.current_stage = key
                    running_found = True
            elif info.status == StageStatus.COMPLETED:
                continue
            elif not running_found:
                project.pipeline.current_stage = key
                running_found = True
        if not running_found:
            first_pending = ProgressTrackerCompat.next_stage(project.pipeline.stages)
            if first_pending:
                project.pipeline.current_stage = first_pending
        return project

    def validate_artifacts(self, project_id: str) -> list[dict]:
        issues = []
        expected_files = {
            "project": "project.json",
            "metadata": "metadata.json",
            "transcript": "transcript.json",
            "analysis": "analysis.json",
            "outline": "outline.json",
            "blog": "blog.json",
            "review": "review.json",
            "export": "export.json",
        }
        project_data = self._storage.load_json(project_id, "project.json")
        if project_data is None:
            return [{"severity": "error", "message": "project.json missing"}]

        pipeline = project_data.get("pipeline", {})
        stages = pipeline.get("stages", {})

        for stage_name, filename in expected_files.items():
            stage_info = stages.get(stage_name)
            if stage_info and stage_info.get("status") == "completed":
                if not self._storage.file_exists(project_id, filename):
                    issues.append({
                        "severity": "error",
                        "message": f"Stage '{stage_name}' marked complete but {filename} missing",
                        "stage": stage_name,
                    })
                else:
                    data = self._storage.load_json(project_id, filename)
                    if data is None:
                        issues.append({
                            "severity": "error",
                            "message": f"{filename} is corrupted",
                            "stage": stage_name,
                        })
        return issues


class ProgressTrackerCompat:
    @staticmethod
    def next_stage(stages: dict[str, Any]) -> str:
        for stage_enum in PipelineStage:
            key = stage_enum.value
            info = stages.get(key)
            if info is None:
                return key
            status = info if isinstance(info, str) else (info.status if hasattr(info, "status") else info.get("status", ""))
            if status in ("pending", ""):
                return key
        return ""
