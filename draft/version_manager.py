"""Draft Version Manager — manages version history for assembled drafts.

Every merge creates an immutable version snapshot.
Supports unlimited version history with rollback capability.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from draft.draft_models import (
    DraftDocument,
    DraftVersion,
    utc_now,
    compute_checksum,
)

logger = logging.getLogger(__name__)


class DraftVersionManager:
    """Manages draft versioning with rollback support."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def create_version(
        self,
        project_id: str,
        document: DraftDocument,
        modified_sections: list[str] | None = None,
    ) -> DraftVersion:
        versions = self._storage.list_versions(project_id)
        last_version_number = max((v.version_number for v in versions), default=0)

        content_hash = hashlib.sha256(
            document.content.encode("utf-8")
        ).hexdigest()[:32]

        version = DraftVersion(
            version_number=last_version_number + 1,
            created_at=utc_now(),
            content_hash=content_hash,
            modified_sections=modified_sections or [],
            checksum=compute_checksum(document.content),
            merge_metadata={
                "section_count": document.section_count,
                "word_count": document.word_count,
                "toc_entries": len(document.toc),
            },
        )

        self._storage.save_version(project_id, version)
        logger.info(
            "Created draft version %d for project %s",
            version.version_number, project_id,
        )
        return version

    def get_latest_version(self, project_id: str) -> DraftVersion | None:
        versions = self._storage.list_versions(project_id)
        return max(versions, key=lambda v: v.version_number) if versions else None

    def get_version(self, project_id: str, version_number: int) -> DraftVersion | None:
        return self._storage.load_version(project_id, version_number)

    def get_versions(self, project_id: str) -> list[DraftVersion]:
        return self._storage.list_versions(project_id)

    def rollback(
        self,
        project_id: str,
        target_version: int,
    ) -> str | None:
        content = self._storage.load_draft(project_id, target_version)
        if content is None:
            logger.warning(
                "Cannot rollback: version %d not found for project %s",
                target_version, project_id,
            )
            return None

        latest_version = self.get_latest_version(project_id)
        current_number = latest_version.version_number if latest_version else 0

        metadata = self._storage.load_metadata(project_id)
        if metadata:
            metadata.draft_version = current_number + 1
            metadata.updated_at = utc_now()

        version = DraftVersion(
            version_number=current_number + 1,
            created_at=utc_now(),
            content_hash=compute_checksum(content),
            modified_sections=["__rollback_from_v" + str(target_version)],
            checksum=compute_checksum(content),
            merge_metadata={
                "rollback": True,
                "rollback_from": target_version,
            },
        )

        self._storage.save_draft(project_id, target_version, version.version_number)
        self._storage.save_version(project_id, version)
        if metadata:
            self._storage.save_metadata(project_id, metadata)

        logger.info(
            "Rollback to version %d created new version %d for project %s",
            target_version, version.version_number, project_id,
        )
        return content

    def prune_versions(self, project_id: str, keep: int = 10) -> int:
        versions = self._storage.list_versions(project_id)
        if len(versions) <= keep:
            return 0

        versions.sort(key=lambda v: v.version_number)
        to_prune = versions[:-keep]
        pruned = 0

        for v in to_prune:
            draft_path = self._storage.draft_path(project_id)
            filepath = draft_path / f"draft_v{v.version_number}.md"
            if filepath.exists():
                filepath.unlink()
                pruned += 1
            ver_path = draft_path / "versions" / f"draft_v{v.version_number}.json"
            if ver_path.exists():
                ver_path.unlink()

        logger.info("Pruned %d old draft versions for project %s", pruned, project_id)
        return pruned

    def can_rollback(self, project_id: str, version_number: int) -> bool:
        version = self.get_version(project_id, version_number)
        if version is None:
            return False
        content = self._storage.load_draft(project_id, version_number)
        return content is not None

    def version_count(self, project_id: str) -> int:
        return len(self._storage.list_versions(project_id))

    def latest_version_number(self, project_id: str) -> int:
        latest = self.get_latest_version(project_id)
        return latest.version_number if latest else 0
