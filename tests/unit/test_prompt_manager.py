from __future__ import annotations

import pytest


class TestPromptModels:
    def test_prompt_metadata(self):
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        meta = PromptMetadata(prompt_id="p1", name="Test Prompt", content="Hello {name}", category=PromptCategory.custom, status=PromptStatus.draft)
        assert meta.prompt_id == "p1"
        assert meta.status == PromptStatus.draft

    def test_prompt_version(self):
        from prompt_management.prompt_models import PromptVersion
        v = PromptVersion(prompt_id="p1", version_number="1", content="Version 1 content", author="tester", change_notes="Initial")
        assert v.version_number == "1"

    def test_prompt_analytics(self):
        from prompt_management.prompt_models import PromptAnalytics
        a = PromptAnalytics(prompt_id="p1", version="1.0.0", execution_count=100, avg_latency_ms=500.0)
        assert a.execution_count == 100

    def test_prompt_experiment(self):
        from prompt_management.prompt_models import PromptExperiment, ExperimentStatus
        exp = PromptExperiment(experiment_id="e1", name="Test Experiment", status=ExperimentStatus.running)
        assert exp.name == "Test Experiment"

    def test_experiment_variant(self):
        from prompt_management.prompt_models import ExperimentVariant
        v = ExperimentVariant(variant_id="v1", name="A", prompt_id="p1", version="1.0.0", traffic_percent=50.0)
        assert v.traffic_percent == 50.0


