"""Draft Storage — atomic file system operations for draft persistence.

Project/
  draft/
    draft.md
    draft_v1.md
    draft_v2.md
    draft_metadata.json
    merge_log.json
    versions/
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from draft.draft_models import (
    DraftDocument,
    DraftMetadata,
    DraftVersion,
    MergeLogEntry,
    MergeStatus,
    utc_now,
    compute_checksum,
)

logger = logging.getLogger(__name__)


class DraftStorageError(Exception):
    pass


class DraftStorage:
    """Atomic file system storage for draft artifacts."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        self._base = Path(base_path) if base_path else Path.cwd()

    def draft_path(self, project_id: str) -> Path:
        return self._base / "projects" / project_id / "draft"

    def ensure_dirs(self, project_id: str) -> Path:
        base = self.draft_path(project_id)
        base.mkdir(parents=True, exist_ok=True)
        (base / "versions").mkdir(exist_ok=True)
        logger.debug("Ensured draft directories for project %s at %s", project_id, base)
        return base

    def save_draft(self, project_id: str, document: DraftDocument, version: int = 1) -> Path:
        base = self.ensure_dirs(project_id)
        filepath = base / f"draft_v{version}.md"
        content = document.content
        tmp = filepath.with_suffix(".tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            if filepath.exists():
                filepath.unlink()
            tmp.rename(filepath)
            latest = base / "draft.md"
            if latest.exists():
                latest.unlink()
            shutil.copy2(str(filepath), str(latest))
            logger.info("Saved draft v%d for project %s (%d bytes)", version, project_id, len(content))
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise DraftStorageError(f"Failed to save draft: {exc}") from exc
        return filepath

    def load_draft(self, project_id: str, version: int | None = None) -> str | None:
        base = self.draft_path(project_id)
        if version is not None:
            filepath = base / f"draft_v{version}.md"
        else:
            filepath = base / "draft.md"
        if not filepath.exists():
            return None
        try:
            return filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to load draft for %s: %s", project_id, exc)
            return None

    def load_draft_file(self, project_id: str, filename: str) -> str | None:
        base = self.draft_path(project_id)
        filepath = base / filename
        if not filepath.exists():
            return None
        try:
            return filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to load draft file %s: %s", filename, exc)
            return None

    def draft_exists(self, project_id: str, version: int | None = None) -> bool:
        base = self.draft_path(project_id)
        if version is not None:
            return (base / f"draft_v{version}.md").exists()
        return (base / "draft.md").exists()

    def list_draft_versions(self, project_id: str) -> list[int]:
        base = self.draft_path(project_id)
        if not base.exists():
            return []
        versions = []
        for f in base.iterdir():
            if f.name.startswith("draft_v") and f.suffix == ".md":
                try:
                    v = int(f.stem.split("_v")[1])
                    versions.append(v)
                except (ValueError, IndexError):
                    continue
        return sorted(versions)

    def save_metadata(self, project_id: str, metadata: DraftMetadata) -> Path:
        base = self.ensure_dirs(project_id)
        filepath = base / "draft_metadata.json"
        tmp = filepath.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(metadata.model_dump(), indent=2, default=str),
                encoding="utf-8",
            )
            if filepath.exists():
                filepath.unlink()
            tmp.rename(filepath)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise DraftStorageError(f"Failed to save draft metadata: {exc}") from exc
        return filepath

    def load_metadata(self, project_id: str) -> DraftMetadata | None:
        base = self.draft_path(project_id)
        filepath = base / "draft_metadata.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return DraftMetadata(**data)
        except (json.JSONDecodeError, OSError, Exception) as exc:
            logger.warning("Failed to load draft metadata for %s: %s", project_id, exc)
            return None

    def save_merge_log(self, project_id: str, entry: MergeLogEntry) -> Path:
        base = self.ensure_dirs(project_id)
        filepath = base / "merge_log.json"
        existing = []
        if filepath.exists():
            try:
                existing = json.loads(filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(entry.model_dump())
        tmp = filepath.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
            if filepath.exists():
                filepath.unlink()
            tmp.rename(filepath)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise DraftStorageError(f"Failed to save merge log: {exc}") from exc
        return filepath

    def load_merge_log(self, project_id: str) -> list[MergeLogEntry]:
        base = self.draft_path(project_id)
        filepath = base / "merge_log.json"
        if not filepath.exists():
            return []
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return [MergeLogEntry(**d) for d in data]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load merge log for %s: %s", project_id, exc)
            return []

    def save_version(self, project_id: str, version: DraftVersion) -> Path:
        base = self.ensure_dirs(project_id)
        version_dir = base / "versions"
        filepath = version_dir / f"draft_v{version.version_number}.json"
        tmp = filepath.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(version.model_dump(), indent=2, default=str),
                encoding="utf-8",
            )
            if filepath.exists():
                filepath.unlink()
            tmp.rename(filepath)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise DraftStorageError(f"Failed to save draft version: {exc}") from exc
        return filepath

    def load_version(self, project_id: str, version_number: int) -> DraftVersion | None:
        base = self.draft_path(project_id)
        filepath = base / "versions" / f"draft_v{version_number}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return DraftVersion(**data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load version %d for %s: %s", version_number, project_id, exc)
            return None

    def list_versions(self, project_id: str) -> list[DraftVersion]:
        base = self.draft_path(project_id)
        version_dir = base / "versions"
        if not version_dir.exists():
            return []
        versions = []
        for f in sorted(version_dir.iterdir(), key=lambda p: p.name):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    versions.append(DraftVersion(**data))
                except Exception:
                    continue
        return versions

    def delete_draft(self, project_id: str, version: int | None = None) -> bool:
        base = self.draft_path(project_id)
        if not base.exists():
            return False
        if version is not None:
            filepath = base / f"draft_v{version}.md"
            if filepath.exists():
                filepath.unlink()
                return True
            return False
        shutil.rmtree(str(base), ignore_errors=True)
        return True

    def get_storage_usage(self, project_id: str) -> int:
        base = self.draft_path(project_id)
        if not base.exists():
            return 0
        total = 0
        for f in base.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total

    def compute_draft_checksum(self, project_id: str, version: int) -> str:
        content = self.load_draft(project_id, version)
        if content is None:
            return ""
        return compute_checksum(content)
