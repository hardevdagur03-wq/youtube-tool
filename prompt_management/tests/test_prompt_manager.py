from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_manager import PromptManager
from prompt_management.prompt_models import ExperimentVariant, PromptStatus
from prompt_management.prompt_repository import PromptRepository


@pytest.fixture
def manager():
    with tempfile.TemporaryDirectory() as tmp:
        prompts_dir = Path(tmp) / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        (prompts_dir / "shared").mkdir(parents=True, exist_ok=True)
        (prompts_dir / "partials").mkdir(parents=True, exist_ok=True)

        (prompts_dir / "analysis.md").write_text("""---
prompt_id: p_analysis_v1
name: Content Analysis
version: 1.0.0
author: Platform Team
status: draft
category: analysis
tags: [content, analysis, transcript]
language: en
target_model: gemini-2.0-flash
temperature: 0.3
max_tokens: 4096
risk_level: medium
supported_models: [gemini-2.0-flash, gemini-2.5-pro]
dependencies: []
---

Analyze this transcript: {{transcript}}
Title: {{title}}
""", encoding="utf-8")

        (prompts_dir / "shared" / "writing_style.md").write_text(
            "Style: {{tone}}", encoding="utf-8",
        )

        repo = PromptRepository(Path(tmp) / "prompts_data")
        m = PromptManager(
            prompts_dir=prompts_dir,
            repository=repo,
        )
        asyncio.run(m.initialize())
        yield m


@pytest.mark.asyncio
class TestPromptManager:
    async def test_initialize(self, manager):
        assert manager._initialized
        assert len(manager.registry.list_all()) > 0

    async def test_get_prompt(self, manager):
        meta, content = manager.get_prompt("analysis")
        assert meta is not None
        assert content is not None
        assert meta.name == "Content Analysis"

    async def test_get_nonexistent_prompt(self, manager):
        meta, content = manager.get_prompt("nonexistent_prompt_xyz")
        assert meta is None
        assert content is None

    async def test_render_prompt(self, manager):
        result = manager.render("analysis", {
            "transcript": "test transcript",
            "title": "Test",
        })
        assert result is not None
        assert "test transcript" in result

    async def test_render_nonexistent(self, manager):
        result = manager.render("nonexistent_prompt_xyz", {})
        assert result is None

    async def test_render_content(self, manager):
        result = manager.render_content("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    async def test_validate_prompt(self, manager):
        result = manager.validate("analysis", {"transcript": "test", "title": "test"})
        assert result.is_valid

    async def test_create_version(self, manager):
        version = manager.create_version(
            prompt_name="analysis",
            content="New content",
            author="test",
            change_summary="Test update",
            change_type="patch",
        )
        assert version is not None
        assert version.content == "New content"

    async def test_get_version_history(self, manager):
        history = manager.get_version_history("analysis")
        assert len(history) >= 1

    async def test_promote_prompt(self, manager):
        result = manager.promote("analysis", PromptStatus.review)
        assert result is True
        meta = manager.repository.get_metadata("p_analysis_v1")
        assert meta is not None
        assert meta.status == PromptStatus.review

    async def test_rollback(self, manager):
        manager.create_version("analysis", "v2 content", author="test", change_summary="v2")
        manager.create_version("analysis", "v3 content", author="test", change_summary="v3")
        rolled = manager.rollback("analysis", "1.0.0", author="test")
        assert rolled is not None

    async def test_search_prompts(self, manager):
        results = manager.search_prompts("analysis")
        assert len(results) >= 1

    async def test_list_prompts(self, manager):
        prompts = manager.list_prompts()
        assert len(prompts) > 0

    async def test_list_categories(self, manager):
        categories = manager.list_categories()
        assert "analysis" in categories

    async def test_record_execution(self, manager):
        manager.record_execution(
            prompt_name="analysis",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=250.0,
            success=True,
            quality_score=0.85,
            model_used="gemini-2.0-flash",
        )

    async def test_get_analytics(self, manager):
        manager.record_execution(prompt_name="analysis", prompt_tokens=100, completion_tokens=50, latency_ms=200.0, success=True, quality_score=0.9, model_used="gemini-2.0-flash")
        analytics = manager.get_analytics("analysis")
        assert analytics["total_executions"] >= 1

    async def test_global_analytics(self, manager):
        stats = manager.get_global_analytics()
        assert stats["total_prompts"] > 0

    async def test_create_experiment(self, manager):
        variants = [
            ExperimentVariant(name="Control", prompt_id="p_analysis_v1", version="1.0.0", traffic_percent=50.0, is_control=True),
            ExperimentVariant(name="Test", prompt_id="p_analysis_v1", version="1.1.0", traffic_percent=50.0),
        ]
        exp = manager.create_experiment(
            name="Analysis Test",
            prompt_name="analysis",
            variants=variants,
            created_by="test",
        )
        assert exp is not None
        assert exp.name == "Analysis Test"

    async def test_get_experiment(self, manager):
        variants = [
            ExperimentVariant(name="A", prompt_id="p_analysis_v1", version="1.0.0", traffic_percent=50.0),
            ExperimentVariant(name="B", prompt_id="p_analysis_v1", version="1.1.0", traffic_percent=50.0),
        ]
        exp = manager.create_experiment(name="Test", prompt_name="analysis", variants=variants)
        fetched = manager.get_experiment(exp.experiment_id)
        assert fetched is not None

    async def test_cache_stats(self, manager):
        stats = manager.get_cache_stats()
        assert "size" in stats
        assert "hit_ratio" in stats

    async def test_invalidate_cache(self, manager):
        manager.render("analysis", {"transcript": "test", "title": "T"})
        manager.invalidate_cache("analysis")
        stats = manager.get_cache_stats()
        assert stats["hits"] == 0 or stats["size"] == 0

    async def test_get_prompts_dir(self, manager):
        d = manager.get_prompts_dir()
        assert d.exists()
        assert (d / "analysis.md").exists()
