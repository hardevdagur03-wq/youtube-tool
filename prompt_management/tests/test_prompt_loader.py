from __future__ import annotations

from pathlib import Path

import pytest

from prompt_management.prompt_loader import PromptLoader


@pytest.fixture
def loader():
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    return PromptLoader(prompts_dir)


class TestPromptLoader:
    def test_load_existing_prompt(self, loader):
        content = loader.load_content("analysis")
        assert content is not None
        assert len(content) > 0

    def test_load_nonexistent_prompt(self, loader):
        content = loader.load_content("nonexistent_prompt_xyz")
        assert content is None

    def test_load_raw_contains_front_matter(self, loader):
        raw = loader.load_raw("analysis")
        assert raw is not None
        assert raw.startswith("---")

    def test_load_content_strips_front_matter(self, loader):
        raw = loader.load_raw("analysis")
        content = loader.load_content("analysis")
        assert raw is not None
        assert content is not None
        assert len(content) < len(raw)
        assert not content.startswith("---")

    def test_load_metadata_from_prompt(self, loader):
        meta = loader.load_metadata("analysis")
        assert meta is not None
        assert meta.name == "Content Analysis"
        assert meta.version == "1.0.0"
        assert meta.category.value == "analysis"

    def test_load_with_metadata(self, loader):
        meta, content = loader.load_with_metadata("analysis")
        assert meta is not None
        assert content is not None
        assert meta.name == "Content Analysis"

    def test_resolve_path(self, loader):
        path = loader.resolve_path("analysis")
        assert path is not None
        assert path.exists()
        assert path.name == "analysis.md"

    def test_resolve_path_nonexistent(self, loader):
        path = loader.resolve_path("does_not_exist_xyz")
        assert path is None

    def test_prompt_exists(self, loader):
        assert loader.prompt_exists("analysis")
        assert not loader.prompt_exists("does_not_exist_xyz")

    def test_list_prompt_names(self, loader):
        names = loader.list_prompt_names()
        assert "analysis" in names
        assert "seo" in names
        assert len(names) > 0

    def test_load_all_prompts(self, loader):
        prompts = loader.load_all_prompts()
        assert "analysis" in prompts
        assert "seo" in prompts
        meta, content = prompts["analysis"]
        assert meta is not None
        assert content is not None

    def test_reload(self, loader):
        content1 = loader.load_content("analysis")
        loader.reload("analysis")
        content2 = loader.load_content("analysis")
        assert content1 == content2

    def test_reload_all(self, loader):
        loader.load_content("analysis")
        loader.load_content("seo")
        loader.reload_all()
        assert "analysis" not in loader._content_cache
        assert "seo" not in loader._content_cache

    def test_load_shared_partial(self, loader):
        content = loader.load_content("shared/writing_style")
        if content is None:
            content = loader.load_content("writing_style")
        assert content is not None

    def test_load_template(self, loader):
        content = loader.load_content("templates/system_prompt")
        if content is None:
            content = loader.load_content("system_prompt")
        assert content is not None

    def test_metadata_contains_dependencies(self, loader):
        meta = loader.load_metadata("knowledge_graph")
        assert meta is not None
        assert "analysis" in meta.dependencies

    def test_metadata_contains_supported_models(self, loader):
        meta = loader.load_metadata("analysis")
        assert meta is not None
        assert "gemini-2.0-flash" in meta.supported_models
