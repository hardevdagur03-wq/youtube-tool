from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prompt_management.prompt_models import PromptMetadata
from prompt_management.prompt_repository import PromptRepository


@dataclass
class RegistryEntry:
    prompt_id: str
    name: str
    version: str
    category: str
    owner: str
    status: str
    dependencies: list[str]
    consumers: list[str] = field(default_factory=list)
    usage_count: int = 0
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    last_used: str = ""
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "owner": self.owner,
            "status": self.status,
            "dependencies": self.dependencies,
            "consumers": self.consumers,
            "usage_count": self.usage_count,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_quality_score": self.avg_quality_score,
            "tags": self.tags,
            "last_used": self.last_used,
            "registered_at": self.registered_at,
        }


class PromptRegistry:
    def __init__(self, repository: PromptRepository):
        self._repository = repository
        self._entries: dict[str, RegistryEntry] = {}
        self._name_index: dict[str, str] = {}
        self._category_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}

    def register(self, metadata: PromptMetadata, consumers: list[str] | None = None) -> RegistryEntry:
        entry = RegistryEntry(
            prompt_id=metadata.prompt_id,
            name=metadata.name,
            version=metadata.version,
            category=metadata.category.value,
            owner=metadata.owner or metadata.author,
            status=metadata.status.value,
            dependencies=metadata.dependencies,
            consumers=consumers or [],
            tags=metadata.tags,
        )
        self._entries[metadata.prompt_id] = entry
        self._name_index[metadata.name] = metadata.prompt_id
        self._category_index.setdefault(metadata.category.value, []).append(metadata.prompt_id)
        for tag in metadata.tags:
            self._tag_index.setdefault(tag, []).append(metadata.prompt_id)
        return entry

    def unregister(self, prompt_id: str) -> bool:
        entry = self._entries.pop(prompt_id, None)
        if entry is None:
            return False
        self._name_index.pop(entry.name, None)
        cat_list = self._category_index.get(entry.category, [])
        if prompt_id in cat_list:
            cat_list.remove(prompt_id)
        for tag in entry.tags:
            tag_list = self._tag_index.get(tag, [])
            if prompt_id in tag_list:
                tag_list.remove(prompt_id)
        return True

    def get(self, prompt_id: str) -> RegistryEntry | None:
        return self._entries.get(prompt_id)

    def get_by_name(self, name: str) -> RegistryEntry | None:
        prompt_id = self._name_index.get(name)
        if prompt_id:
            return self.get(prompt_id)
        return None

    def get_by_category(self, category: str) -> list[RegistryEntry]:
        ids = self._category_index.get(category, [])
        return [self._entries[i] for i in ids if i in self._entries]

    def get_by_tag(self, tag: str) -> list[RegistryEntry]:
        ids = self._tag_index.get(tag.lower(), [])
        return [self._entries[i] for i in ids if i in self._entries]

    def list_all(self) -> list[RegistryEntry]:
        return list(self._entries.values())

    def search(self, query: str) -> list[RegistryEntry]:
        q = query.lower()
        results = []
        for entry in self._entries.values():
            if (
                q in entry.name.lower()
                or q in entry.prompt_id.lower()
                or q in entry.category.lower()
                or q in entry.owner.lower()
                or any(q in d.lower() for d in entry.dependencies)
                or any(q in t.lower() for t in entry.tags)
            ):
                results.append(entry)
        return results

    def record_usage(self, prompt_id: str, latency_ms: float = 0.0, quality_score: float = 0.0) -> None:
        entry = self._entries.get(prompt_id)
        if entry is None:
            return
        entry.usage_count += 1
        entry.last_used = datetime.now(timezone.utc).isoformat()
        if latency_ms > 0:
            old_total = entry.avg_latency_ms * (entry.usage_count - 1)
            entry.avg_latency_ms = (old_total + latency_ms) / entry.usage_count
        if quality_score > 0:
            old_total = entry.avg_quality_score * (entry.usage_count - 1)
            entry.avg_quality_score = (old_total + quality_score) / entry.usage_count

    def add_consumer(self, prompt_id: str, consumer: str) -> None:
        entry = self._entries.get(prompt_id)
        if entry and consumer not in entry.consumers:
            entry.consumers.append(consumer)

    def get_summary(self) -> dict[str, Any]:
        entries = self._entries.values()
        return {
            "total_prompts": len(entries),
            "by_category": {cat: len(items) for cat, items in self._category_index.items()},
            "by_status": self._count_by_status(entries),
            "total_usage": sum(e.usage_count for e in entries),
            "top_used": sorted(
                [{"name": e.name, "usage": e.usage_count} for e in entries],
                key=lambda x: x["usage"],
                reverse=True,
            )[:10],
        }

    def _count_by_status(self, entries: list[RegistryEntry]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in entries:
            counts[e.status] = counts.get(e.status, 0) + 1
        return counts
