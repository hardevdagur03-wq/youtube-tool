"""Cache Manager — intelligent caching for pipeline stage outputs.

Stores and retrieves stage results to avoid redundant work.
No existing code is modified.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from infrastructure.cache import TTLCache

logger = logging.getLogger(__name__)

STAGE_TTL: dict[str, float] = {
    "metadata": 86400,
    "transcript": 86400,
    "analysis": 3600,
    "seo": 3600,
    "outline": 3600,
    "sections": 3600,
    "merge": 3600,
    "review": 1800,
    "export": 3600,
}


class CacheManager:
    """Intelligent caching for pipeline stage outputs."""

    def __init__(self) -> None:
        self._caches: dict[str, TTLCache] = {}
        self._hits = 0
        self._misses = 0

    def _get_cache(self, stage: str) -> TTLCache:
        if stage not in self._caches:
            ttl = STAGE_TTL.get(stage, 3600)
            self._caches[stage] = TTLCache[dict](ttl_seconds=ttl, max_size=5000)
        return self._caches[stage]

    def _make_key(self, stage: str, ctx: Any) -> str:
        video_id = getattr(ctx, "video_id", "") or ""
        settings = getattr(ctx, "settings", {}) or {}
        stable = f"{stage}:{video_id}:{json.dumps(settings, sort_keys=True, default=str)}"
        return hashlib.sha256(stable.encode()).hexdigest()[:32]

    def get(self, stage: str, ctx: Any) -> dict | None:
        cache = self._get_cache(stage)
        key = self._make_key(stage, ctx)
        result = cache.get(key)
        if result is not None:
            self._hits += 1
            logger.debug("Cache HIT for stage '%s' (key=%s)", stage, key[:12])
            return result
        self._misses += 1
        logger.debug("Cache MISS for stage '%s' (key=%s)", stage, key[:12])
        return None

    def set(self, stage: str, ctx: Any, data: dict) -> None:
        cache = self._get_cache(stage)
        key = self._make_key(stage, ctx)
        cache.set(key, data)
        logger.debug("Cache SET for stage '%s' (key=%s)", stage, key[:12])

    def invalidate(self, stage: str, ctx: Any) -> None:
        cache = self._get_cache(stage)
        key = self._make_key(stage, ctx)
        cache.delete(key)

    def invalidate_all(self, stage: str) -> None:
        if stage in self._caches:
            self._caches[stage].clear()

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / total * 100, 1) if total > 0 else 0,
            "caches": {
                name: {"size": c.size, "ttl": STAGE_TTL.get(name, 3600)}
                for name, c in self._caches.items()
            },
        }
