from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_models import PromptMetadata, PromptStatus
from prompt_management.prompt_repository import PromptRepository
from prompt_management.prompt_version_manager import PromptVersionManager


@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmp:
        yield PromptRepository(Path(tmp) / "prompts")


@pytest.fixture
def version_manager(repo):
    return PromptVersionManager(repo)


@pytest.fixture
def sample_metadata(repo):
    meta = PromptMetadata(name="Test", prompt_id="p_test", version="1.0.0")
    repo.save_metadata(meta)
    return meta


class TestPromptVersionManager:
    def test_create_initial_version(self, version_manager, sample_metadata):
        v = version_manager.create_version(
            prompt_id="p_test",
            content="Hello {{name}}",
            author="test",
            change_summary="Initial version",
        )
        assert v.version_number == "1.0.0"
        assert v.content == "Hello {{name}}"
        assert v.previous_version is None

    def test_create_patch_version(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="test")
        v2 = version_manager.create_version(
            prompt_id="p_test",
            content="v2",
            author="test",
            change_summary="Patch update",
            change_type="patch",
        )
        assert v2.version_number == "1.0.1"
        assert v2.previous_version == "1.0.0"

    def test_create_minor_version(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="test")
        v2 = version_manager.create_version(
            prompt_id="p_test",
            content="v2",
            author="test",
            change_summary="Minor update",
            change_type="minor",
        )
        assert v2.version_number == "1.1.0"

    def test_create_major_version(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="test")
        v2 = version_manager.create_version(
            prompt_id="p_test",
            content="v2",
            author="test",
            change_summary="Major update",
            change_type="major",
        )
        assert v2.version_number == "2.0.0"

    def test_rollback(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="test")
        version_manager.create_version(prompt_id="p_test", content="v2", author="test")
        rolled = version_manager.rollback(prompt_id="p_test", target_version="1.0.0", author="test")
        assert rolled is not None
        assert rolled.content == "v1"

    def test_rollback_nonexistent_version(self, version_manager, sample_metadata):
        result = version_manager.rollback(prompt_id="p_test", target_version="99.0.0", author="test")
        assert result is None

    def test_get_version_history(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="a")
        version_manager.create_version(prompt_id="p_test", content="v2", author="b")
        history = version_manager.get_version_history("p_test")
        assert len(history) == 2

    def test_diff_versions(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="Hello World", author="a")
        version_manager.create_version(prompt_id="p_test", content="Hello Universe", author="a")
        diff = version_manager.diff_versions("p_test", "1.0.0", "1.0.1")
        assert diff != ""
        assert "World" in diff or "Universe" in diff

    def test_diff_same_version(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="Hello", author="a")
        diff = version_manager.diff_versions("p_test", "1.0.0", "1.0.0")
        assert diff == "" or diff is not None

    def test_promote_draft_to_review(self, version_manager, sample_metadata):
        result = version_manager.promote("p_test", PromptStatus.draft, PromptStatus.review)
        assert result is True
        meta = version_manager._repository.get_metadata("p_test")
        assert meta is not None
        assert meta.status == PromptStatus.review

    def test_promote_invalid_transition(self, version_manager, sample_metadata):
        result = version_manager.promote("p_test", PromptStatus.draft, PromptStatus.production)
        assert result is False

    def test_promote_full_workflow(self, version_manager, sample_metadata):
        assert version_manager.promote("p_test", PromptStatus.draft, PromptStatus.review)
        assert version_manager.promote("p_test", PromptStatus.review, PromptStatus.approved)
        assert version_manager.promote("p_test", PromptStatus.approved, PromptStatus.production)
        meta = version_manager._repository.get_metadata("p_test")
        assert meta is not None
        assert meta.status == PromptStatus.production

    def test_list_available_versions(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="v1", author="a")
        version_manager.create_version(prompt_id="p_test", content="v2", author="a")
        versions = version_manager.list_available_versions("p_test")
        assert len(versions) == 2

    def test_compare_versions(self, version_manager, sample_metadata):
        version_manager.create_version(prompt_id="p_test", content="Hello World", author="a")
        version_manager.create_version(prompt_id="p_test", content="Hello Universe", author="a")
        comparison = version_manager.compare_versions("p_test", "1.0.0", "1.0.1")
        assert "diff" in comparison
        assert comparison["content_1_length"] > 0
