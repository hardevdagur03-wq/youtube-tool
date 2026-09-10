"""Tests for OptimizationCacheManager."""

from __future__ import annotations
import tempfile
import os
from optimization.cache_manager import OptimizationCacheManager


class TestOptimizationCacheManager:
    def _make_cm(self):
        tmpdir = tempfile.mkdtemp()
        return OptimizationCacheManager(cache_dir=tmpdir), tmpdir

    def test_init(self):
        cm = OptimizationCacheManager()
        assert cm is not None

    def test_set_and_get(self):
        cm, tmpdir = self._make_cm()
        cm.set("test_key", {"value": 42})
        result = cm.get("test_key")
        assert result == {"value": 42}

    def test_get_missing(self):
        cm, tmpdir = self._make_cm()
        result = cm.get("nonexistent")
        assert result is None

    def test_get_or_compute(self):
        cm, tmpdir = self._make_cm()
        called = False

        def compute():
            nonlocal called
            called = True
            return "computed_value"

        result = cm.get_or_compute("compute_key", compute)
        assert result == "computed_value"
        assert called is True

        # Second call should use cache
        called = False
        result = cm.get_or_compute("compute_key", compute)
        assert result == "computed_value"
        assert called is False

    def test_invalidate(self):
        cm, tmpdir = self._make_cm()
        cm.set("prefix_key1", "value1")
        cm.set("prefix_key2", "value2")
        cm.set("other_key", "value3")
        cm.invalidate("prefix_")
        assert cm.get("prefix_key1") is None

    def test_make_key(self):
        cm = OptimizationCacheManager()
        key1 = cm.make_key("section", "0", "seo")
        key2 = cm.make_key("section", "0", "seo")
        assert key1 == key2
        assert len(key1) == 64

    def test_stats(self):
        cm, tmpdir = self._make_cm()
        cm.get("nonexistent")
        stats = cm.stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_ratio" in stats

    def test_clear(self):
        cm, tmpdir = self._make_cm()
        cm.set("key", "value")
        cm.clear()
        assert cm._hits == 0
        assert cm._misses == 0
