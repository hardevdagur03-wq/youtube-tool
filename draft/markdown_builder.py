"""Markdown Builder — generates clean, standards-compliant Markdown.

Produces Markdown that renders correctly in:
- GitHub
- Notion
- Obsidian
- VS Code
- Pandoc
- Static Site Generators (Hugo, Jekyll, Next.js, Gatsby)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from draft.draft_models import DiscoveredSection, HeadingInfo, TableOfContentsEntry

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownBuilder:
    """Builds clean, standards-compliant Markdown output."""

    def build_document(
        self,
        title: str,
        sections: list[DiscoveredSection],
        toc_markdown: str = "",
        seo_title: str = "",
        meta_description: str = "",
        add_horizontal_rules: bool = True,
        add_metadata_header: bool = True,
    ) -> str:
        parts: list[str] = []

        parts.append(f"# {title}\n")

        if add_metadata_header:
            meta_lines = []
            if seo_title and seo_title != title:
                meta_lines.append(f"> **SEO Title:** {seo_title}")
            if meta_description:
                meta_lines.append(f"> **Description:** {meta_description}")
            if meta_lines:
                parts.append("\n".join(meta_lines))
                parts.append("")

        if toc_markdown:
            parts.append(toc_markdown)

        for i, section in enumerate(sections):
            if add_horizontal_rules and i > 0:
                parts.append("---\n")

            section_content = self._clean_section_content(section.content)
            if section_content:
                parts.append(section_content)

        document = "\n\n".join(p.strip() for p in parts if p.strip())
        document = self._normalize_whitespace(document)
        return document.strip() + "\n"

    def _clean_section_content(self, content: str) -> str:
        if not content:
            return ""
        content = content.strip()
        content = re.sub(r"\r\n", "\n", content)
        content = re.sub(r"\r", "\n", content)
        content = re.sub(r"\n{4,}", "\n\n\n", content)
        return content

    def _normalize_whitespace(self, content: str) -> str:
        content = re.sub(r"\r\n", "\n", content)
        content = re.sub(r"\r", "\n", content)
        content = re.sub(r"\n{4,}", "\n\n\n", content)
        content = re.sub(r" +\n", "\n", content)
        return content

    def format_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        alignments: list[str] | None = None,
        caption: str = "",
    ) -> str:
        if not headers or not rows:
            return ""

        alignments = alignments or ["left"] * len(headers)
        align_map = {"left": ":---", "center": ":---:", "right": "---:"}

        col_count = len(headers)
        parts: list[str] = []

        if caption:
            parts.append(f"**{caption}**")

        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(
            align_map.get(a, ":---") for a in alignments[:col_count]
        ) + " |"
        parts.append(header_line)
        parts.append(sep_line)

        for row in rows:
            padded = list(row) + [""] * (col_count - len(row))
            parts.append("| " + " | ".join(padded[:col_count]) + " |")

        return "\n".join(parts) + "\n"

    def format_image(
        self,
        alt_text: str,
        url: str,
        title: str = "",
        caption: str = "",
    ) -> str:
        img = f"![{alt_text}]({url})"
        if title:
            img = f"![{alt_text}]({url} \"{title}\")"
        if caption:
            return f"{img}\n*{caption}*\n"
        return img + "\n"

    def format_code_block(
        self,
        code: str,
        language: str = "",
    ) -> str:
        lang = language if language else ""
        return f"```{lang}\n{code}\n```\n"

    def format_blockquote(self, text: str, attribution: str = "") -> str:
        lines = text.strip().split("\n")
        quoted = "\n".join(f"> {l}" for l in lines)
        if attribution:
            quoted += f"\n> — {attribution}"
        return quoted + "\n"

    def format_list(self, items: list[str], ordered: bool = False) -> str:
        if ordered:
            return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items)) + "\n"
        return "\n".join(f"- {item}" for item in items) + "\n"

    def format_link(self, text: str, url: str, title: str = "") -> str:
        if title:
            return f"[{text}]({url} \"{title}\")"
        return f"[{text}]({url})"

    def format_horizontal_rule(self) -> str:
        return "---\n"

    def format_footnote(self, number: int, text: str) -> str:
        return f"[^{number}]: {text}\n"

    def format_footnote_ref(self, number: int) -> str:
        return f"[^{number}]"

    def wrap_in_toc_container(self, toc: str) -> str:
        return f"<!-- TOC -->\n{toc}\n<!-- /TOC -->\n"
