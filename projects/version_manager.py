"""Version Manager — tracks project versions with rollback support.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Any

from projects.project_models import Version, utc_now
from projects.uuid_manager import UUIDManager
from projects.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages version history for projects."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage

    def create_version(
        self,
        project_id: str,
        project_data: dict,
        reason: str = "auto_save",
        changed_files: list[str] | None = None,
    ) -> Version:
        versions = self._load_versions(project_id)
        last_version = versions[-1] if versions else {}
        version = Version(
            version_id=UUIDManager.generate_version_id(),
            version_number=(last_version.get("version_number", 0) or 0) + 1,
            created_at=utc_now(),
            reason=reason,
            changed_files=changed_files or [],
            checksum=UUIDManager.checksum(json.dumps(project_data, default=str)),
            parent_version=last_version.get("version_id", ""),
            rollback_data=deepcopy(project_data) if reason != "auto_save" else {},
        )
        versions.append(version.model_dump())
        self._storage.save_json(project_id, "versions.json", versions)
        return version

    def _load_versions(self, project_id: str) -> list[dict]:
        data = self._storage.load_json(project_id, "versions.json")
        return data if isinstance(data, list) else []

    def get_versions(self, project_id: str) -> list[Version]:
        return [Version(**v) for v in self._load_versions(project_id)]

    def get_latest_version(self, project_id: str) -> Version | None:
        versions = self._load_versions(project_id)
        if not versions:
            return None
        return Version(**versions[-1])

    def get_version(self, project_id: str, version_number: int) -> Version | None:
        versions = self._load_versions(project_id)
        for v in versions:
            if v.get("version_number") == version_number:
                return Version(**v)
        return None

    def get_version_by_id(self, project_id: str, version_id: str) -> Version | None:
        versions = self._load_versions(project_id)
        for v in versions:
            if v.get("version_id") == version_id:
                return Version(**v)
        return None

    def can_rollback(self, project_id: str, version_number: int) -> bool:
        version = self.get_version(project_id, version_number)
        if version is None:
            return False
        return bool(version.rollback_data)

    def get_rollback_data(self, project_id: str, version_number: int) -> dict | None:
        version = self.get_version(project_id, version_number)
        if version is None:
            return None
        return version.rollback_data or None

    def prune_versions(self, project_id: str, keep: int = 10) -> int:
        versions = self._load_versions(project_id)
        if len(versions) <= keep:
            return 0
        pruned = len(versions) - keep
        versions = versions[-keep:]
        self._storage.save_json(project_id, "versions.json", versions)
        logger.info("Pruned %d old versions for project %s", pruned, project_id)
        return pruned
