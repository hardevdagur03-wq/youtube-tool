from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from publishing.models import ExportVersion

logger = logging.getLogger(__name__)


class VersionManager:
    def __init__(self, base_dir: str | Path = "exports_versions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def next_version(self, project_id: str) -> int:
        versions_path = self.base_dir / project_id
        if not versions_path.exists():
            return 1
        existing = list(versions_path.iterdir())
        version_numbers = []
        for p in existing:
            if p.is_dir() and p.name.isdigit():
                version_numbers.append(int(p.name))
        return max(version_numbers) + 1 if version_numbers else 1

    def save(self, project_id: str, version: int,
             files: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> ExportVersion:
        version_dir = self.base_dir / project_id / str(version)
        version_dir.mkdir(parents=True, exist_ok=True)

        export_version = ExportVersion(
            project_id=project_id,
            version=version,
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            files=files,
            metadata=metadata or {},
            checksum=self._compute_checksum(files),
        )

        meta_path = version_dir / "version.json"
        meta_path.write_text(export_version.model_dump_json(indent=2), encoding="utf-8")

        return export_version

    def get(self, project_id: str, version: int) -> ExportVersion | None:
        meta_path = self.base_dir / project_id / str(version) / "version.json"
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return ExportVersion(**data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load version %d for project %s: %s", version, project_id, e)
            return None

    def list_versions(self, project_id: str) -> list[ExportVersion]:
        versions: list[ExportVersion] = []
        project_dir = self.base_dir / project_id
        if not project_dir.exists():
            return versions

        for version_dir in sorted(
            (d for d in project_dir.iterdir() if d.is_dir() and d.name.isdigit()),
            key=lambda d: int(d.name), reverse=True,
        ):
            meta_path = version_dir / "version.json"
            if meta_path.exists():
                try:
                    data = json.loads(meta_path.read_text(encoding="utf-8"))
                    versions.append(ExportVersion(**data))
                except (json.JSONDecodeError, KeyError):
                    continue

        return versions

    def get_latest_version_number(self, project_id: str) -> int:
        versions = self.list_versions(project_id)
        return versions[0].version if versions else 0

    def delete_version(self, project_id: str, version: int) -> bool:
        version_dir = self.base_dir / project_id / str(version)
        if not version_dir.exists():
            return False
        shutil.rmtree(str(version_dir))
        return True

    @staticmethod
    def _compute_checksum(files: list[dict[str, Any]]) -> str:
        import hashlib
        content = json.dumps(files, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
