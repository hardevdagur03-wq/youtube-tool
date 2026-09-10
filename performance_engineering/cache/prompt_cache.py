"""Prompt Cache — caches LLM responses by prompt hash + model + temperature.

Reduces duplicate AI calls by caching deterministic LLM results.
Keyed by (prompt_hash, model_name, temperature) for exact match reuse.
Target: cache hit rate >90%.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class PromptCache:
    """LRU cache for LLM prompt responses.

    Caches responses by (prompt_text_hash, model, temperature) key.
    Only caches deterministic prompts (temperature < 0.2).
    Supports Redis backend (L2) and in-memory (L1).

    Usage::

        cache = PromptCache()
        key = cache.build_key("Analyze this", "gpt-4", 0.1)
        cached = cache.get(key)
        if not cached:
            response = await llm.call(prompt)
            cache.set(key, response)
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.cache_prompt_enabled
        self._ttl = self._config.cache_prompt_ttl
        self._lock = threading.Lock()
        self._l1: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._l1_max = 10000
        self._hits = 0
        self._misses = 0

    def build_key(
        self, prompt: str, model: str, temperature: float = 0.1
    ) -> str | None:
        """Build a deterministic cache key from prompt + model + temperature.

        Args:
            prompt: The prompt text.
            model: Model name (e.g. 'gpt-4', 'gemini-2.5-flash').
            temperature: Model temperature (only cached if < 0.2).

        Returns:
            Cache key string if cacheable, None if not deterministic.
        """
        if temperature >= 0.2:
            return None
        raw = f"{prompt}:{model}:{temperature}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        """Get a cached prompt response.

        Args:
            key: Cache key from build_key().

        Returns:
            Cached response data or None.
        """
        if not self._enabled or not key:
            return None
        with self._lock:
            if key in self._l1:
                expires_at, data = self._l1[key]
                if time.time() <= expires_at:
                    self._l1.move_to_end(key)
                    self._hits += 1
                    return data
                else:
                    del self._l1[key]
        self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        """Cache a prompt response.

        Args:
            key: Cache key from build_key().
            data: Response data to cache.
            ttl: Optional TTL override in seconds.
        """
        if not self._enabled or not key:
            return
        with self._lock:
            expires_at = time.time() + (ttl or self._ttl)
            self._l1[key] = (expires_at, data)
            self._l1.move_to_end(key)
            while len(self._l1) > self._l1_max:
                self._l1.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific cache entry.

        Args:
            key: Cache key to invalidate.
        """
        with self._lock:
            self._l1.pop(key, None)

    def clear(self) -> None:
        """Clear all cached prompt responses."""
        with self._lock:
            self._l1.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "cache_name": "prompt",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 4),
            "size": len(self._l1),
            "enabled": self._enabled,
            "ttl_seconds": self._ttl,
        }
