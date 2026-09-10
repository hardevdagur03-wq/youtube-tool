from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from editor.document_manager import DocumentManager
from editor.history_manager import HistoryManager
from editor.version_manager import VersionManager
from editor.autosave_manager import AutosaveManager
from editor.ai_assistant import AIAssistant
from editor.translation_engine import TranslationEngine
from editor.find_replace_engine import FindReplaceEngine
from editor.heading_navigator import HeadingNavigator
from editor.diff_viewer import DiffViewer
from editor.editor_models import (
    AIActionRequest, AIActionResponse, AutosaveState, CursorPosition,
    DocumentModel, DocumentStats, EditorConfig, EditorState,
    FindReplaceRequest, FindReplaceResult, SelectionRange, TranslationRequest,
    TranslationResponse, VersionDiff, VersionInfo, VersionMetadata, ViewMode,
    utc_now,
)

logger = logging.getLogger(__name__)


class EditorEngine:
    def __init__(
        self,
        storage_dir: Path | None = None,
        project_manager: Any | None = None,
        cache_manager: Any | None = None,
        checkpoint_manager: Any | None = None,
    ):
        self._storage_dir = storage_dir
        self._pm = project_manager
        self._cache = cache_manager
        self._checkpoint_mgr = checkpoint_manager

        self._doc_managers: dict[str, DocumentManager] = {}
        self._history_managers: dict[str, HistoryManager] = {}
        self._version_manager = VersionManager(
            storage_dir=storage_dir,
            max_versions=100,
        )
        self._autosave_manager = AutosaveManager(storage_dir=storage_dir)
        self._ai_assistant = AIAssistant()
        self._translation_engine = TranslationEngine()
        self._find_replace_engine = FindReplaceEngine()
        self._heading_navigator = HeadingNavigator()
        self._diff_viewer = DiffViewer()
        self._version_cache: dict[str, dict] = {}

    def _get_doc_manager(self, project_id: str) -> DocumentManager:
        if project_id not in self._doc_managers:
            self._doc_managers[project_id] = DocumentManager()
        return self._doc_managers[project_id]

    def _get_history_manager(self, project_id: str) -> HistoryManager:
        if project_id not in self._history_managers:
            self._history_managers[project_id] = HistoryManager()
        return self._history_managers[project_id]

    def load_draft(self, project_id: str) -> tuple[str, str]:
        content = ""
        title = ""

        if self._pm:
            try:
                project = self._pm.get_project(project_id)
                if project:
                    blog = getattr(project, "blog", {}) or {}
                    content = blog.get("content", "")
                    title = getattr(project, "name", "") or blog.get("title", "") or ""
            except Exception as e:
                logger.warning(f"Could not load project {project_id}: {e}")

        if not content and self._storage_dir:
            draft_file = self._storage_dir / project_id / "draft" / "draft.md"
            if draft_file.exists():
                try:
                    content = draft_file.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Could not load draft file: {e}")

        if not content:
            content = "# Untitled Document\n\nStart writing here..."

        doc_mgr = self._get_doc_manager(project_id)
        doc_mgr.load_document(content=content, project_id=project_id, title=title)

        auto_state = self._autosave_manager.load_latest(project_id)
        if auto_state and auto_state.content != content:
            content = auto_state.content
            doc_mgr.load_document(content=content, project_id=project_id, title=title)

        return content, title

    def get_state(self, project_id: str) -> EditorState | None:
        doc_mgr = self._get_doc_manager(project_id)
        return doc_mgr.state if doc_mgr else None

    def update_content(self, project_id: str, content: str) -> None:
        doc_mgr = self._get_doc_manager(project_id)
        old_content = doc_mgr.get_content()
        doc_mgr.set_content(content)

        if old_content != content:
            hist_mgr = self._get_history_manager(project_id)
            hist_mgr.record(
                content_before=old_content,
                content_after=content,
                description="content_update",
            )

        self._autosave_manager.mark_dirty()

    def update_title(self, project_id: str, title: str) -> None:
        doc_mgr = self._get_doc_manager(project_id)
        doc_mgr.document.title = title

    def update_config(self, project_id: str, config: EditorConfig) -> None:
        doc_mgr = self._get_doc_manager(project_id)
        doc_mgr.set_config(config)

    def autosave(self, project_id: str) -> AutosaveState | None:
        doc_mgr = self._get_doc_manager(project_id)
        content = doc_mgr.get_content()
        cursor = doc_mgr.get_cursor()

        state = self._autosave_manager.save(
            project_id=project_id,
            content=content,
            cursor=cursor,
            view_mode=doc_mgr.get_view_mode().value,
        )

        if self._pm:
            try:
                project = self._pm.get_project(project_id)
                if project:
                    if not isinstance(project.blog, dict):
                        project.blog = {}
                    project.blog["editor_content"] = content
                    project.blog["editor_updated_at"] = utc_now()
                    self._pm._save(project)
            except Exception as e:
                logger.warning(f"Could not persist to project {project_id}: {e}")

        return state

    def get_statistics(self, project_id: str) -> DocumentStats:
        doc_mgr = self._get_doc_manager(project_id)
        return doc_mgr.compute_statistics()

    def get_seo_score(self, project_id: str) -> float:
        doc_mgr = self._get_doc_manager(project_id)
        return doc_mgr.compute_seo_score()

    def validate(self, project_id: str) -> list[dict]:
        doc_mgr = self._get_doc_manager(project_id)
        results = doc_mgr.validate()
        return [r.model_dump() for r in results]

    def record_history(self, project_id: str, content_before: str, content_after: str, description: str = "edit") -> str:
        hist_mgr = self._get_history_manager(project_id)
        return hist_mgr.record(
            content_before=content_before,
            content_after=content_after,
            description=description,
        )

    def undo(self, project_id: str) -> str | None:
        hist_mgr = self._get_history_manager(project_id)
        action = hist_mgr.undo()
        if action:
            doc_mgr = self._get_doc_manager(project_id)
            doc_mgr.set_content(action.content_before)
            return action.content_before
        return None

    def redo(self, project_id: str) -> str | None:
        hist_mgr = self._get_history_manager(project_id)
        action = hist_mgr.redo()
        if action:
            doc_mgr = self._get_doc_manager(project_id)
            doc_mgr.set_content(action.content_after)
            return action.content_after
        return None

    def can_undo(self, project_id: str) -> bool:
        hist_mgr = self._get_history_manager(project_id)
        return hist_mgr.can_undo

    def can_redo(self, project_id: str) -> bool:
        hist_mgr = self._get_history_manager(project_id)
        return hist_mgr.can_redo

    def create_version(self, project_id: str, label: str = "", reason: str = "manual_save", author: str = "user") -> VersionInfo:
        doc_mgr = self._get_doc_manager(project_id)
        content = doc_mgr.get_content()
        return self._version_manager.create_version(
            project_id=project_id,
            content=content,
            label=label,
            author=author,
            reason=reason,
        )

    def list_versions(self, project_id: str) -> VersionMetadata:
        return self._version_manager.list_versions(project_id)

    def get_version_content(self, project_id: str, version_number: int) -> str | None:
        return self._version_manager.get_version_content(project_id, version_number)

    def diff_versions(self, project_id: str, old_version: int, new_version: int) -> VersionDiff | None:
        return self._version_manager.diff_versions(project_id, old_version, new_version)

    def restore_version(self, project_id: str, version_number: int) -> str | None:
        content = self._version_manager.restore_version(project_id, version_number)
        if content:
            doc_mgr = self._get_doc_manager(project_id)
            doc_mgr.load_document(content=content, project_id=project_id)
            self._autosave_manager.mark_dirty()
        return content

    def find_replace(self, project_id: str, content: str, request: FindReplaceRequest) -> FindReplaceResult:
        return self._find_replace_engine.find_all(content, request)

    def replace_all(self, project_id: str, content: str, request: FindReplaceRequest) -> FindReplaceResult:
        result = self._find_replace_engine.replace_all(content, request)
        if result.replaced_text:
            doc_mgr = self._get_doc_manager(project_id)
            doc_mgr.set_content(result.replaced_text)
        return result

    def execute_ai_action(self, project_id: str, request: AIActionRequest) -> AIActionResponse:
        if self._checkpoint_mgr:
            try:
                doc_mgr = self._get_doc_manager(project_id)
                self._checkpoint_mgr.create_checkpoint(
                    project_id, {"content": doc_mgr.get_content()},
                    reason=f"Before AI {request.action_type.value}",
                )
            except Exception as e:
                logger.warning(f"Failed to create checkpoint: {e}")

        response = self._ai_assistant.execute(request)

        if response.success and response.modified_text and request.text:
            doc_mgr = self._get_doc_manager(project_id)
            content = doc_mgr.get_content()
            original = request.text
            modified = response.modified_text

            if original in content:
                new_content = content.replace(original, modified, 1)
                doc_mgr.set_content(new_content)
                self._autosave_manager.mark_dirty()
                self._version_manager.create_version(
                    project_id=project_id,
                    content=new_content,
                    label=f"AI {request.action_type.value}",
                    reason=f"ai_{request.action_type.value}",
                    is_automatic=True,
                )

        return response

    def translate(self, project_id: str, request: TranslationRequest) -> TranslationResponse:
        response = self._translation_engine.translate(request)
        if response.success and request.scope == "document" and response.translated_text:
            doc_mgr = self._get_doc_manager(project_id)
            doc_mgr.set_content(response.translated_text)
            self._autosave_manager.mark_dirty()
        return response

    def get_headings(self, project_id: str, content: str) -> list[dict]:
        headings = self._heading_navigator.parse(content)
        return [h.model_dump() for h in headings]

    def has_draft(self, project_id: str) -> bool:
        if self._pm:
            try:
                project = self._pm.get_project(project_id)
                if project:
                    blog = getattr(project, "blog", {}) or {}
                    return bool(blog.get("content"))
            except Exception:
                pass
        return False

    def recover_autosave(self, project_id: str) -> str | None:
        state = self._autosave_manager.load_latest(project_id)
        if state and state.content:
            doc_mgr = self._get_doc_manager(project_id)
            old_content = doc_mgr.get_content()
            doc_mgr.load_document(content=state.content, project_id=project_id)
            hist_mgr = self._get_history_manager(project_id)
            hist_mgr.record(
                content_before=old_content,
                content_after=state.content,
                description="autosave_recovery",
            )
            return state.content
        return None

    def clear_autosave(self, project_id: str) -> None:
        self._autosave_manager.clear_recovery(project_id)

    def create_recovery_point(self, project_id: str, content: str, reason: str = "manual") -> None:
        self._autosave_manager.create_recovery_point(
            project_id=project_id,
            content=content,
            reason=reason,
        )
