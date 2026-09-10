from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from editor.editor_engine import EditorEngine
from editor.editor_models import (
    AIActionRequest, AIActionResponse, DocumentModel, DocumentStats,
    EditorConfig, EditorState, FindReplaceRequest, FindReplaceResult,
    TranslationRequest, TranslationResponse, VersionDiff, VersionInfo,
    VersionMetadata, ViewMode,
)

logger = logging.getLogger(__name__)


class EditorService:
    def __init__(
        self,
        engine: EditorEngine | None = None,
        project_manager: Any | None = None,
        cache_manager: Any | None = None,
        checkpoint_manager: Any | None = None,
        storage_dir: Path | None = None,
    ):
        self._engine = engine or EditorEngine(
            storage_dir=storage_dir,
            project_manager=project_manager,
            cache_manager=cache_manager,
            checkpoint_manager=checkpoint_manager,
        )
        self._pm = project_manager

    @property
    def engine(self) -> EditorEngine:
        return self._engine

    def load_draft(self, project_id: str) -> dict:
        content, title = self._engine.load_draft(project_id)
        state = self._engine.get_state(project_id)
        doc = state.document if state else None
        return {
            "project_id": project_id,
            "content": content or "",
            "title": title or "",
            "document": doc.model_dump() if doc else None,
            "state": state.model_dump() if state else None,
        }

    def save_draft(self, project_id: str, content: str, title: str = "") -> dict:
        self._engine.update_content(project_id, content)
        if title:
            self._engine.update_title(project_id, title)
        state = self._engine.autosave(project_id)
        return {
            "success": True,
            "project_id": project_id,
            "saved_at": state.saved_at if state else "",
        }

    def get_draft_content(self, project_id: str) -> str:
        state = self._engine.get_state(project_id)
        return state.document.content if state else ""

    def set_content(self, project_id: str, content: str) -> dict:
        self._engine.update_content(project_id, content)
        return {"success": True}

    def get_state(self, project_id: str) -> EditorState | None:
        return self._engine.get_state(project_id)

    def set_config(self, project_id: str, config: dict) -> dict:
        self._engine.update_config(project_id, EditorConfig(**config))
        return {"success": True}

    def get_statistics(self, project_id: str) -> DocumentStats:
        return self._engine.get_statistics(project_id)

    def get_seo_score(self, project_id: str) -> float:
        return self._engine.get_seo_score(project_id)

    def validate(self, project_id: str) -> list[dict]:
        return self._engine.validate(project_id)

    def record_history(self, project_id: str, content_before: str, content_after: str, description: str = "edit") -> str:
        return self._engine.record_history(project_id, content_before, content_after, description)

    def undo(self, project_id: str) -> str | None:
        return self._engine.undo(project_id)

    def redo(self, project_id: str) -> str | None:
        return self._engine.redo(project_id)

    def can_undo(self, project_id: str) -> bool:
        return self._engine.can_undo(project_id)

    def can_redo(self, project_id: str) -> bool:
        return self._engine.can_redo(project_id)

    def create_version(self, project_id: str, label: str = "", reason: str = "manual_save", author: str = "user") -> VersionInfo:
        return self._engine.create_version(project_id, label=label, reason=reason, author=author)

    def list_versions(self, project_id: str) -> list[VersionInfo]:
        meta = self._engine.list_versions(project_id)
        return meta.versions if meta else []

    def get_version_content(self, project_id: str, version_number: int) -> str | None:
        return self._engine.get_version_content(project_id, version_number)

    def diff_versions(self, project_id: str, old_version: int, new_version: int) -> VersionDiff | None:
        return self._engine.diff_versions(project_id, old_version, new_version)

    def restore_version(self, project_id: str, version_number: int) -> str | None:
        return self._engine.restore_version(project_id, version_number)

    def find_in_document(self, project_id: str, request: FindReplaceRequest) -> FindReplaceResult:
        content = self.get_draft_content(project_id)
        return self._engine.find_replace(project_id, content, request)

    def replace_in_document(self, project_id: str, request: FindReplaceRequest) -> FindReplaceResult:
        content = self.get_draft_content(project_id)
        return self._engine.replace_all(project_id, content, request)

    def execute_ai_action(self, project_id: str, request: AIActionRequest) -> AIActionResponse:
        return self._engine.execute_ai_action(project_id, request)

    def translate_document(self, project_id: str, request: TranslationRequest) -> TranslationResponse:
        return self._engine.translate(project_id, request)

    def get_heading_navigation(self, project_id: str) -> list[dict]:
        content = self.get_draft_content(project_id)
        return self._engine.get_headings(project_id, content)

    def get_editor_state(self, project_id: str) -> dict:
        state = self._engine.get_state(project_id)
        if not state:
            return {}
        return state.model_dump()

    def has_draft(self, project_id: str) -> bool:
        return self._engine.has_draft(project_id)

    def recover_autosave(self, project_id: str) -> str | None:
        return self._engine.recover_autosave(project_id)

    def clear_autosave(self, project_id: str) -> None:
        self._engine.clear_autosave(project_id)
