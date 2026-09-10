"""Storage Manager — file system operations for project persistence.

All reads and writes use atomic operations to prevent corruption.
No existing code is modified.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

PROJECTS_ROOT = settings.base_dir / "projects"


class StorageError(Exception):
    pass


class StorageManager:
    """Manages project directories and files on disk."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or PROJECTS_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def project_path(self, project_id: str) -> Path:
        return self._root / project_id

    def project_file(self, project_id: str, filename: str) -> Path:
        return self.project_path(project_id) / filename

    def create_project_dir(self, project_id: str) -> Path:
        path = self.project_path(project_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "exports").mkdir(exist_ok=True)
        (path / "logs").mkdir(exist_ok=True)
        (path / "cache").mkdir(exist_ok=True)
        (path / "history").mkdir(exist_ok=True)
        return path

    def save_json(self, project_id: str, filename: str, data: Any) -> Path:
        path = self.project_file(project_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
            if path.exists():
                path.unlink()
            tmp.rename(path)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise StorageError(f"Failed to save {filename}: {exc}") from exc
        return path

    def load_json(self, project_id: str, filename: str) -> Any | None:
        path = self.project_file(project_id, filename)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s/%s: %s", project_id, filename, exc)
            return None

    def file_exists(self, project_id: str, filename: str) -> bool:
        return self.project_file(project_id, filename).exists()

    def delete_project(self, project_id: str, permanent: bool = False) -> bool:
        path = self.project_path(project_id)
        if not path.exists():
            return False
        if permanent:
            shutil.rmtree(str(path), ignore_errors=True)
            logger.info("Permanently deleted project %s", project_id)
        else:
            trash = self._root / ".trash"
            trash.mkdir(exist_ok=True)
            dest = trash / project_id
            if dest.exists():
                shutil.rmtree(str(dest), ignore_errors=True)
            path.rename(dest)
            logger.info("Soft-deleted project %s", project_id)
        return True

    def restore_project(self, project_id: str) -> bool:
        trash = self._root / ".trash" / project_id
        if not trash.exists():
            return False
        dest = self.project_path(project_id)
        if dest.exists():
            return False
        trash.rename(dest)
        logger.info("Restored project %s", project_id)
        return True

    def list_projects(self, include_trash: bool = False) -> list[str]:
        projects = []
        if self._root.exists():
            for entry in self._root.iterdir():
                if entry.is_dir() and (self._root / entry.name / "project.json").exists():
                    projects.append(entry.name)
        if include_trash:
            trash = self._root / ".trash"
            if trash.exists():
                for entry in trash.iterdir():
                    if entry.is_dir():
                        projects.append(entry.name)
        return sorted(projects, reverse=True)

    def project_exists(self, project_id: str) -> bool:
        return self.project_path(project_id).exists()

    def copy_to(self, project_id: str, src_path: Path, dest_filename: str) -> Path:
        dest = self.project_file(project_id, dest_filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src_path.exists():
            shutil.copy2(str(src_path), str(dest))
        return dest

    def get_storage_usage(self, project_id: str) -> int:
        path = self.project_path(project_id)
        if not path.exists():
            return 0
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
