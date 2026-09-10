from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_models import PromptCategory, PromptMetadata, PromptStatus, RiskLevel
from prompt_management.prompt_registry import PromptRegistry
from prompt_management.prompt_repository import PromptRepository


@pytest.fixture
def registry():
    with tempfile.TemporaryDirectory() as tmp:
        repo = PromptRepository(Path(tmp) / "prompts")
        yield PromptRegistry(repo)


class TestPromptRegistry:
    def test_register_prompt(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        entry = registry.register(meta)
        assert entry.prompt_id == "p_test"
        assert entry.name == "Test"

    def test_get_prompt(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        registry.register(meta)
        entry = registry.get("p_test")
        assert entry is not None
        assert entry.name == "Test"

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_get_by_name(self, registry):
        meta = PromptMetadata(name="My Prompt", prompt_id="p_my")
        registry.register(meta)
        entry = registry.get_by_name("My Prompt")
        assert entry is not None
        assert entry.prompt_id == "p_my"

    def test_unregister(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        registry.register(meta)
        assert registry.unregister("p_test") is True
        assert registry.get("p_test") is None

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("nonexistent") is False

    def test_get_by_category(self, registry):
        meta1 = PromptMetadata(name="A", prompt_id="p_a", category=PromptCategory.analysis)
        meta2 = PromptMetadata(name="B", prompt_id="p_b", category=PromptCategory.analysis)
        meta3 = PromptMetadata(name="C", prompt_id="p_c", category=PromptCategory.seo)
        registry.register(meta1)
        registry.register(meta2)
        registry.register(meta3)
        analysis = registry.get_by_category("analysis")
        assert len(analysis) == 2
        seo = registry.get_by_category("seo")
        assert len(seo) == 1

    def test_get_by_tag(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test", tags=["test_tag", "important"])
        registry.register(meta)
        results = registry.get_by_tag("important")
        assert len(results) == 1
        results = registry.get_by_tag("nonexistent")
        assert len(results) == 0

    def test_list_all(self, registry):
        registry.register(PromptMetadata(name="A", prompt_id="p_a"))
        registry.register(PromptMetadata(name="B", prompt_id="p_b"))
        assert len(registry.list_all()) == 2

    def test_search(self, registry):
        registry.register(PromptMetadata(name="Analysis Prompt", prompt_id="p_analysis"))
        registry.register(PromptMetadata(name="SEO Prompt", prompt_id="p_seo"))
        results = registry.search("analysis")
        assert len(results) == 1
        assert results[0].name == "Analysis Prompt"

    def test_record_usage(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        registry.register(meta)
        registry.record_usage("p_test", latency_ms=100.0, quality_score=0.85)
        entry = registry.get("p_test")
        assert entry.usage_count == 1
        assert entry.avg_latency_ms == 100.0
        assert entry.avg_quality_score == 0.85

    def test_record_usage_multiple(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        registry.register(meta)
        registry.record_usage("p_test", latency_ms=100.0, quality_score=0.8)
        registry.record_usage("p_test", latency_ms=200.0, quality_score=0.9)
        entry = registry.get("p_test")
        assert entry.usage_count == 2
        assert entry.avg_latency_ms == 150.0
        assert entry.avg_quality_score == pytest.approx(0.85, rel=1e-3)

    def test_add_consumer(self, registry):
        meta = PromptMetadata(name="Test", prompt_id="p_test")
        registry.register(meta)
        registry.add_consumer("p_test", "analysis_service")
        entry = registry.get("p_test")
        assert "analysis_service" in entry.consumers

    def test_get_summary(self, registry):
        registry.register(PromptMetadata(name="A", prompt_id="p_a", category=PromptCategory.analysis, tags=["tag1"]))
        registry.register(PromptMetadata(name="B", prompt_id="p_b", category=PromptCategory.seo, tags=["tag2"]))
        summary = registry.get_summary()
        assert summary["total_prompts"] == 2
        assert "analysis" in summary["by_category"]
        assert "seo" in summary["by_category"]
