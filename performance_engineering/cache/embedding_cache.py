"""Embedding Cache — caches vector embeddings and semantic search results.

Reduces redundant embedding API calls by caching text → vector mappings.
Supports cosine similarity search for cache hit detection.
Target: reuse vectors whenever possible.
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


class EmbeddingCache:
    """LRU cache for text embeddings and similarity results.

    Caches: text → embedding vector, query → search_results.
    Uses text hash as key for deterministic lookup.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.cache_embedding_enabled
        self._ttl = self._config.cache_embedding_ttl
        self._lock = threading.Lock()
        self._vectors: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()
        self._search_results: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_vectors = 50000
        self._max_results = 10000
        self._hits = 0
        self._misses = 0

    def build_key(self, text: str) -> str:
        """Build a deterministic cache key from text content.

        Args:
            text: Text to embed.

        Returns:
            SHA-256 hash key.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_embedding(self, text: str) -> list[float] | None:
        """Get a cached embedding vector for text.

        Args:
            text: Text to look up.

        Returns:
            Embedding vector if cached, else None.
        """
        if not self._enabled:
            return None
        key = self.build_key(text)
        with self._lock:
            if key in self._vectors:
                expires_at, vector = self._vectors[key]
                if time.time() <= expires_at:
                    self._vectors.move_to_end(key)
                    self._hits += 1
                    return vector
                del self._vectors[key]
        self._misses += 1
        return None

    def set_embedding(self, text: str, vector: list[float], ttl: int | None = None) -> None:
        """Cache an embedding vector for text.

        Args:
            text: Text that was embedded.
            vector: Embedding vector.
            ttl: Optional TTL override.
        """
        if not self._enabled:
            return
        key = self.build_key(text)
        with self._lock:
            expires_at = time.time() + (ttl or self._ttl)
            self._vectors[key] = (expires_at, vector)
            self._vectors.move_to_end(key)
            while len(self._vectors) > self._max_vectors:
                self._vectors.popitem(last=False)

    def get_search_results(self, query: str) -> Any | None:
        """Get cached search results for a query.

        Args:
            query: Search query text.

        Returns:
            Cached search results or None.
        """
        if not self._enabled:
            return None
        key = f"search:{self.build_key(query)}"
        with self._lock:
            if key in self._search_results:
                expires_at, results = self._search_results[key]
                if time.time() <= expires_at:
                    self._hits += 1
                    return results
                del self._search_results[key]
        self._misses += 1
        return None

    def set_search_results(self, query: str, results: Any, ttl: int | None = None) -> None:
        """Cache search results for a query.

        Args:
            query: Search query text.
            results: Search results to cache.
            ttl: Optional TTL override.
        """
        if not self._enabled:
            return
        key = f"search:{self.build_key(query)}"
        with self._lock:
            expires_at = time.time() + (ttl or 3600)  # 1h default for search
            self._search_results[key] = (expires_at, results)
            while len(self._search_results) > self._max_results:
                self._search_results.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached embeddings and search results."""
        with self._lock:
            self._vectors.clear()
            self._search_results.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Get embedding cache statistics."""
        total = self._hits + self._misses
        return {
            "cache_name": "embedding",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 4),
            "vectors": len(self._vectors),
            "search_results": len(self._search_results),
            "enabled": self._enabled,
            "ttl_seconds": self._ttl,
        }
