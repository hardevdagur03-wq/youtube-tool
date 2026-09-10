from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from prompt_management.prompt_analytics import PromptAnalyticsCollector
from prompt_management.prompt_cache import PromptCache
from prompt_management.prompt_experiments import PromptExperimentManager
from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_models import (
    ExperimentVariant,
    PromptExperiment,
    PromptMetadata,
    PromptStatus,
    PromptVersion,
)
from prompt_management.prompt_registry import PromptRegistry, RegistryEntry
from prompt_management.prompt_renderer import PromptRenderer
from prompt_management.prompt_repository import PromptRepository
from prompt_management.prompt_validator import PromptValidator, ValidationResult
from prompt_management.prompt_version_manager import PromptVersionManager

logger = logging.getLogger("prompt_management")


class PromptManager:
    def __init__(
        self,
        prompts_dir: str | Path | None = None,
        repository: PromptRepository | None = None,
        loader: PromptLoader | None = None,
        renderer: PromptRenderer | None = None,
        validator: PromptValidator | None = None,
        version_manager: PromptVersionManager | None = None,
        registry: PromptRegistry | None = None,
        analytics_collector: PromptAnalyticsCollector | None = None,
        experiment_manager: PromptExperimentManager | None = None,
        cache: PromptCache | None = None,
    ):
        self.repository = repository or PromptRepository(prompts_dir)
        self.loader = loader or PromptLoader(prompts_dir)
        self.cache = cache or PromptCache()
        self.renderer = renderer or PromptRenderer(self.loader, self.cache)
        self.validator = validator or PromptValidator(self.loader)
        self.version_manager = version_manager or PromptVersionManager(self.repository)
        self.registry = registry or PromptRegistry(self.repository)
        self.analytics = analytics_collector or PromptAnalyticsCollector(self.repository)
        self.experiments = experiment_manager or PromptExperimentManager(self.repository)
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._load_all_prompts_into_registry()
        self._initialized = True
        logger.info("PromptManager initialized with %d prompts", len(self.registry.list_all()))

    def get_prompt(self, prompt_name: str) -> tuple[PromptMetadata | None, str | None]:
        return self.loader.load_with_metadata(prompt_name)

    def render(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        experiment_id: str | None = None,
    ) -> str | None:
        if experiment_id:
            variant = self.experiments.select_variant(experiment_id)
            if variant:
                merged_vars = {**variables, **variant.config_overrides}
                result = self.renderer.render(prompt_name, merged_vars)
                if result:
                    self.registry.record_usage(variant.prompt_id)
                return result

        result = self.renderer.render(prompt_name, variables)
        if result:
            meta, _ = self.loader.load_with_metadata(prompt_name)
            if meta:
                self.registry.record_usage(meta.prompt_id)
        return result

    def render_content(self, content: str, variables: dict[str, Any]) -> str:
        return self.renderer.render_content(content, variables)

    def validate(self, prompt_name: str, variables: dict[str, Any] | None = None) -> ValidationResult:
        return self.validator.validate(prompt_name, variables)

    def validate_content(self, content: str, metadata: PromptMetadata | None = None) -> ValidationResult:
        return self.validator.validate_content(content, metadata)

    def create_version(
        self,
        prompt_name: str,
        content: str,
        author: str = "system",
        change_summary: str = "",
        change_type: str = "patch",
    ) -> PromptVersion | None:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return None

        old_content = self.loader.load_content(prompt_name)
        self._write_prompt_file(prompt_name, content, metadata)

        version = self.version_manager.create_version(
            prompt_id=metadata.prompt_id,
            content=content,
            author=author,
            change_summary=change_summary,
            change_type=change_type,
        )

        self.loader.reload(prompt_name)
        self.renderer.invalidate_cache(prompt_name)
        logger.info("Created version %s for prompt '%s': %s", version.version_number, prompt_name, change_summary)
        return version

    def rollback(self, prompt_name: str, target_version: str, author: str = "system") -> PromptVersion | None:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return None

        version = self.version_manager.rollback(metadata.prompt_id, target_version, author)
        if version is None:
            return None

        self._write_prompt_file(prompt_name, version.content, metadata)
        self.loader.reload(prompt_name)
        self.renderer.invalidate_cache(prompt_name)
        logger.info("Rolled back prompt '%s' to version %s", prompt_name, target_version)
        return version

    def promote(self, prompt_name: str, to_status: PromptStatus) -> bool:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return False
        return self.version_manager.promote(metadata.prompt_id, metadata.status, to_status)

    def get_version_history(self, prompt_name: str) -> list[PromptVersion]:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return []
        return self.version_manager.get_version_history(metadata.prompt_id)

    def diff_versions(self, prompt_name: str, v1: str, v2: str) -> str:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return ""
        return self.version_manager.diff_versions(metadata.prompt_id, v1, v2)

    def record_execution(
        self,
        prompt_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        quality_score: float = 0.0,
        model_used: str = "",
    ) -> None:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return
        self.analytics.record_execution(
            prompt_id=metadata.prompt_id,
            version=metadata.version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            quality_score=quality_score,
            model_used=model_used,
        )

    def get_analytics(self, prompt_name: str) -> dict[str, Any]:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return {"error": f"Prompt '{prompt_name}' not found"}
        return self.analytics.get_summary(metadata.prompt_id)

    def get_global_analytics(self) -> dict[str, Any]:
        return self.analytics.get_global_stats()

    def search_prompts(self, query: str) -> list[RegistryEntry]:
        return self.registry.search(query)

    def list_prompts(self) -> list[RegistryEntry]:
        return self.registry.list_all()

    def list_categories(self) -> dict[str, int]:
        return self.registry.get_summary().get("by_category", {})

    def create_experiment(
        self,
        name: str,
        prompt_name: str,
        variants: list[ExperimentVariant],
        description: str = "",
        created_by: str = "system",
        min_executions: int = 100,
    ) -> PromptExperiment | None:
        metadata = self.loader.load_metadata(prompt_name)
        if metadata is None:
            return None
        return self.experiments.create_experiment(
            name=name,
            target_prompt_id=metadata.prompt_id,
            variants=variants,
            description=description,
            created_by=created_by,
            min_executions=min_executions,
        )

    def get_experiment(self, experiment_id: str) -> PromptExperiment | None:
        return self.experiments.get_experiment(experiment_id)

    def evaluate_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        return self.experiments.evaluate_experiment(experiment_id)

    def get_cache_stats(self) -> dict[str, Any]:
        return self.cache.stats()

    def invalidate_cache(self, prompt_name: str | None = None) -> None:
        self.renderer.invalidate_cache(prompt_name)

    def get_prompts_dir(self) -> Path:
        return self.loader.get_prompts_dir()

    def _load_all_prompts_into_registry(self) -> None:
        prompts = self.loader.load_all_prompts()
        for name, (metadata, content) in prompts.items():
            if metadata:
                self.repository.save_metadata(metadata)
                self.registry.register(metadata)
                existing = self.repository.list_versions(metadata.prompt_id)
                if not existing:
                    self.version_manager.create_version(
                        prompt_id=metadata.prompt_id,
                        content=content or "",
                        author=metadata.author,
                        change_summary="Initial version from file",
                        change_type="major",
                    )

    def _write_prompt_file(self, prompt_name: str, content: str, metadata: PromptMetadata) -> None:
        path = self.loader.resolve_path(prompt_name)
        if path is None:
            path = self.loader.get_prompts_dir() / f"{prompt_name}.md"
        import yaml
        front_matter = {
            "prompt_id": metadata.prompt_id,
            "name": metadata.name,
            "version": metadata.version,
            "author": metadata.author,
            "status": metadata.status.value,
            "category": metadata.category.value,
            "tags": metadata.tags,
            "language": metadata.language,
            "target_model": metadata.target_model,
            "temperature": metadata.temperature,
            "max_tokens": metadata.max_tokens,
            "owner": metadata.owner,
            "approval": metadata.approval,
            "risk_level": metadata.risk_level.value,
            "supported_models": metadata.supported_models,
            "dependencies": metadata.dependencies,
            "change_log": metadata.change_log,
        }
        yaml_str = yaml.dump(front_matter, default_flow_style=False, sort_keys=False)
        full_content = f"---\n{yaml_str}---\n\n{content}"
        path.write_text(full_content, encoding="utf-8")

    def get_prompt_metadata(self, prompt_name: str) -> PromptMetadata | None:
        return self.loader.load_metadata(prompt_name)
