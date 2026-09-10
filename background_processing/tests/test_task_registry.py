"""Tests for TaskRegistry — JobType to Celery task path mapping."""

from __future__ import annotations

import pytest

from background_processing.models import JobType
from background_processing.task_registry import (
    clear, get_registry, register, resolve, resolve_all,
)


class TestTaskRegistry:
    def cleanup(self):
        clear()

    def test_register_and_resolve(self):
        clear()
        register("pipeline.test", "pipeline.test_task")
        path = resolve("pipeline.test")
        assert path == "pipeline.test_task"

    def test_resolve_with_enum(self):
        clear()
        register(JobType.PIPELINE_ANALYSIS, "pipeline.generate_analysis")
        path = resolve(JobType.PIPELINE_ANALYSIS)
        assert path == "pipeline.generate_analysis"

    def test_resolve_unknown_raises(self):
        clear()
        with pytest.raises(KeyError):
            resolve("pipeline.nonexistent")

    def test_resolve_all(self):
        clear()
        register("a", "task_a")
        register("b", "task_b")
        paths = resolve_all(["a", "b"])
        assert paths == ["task_a", "task_b"]

    def test_default_registrations_present(self):
        clear()
        from background_processing import task_registry
        import importlib
        importlib.reload(task_registry)
        reg = get_registry()
        assert JobType.PIPELINE_ANALYSIS.value in reg
        assert JobType.PIPELINE_EXPORT.value in reg
        assert JobType.EXPORT_SINGLE.value in reg
        assert JobType.SYSTEM_HEALTH_CHECK.value in reg
        assert len(reg) == 35

    def test_get_registry_returns_copy(self):
        clear()
        register("test.key", "test.path")
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is not reg2
        assert reg1 == reg2

    def test_clear_removes_all(self):
        clear()
        register("key1", "path1")
        register("key2", "path2")
        assert len(get_registry()) == 2
        clear()
        assert len(get_registry()) == 0
