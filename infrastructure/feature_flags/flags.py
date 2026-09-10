"""Feature flag system for gradual rollout and experimentation.

Flags can be controlled via environment variables or a backend store.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureFlag:
    """A single feature flag definition."""
    key: str
    enabled: bool = False
    description: str = ""
    env_var: str = ""

    def is_enabled(self) -> bool:
        if self.env_var:
            env_val = os.environ.get(self.env_var)
            if env_val is not None:
                return env_val.lower() in ("1", "true", "yes", "enabled")
        return self.enabled


DEFAULT_FLAGS = [
    FeatureFlag("pipeline_v2", enabled=False, description="Enable v2 pipeline", env_var="FF_PIPELINE_V2"),
    FeatureFlag("gemini_provider", enabled=True, description="Enable Gemini AI provider", env_var="FF_GEMINI"),
    FeatureFlag("openai_provider", enabled=False, description="Enable OpenAI provider", env_var="FF_OPENAI"),
    FeatureFlag("anthropic_provider", enabled=False, description="Enable Anthropic provider", env_var="FF_ANTHROPIC"),
    FeatureFlag("whisper_fallback", enabled=True, description="Enable Whisper fallback for transcripts", env_var="FF_WHISPER"),
    FeatureFlag("knowledge_graph", enabled=True, description="Enable knowledge graph generation", env_var="FF_KG"),
    FeatureFlag("seo_intelligence", enabled=True, description="Enable SEO intelligence", env_var="FF_SEO_INTEL"),
    FeatureFlag("batch_exports", enabled=False, description="Enable batch export", env_var="FF_BATCH_EXPORT"),
    FeatureFlag("editor_ai_actions", enabled=True, description="Enable AI actions in editor", env_var="FF_EDITOR_AI"),
    FeatureFlag("publishing_cms", enabled=False, description="Enable CMS publishing", env_var="FF_PUBLISHING"),
    FeatureFlag("cache_enabled", enabled=True, description="Enable response caching", env_var="FF_CACHE"),
    FeatureFlag("debug_mode", enabled=False, description="Enable debug endpoints", env_var="FF_DEBUG"),
]


class FeatureFlagStore(ABC):
    @abstractmethod
    def get(self, key: str) -> bool:
        ...

    @abstractmethod
    def set(self, key: str, enabled: bool) -> None:
        ...


class EnvFeatureFlagStore(FeatureFlagStore):
    def get(self, key: str) -> bool:
        env_var = f"FF_{key.upper()}"
        val = os.environ.get(env_var)
        if val is not None:
            return val.lower() in ("1", "true", "yes", "enabled")
        return False

    def set(self, key: str, enabled: bool) -> None:
        pass


class FeatureFlagManager:
    """Manages feature flag evaluation."""

    def __init__(self, store: FeatureFlagStore | None = None) -> None:
        self._store = store or EnvFeatureFlagStore()
        self._flags: dict[str, FeatureFlag] = {}
        for flag in DEFAULT_FLAGS:
            self._flags[flag.key] = flag

    def register(self, flag: FeatureFlag) -> None:
        self._flags[flag.key] = flag

    def is_enabled(self, key: str) -> bool:
        flag = self._flags.get(key)
        if not flag:
            return False
        return self._store.get(key) or flag.is_enabled()

    def get_all(self) -> list[FeatureFlag]:
        return list(self._flags.values())

    def update(self, key: str, enabled: bool) -> None:
        flag = self._flags.get(key)
        if flag:
            flag.enabled = enabled


feature_flags = FeatureFlagManager()
