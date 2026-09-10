"""Section Storage — stores each section independently on disk.

Project/
  sections/
    intro.md
    section_01.md
    section_02.md
    ...
    faq.md
    conclusion.md
    cta.md
    metadata.json
    validation.json
    versions/
    logs/

Each file is independently reusable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from section_generation.section_models import (
    SectionOutput,
    SectionMetadata,
    SectionManifest,
    SectionValidation,
    SectionType,
    SectionStatus,
    SectionVersion,
    utc_now,
)

logger = logging.getLogger(__name__)


class SectionStorage:
    """File system storage for generated sections."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        self._base = Path(base_path) if base_path else Path.cwd()

    @property
    def base_path(self) -> Path:
        return self._base

    def get_project_sections_path(self, project_id: str) -> Path:
        return self._base / "projects" / project_id / "sections"

    def ensure_dirs(self, project_id: str) -> Path:
        base = self.get_project_sections_path(project_id)
        base.mkdir(parents=True, exist_ok=True)
        (base / "versions").mkdir(exist_ok=True)
        (base / "logs").mkdir(exist_ok=True)
        logger.debug("Ensured section directories for project %s at %s", project_id, base)
        return base

    def get_filename_for_type(self, section_type: SectionType, order: int = 0) -> str:
        mapping = {
            SectionType.INTRODUCTION: "intro.md",
            SectionType.PROBLEM: f"section_{order:02d}.md",
            SectionType.EXPLANATION: f"section_{order:02d}.md",
            SectionType.STEP_BY_STEP: f"section_{order:02d}.md",
            SectionType.COMPARISON: f"section_{order:02d}.md",
            SectionType.DEFINITION: f"section_{order:02d}.md",
            SectionType.BENEFITS: f"section_{order:02d}.md",
            SectionType.DRAWBACKS: f"section_{order:02d}.md",
            SectionType.USE_CASES: f"section_{order:02d}.md",
            SectionType.EXAMPLES: f"section_{order:02d}.md",
            SectionType.CASE_STUDIES: f"section_{order:02d}.md",
            SectionType.TABLE: f"section_{order:02d}.md",
            SectionType.LIST: f"section_{order:02d}.md",
            SectionType.CODE: f"section_{order:02d}.md",
            SectionType.QUOTE: f"section_{order:02d}.md",
            SectionType.FAQ: "faq.md",
            SectionType.CONCLUSION: "conclusion.md",
            SectionType.CTA: "cta.md",
            SectionType.SUMMARY: "summary.md",
            SectionType.BODY: f"section_{order:02d}.md",
        }
        return mapping.get(section_type, f"section_{order:02d}.md")

    def save_section(
        self,
        project_id: str,
        output: SectionOutput,
    ) -> Path:
        base = self.ensure_dirs(project_id)
        filename = self.get_filename_for_type(output.section_type, output.order)
        filepath = base / filename

        content = self._format_section_output(output)
        filepath.write_text(content, encoding="utf-8")
        logger.info(
            "Saved section %s (%s) to %s (%d words)",
            output.section_id, output.section_type.value,
            filepath, output.word_count,
        )
        return filepath

    def _format_section_output(self, output: SectionOutput) -> str:
        parts = []
        if output.heading:
            heading_tag = "##" if output.order > 0 else "#"
            parts.append(f"{heading_tag} {output.heading}\n")
        parts.append(output.content)
        if output.content and not output.content.endswith("\n"):
            parts.append("\n")
        return "".join(parts)

    def load_section(
        self,
        project_id: str,
        section_type: SectionType,
        order: int = 0,
    ) -> str | None:
        base = self.get_project_sections_path(project_id)
        filename = self.get_filename_for_type(section_type, order)
        filepath = base / filename
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")

    def section_exists(
        self,
        project_id: str,
        section_type: SectionType,
        order: int = 0,
    ) -> bool:
        base = self.get_project_sections_path(project_id)
        filename = self.get_filename_for_type(section_type, order)
        return (base / filename).exists()

    def save_manifest(
        self,
        project_id: str,
        manifest: SectionManifest,
    ) -> Path:
        base = self.ensure_dirs(project_id)
        filepath = base / "metadata.json"
        filepath.write_text(
            json.dumps(manifest.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
        return filepath

    def load_manifest(self, project_id: str) -> SectionManifest | None:
        base = self.get_project_sections_path(project_id)
        filepath = base / "metadata.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return SectionManifest(**data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to load manifest for %s: %s", project_id, exc)
            return None

    def save_validation(
        self,
        project_id: str,
        section_id: str,
        validation: SectionValidation,
    ) -> Path:
        base = self.ensure_dirs(project_id)
        filepath = base / "validation.json"
        existing = {}
        if filepath.exists():
            try:
                existing = json.loads(filepath.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        existing[section_id] = validation.model_dump()
        filepath.write_text(
            json.dumps(existing, indent=2, default=str),
            encoding="utf-8",
        )
        return filepath

    def save_version(
        self,
        project_id: str,
        section_id: str,
        version: SectionVersion,
    ) -> Path:
        base = self.ensure_dirs(project_id)
        version_dir = base / "versions"
        filepath = version_dir / f"{section_id}_v{version.version_number}.json"
        filepath.write_text(
            json.dumps(version.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
        return filepath

    def log_event(
        self,
        project_id: str,
        section_id: str,
        event: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        base = self.ensure_dirs(project_id)
        log_dir = base / "logs"
        log_file = log_dir / f"{section_id}.log"
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = json.dumps({
            "timestamp": timestamp,
            "event": event,
            "section_id": section_id,
            "details": details or {},
        }, default=str)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def list_generated_sections(self, project_id: str) -> list[Path]:
        base = self.get_project_sections_path(project_id)
        if not base.exists():
            return []
        return sorted(
            [f for f in base.iterdir() if f.suffix == ".md" and f.is_file()],
            key=lambda p: p.name,
        )

    def get_section_word_count(self, project_id: str, filename: str) -> int:
        base = self.get_project_sections_path(project_id)
        filepath = base / filename
        if not filepath.exists():
            return 0
        return len(filepath.read_text(encoding="utf-8").split())
