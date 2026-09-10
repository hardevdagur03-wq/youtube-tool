"""Table of Contents Generator — builds navigable TOC from section headings.

Generates anchor-linked table of contents with proper nesting.
Supports clickable navigation in GitHub, Notion, Obsidian, VS Code.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from draft.draft_models import DiscoveredSection, HeadingInfo, TableOfContentsEntry

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class TOCGenerator:
    """Generates structured, anchor-linked table of contents."""

    def generate(
        self,
        sections: list[DiscoveredSection],
        title: str = "",
    ) -> list[TableOfContentsEntry]:
        toc: list[TableOfContentsEntry] = []

        if title:
            toc.append(TableOfContentsEntry(
                title=title,
                anchor_id=self._anchor_id(title),
                level=1,
            ))

        for section in sections:
            headings = self._extract_headings(section.content)
            for heading in headings:
                entry = TableOfContentsEntry(
                    title=heading.text,
                    anchor_id=heading.anchor_id,
                    level=heading.level,
                )
                if heading.level == 2:
                    toc.append(entry)
                elif heading.level >= 3 and toc:
                    toc[-1].children.append(entry)

        return toc

    def generate_markdown(self, toc: list[TableOfContentsEntry]) -> str:
        if not toc:
            return ""

        lines = ["## Table of Contents\n"]
        for entry in toc:
            if entry.level >= 2:
                indent = "  " * (entry.level - 2)
                link = f"- {indent}[{entry.title}](#{entry.anchor_id})"
                lines.append(link + "\n")
                for child in entry.children:
                    child_indent = "  " * (child.level - 1)
                    child_link = f"- {child_indent}[{child.title}](#{child.anchor_id})"
                    lines.append(child_link + "\n")
        lines.append("\n---\n")
        return "".join(lines)

    def generate_html_toc(self, toc: list[TableOfContentsEntry]) -> str:
        if not toc:
            return ""
        parts = ['<nav class="toc" role="navigation" aria-label="Table of Contents">']
        parts.append("<ul>")
        for entry in toc:
            if entry.level >= 2:
                parts.append(
                    f'<li><a href="#{entry.anchor_id}">{entry.title}</a></li>'
                )
                for child in entry.children:
                    parts.append(
                        f'<li style="margin-left:1.5rem">'
                        f'<a href="#{child.anchor_id}">{child.title}</a></li>'
                    )
        parts.append("</ul>")
        parts.append("</nav>")
        return "\n".join(parts)

    def _extract_headings(self, content: str) -> list[HeadingInfo]:
        headings: list[HeadingInfo] = []
        for m in MARKDOWN_HEADING_RE.finditer(content):
            tag = len(m.group(1))
            text = m.group(2).strip()
            headings.append(HeadingInfo(
                text=text,
                tag=f"h{tag}",
                level=tag,
                anchor_id=self._anchor_id(text),
                original_text=text,
            ))
        return headings

    def _anchor_id(self, text: str) -> str:
        anchor = text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s_]+", "-", anchor)
        anchor = re.sub(r"-+", "-", anchor)
        return anchor.strip("-")
