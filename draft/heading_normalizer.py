"""Heading Normalizer — ensures consistent heading hierarchy across the document.

Rules:
- Exactly one H1 (document title)
- Introduction uses H2
- Body sections use H2
- Subsections within body use H3
- FAQ uses H2, individual questions use H3
- Conclusion uses H2
- CTA uses H2
- No duplicate headings
- Consistent spacing before/after headings
"""

from __future__ import annotations

import logging
import re
from typing import Any

from draft.draft_models import DiscoveredSection, SectionType

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class HeadingNormalizer:
    """Normalizes heading hierarchy across assembled sections."""

    SECTION_HEADING_MAP: dict[SectionType, str] = {
        SectionType.INTRODUCTION: "h2",
        SectionType.BODY: "h2",
        SectionType.FAQ: "h2",
        SectionType.CONCLUSION: "h2",
        SectionType.CTA: "h2",
        SectionType.SUMMARY: "h2",
    }

    SUBSECTION_HEADING_MAP: dict[SectionType, str] = {
        SectionType.FAQ: "h3",
    }

    def normalize(self, sections: list[DiscoveredSection]) -> list[DiscoveredSection]:
        normalized = []
        seen_headings: set[str] = set()

        for section in sections:
            normalized_section = self._normalize_section_headings(section, seen_headings)
            normalized.append(normalized_section)

        return normalized

    def _normalize_section_headings(
        self,
        section: DiscoveredSection,
        seen_headings: set[str],
    ) -> DiscoveredSection:
        content = section.content
        lines = content.split("\n")
        new_lines: list[str] = []
        heading_count = 0

        for line in lines:
            m = MARKDOWN_HEADING_RE.match(line)
            if m:
                heading_count += 1
                current_tag = len(m.group(1))
                heading_text = m.group(2).strip()

                if heading_count == 1:
                    new_tag = self._get_primary_tag(section.section_type)
                else:
                    new_tag = self._get_sub_tag(current_tag, section.section_type)

                new_heading = f"{'#' * new_tag} {heading_text}"

                if heading_text.lower() in seen_headings and heading_count == 1:
                    logger.debug(
                        "Duplicate heading '%s' in section %s",
                        heading_text, section.filename,
                    )
                seen_headings.add(heading_text.lower())

                new_lines.append(new_heading)
            else:
                new_lines.append(line)

        section.content = "\n".join(new_lines)
        if section.heading:
            first_heading = self._find_first_heading(section.content)
            if first_heading:
                section.heading_tag = f"h{first_heading}"
        return section

    def _get_primary_tag(self, section_type: SectionType) -> int:
        tag = self.SECTION_HEADING_MAP.get(section_type, "h2")
        return int(tag[1])

    def _get_sub_tag(self, current_level: int, section_type: SectionType) -> int:
        if section_type in self.SUBSECTION_HEADING_MAP:
            target = self.SUBSECTION_HEADING_MAP[section_type]
            return int(target[1])
        return min(current_level + 1, 6)

    def _find_first_heading(self, content: str) -> int | None:
        for line in content.split("\n"):
            m = MARKDOWN_HEADING_RE.match(line)
            if m:
                return len(m.group(1))
        return None

    def ensure_title_h1(self, content: str, title: str) -> str:
        first_line = content.split("\n")[0] if content else ""
        m = MARKDOWN_HEADING_RE.match(first_line) if first_line else None
        if m:
            content = re.sub(r"^#\s+.+$", f"# {title}", content, count=1, flags=re.MULTILINE)
        else:
            content = f"# {title}\n\n{content}"
        return content

    def normalize_heading_spacing(self, content: str) -> str:
        content = re.sub(r"^(#{1,6}\s+.+)\n{3,}", r"\1\n\n", content, flags=re.MULTILINE)
        content = re.sub(r"\n{3,}(#{1,6}\s+.+)", r"\n\n\1", content, flags=re.MULTILINE)
        return content

    def get_anchor_id(self, heading_text: str) -> str:
        anchor = heading_text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s_]+", "-", anchor)
        anchor = re.sub(r"-+", "-", anchor)
        return anchor.strip("-")

    def get_section_type_for_heading(self, heading: str) -> SectionType:
        hl = heading.lower()
        if "introduction" in hl or "intro" in hl:
            return SectionType.INTRODUCTION
        if "faq" in hl or "frequently asked" in hl or "question" in hl:
            return SectionType.FAQ
        if "conclusion" in hl or "summary" in hl or "wrapping up" in hl:
            return SectionType.CONCLUSION
        if "next step" in hl or "get started" in hl or "call to action" in hl or "subscribe" in hl:
            return SectionType.CTA
        return SectionType.BODY
