"""Reference Resolver — resolves internal cross-references in assembled draft.

Updates:
- Table references (e.g., "see Table 1" → linked anchor)
- Section references (e.g., "as discussed in Section 2")
- Anchor links (e.g., [link](#section-id))
- Heading IDs for named anchors
- Cross references between sections
"""

from __future__ import annotations

import logging
import re
from typing import Any

from draft.draft_models import DiscoveredSection, HeadingInfo

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
TABLE_REF_RE = re.compile(r"\b(Table|Figure|Section)\s+#?(\d+)\b", re.IGNORECASE)
ANCHOR_LINK_RE = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")
HEADING_ID_RE = re.compile(r"{#([^}]+)}")


class ReferenceResolver:
    """Resolves internal cross-references across the assembled document."""

    def __init__(self) -> None:
        self._heading_map: dict[str, str] = {}
        self._section_index: dict[str, int] = {}

    def build_index(self, sections: list[DiscoveredSection]) -> None:
        self._heading_map.clear()
        self._section_index.clear()

        for i, section in enumerate(sections):
            self._section_index[section.section_id] = i
            headings = self._extract_headings(section.content)
            for heading in headings:
                anchor = self._anchor_id(heading.text)
                self._heading_map[anchor] = heading.text
                self._heading_map[heading.text.lower()] = anchor

    def resolve_section_references(
        self,
        content: str,
        sections: list[DiscoveredSection],
    ) -> str:
        resolved = content

        def replace_ref(m: re.Match) -> str:
            prefix = m.group(1)
            num_str = m.group(2)
            try:
                num = int(num_str)
            except ValueError:
                return m.group(0)

            if prefix.lower() == "section" and 1 <= num <= len(sections):
                section = sections[num - 1]
                heading = self._extract_first_heading(section.content)
                if heading:
                    anchor = self._anchor_id(heading.text)
                    return f"[{prefix} {num}: {heading.text}](#{anchor})"

            return m.group(0)

        resolved = TABLE_REF_RE.sub(replace_ref, resolved)

        return resolved

    def resolve_anchor_links(self, content: str) -> str:
        resolved = content

        def replace_anchor(m: re.Match) -> str:
            text = m.group(1)
            target = m.group(2)
            if target in self._heading_map:
                actual_text = self._heading_map[target]
                if text.lower() != actual_text.lower():
                    return f"[{actual_text}](#{target})"
            return m.group(0)

        resolved = ANCHOR_LINK_RE.sub(replace_anchor, resolved)

        return resolved

    def add_heading_anchors(self, content: str) -> str:
        lines = content.split("\n")
        new_lines: list[str] = []

        for line in lines:
            m = MARKDOWN_HEADING_RE.match(line)
            if m:
                tag = m.group(1)
                text = m.group(2).strip()
                if not HEADING_ID_RE.search(text):
                    anchor = self._anchor_id(text)
                    new_lines.append(f"{tag} {text} {{#{anchor}}}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def update_table_captions(self, content: str) -> str:
        lines = content.split("\n")
        new_lines: list[str] = []
        table_count = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            if re.match(r"^\|.+\|\s*$", line):
                table_count += 1
                if i > 0 and lines[i - 1].strip() == "" and i > 1:
                    prev = lines[i - 2].strip()
                    if not prev.startswith("|") and not prev.startswith("#"):
                        pass
                if i + 2 < len(lines):
                    sep = lines[i + 1]
                    if re.match(r"^\|[\s:-]+\|\s*$", sep):
                        caption_line = f"*Table {table_count}*"
                        new_lines.append(line)
                        new_lines.append(sep)
                        i += 2
                        continue
            new_lines.append(line)
            i += 1

        return "\n".join(new_lines)

    def _extract_headings(self, content: str) -> list[HeadingInfo]:
        headings: list[HeadingInfo] = []
        for m in MARKDOWN_HEADING_RE.finditer(content):
            text = m.group(2).strip()
            headings.append(HeadingInfo(text=text, anchor_id=self._anchor_id(text)))
        return headings

    def _extract_first_heading(self, content: str) -> HeadingInfo | None:
        headings = self._extract_headings(content)
        return headings[0] if headings else None

    def _anchor_id(self, text: str) -> str:
        anchor = text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s_]+", "-", anchor)
        anchor = re.sub(r"-+", "-", anchor)
        return anchor.strip("-")

    def resolve_all(
        self,
        content: str,
        sections: list[DiscoveredSection],
    ) -> str:
        self.build_index(sections)
        content = self.resolve_section_references(content, sections)
        content = self.resolve_anchor_links(content)
        content = self.add_heading_anchors(content)
        content = self.update_table_captions(content)
        return content
