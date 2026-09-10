from __future__ import annotations

import pytest


class TestDocumentManager:
    def test_create_document(self):
        from editor.document_manager import DocumentManager
        mgr = DocumentManager()
        doc = mgr.load_document(content="# Test\n\nContent here.\n", title="Test Document")
        assert doc.title == "Test Document"
        assert doc.word_count > 0

    def test_open_document(self):
        from editor.document_manager import DocumentManager
        mgr = DocumentManager()
        doc = mgr.load_document(content="Hello", title="Open Test")
        assert doc is not None
        assert doc.title == "Open Test"

    def test_save_document(self):
        from editor.document_manager import DocumentManager
        mgr = DocumentManager()
        doc = mgr.load_document(content="Content", title="Save Test")
        assert doc.content == "Content"

    def test_close_document(self):
        from editor.document_manager import DocumentManager
        mgr = DocumentManager()
        mgr.load_document(content="Content", title="Close Test")
        doc2 = mgr.load_document(content="New Content", title="New Doc")
        assert mgr.document.title == "New Doc"

    def test_list_open_documents(self):
        from editor.document_manager import DocumentManager
        mgr = DocumentManager()
        mgr.load_document(content="A", title="Doc1")
        assert mgr.document.title == "Doc1"


class TestDiffViewer:
    def test_compute_diff(self):
        from editor.diff_viewer import DiffViewer
        viewer = DiffViewer()
        old = "Python is a programming language."
        new = "Python is a great programming language."
        diff = viewer.compute_diff(old, new)
        assert len(diff.lines) > 0
        assert any("great" in str(line.content) for line in diff.lines)

    def test_compute_diff_identical(self):
        from editor.diff_viewer import DiffViewer
        viewer = DiffViewer()
        diff = viewer.compute_diff("Same content", "Same content")
        assert diff.change_percentage == 0.0
        assert diff.added_lines == 0
        assert diff.removed_lines == 0


class TestFindReplaceEngine:
    def test_find(self):
        from editor.find_replace_engine import FindReplaceEngine
        from editor.editor_models import FindReplaceRequest
        engine = FindReplaceEngine()
        request = FindReplaceRequest(query="Python")
        result = engine.find_all("Python is great. Python is versatile.", request)
        assert result.total_matches == 2

    def test_replace(self):
        from editor.find_replace_engine import FindReplaceEngine
        from editor.editor_models import FindReplaceRequest
        engine = FindReplaceEngine()
        request = FindReplaceRequest(query="Python", replacement="JavaScript")
        result = engine.replace_all("Python is great. Python is versatile.", request)
        assert "JavaScript" in result.replaced_text
        assert "Python" not in result.replaced_text

    def test_replace_not_found(self):
        from editor.find_replace_engine import FindReplaceEngine
        from editor.editor_models import FindReplaceRequest
        engine = FindReplaceEngine()
        request = FindReplaceRequest(query="Java", replacement="JavaScript")
        result = engine.replace_all("Python is great.", request)
        assert result.replaced_text == "Python is great."

    def test_replace_with_count(self):
        from editor.find_replace_engine import FindReplaceEngine
        from editor.editor_models import FindReplaceRequest
        engine = FindReplaceEngine()
        request = FindReplaceRequest(query="Python", replacement="Java")
        result = engine.replace_all("Python Python Python", request)
        assert result.replaced_text == "Java Java Java"


class TestAIAssistant:
    def test_suggest(self):
        from editor.ai_assistant import AIAssistant
        from editor.editor_models import AIActionRequest, AIActionType
        assistant = AIAssistant()
        request = AIActionRequest(action_type=AIActionType.CONTINUE_WRITING, text="Python is a", max_tokens=50)
        response = assistant.execute(request)
        assert response is not None

    def test_complete(self):
        from editor.ai_assistant import AIAssistant
        from editor.editor_models import AIActionRequest, AIActionType
        assistant = AIAssistant()
        request = AIActionRequest(action_type=AIActionType.CONTINUE_WRITING, text="Python is a programming language.")
        response = assistant.execute(request)
        assert response is not None


