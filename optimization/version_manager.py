"""Version Manager — section versioning, history, and rollback point creation."""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from optimization.optimization_models import (
    SectionVersion, OptimizationType, OptimizationStatus,
)

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages section versioning, history, and rollback points."""

    def __init__(self, output_dir: str = "output"):
        self._output_dir = output_dir
        self._versions: dict[str, list[SectionVersion]] = {}
        self._version_counter: int = 0

    def create_version(
        self,
        section_index: int,
        section_heading: str,
        prompt: str,
        content_before: str,
        content_after: str,
        scores_before: dict[str, float],
        scores_after: dict[str, float],
        optimization_type: OptimizationType,
        retry_count: int = 0,
    ) -> SectionVersion:
        self._version_counter += 1
        version = SectionVersion(
            version_id=f"v{self._version_counter}_s{section_index}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            section_index=section_index,
            section_heading=section_heading,
            prompt=prompt,
            content_before=content_before,
            content_after=content_after,
            scores_before=scores_before,
            scores_after=scores_after,
            optimization_type=optimization_type,
            retry_count=retry_count,
            status=OptimizationStatus.SUCCESS,
        )

        key = f"section_{section_index}"
        if key not in self._versions:
            self._versions[key] = []
        self._versions[key].append(version)

        logger.debug(
            "[VersionManager] Created %s for section %d (%s)",
            version.version_id, section_index, optimization_type.value,
        )
        return version

    def get_latest_version(self, section_index: int) -> SectionVersion | None:
        versions = self._versions.get(f"section_{section_index}", [])
        return versions[-1] if versions else None

    def get_all_versions(self, section_index: int) -> list[SectionVersion]:
        return self._versions.get(f"section_{section_index}", [])

    def get_version_to_rollback(self, section_index: int) -> SectionVersion | None:
        versions = self._versions.get(f"section_{section_index}", [])
        if len(versions) <= 1:
            return None
        return versions[-2]

    def mark_rolled_back(self, version_id: str) -> None:
        for versions in self._versions.values():
            for v in versions:
                if v.version_id == version_id:
                    v.status = OptimizationStatus.ROLLED_BACK
                    return

    def persist_versions(self, project_id: str = "") -> str:
        directory = f"{self._output_dir}/versions"
        os.makedirs(directory, exist_ok=True)
        filename = f"optimization_versions_{project_id}.json" if project_id else "optimization_versions.json"
        path = os.path.join(directory, filename)

        all_versions = []
        for versions in self._versions.values():
            for v in versions:
                all_versions.append(v.model_dump())

        data = {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_versions": len(all_versions),
            "versions": all_versions,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("[VersionManager] Persisted %d versions to %s", len(all_versions), path)
        return path

    def load_versions(self, project_id: str = "") -> list[SectionVersion]:
        directory = f"{self._output_dir}/versions"
        filename = f"optimization_versions_{project_id}.json" if project_id else "optimization_versions.json"
        path = os.path.join(directory, filename)

        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            versions = [SectionVersion(**v) for v in data.get("versions", [])]
            key = f"section_{data.get('section_index', 0)}"
            self._versions[key] = versions
            return versions
        except Exception as exc:
            logger.warning("[VersionManager] Failed loading versions: %s", exc)
            return []

    def clear(self) -> None:
        self._versions.clear()
        self._version_counter = 0
