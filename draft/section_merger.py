"""Section Merger — merges independently generated sections in correct order.

Discovers section files from disk in the correct pipeline order:
  intro.md → section_*.md → faq.md → conclusion.md → cta.md

Supports dynamic section counts and automatic filename discovery.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from draft.draft_models import (
    DiscoveredSection,
    SectionType,
    SectionValidationResult,
    utc_now,
)

logger = logging.getLogger(__name__)

SECTION_FILENAME_ORDER: list[tuple[str, SectionType]] = [
    ("intro.md", SectionType.INTRODUCTION),
    ("section_*.md", SectionType.BODY),
    ("faq.md", SectionType.FAQ),
    ("conclusion.md", SectionType.CONCLUSION),
    ("cta.md", SectionType.CTA),
]

STANDARD_FILENAMES = {"intro.md", "faq.md", "conclusion.md", "cta.md", "summary.md"}


class SectionMerger:
    """Discovers and merges sections from disk in correct pipeline order."""

    def __init__(self) -> None:
        self._discovered: list[DiscoveredSection] = []

    @property
    def discovered(self) -> list[DiscoveredSection]:
        return list(self._discovered)

    def discover_sections(self, sections_path: Path) -> list[DiscoveredSection]:
        if not sections_path.exists():
            logger.warning("Sections path does not exist: %s", sections_path)
            return []

        files = self._collect_files(sections_path)
        discovered: list[DiscoveredSection] = []
        seen_ids: set[str] = set()
        order_counter = 1

        for filename, section_type in SECTION_FILENAME_ORDER:
            if filename == "section_*.md":
                body_files = sorted(
                    [f for f in files if f.name not in STANDARD_FILENAMES],
                    key=lambda p: p.name,
                )
                for body_file in body_files:
                    section = self._build_section(body_file, section_type, order_counter)
                    if section and section.section_id not in seen_ids:
                        seen_ids.add(section.section_id)
                        discovered.append(section)
                        order_counter += 1
            else:
                filepath = sections_path / filename
                if filepath.exists():
                    section = self._build_section(filepath, section_type, order_counter)
                    if section and section.section_id not in seen_ids:
                        seen_ids.add(section.section_id)
                        discovered.append(section)
                        order_counter += 1

        self._discovered = discovered
        return discovered

    def discover_from_manifest(
        self,
        sections_path: Path,
        manifest: dict[str, Any] | None = None,
    ) -> list[DiscoveredSection]:
        return self.discover_sections(sections_path)

    def discover_from_list(
        self,
        sections_data: list[dict[str, Any]],
    ) -> list[DiscoveredSection]:
        discovered: list[DiscoveredSection] = []
        order_map: dict[str, int] = {}

        for item in sections_data:
            section_type_str = item.get("type", "body")
            content = item.get("content", "")
            heading = item.get("heading", "")
            section_id = item.get("section_id", "")
            order = item.get("order", 0)

            try:
                section_type = SectionType(section_type_str)
            except ValueError:
                section_type = SectionType.BODY

            if not section_id:
                section_id = f"section_{order:02d}" if order > 0 else "body"

            discovered.append(DiscoveredSection(
                section_id=section_id,
                filename=f"{section_id}.md",
                section_type=section_type,
                heading=heading,
                content=content,
                order=order,
                word_count=len(content.split()),
            ))
            order_map[section_id] = order

        discovered.sort(key=lambda s: (s.order, s.section_id))
        return discovered

    def sort_by_order(self, sections: list[DiscoveredSection]) -> list[DiscoveredSection]:
        type_order: dict[SectionType, int] = {
            SectionType.INTRODUCTION: 0,
            SectionType.BODY: 1,
            SectionType.FAQ: 2,
            SectionType.CONCLUSION: 3,
            SectionType.CTA: 4,
            SectionType.SUMMARY: 5,
        }

        def sort_key(s: DiscoveredSection) -> tuple:
            return (type_order.get(s.section_type, 10), s.order, s.section_id)

        return sorted(sections, key=sort_key)

    def detect_changes(
        self,
        old_sections: list[DiscoveredSection],
        new_sections: list[DiscoveredSection],
    ) -> dict[str, list[str]]:
        changes: dict[str, list[str]] = {
            "added": [],
            "removed": [],
            "modified": [],
            "unchanged": [],
        }

        old_map = {s.section_id: s for s in old_sections}
        new_map = {s.section_id: s for s in new_sections}

        for sid in new_map:
            if sid not in old_map:
                changes["added"].append(sid)

        for sid in old_map:
            if sid not in new_map:
                changes["removed"].append(sid)

        for sid in new_map:
            if sid in old_map:
                old_section = old_map[sid]
                new_section = new_map[sid]
                if (old_section.content.strip() != new_section.content.strip()
                        or old_section.heading != new_section.heading):
                    changes["modified"].append(sid)
                else:
                    changes["unchanged"].append(sid)

        return changes

    def _collect_files(self, sections_path: Path) -> list[Path]:
        return sorted(
            [f for f in sections_path.iterdir() if f.suffix == ".md" and f.is_file()],
            key=lambda p: p.name,
        )

    def _build_section(
        self,
        filepath: Path,
        section_type: SectionType,
        order: int,
    ) -> DiscoveredSection | None:
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read section file %s: %s", filepath.name, exc)
            return None

        if not content.strip():
            logger.warning("Empty section file: %s", filepath.name)
            return None

        heading, heading_tag = self._extract_heading(content)
        section_id = filepath.stem

        return DiscoveredSection(
            section_id=section_id,
            filename=filepath.name,
            section_type=section_type,
            heading=heading,
            heading_tag=heading_tag,
            content=content.strip(),
            order=order,
            word_count=len(content.split()),
        )

    def _extract_heading(self, content: str) -> tuple[str, str]:
        m = re.match(r"^(#{1,6})\s+(.+)$", content.strip(), re.MULTILINE)
        if m:
            tag = len(m.group(1))
            text = m.group(2).strip()
            return text, f"h{tag}"
        return "", "h2"

    def get_expected_filenames(self, section_count: int) -> list[str]:
        names = ["intro.md"]
        for i in range(1, section_count + 1):
            names.append(f"section_{i:02d}.md")
        names.extend(["faq.md", "conclusion.md", "cta.md"])
        return names

    def check_completeness(
        self,
        found_sections: list[DiscoveredSection],
    ) -> tuple[bool, list[str]]:
        found_types = {s.section_type for s in found_sections}
        missing: list[str] = []

        required = {SectionType.INTRODUCTION, SectionType.BODY,
                    SectionType.CONCLUSION, SectionType.CTA}

        for rt in required:
            if rt not in found_types:
                missing.append(rt.value)

        return len(missing) == 0, missing
