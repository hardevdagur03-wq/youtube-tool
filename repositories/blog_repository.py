"""Blog repository — in-memory cache for blog generation results."""

from __future__ import annotations
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from models.blog_generation import BlogGenerationResult

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600


class BlogRepository:
    """In-memory cache with optional disk persistence for blog results."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def save(self, video_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._cache[video_id] = (time.time(), result)
        if self._cache_dir:
            self._save_to_disk(video_id, result)

    def get(self, video_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._cache.get(video_id)
            if entry is None:
                return None
            ts, result = entry
            if time.time() - ts > _CACHE_TTL_SECONDS:
                del self._cache[video_id]
                return None
            return result

    def delete(self, video_id: str) -> bool:
        with self._lock:
            existed = video_id in self._cache
            self._cache.pop(video_id, None)
        if existed and self._cache_dir:
            path = self._cache_dir / f"{video_id}.json"
            if path.exists():
                path.unlink(missing_ok=True)
        return existed

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
        if self._cache_dir:
            for f in self._cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)

    def get_cached_video_ids(self) -> list[str]:
        with self._lock:
            now = time.time()
            return [vid for vid, (ts, _) in self._cache.items() if now - ts <= _CACHE_TTL_SECONDS]

    def _save_to_disk(self, video_id: str, result: dict[str, Any]) -> None:
        try:
            path = self._cache_dir / f"{video_id}.json"
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to cache blog for %s to disk: %s", video_id, exc)

    def _load_from_disk(self) -> None:
        if not self._cache_dir or not self._cache_dir.exists():
            return
        for path in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._cache[path.stem] = (time.time(), data)
            except Exception as exc:
                logger.warning("Failed to load cached blog from %s: %s", path.name, exc)
