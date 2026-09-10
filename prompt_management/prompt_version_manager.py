from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptVersion


class PromptVersionManager:
    SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

    def __init__(self, repository: Any):
        self._repository = repository

    def create_version(
        self,
        prompt_id: str,
        content: str,
        author: str = "system",
        change_summary: str = "",
        change_type: str = "patch",
    ) -> PromptVersion:
        latest = self._repository.get_latest_version(prompt_id)
        metadata = self._repository.get_metadata(prompt_id)

        if latest:
            new_version = self._bump_version(latest.version_number, change_type)
            previous_version = latest.version_number
            diff = self._compute_diff(
                self._get_version_content(prompt_id, latest.version_number),
                content,
            )
        else:
            new_version = "1.0.0"
            previous_version = None
            diff = ""

        content_hash = self._compute_hash(content)
        existing_versions = self._repository.list_versions(prompt_id)
        version_number = str(len(existing_versions) + 1)

        if metadata:
            metadata.version = new_version
            metadata.updated_at = datetime.now(timezone.utc).isoformat()
            metadata.content_hash = content_hash
            if change_summary:
                log_entry = {
                    "version": new_version,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "author": author,
                    "summary": change_summary,
                    "changes": change_type,
                }
                if not metadata.change_log:
                    metadata.change_log = []
                metadata.change_log.append(log_entry)
            self._repository.save_metadata(metadata)

        version = PromptVersion(
            prompt_id=prompt_id,
            version_number=new_version,
            previous_version=previous_version,
            content=content,
            author=author,
            change_summary=change_summary,
            changes=[{"type": change_type, "description": change_summary}],
            diff=diff,
            content_hash=content_hash,
            status=PromptStatus.draft,
        )
        return self._repository.save_version(version)

    def rollback(self, prompt_id: str, target_version: str, author: str = "system") -> PromptVersion | None:
        metadata = self._repository.get_metadata(prompt_id)
        if metadata is None:
            return None

        target = self._repository.get_version(prompt_id, target_version)
        if target is None:
            return None

        rollback_version = self.create_version(
            prompt_id=prompt_id,
            content=target.content,
            author=author,
            change_summary=f"Rollback to version {target_version}",
            change_type="rollback",
        )
        return rollback_version

    def promote(self, prompt_id: str, from_status: PromptStatus, to_status: PromptStatus) -> bool:
        metadata = self._repository.get_metadata(prompt_id)
        if metadata is None:
            return False

        valid_transitions = {
            PromptStatus.draft: [PromptStatus.review],
            PromptStatus.review: [PromptStatus.approved, PromptStatus.draft],
            PromptStatus.approved: [PromptStatus.production, PromptStatus.draft],
            PromptStatus.production: [PromptStatus.deprecated, PromptStatus.draft],
            PromptStatus.deprecated: [PromptStatus.archived],
        }

        allowed = valid_transitions.get(from_status, [])
        if to_status not in allowed:
            return False

        metadata.status = to_status
        metadata.updated_at = datetime.now(timezone.utc).isoformat()

        latest = self._repository.get_latest_version(prompt_id)
        if latest:
            latest.status = to_status
            self._repository.save_version(latest)

        self._repository.save_metadata(metadata)
        return True

    def get_version_history(self, prompt_id: str) -> list[PromptVersion]:
        versions = self._repository.list_versions(prompt_id)
        return sorted(versions, key=lambda v: v.timestamp, reverse=True)

    def diff_versions(self, prompt_id: str, v1: str, v2: str) -> str:
        content1 = self._get_version_content(prompt_id, v1)
        content2 = self._get_version_content(prompt_id, v2)
        if content1 is None and content2 is None:
            return ""
        content1 = content1 or ""
        content2 = content2 or ""
        return self._compute_diff(content1, content2)

    def compare_versions(self, prompt_id: str, v1: str, v2: str) -> dict[str, Any]:
        meta1 = self._repository.get_version(prompt_id, v1)
        meta2 = self._repository.get_version(prompt_id, v2)
        content1 = self._get_version_content(prompt_id, v1) or ""
        content2 = self._get_version_content(prompt_id, v2) or ""
        return {
            "version_1": {"version": v1, "author": meta1.author if meta1 else "", "timestamp": meta1.timestamp if meta1 else ""},
            "version_2": {"version": v2, "author": meta2.author if meta2 else "", "timestamp": meta2.timestamp if meta2 else ""},
            "diff": self._compute_diff(content1, content2),
            "content_1_length": len(content1),
            "content_2_length": len(content2),
            "content_1_hash": self._compute_hash(content1),
            "content_2_hash": self._compute_hash(content2),
        }

    def _bump_version(self, current: str, change_type: str) -> str:
        m = self.SEMVER_PATTERN.match(current)
        if not m:
            return "1.0.0"
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if change_type == "major":
            return f"{major + 1}.0.0"
        elif change_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"

    def _compute_diff(self, old: str, new: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm="")
        return "".join(diff)

    def _get_version_content(self, prompt_id: str, version: str) -> str | None:
        v = self._repository.get_version(prompt_id, version)
        if v:
            return v.content
        return None

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def list_available_versions(self, prompt_id: str) -> list[str]:
        versions = self._repository.list_versions(prompt_id)
        return [v.version_number for v in versions]
