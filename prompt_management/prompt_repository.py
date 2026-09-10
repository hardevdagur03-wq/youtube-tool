from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_management.prompt_models import (
    PromptAnalytics,
    PromptExperiment,
    PromptMetadata,
    PromptStatus,
    PromptVersion,
)


class PromptRepository:
    def __init__(self, base_path: str | Path | None = None):
        self.base_path = Path(base_path) if base_path else Path.cwd() / "prompts"
        self._metadata_cache: dict[str, PromptMetadata] = {}
        self._version_cache: dict[str, list[PromptVersion]] = {}
        self._analytics_cache: dict[str, list[PromptAnalytics]] = {}
        self._experiment_cache: dict[str, PromptExperiment] = {}

    def _metadata_path(self, prompt_id: str) -> Path:
        return self.base_path / "metadata" / f"{prompt_id}.json"

    def _versions_dir(self, prompt_id: str) -> Path:
        p = self.base_path / "versions" / prompt_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save_metadata(self, metadata: PromptMetadata) -> PromptMetadata:
        path = self._metadata_path(metadata.prompt_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        self._metadata_cache[metadata.prompt_id] = metadata
        return metadata

    def get_metadata(self, prompt_id: str) -> PromptMetadata | None:
        if prompt_id in self._metadata_cache:
            return self._metadata_cache[prompt_id]
        path = self._metadata_path(prompt_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        metadata = PromptMetadata(**data)
        self._metadata_cache[prompt_id] = metadata
        return metadata

    def list_metadata(self) -> list[PromptMetadata]:
        metadata_dir = self.base_path / "metadata"
        if not metadata_dir.exists():
            return []
        results = []
        for f in sorted(metadata_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(PromptMetadata(**data))
        return results

    def delete_metadata(self, prompt_id: str) -> bool:
        path = self._metadata_path(prompt_id)
        if path.exists():
            path.unlink()
        self._metadata_cache.pop(prompt_id, None)
        return True

    def save_version(self, version: PromptVersion) -> PromptVersion:
        versions_dir = self._versions_dir(version.prompt_id)
        path = versions_dir / f"v{version.version_number}.json"
        path.write_text(version.model_dump_json(indent=2), encoding="utf-8")
        if version.prompt_id not in self._version_cache:
            self._version_cache[version.prompt_id] = []
        existing = [v for v in self._version_cache[version.prompt_id] if v.version_id != version.version_id]
        existing.append(version)
        self._version_cache[version.prompt_id] = sorted(existing, key=lambda v: v.version_number)
        return version

    def get_version(self, prompt_id: str, version: str) -> PromptVersion | None:
        versions_dir = self._versions_dir(prompt_id)
        path = versions_dir / f"v{version}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return PromptVersion(**data)
        return None

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        if prompt_id in self._version_cache:
            return self._version_cache[prompt_id]
        versions_dir = self._versions_dir(prompt_id)
        if not versions_dir.exists():
            return []
        results = []
        for f in sorted(versions_dir.glob("v*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(PromptVersion(**data))
        self._version_cache[prompt_id] = results
        return results

    def get_latest_version(self, prompt_id: str) -> PromptVersion | None:
        versions = self.list_versions(prompt_id)
        if not versions:
            return None

        def _sort_key(v: PromptVersion) -> tuple[int, int, int]:
            parts = v.version_number.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))

        return max(versions, key=_sort_key)

    def save_analytics(self, analytics: PromptAnalytics) -> PromptAnalytics:
        analytics_dir = self.base_path / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)
        path = analytics_dir / f"{analytics.analytics_id}.json"
        path.write_text(analytics.model_dump_json(indent=2), encoding="utf-8")
        if analytics.prompt_id not in self._analytics_cache:
            self._analytics_cache[analytics.prompt_id] = []
        self._analytics_cache[analytics.prompt_id].append(analytics)
        return analytics

    def get_analytics(self, prompt_id: str) -> list[PromptAnalytics]:
        if prompt_id in self._analytics_cache:
            return self._analytics_cache[prompt_id]
        analytics_dir = self.base_path / "analytics"
        if not analytics_dir.exists():
            return []
        results = []
        for f in sorted(analytics_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            record = PromptAnalytics(**data)
            if record.prompt_id == prompt_id:
                results.append(record)
        self._analytics_cache[prompt_id] = results
        return results

    def save_experiment(self, experiment: PromptExperiment) -> PromptExperiment:
        experiments_dir = self.base_path / "experiments"
        experiments_dir.mkdir(parents=True, exist_ok=True)
        path = experiments_dir / f"{experiment.experiment_id}.json"
        path.write_text(experiment.model_dump_json(indent=2), encoding="utf-8")
        self._experiment_cache[experiment.experiment_id] = experiment
        return experiment

    def get_experiment(self, experiment_id: str) -> PromptExperiment | None:
        if experiment_id in self._experiment_cache:
            return self._experiment_cache[experiment_id]
        experiments_dir = self.base_path / "experiments"
        path = experiments_dir / f"{experiment_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        experiment = PromptExperiment(**data)
        self._experiment_cache[experiment_id] = experiment
        return experiment

    def list_experiments(self) -> list[PromptExperiment]:
        experiments_dir = self.base_path / "experiments"
        if not experiments_dir.exists():
            return []
        results = []
        for f in sorted(experiments_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(PromptExperiment(**data))
        return results

    def get_prompt_by_name(self, name: str) -> PromptMetadata | None:
        for meta in self.list_metadata():
            if meta.name == name:
                return meta
        return None

    def search_prompts(self, query: str) -> list[PromptMetadata]:
        q = query.lower()
        results = []
        for meta in self.list_metadata():
            if (
                q in meta.name.lower()
                or q in meta.prompt_id.lower()
                or q in meta.description.lower()
                or any(q in t.lower() for t in meta.tags)
                or q in meta.category.value.lower()
            ):
                results.append(meta)
        return results

    def get_prompts_by_category(self, category: str) -> list[PromptMetadata]:
        return [m for m in self.list_metadata() if m.category.value == category]

    def get_prompts_by_status(self, status: PromptStatus) -> list[PromptMetadata]:
        return [m for m in self.list_metadata() if m.status == status]
