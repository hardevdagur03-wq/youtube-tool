from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from editor.editor_models import (
    DiffLine, DiffType, VersionDiff, VersionInfo, VersionMetadata,
    utc_now,
)

logger = logging.getLogger(__name__)


class VersionManager:
    def __init__(self, storage_dir: Path | None = None, max_versions: int = 100):
        self._storage_dir = storage_dir
        self._max_versions = max_versions
        self._versions: dict[str, VersionMetadata] = {}
        self._current_version: dict[str, int] = {}

    def _get_meta(self, project_id: str) -> VersionMetadata:
        if project_id not in self._versions:
            self._versions[project_id] = VersionMetadata(project_id=project_id)
        return self._versions[project_id]

    def create_version(
        self,
        project_id: str,
        content: str,
        label: str = "",
        author: str = "user",
        reason: str = "manual_save",
        is_automatic: bool = False,
        is_checkpoint: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> VersionInfo:
        meta = self._get_meta(project_id)
        current = meta.current_version
        new_number = current + 1

        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
        word_count = len(content.split()) if content else 0

        version = VersionInfo(
            version_number=new_number,
            label=label or f"Version {new_number}",
            created_at=utc_now(),
            author=author,
            reason=reason,
            checksum=checksum,
            word_count=word_count,
            character_count=len(content),
            is_automatic=is_automatic,
            is_checkpoint=is_checkpoint,
            metadata=metadata or {},
        )

        meta.versions.append(version)
        meta.current_version = new_number
        meta.total_versions = len(meta.versions)
        meta.last_version_at = utc_now()

        if self._storage_dir:
            self._persist_version(project_id, new_number, content, version)

        if len(meta.versions) > self._max_versions:
            old = meta.versions.pop(0)
            if self._storage_dir:
                self._remove_persisted_version(project_id, old.version_number)

        return version

    def get_version(self, project_id: str, version_number: int) -> VersionInfo | None:
        meta = self._get_meta(project_id)
        for v in meta.versions:
            if v.version_number == version_number:
                return v
        return None

    def get_version_content(self, project_id: str, version_number: int) -> str | None:
        if self._storage_dir:
            return self._load_persisted_version(project_id, version_number)
        meta = self._get_meta(project_id)
        for v in meta.versions:
            if v.version_number == version_number:
                return v.metadata.get("_content", "")
        return None

    def list_versions(self, project_id: str) -> VersionMetadata:
        return self._get_meta(project_id)

    def get_latest_version_number(self, project_id: str) -> int:
        return self._get_meta(project_id).current_version

    def restore_version(self, project_id: str, version_number: int) -> str | None:
        content = self.get_version_content(project_id, version_number)
        if content is not None:
            self.create_version(
                project_id=project_id,
                content=content,
                label=f"Restore from v{version_number}",
                author="system",
                reason="version_restore",
                is_automatic=False,
                is_checkpoint=True,
                metadata={"restored_from": version_number},
            )
        return content

    def diff_versions(
        self,
        project_id: str,
        old_version: int,
        new_version: int,
    ) -> VersionDiff | None:
        old_content = self.get_version_content(project_id, old_version)
        new_content = self.get_version_content(project_id, new_version)
        if old_content is None or new_content is None:
            return None
        return self.compute_diff(old_content, new_content, old_version, new_version)

    def compute_diff(
        self,
        old_content: str,
        new_content: str,
        old_version: int = 0,
        new_version: int = 1,
    ) -> VersionDiff:
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        diff = VersionDiff(
            old_version=old_version,
            new_version=new_version,
            old_content=old_content,
            new_content=new_content,
        )

        lcs = self._lcs(old_lines, new_lines)
        lcs_set = set(lcs)

        old_map: dict[str, list[int]] = {}
        for i, line in enumerate(old_lines):
            old_map.setdefault(line, []).append(i)

        matched_old = set()
        matched_new = set()
        for line in lcs:
            if line in old_map:
                for idx in old_map[line]:
                    if idx not in matched_old:
                        matched_old.add(idx)
                        break
            for j, nl in enumerate(new_lines):
                if nl == line and j not in matched_new:
                    matched_new.add(j)
                    break

        i, j = 0, 0
        while i < len(old_lines) or j < len(new_lines):
            if i < len(old_lines) and j < len(new_lines) and old_lines[i] == new_lines[j]:
                diff.lines.append(DiffLine(
                    type=DiffType.UNCHANGED,
                    content=old_lines[i],
                    old_line_number=i + 1,
                    new_line_number=j + 1,
                ))
                i += 1
                j += 1
                diff.unchanged_lines += 1
            elif i < len(old_lines) and (j >= len(new_lines) or old_lines[i] not in new_lines[j:]):
                diff.lines.append(DiffLine(
                    type=DiffType.REMOVED,
                    content=old_lines[i],
                    old_line_number=i + 1,
                ))
                i += 1
                diff.removed_lines += 1
            elif j < len(new_lines):
                diff.lines.append(DiffLine(
                    type=DiffType.ADDED,
                    content=new_lines[j],
                    new_line_number=j + 1,
                ))
                j += 1
                diff.added_lines += 1

        total = max(len(old_lines), len(new_lines))
        diff.change_percentage = round(
            ((diff.added_lines + diff.removed_lines) / max(1, total)) * 100, 2
        )
        diff.modified_lines = max(0, total - diff.unchanged_lines - diff.added_lines - diff.removed_lines)

        return diff

    def _lcs(self, a: list[str], b: list[str]) -> list[str]:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        result: list[str] = []
        i, j = m, n
        while i > 0 and j > 0:
            if a[i - 1] == b[j - 1]:
                result.append(a[i - 1])
                i -= 1
                j -= 1
            elif dp[i - 1][j] > dp[i][j - 1]:
                i -= 1
            else:
                j -= 1
        return list(reversed(result))

    def _persist_version(
        self,
        project_id: str,
        version_number: int,
        content: str,
        info: VersionInfo,
    ) -> None:
        if not self._storage_dir:
            return
        version_dir = self._storage_dir / project_id / "editor_versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        content_file = version_dir / f"v{version_number}.md"
        meta_file = version_dir / f"v{version_number}.json"
        try:
            content_file.write_text(content, encoding="utf-8")
            meta_file.write_text(info.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist version {version_number}: {e}")

    def _load_persisted_version(self, project_id: str, version_number: int) -> str | None:
        if not self._storage_dir:
            return None
        content_file = self._storage_dir / project_id / "editor_versions" / f"v{version_number}.md"
        if content_file.exists():
            try:
                return content_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to load version {version_number}: {e}")
        return None

    def _remove_persisted_version(self, project_id: str, version_number: int) -> None:
        if not self._storage_dir:
            return
        version_dir = self._storage_dir / project_id / "editor_versions"
        for f in [version_dir / f"v{version_number}.md", version_dir / f"v{version_number}.json"]:
            try:
                if f.exists():
                    f.unlink()
            except Exception as e:
                logger.error(f"Failed to remove version {version_number}: {e}")

    def prune_versions(self, project_id: str, keep: int = 20) -> int:
        meta = self._get_meta(project_id)
        if len(meta.versions) <= keep:
            return 0
        to_remove = len(meta.versions) - keep
        removed = 0
        while len(meta.versions) > keep:
            old = meta.versions.pop(0)
            self._remove_persisted_version(project_id, old.version_number)
            removed += 1
        return removed
