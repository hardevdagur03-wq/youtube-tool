from __future__ import annotations

import time

import pytest

from prompt_management.prompt_cache import PromptCache


@pytest.fixture
def cache():
    return PromptCache(default_ttl=60.0, max_size=100)


class TestPromptCache:
    def test_set_and_get(self, cache):
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self, cache):
        assert cache.get("nonexistent") is None

    def test_expiry(self, cache):
        cache.set("key1", "value1", ttl=0.1)
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_delete(self, cache):
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing(self, cache):
        assert cache.delete("nonexistent") is False

    def test_clear(self, cache):
        cache.set("a", "1")
        cache.set("b", "2")
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.stats()["size"] == 0

    def test_invalidate_pattern(self, cache):
        cache.set("rendered:abc123", "value1")
        cache.set("rendered:def456", "value2")
        cache.set("other:xyz", "value3")
        count = cache.invalidate_pattern("rendered:*")
        assert count == 2
        assert cache.get("rendered:abc123") is None
        assert cache.get("other:xyz") == "value3"

    def test_get_or_set_factory(self, cache):
        called = []
        result = cache.get_or_set("key1", lambda: (called.append(1), "factory_value")[1])
        assert result == "factory_value"
        assert len(called) == 1
        result2 = cache.get_or_set("key1", lambda: "should_not_call")
        assert result2 == "factory_value"
        assert len(called) == 1

    def test_stats(self, cache):
        stats = cache.stats()
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats

    def test_hit_and_miss_counting(self, cache):
        cache.get("miss1")
        cache.get("miss2")
        cache.set("hit1", "val")
        cache.get("hit1")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    def test_make_key(self, cache):
        key = cache.make_key("test", "simple")
        assert key == "prompt:test:simple"

    def test_make_key_long(self, cache):
        key = cache.make_key("test", "x" * 200)
        assert key.startswith("prompt:test:")
        assert len(key) < 80

    def test_max_size_eviction(self, cache):
        small_cache = PromptCache(default_ttl=60.0, max_size=3)
        small_cache.set("a", "1")
        small_cache.set("b", "2")
        small_cache.set("c", "3")
        small_cache.set("d", "4")
        assert small_cache.stats()["size"] <= 3

    def test_contains(self, cache):
        cache.set("key1", "value1")
        assert "key1" in cache
        assert "nonexistent" not in cache

    def test_age(self, cache):
        cache.set("key1", "value1")
        entry = cache._store["key1"]
        assert entry.age() >= 0
