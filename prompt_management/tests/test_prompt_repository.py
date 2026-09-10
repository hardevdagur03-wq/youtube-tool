from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_models import (
    ExperimentVariant,
    PromptAnalytics,
    PromptExperiment,
    PromptMetadata,
    PromptStatus,
    PromptVersion,
)
from prompt_management.prompt_repository import PromptRepository


@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmp:
        yield PromptRepository(Path(tmp) / "prompts")


class TestPromptRepository:
    def test_save_and_get_metadata(self, repo):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        saved = repo.save_metadata(meta)
        assert saved.prompt_id == "p_test"
        fetched = repo.get_metadata("p_test")
        assert fetched is not None
        assert fetched.name == "Test"

    def test_get_nonexistent_metadata(self, repo):
        assert repo.get_metadata("nonexistent") is None

    def test_list_metadata(self, repo):
        repo.save_metadata(PromptMetadata(name="A", prompt_id="p_a"))
        repo.save_metadata(PromptMetadata(name="B", prompt_id="p_b"))
        items = repo.list_metadata()
        assert len(items) == 2

    def test_delete_metadata(self, repo):
        repo.save_metadata(PromptMetadata(name="Test", prompt_id="p_test"))
        assert repo.delete_metadata("p_test") is True
        assert repo.get_metadata("p_test") is None

    def test_save_and_get_version(self, repo):
        version = PromptVersion(prompt_id="p_test", version_number="1.0.0", content="Hello", author="test")
        saved = repo.save_version(version)
        assert saved.version_id == version.version_id
        fetched = repo.get_version("p_test", "1.0.0")
        assert fetched is not None
        assert fetched.content == "Hello"

    def test_list_versions(self, repo):
        repo.save_version(PromptVersion(prompt_id="p_test", version_number="1.0.0", content="v1", author="a"))
        repo.save_version(PromptVersion(prompt_id="p_test", version_number="1.0.1", content="v2", author="a"))
        versions = repo.list_versions("p_test")
        assert len(versions) == 2

    def test_get_latest_version(self, repo):
        repo.save_version(PromptVersion(prompt_id="p_test", version_number="1.0.0", content="v1", author="a"))
        repo.save_version(PromptVersion(prompt_id="p_test", version_number="2.0.0", content="v2", author="a"))
        latest = repo.get_latest_version("p_test")
        assert latest is not None
        assert latest.version_number == "2.0.0"

    def test_get_latest_version_empty(self, repo):
        assert repo.get_latest_version("p_test") is None

    def test_save_and_get_analytics(self, repo):
        record = PromptAnalytics(prompt_id="p_test", version="1.0.0")
        saved = repo.save_analytics(record)
        assert saved.analytics_id == record.analytics_id
        records = repo.get_analytics("p_test")
        assert len(records) == 1

    def test_save_and_get_experiment(self, repo):
        exp = PromptExperiment(name="Test", target_prompt_id="p_test", variants=[])
        saved = repo.save_experiment(exp)
        assert saved.experiment_id == exp.experiment_id
        fetched = repo.get_experiment(exp.experiment_id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_list_experiments(self, repo):
        repo.save_experiment(PromptExperiment(name="A", target_prompt_id="p_test", variants=[]))
        repo.save_experiment(PromptExperiment(name="B", target_prompt_id="p_test", variants=[]))
        experiments = repo.list_experiments()
        assert len(experiments) == 2

    def test_get_prompt_by_name(self, repo):
        repo.save_metadata(PromptMetadata(name="My Prompt", prompt_id="p_my"))
        found = repo.get_prompt_by_name("My Prompt")
        assert found is not None
        assert found.prompt_id == "p_my"

    def test_get_prompt_by_name_nonexistent(self, repo):
        assert repo.get_prompt_by_name("nonexistent") is None

    def test_search_prompts(self, repo):
        repo.save_metadata(PromptMetadata(name="Analysis Prompt", prompt_id="p_analysis", tags=["nlp", "ai"]))
        repo.save_metadata(PromptMetadata(name="SEO Prompt", prompt_id="p_seo", tags=["marketing"]))
        results = repo.search_prompts("analysis")
        assert len(results) == 1

    def test_search_prompts_by_tag(self, repo):
        repo.save_metadata(PromptMetadata(name="Test", prompt_id="p_test", tags=["nlp"]))
        results = repo.search_prompts("nlp")
        assert len(results) >= 1

    def test_get_prompts_by_category(self, repo):
        from prompt_management.prompt_models import PromptCategory
        repo.save_metadata(PromptMetadata(name="A", prompt_id="p_a", category=PromptCategory.analysis))
        repo.save_metadata(PromptMetadata(name="B", prompt_id="p_b", category=PromptCategory.analysis))
        analysis = repo.get_prompts_by_category("analysis")
        assert len(analysis) == 2

    def test_get_prompts_by_status(self, repo):
        meta = PromptMetadata(name="Test", prompt_id="p_test", status=PromptStatus.production)
        repo.save_metadata(meta)
        results = repo.get_prompts_by_status(PromptStatus.production)
        assert len(results) == 1
