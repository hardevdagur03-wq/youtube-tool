"""History Manager — maintains audit trail for project actions.

No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from projects.project_models import HistoryEntry, utc_now
from projects.uuid_manager import UUIDManager
from projects.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class HistoryManager:
    """Records and retrieves project history entries."""

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage

    def record(
        self,
        project_id: str,
        action: str,
        stage: str = "",
        previous_state: str = "",
        new_state: str = "",
        duration_seconds: float = 0.0,
        user_action: bool = False,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        retry_count: int = 0,
        details: str = "",
    ) -> HistoryEntry:
        entry = HistoryEntry(
            entry_id=UUIDManager.generate_history_id(),
            timestamp=utc_now(),
            action=action,
            stage=stage,
            previous_state=previous_state,
            new_state=new_state,
            duration_seconds=round(duration_seconds, 3),
            user_action=user_action,
            system_action=not user_action,
            warnings=warnings or [],
            errors=errors or [],
            retry_count=retry_count,
            details=details,
        )
        self._append_entry(project_id, entry)
        return entry

    def _append_entry(self, project_id: str, entry: HistoryEntry) -> None:
        entries = self._load_entries(project_id)
        entries.append(entry.model_dump())
        self._storage.save_json(project_id, "history.json", entries)

    def _load_entries(self, project_id: str) -> list[dict]:
        data = self._storage.load_json(project_id, "history.json")
        return data if isinstance(data, list) else []

    def get_history(self, project_id: str, limit: int = 100) -> list[HistoryEntry]:
        entries = self._load_entries(project_id)
        entries = entries[-limit:]
        return [HistoryEntry(**e) for e in entries]

    def get_history_for_stage(self, project_id: str, stage: str, limit: int = 50) -> list[HistoryEntry]:
        entries = self._load_entries(project_id)
        filtered = [e for e in entries if e.get("stage") == stage]
        return [HistoryEntry(**e) for e in filtered[-limit:]]

    def get_recent_actions(self, project_id: str, count: int = 10) -> list[HistoryEntry]:
        return self.get_history(project_id, limit=count)

    def clear_history(self, project_id: str) -> None:
        self._storage.save_json(project_id, "history.json", [])

    def get_summary(self, project_id: str) -> dict[str, Any]:
        entries = self._load_entries(project_id)
        if not entries:
            return {"total": 0, "actions": {}, "errors": 0, "warnings": 0}
        action_counts: dict[str, int] = {}
        total_errors = 0
        total_warnings = 0
        for e in entries:
            action = e.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            total_errors += len(e.get("errors", []))
            total_warnings += len(e.get("warnings", []))
        return {
            "total": len(entries),
            "actions": action_counts,
            "errors": total_errors,
            "warnings": total_warnings,
        }
