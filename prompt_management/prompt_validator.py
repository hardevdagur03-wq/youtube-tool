from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_models import PromptMetadata


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    missing_variables: list[str] = field(default_factory=list)
    unused_variables: list[str] = field(default_factory=list)
    broken_partial_refs: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    estimated_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "missing_variables": self.missing_variables,
            "unused_variables": self.unused_variables,
            "broken_partial_refs": self.broken_partial_refs,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost": self.estimated_cost,
        }


class PromptValidator:
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
    PARTIAL_PATTERN = re.compile(r"\{\{>(\w+)\}\}")
    CONDITIONAL_PATTERN = re.compile(r"\{\{#(if|each) (\w+)\}\}")
    MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
    MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
    MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s", re.MULTILINE)

    MODEL_TOKEN_LIMITS: dict[str, int] = {
        "gemini-2.0-flash": 1_048_576,
        "gemini-2.5-pro": 1_048_576,
        "gpt-4o": 128_000,
        "gpt-4o-mini": 128_000,
        "claude-3-sonnet": 200_000,
        "claude-3-sonnet-20241022": 200_000,
        "claude-3-haiku": 200_000,
        "deepseek-chat": 128_000,
        "mistral-large": 128_000,
    }

    MODEL_COST_PER_1K_TOKENS: dict[str, float] = {
        "gemini-2.0-flash": 0.0001,
        "gemini-2.5-pro": 0.00125,
        "gpt-4o": 0.0025,
        "gpt-4o-mini": 0.00015,
        "claude-3-sonnet": 0.003,
        "claude-3-haiku": 0.00025,
        "deepseek-chat": 0.0005,
        "mistral-large": 0.002,
    }

    def __init__(self, loader: PromptLoader):
        self._loader = loader

    def validate(self, prompt_name: str, variables: dict[str, Any] | None = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        raw = self._loader.load_raw(prompt_name)
        if raw is None:
            result.is_valid = False
            result.errors.append(f"Prompt not found: {prompt_name}")
            return result

        metadata, content = self._loader.load_with_metadata(prompt_name)
        if content is None:
            content = ""

        front_matter = self._loader.load_raw(prompt_name) or ""

        self._validate_front_matter(front_matter, result, metadata)
        self._validate_variables(content, variables, result)
        self._validate_partials(content, result)
        self._validate_markdown(content, result)
        self._validate_tokens(content, metadata, result)
        self._validate_model_compatibility(metadata, result)
        self._validate_dependencies(metadata, result)

        if result.errors:
            result.is_valid = False
        return result

    def validate_content(self, content: str, metadata: PromptMetadata | None = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        self._validate_markdown(content, result)
        self._validate_tokens(content, metadata, result)
        missing = self.VARIABLE_PATTERN.findall(content)
        if missing:
            result.missing_variables = list(set(missing))
            result.warnings.append(f"Unresolved variables: {', '.join(result.missing_variables)}")
        return result

    def validate_prompt_metadata(self, metadata: PromptMetadata) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not metadata.name:
            result.errors.append("Prompt name is required")
        if not metadata.prompt_id:
            result.errors.append("Prompt ID is required")
        if not re.match(r"^\d+\.\d+\.\d+$", metadata.version):
            result.errors.append(f"Invalid version format: {metadata.version}. Must be semver (X.Y.Z)")
        if not metadata.author:
            result.warnings.append("No author specified")
        if result.errors:
            result.is_valid = False
        return result

    def estimate_tokens(self, text: str) -> int:
        import math
        return math.ceil(len(text) / 4)

    def estimate_cost(self, text: str, model: str = "gemini-2.0-flash") -> float:
        tokens = self.estimate_tokens(text)
        cost_per_1k = self.MODEL_COST_PER_1K_TOKENS.get(model, 0.001)
        return (tokens / 1000) * cost_per_1k

    def _validate_front_matter(self, raw: str, result: ValidationResult, metadata: PromptMetadata | None) -> None:
        import yaml
        m = re.match(r"^---\s*\n(.*?)\n---", raw, re.DOTALL)
        if not m:
            result.errors.append("Missing YAML front matter")
            return
        try:
            fm = yaml.safe_load(m.group(1))
            if not isinstance(fm, dict):
                result.errors.append("Front matter must be a YAML dictionary")
                return
            required = ["prompt_id", "name", "version", "status", "category"]
            for field in required:
                if field not in fm:
                    result.errors.append(f"Missing required front matter field: {field}")
        except Exception as e:
            result.errors.append(f"Invalid YAML front matter: {e}")

    def _validate_variables(self, content: str, variables: dict[str, Any] | None, result: ValidationResult) -> None:
        template_vars = set(self.VARIABLE_PATTERN.findall(content))
        if not template_vars:
            return
        if variables is not None:
            provided = set(variables.keys())
            missing = template_vars - provided
            if missing:
                result.missing_variables = sorted(missing)
                result.warnings.append(f"Missing variables: {', '.join(sorted(missing))}")
            unused = provided - template_vars
            if unused:
                result.unused_variables = sorted(unused)
                result.info.append(f"Unused variables provided: {', '.join(sorted(unused))}")
        else:
            result.missing_variables = sorted(template_vars)

    def _validate_partials(self, content: str, result: ValidationResult) -> None:
        partials = set(self.PARTIAL_PATTERN.findall(content))
        for p in partials:
            if not self._loader.prompt_exists(p):
                result.broken_partial_refs.append(p)
                result.warnings.append(f"Broken partial reference: {p}")

    def _validate_markdown(self, content: str, result: ValidationResult) -> None:
        headings = self.MARKDOWN_HEADING_PATTERN.findall(content)
        if len(headings) > 0:
            h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
            if h1_count > 1:
                result.warnings.append(f"Multiple H1 headings ({h1_count}). Should have exactly one.")

        links = self.MARKDOWN_LINK_PATTERN.findall(content)
        for text, url in links:
            if not text.strip():
                result.warnings.append(f"Link with empty text: {url}")
            if url.startswith("http") and "{{" in url:
                result.warnings.append(f"Link URL contains unresolved variable: {url}")

        images = self.MARKDOWN_IMAGE_PATTERN.findall(content)
        for alt, url in images:
            if not alt.strip():
                result.warnings.append(f"Image without alt text: {url}")

    def _validate_tokens(self, content: str, metadata: PromptMetadata | None, result: ValidationResult) -> None:
        estimated = self.estimate_tokens(content)
        result.estimated_tokens = estimated
        model = metadata.target_model if metadata else "gemini-2.0-flash"
        result.estimated_cost = self.estimate_cost(content, model)
        token_limit = self.MODEL_TOKEN_LIMITS.get(model, 128_000)
        if estimated > token_limit:
            result.errors.append(
                f"Estimated tokens ({estimated:,}) exceed model limit ({token_limit:,}) for {model}"
            )

    def _validate_model_compatibility(self, metadata: PromptMetadata | None, result: ValidationResult) -> None:
        if metadata is None:
            return
        if metadata.target_model and metadata.supported_models:
            if metadata.target_model not in metadata.supported_models:
                result.warnings.append(
                    f"Target model '{metadata.target_model}' not in supported_models: {metadata.supported_models}"
                )

    def _validate_dependencies(self, metadata: PromptMetadata | None, result: ValidationResult) -> None:
        if metadata is None:
            return
        for dep in metadata.dependencies:
            if not self._loader.prompt_exists(dep):
                result.warnings.append(f"Declared dependency not found: {dep}")
