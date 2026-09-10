from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from prompt_management.prompt_models import PromptCategory, PromptMetadata, PromptStatus, RiskLevel


class PromptLoader:
    FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, prompts_dir: str | Path | None = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else Path.cwd() / "prompts"
        self._content_cache: dict[str, str] = {}
        self._metadata_cache: dict[str, PromptMetadata] = {}

    def resolve_path(self, name: str) -> Path | None:
        name = name.replace(".md", "")
        candidates = [
            self.prompts_dir / f"{name}.md",
            self.prompts_dir / "shared" / f"{name}.md",
            self.prompts_dir / "partials" / f"{name}.md",
            self.prompts_dir / "templates" / f"{name}.md",
            self.prompts_dir / "system" / f"{name}.md",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def load_raw(self, name: str) -> str | None:
        path = self.resolve_path(name)
        if path is None:
            return None
        if name in self._content_cache:
            return self._content_cache[name]
        content = path.read_text(encoding="utf-8")
        self._content_cache[name] = content
        return content

    def load_content(self, name: str) -> str | None:
        raw = self.load_raw(name)
        if raw is None:
            return None
        return self._strip_front_matter(raw)

    def load_metadata(self, name: str) -> PromptMetadata | None:
        if name in self._metadata_cache:
            return self._metadata_cache[name]
        raw = self.load_raw(name)
        if raw is None:
            return None
        front_matter = self._parse_front_matter(raw)
        if not front_matter:
            return None
        metadata = self._front_matter_to_metadata(name, front_matter)
        self._metadata_cache[name] = metadata
        return metadata

    def load_with_metadata(self, name: str) -> tuple[PromptMetadata | None, str | None]:
        raw = self.load_raw(name)
        if raw is None:
            return None, None
        content = self._strip_front_matter(raw)
        front_matter = self._parse_front_matter(raw)
        metadata = self._front_matter_to_metadata(name, front_matter) if front_matter else None
        if metadata:
            metadata.content_hash = self._compute_hash(content or "")
        return metadata, content

    def load_all_prompts(self) -> dict[str, tuple[PromptMetadata | None, str | None]]:
        results = {}
        for f in sorted(self.prompts_dir.glob("*.md")):
            name = f.stem
            results[name] = self.load_with_metadata(name)
        return results

    def reload(self, name: str) -> None:
        self._content_cache.pop(name, None)
        self._metadata_cache.pop(name, None)

    def reload_all(self) -> None:
        self._content_cache.clear()
        self._metadata_cache.clear()

    def prompt_exists(self, name: str) -> bool:
        return self.resolve_path(name) is not None

    def list_prompt_names(self) -> list[str]:
        names = []
        for pattern in ["*.md", "shared/*.md", "partials/*.md", "templates/*.md"]:
            for f in sorted(self.prompts_dir.glob(pattern)):
                if f.stem not in names:
                    names.append(f.stem)
        return names

    def _strip_front_matter(self, raw: str) -> str:
        m = self.FRONT_MATTER_PATTERN.match(raw)
        if m:
            return raw[m.end():].strip()
        return raw.strip()

    def _parse_front_matter(self, raw: str) -> dict[str, Any]:
        m = self.FRONT_MATTER_PATTERN.match(raw)
        if not m:
            return {}
        import yaml
        try:
            return yaml.safe_load(m.group(1)) or {}
        except Exception:
            return {}

    def _front_matter_to_metadata(self, name: str, fm: dict[str, Any]) -> PromptMetadata:
        return PromptMetadata(
            prompt_id=fm.get("prompt_id", f"p_{name}"),
            name=fm.get("name", name),
            version=str(fm.get("version", "1.0.0")),
            author=fm.get("author", "unknown"),
            status=PromptStatus(fm["status"]) if "status" in fm and fm["status"] in {e.value for e in PromptStatus} else PromptStatus.draft,
            category=PromptCategory(fm["category"]) if "category" in fm and fm["category"] in {e.value for e in PromptCategory} else PromptCategory.custom,
            tags=fm.get("tags", []),
            language=fm.get("language", "en"),
            target_model=fm.get("target_model", ""),
            temperature=float(fm.get("temperature", 0.3)),
            max_tokens=int(fm.get("max_tokens", 4096)),
            owner=fm.get("owner", ""),
            approval=fm.get("approval", "pending"),
            risk_level=RiskLevel(fm["risk_level"]) if "risk_level" in fm and fm["risk_level"] in {e.value for e in RiskLevel} else RiskLevel.low,
            supported_models=fm.get("supported_models", []),
            dependencies=fm.get("dependencies", []),
            description=fm.get("description", ""),
            source_file=name,
        )

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def get_prompts_dir(self) -> Path:
        return self.prompts_dir
