"""Checkpoint Manager — creates checkpoints after each stage, enables resume.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from projects.project_models import Checkpoint, PipelineStage, utc_now
from projects.uuid_manager import UUIDManager
from projects.storage_manager import StorageManager

logger = logging.getLogger(__name__)

CHECKPOINT_FILES = {
    "project": "project.json",
    "metadata": "metadata.json",
    "transcript": "transcript.json",
    "analysis": "analysis.json",
    "outline": "outline.json",
    "blog": "blog.json",
    "review": "review.json",
    "export": "export.json",
}


class CheckpointManager:
    """Manages checkpoints for crash recovery and resume."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage

    def create_checkpoint(
        self,
        project_id: str,
        stage: PipelineStage | str,
        reason: str = "stage_complete",
        state_snapshot: dict | None = None,
    ) -> Checkpoint:
        stage_key = stage.value if isinstance(stage, PipelineStage) else stage
        cp = Checkpoint(
            checkpoint_id=UUIDManager.generate_checkpoint_id(),
            stage=stage_key,
            created_at=utc_now(),
            reason=reason,
            state_snapshot=state_snapshot or {},
        )
        for name, filename in CHECKPOINT_FILES.items():
            if self._storage.file_exists(project_id, filename):
                cp.files[name] = filename
                content = self._storage.load_json(project_id, filename)
                if content:
                    cp.checksums[name] = UUIDManager.checksum(json.dumps(content, default=str))
        self._save_checkpoint(project_id, cp)
        return cp

    def _save_checkpoint(self, project_id: str, cp: Checkpoint) -> None:
        checkpoints = self._load_checkpoints(project_id)
        checkpoints.append(cp.model_dump())
        self._storage.save_json(project_id, "checkpoints.json", checkpoints)

    def _load_checkpoints(self, project_id: str) -> list[dict]:
        data = self._storage.load_json(project_id, "checkpoints.json")
        return data if isinstance(data, list) else []

    def get_latest_checkpoint(self, project_id: str) -> Checkpoint | None:
        checkpoints = self._load_checkpoints(project_id)
        if not checkpoints:
            return None
        return Checkpoint(**checkpoints[-1])

    def get_checkpoints_for_stage(self, project_id: str, stage: str) -> list[Checkpoint]:
        checkpoints = self._load_checkpoints(project_id)
        return [Checkpoint(**c) for c in checkpoints if c.get("stage") == stage]

    def get_latest_checkpoint_before(self, project_id: str, stage: str) -> Checkpoint | None:
        checkpoints = self._load_checkpoints(project_id)
        stage_index = -1
        for i, s in enumerate(PipelineStage):
            if s.value == stage:
                stage_index = i
                break
        candidates = [
            Checkpoint(**c) for c in checkpoints
            if self._stage_index(c.get("stage", "")) <= stage_index
        ]
        return candidates[-1] if candidates else None

    @staticmethod
    def _stage_index(stage: str) -> int:
        for i, s in enumerate(PipelineStage):
            if s.value == stage:
                return i
        return -1

    def validate_checkpoint(self, project_id: str, cp: Checkpoint) -> bool:
        for name, filename in cp.files.items():
            if not self._storage.file_exists(project_id, filename):
                logger.warning("Checkpoint file missing: %s", filename)
                return False
            content = self._storage.load_json(project_id, filename)
            if content is None:
                return False
            expected = cp.checksums.get(name, "")
            if expected and UUIDManager.checksum(json.dumps(content, default=str)) != expected:
                logger.warning("Checkpoint checksum mismatch: %s", filename)
                return False
        return True

    def delete_checkpoints(self, project_id: str, keep_latest: int = 0) -> None:
        checkpoints = self._load_checkpoints(project_id)
        if keep_latest > 0 and len(checkpoints) > keep_latest:
            checkpoints = checkpoints[-keep_latest:]
            self._storage.save_json(project_id, "checkpoints.json", checkpoints)
        else:
            cp_file = self._storage.project_file(project_id, "checkpoints.json")
            if cp_file.exists():
                cp_file.unlink()