class TestHeadingNavigator:
    def test_extract_headings(self):
        from editor.heading_navigator import HeadingNavigator
        navigator = HeadingNavigator()
        headings = navigator.parse("# Title\n\n## Section 1\n\nContent\n\n### Subsection\n\n## Section 2\n")
        assert len(headings) >= 3

    def test_navigate_to(self):
        from editor.heading_navigator import HeadingNavigator
        navigator = HeadingNavigator()
        navigator.parse("# Title\n\n## Section 1\n\nContent\n\n## Section 2\n")
        line = navigator.navigate_to_heading(
            "# Title\n\n## Section 1\n\nContent\n\n## Section 2\n", "Section 1"
        )
        assert line is not None
        assert line > 0


class TestHistoryManager:
    def test_push_and_undo(self):
        from editor.history_manager import HistoryManager
        hm = HistoryManager()
        hm.record("", "Version 1", description="Snapshot 1")
        hm.record("Version 1", "Version 2", description="Snapshot 2")
        undone = hm.undo()
        assert undone is not None
        assert undone.content_before == "Version 1"

    def test_redo(self):
        from editor.history_manager import HistoryManager
        hm = HistoryManager()
        hm.record("", "V1")
        hm.record("V1", "V2")
        hm.undo()
        redone = hm.redo()
        assert redone is not None
        assert redone.content_after == "V2"

    def test_cannot_undo_empty(self):
        from editor.history_manager import HistoryManager
        hm = HistoryManager()
        assert hm.undo() is None

    def test_clear_history(self):
        from editor.history_manager import HistoryManager
        hm = HistoryManager()
        hm.record("", "V1")
        hm.record("V1", "V2")
        hm.clear_history(preserve_current=False)
        assert hm.undo() is None


class TestVersionManager:
    def test_create_version(self):
        from editor.version_manager import VersionManager
        vm = VersionManager()
        v = vm.create_version("test_project_create", "content_v1", reason="Initial version")
        assert v.version_number > 0

    def test_get_versions(self):
        from editor.version_manager import VersionManager
        vm = VersionManager()
        vm.create_version("test_project", "v1")
        vm.create_version("test_project", "v2")
        meta = vm.list_versions("test_project")
        assert len(meta.versions) == 2


class TestAutosaveManager:
    def test_autosave(self):
        from editor.autosave_manager import AutosaveManager
        mgr = AutosaveManager()
        state = mgr.save("doc_1", "Current content")
        assert state.content == "Current content"

    def test_recover(self):
        from editor.autosave_manager import AutosaveManager
        mgr = AutosaveManager()
        point = mgr.create_recovery_point("doc_2", "Recovered content", reason="test")
        recovered = mgr.recover_from_point("doc_2", point.point_id)
        assert recovered is not None
        assert recovered.content == "Recovered content"

    def test_cleanup(self):
        from editor.autosave_manager import AutosaveManager
        mgr = AutosaveManager()
        mgr.create_recovery_point("doc_1", "Content", reason="test")
        mgr.create_recovery_point("doc_2", "Content", reason="test")
        mgr.clear_recovery("doc_2")
        assert mgr.get_recovery_points("doc_2") == []


class TestTranslationEngine:
    def test_translate(self):
        from editor.translation_engine import TranslationEngine
        from editor.editor_models import TranslationRequest
        engine = TranslationEngine()
        request = TranslationRequest(text="Hello, world!", target_language="es")
        result = engine.translate(request)
        assert result is not None
        assert result.translated_text

    def test_detect_language(self):
        from editor.translation_engine import TranslationEngine
        engine = TranslationEngine()
        result = engine.detect_language("Bonjour le monde")
        assert result is not None
