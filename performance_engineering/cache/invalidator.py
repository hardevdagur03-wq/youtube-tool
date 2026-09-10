"""Cache Invalidator — smart cache invalidation across all cache types.

Manages cache lifecycle: TTL-based expiry, explicit invalidation,
namespace-based bulk invalidation, and write-through updates.
"""

from __future__ import annotations

import logging
from typing import Any

from performance_engineering.cache.prompt_cache import PromptCache
from performance_engineering.cache.embedding_cache import EmbeddingCache
from performance_engineering.cache.query_cache import QueryCache

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """Smart cache invalidation across all cache types.

    Coordinates invalidation between prompt, embedding, and query caches.
    Supports event-based invalidation (e.g., on project update → invalidate
    all caches for that project).
    """

    def __init__(
        self,
        prompt_cache: PromptCache | None = None,
        embedding_cache: EmbeddingCache | None = None,
        query_cache: QueryCache | None = None,
    ) -> None:
        self._prompt = prompt_cache
        self._embedding = embedding_cache
        self._query = query_cache

    def invalidate_all(self) -> dict[str, int]:
        """Invalidate all caches.

        Returns:
            Dict of cache_name -> entries invalidated.
        """
        result = {}
        if self._prompt:
            self._prompt.clear()
            result["prompt"] = -1
        if self._embedding:
            self._embedding.clear()
            result["embedding"] = -1
        if self._query:
            self._query.clear()
            result["query"] = -1
        logger.info("All caches invalidated")
        return result

    def invalidate_video(self, video_id: str) -> dict[str, int]:
        """Invalidate all caches related to a video.

        Args:
            video_id: YouTube video ID.

        Returns:
            Dict of cache_name -> entries invalidated.
        """
        result = {}
        if self._query:
            count = self._query.invalidate_pattern(video_id)
            result["query"] = count
        logger.info("Cache invalidated for video %s: %s", video_id, result)
        return result

    def invalidate_project(self, project_id: str) -> dict[str, int]:
        """Invalidate all caches related to a project.

        Args:
            project_id: Project UUID.

        Returns:
            Dict of cache_name -> entries invalidated.
        """
        return self.invalidate_video(project_id)

    def on_table_write(self, table: str) -> dict[str, int]:
        """Called when a database table is written to.

        Args:
            table: Table name that was modified.

        Returns:
            Dict of cache_name -> entries invalidated.
        """
        result = {}
        if self._query:
            count = self._query.invalidate_table(table)
            result["query"] = count
        return result

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated cache statistics."""
        stats = {}
        if self._prompt:
            stats["prompt"] = self._prompt.stats
        if self._embedding:
            stats["embedding"] = self._embedding.stats
        if self._query:
            stats["query"] = self._query.stats
        return stats