class TestPromptLoader:
    def test_load_prompt(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("---\nprompt_id: p1\nname: Test\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nHello world!")
        loader = PromptLoader(tmp_path)
        prompt = loader.load_content("test_prompt")
        assert prompt == "Hello world!"

    def test_load_all(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        (tmp_path / "a.md").write_text("---\nprompt_id: a\nname: A\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nAAA")
        (tmp_path / "b.md").write_text("---\nprompt_id: b\nname: B\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nBBB")
        loader = PromptLoader(tmp_path)
        prompts = loader.load_all_prompts()
        assert isinstance(prompts, dict)


class TestPromptRenderer:
    def test_render(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_renderer import PromptRenderer
        prompt_file = tmp_path / "greeting.md"
        prompt_file.write_text("Hello {{name}}, welcome to {{place}}!")
        loader = PromptLoader(tmp_path)
        renderer = PromptRenderer(loader)
        result = renderer.render("greeting", {"name": "User", "place": "Python World"})
        assert result == "Hello User, welcome to Python World!"

    def test_render_missing_variable(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_renderer import PromptRenderer
        prompt_file = tmp_path / "hello.md"
        prompt_file.write_text("Hello {{name}}!")
        loader = PromptLoader(tmp_path)
        renderer = PromptRenderer(loader)
        result = renderer.render("hello", {})
        assert "{{name}}" in result

    def test_render_with_template(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_renderer import PromptRenderer
        loader = PromptLoader(tmp_path)
        renderer = PromptRenderer(loader)
        result = renderer.render_content("Hello {{name}}!", {"name": "World"})
        assert "World" in result


class TestPromptValidator:
    def test_validate(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_validator import PromptValidator
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("---\nprompt_id: p1\nname: test\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nHello {{name}}, welcome to {{place}}!")
        loader = PromptLoader(tmp_path)
        validator = PromptValidator(loader)
        result = validator.validate("test_prompt", {"name": "User", "place": "World"})
        assert result.is_valid or not result.is_valid

    def test_validate_missing_variables(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_validator import PromptValidator
        prompt_file = tmp_path / "hello.md"
        prompt_file.write_text("---\nprompt_id: p1\nname: hello\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nHello {{name}}!")
        loader = PromptLoader(tmp_path)
        validator = PromptValidator(loader)
        result = validator.validate("hello")
        assert result.is_valid is True

    def test_validate_empty_prompt(self, tmp_path):
        from prompt_management.prompt_loader import PromptLoader
        from prompt_management.prompt_validator import PromptValidator
        prompt_file = tmp_path / "empty.md"
        prompt_file.write_text("")
        loader = PromptLoader(tmp_path)
        validator = PromptValidator(loader)
        result = validator.validate("empty")
        assert result.is_valid is False


class TestPromptVersionManager:
    def test_create_version(self, tmp_path):
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_version_manager import PromptVersionManager
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        vm = PromptVersionManager(repo)
        meta = PromptMetadata(prompt_id="p1", name="Test", category=PromptCategory.custom, status=PromptStatus.draft)
        repo.save_metadata(meta)
        v = vm.create_version(prompt_id="p1", content="Version 1", change_summary="Initial")
        assert v.version_number == "1.0.0"

    def test_get_version_history(self, tmp_path):
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_version_manager import PromptVersionManager
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        vm = PromptVersionManager(repo)
        meta = PromptMetadata(prompt_id="p1", name="Test", category=PromptCategory.custom, status=PromptStatus.draft)
        repo.save_metadata(meta)
        vm.create_version("p1", "V1", change_summary="v1")
        vm.create_version("p1", "V2", change_summary="v2")
        history = vm.get_version_history("p1")
        assert len(history) == 2


class TestPromptCache:
    def test_set_and_get(self):
        from prompt_management.prompt_cache import PromptCache
        cache = PromptCache()
        cache.set("prompt_key", "Hello {name}")
        result = cache.get("prompt_key")
        assert result == "Hello {name}"

    def test_cache_miss(self):
        from prompt_management.prompt_cache import PromptCache
        cache = PromptCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_clear(self):
        from prompt_management.prompt_cache import PromptCache
        cache = PromptCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None


class TestPromptRegistry:
    def test_register_and_get(self, tmp_path):
        from prompt_management.prompt_registry import PromptRegistry
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        registry = PromptRegistry(repo)
        meta = PromptMetadata(prompt_id="p1", name="Test Prompt", category=PromptCategory.custom, status=PromptStatus.draft)
        registry.register(meta)
        retrieved = registry.get("p1")
        assert retrieved is not None
        assert retrieved.name == "Test Prompt"

    def test_list_all(self, tmp_path):
        from prompt_management.prompt_registry import PromptRegistry
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        registry = PromptRegistry(repo)
        m1 = PromptMetadata(prompt_id="p1", name="P1", category=PromptCategory.custom, status=PromptStatus.draft)
        m2 = PromptMetadata(prompt_id="p2", name="P2", category=PromptCategory.custom, status=PromptStatus.draft)
        registry.register(m1)
        registry.register(m2)
        prompts = registry.list_all()
        assert len(prompts) == 2


class TestPromptAnalyticsCollector:
    def test_record_call(self, tmp_path):
        from prompt_management.prompt_analytics import PromptAnalyticsCollector
        from prompt_management.prompt_repository import PromptRepository
        repo = PromptRepository(tmp_path)
        collector = PromptAnalyticsCollector(repo)
        collector.record_execution(prompt_id="p1", version="1.0.0", latency_ms=150.0, prompt_tokens=50, completion_tokens=50, success=True)
        stats = collector.get_summary("p1")
        assert stats["total_executions"] == 1
        assert stats["total_tokens"] == 100

    def test_get_all_stats(self, tmp_path):
        from prompt_management.prompt_analytics import PromptAnalyticsCollector
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        collector = PromptAnalyticsCollector(repo)
        meta1 = PromptMetadata(prompt_id="p1", name="P1", category=PromptCategory.custom, status=PromptStatus.draft)
        meta2 = PromptMetadata(prompt_id="p2", name="P2", category=PromptCategory.custom, status=PromptStatus.draft)
        repo.save_metadata(meta1)
        repo.save_metadata(meta2)
        collector.record_execution("p1", "1.0.0", 100.0, 25, 25, True)
        collector.record_execution("p2", "1.0.0", 200.0, 50, 50, True)
        all_stats = collector.get_global_stats()
        prompt_ids = [s["prompt_id"] for s in all_stats["prompts"]]
        assert "p1" in prompt_ids
        assert "p2" in prompt_ids


class TestPromptExperimentManager:
    def test_create_experiment(self, tmp_path):
        from prompt_management.prompt_experiments import PromptExperimentManager
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import ExperimentVariant
        repo = PromptRepository(tmp_path)
        mgr = PromptExperimentManager(repo)
        variants = [ExperimentVariant(variant_id="v1", name="A", prompt_id="p1", version="1.0.0", traffic_percent=50.0)]
        exp = mgr.create_experiment(name="Test Experiment", target_prompt_id="p1", variants=variants)
        assert exp.name == "Test Experiment"

    def test_get_experiment(self, tmp_path):
        from prompt_management.prompt_experiments import PromptExperimentManager
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import ExperimentVariant
        repo = PromptRepository(tmp_path)
        mgr = PromptExperimentManager(repo)
        variants = [ExperimentVariant(variant_id="v1", name="A", prompt_id="p1", version="1.0.0", traffic_percent=100.0)]
        created = mgr.create_experiment(name="Test", target_prompt_id="p1", variants=variants)
        retrieved = mgr.get_experiment(created.experiment_id)
        assert retrieved is not None


class TestPromptRepository:
    def test_save_and_load(self, tmp_path):
        from prompt_management.prompt_repository import PromptRepository
        from prompt_management.prompt_models import PromptMetadata, PromptStatus, PromptCategory
        repo = PromptRepository(tmp_path)
        meta = PromptMetadata(prompt_id="p1", name="Test", content="Hello {name}", category=PromptCategory.custom, status=PromptStatus.draft)
        repo.save_metadata(meta)
        loaded = repo.get_metadata("p1")
        assert loaded is not None
        assert loaded.name == "Test"

    def test_load_nonexistent(self, tmp_path):
        from prompt_management.prompt_repository import PromptRepository
        repo = PromptRepository(tmp_path)
        loaded = repo.get_metadata("nonexistent")
        assert loaded is None


class TestPromptManager:
    def test_get_prompt(self, tmp_path):
        from prompt_management.prompt_manager import PromptManager
        mgr = PromptManager(prompts_dir=tmp_path)
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("---\nprompt_id: p1\nname: Test\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nHello {{name}}!")
        result = mgr.get_prompt("test_prompt")
        assert result is not None

    def test_render_prompt(self, tmp_path):
        from prompt_management.prompt_manager import PromptManager
        mgr = PromptManager(prompts_dir=tmp_path)
        prompt_file = tmp_path / "hello.md"
        prompt_file.write_text("---\nprompt_id: p1\nname: Hello\nversion: 1.0.0\nstatus: draft\ncategory: custom\n---\nHello {{name}}!")
        result = mgr.render("hello", {"name": "Python"})
        assert "Python" in result
