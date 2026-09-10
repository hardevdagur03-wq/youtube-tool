from __future__ import annotations

import logging
import re
from typing import Any

from publishing.models import (
    CodeBlockInfo, DocumentModel, FAQItem, HeadingInfo,
    ImageInfo, LinkInfo, ReferenceInfo, SectionInfo, TableInfo,
)

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TABLE_RE = re.compile(r"^\|(.+)\|$", re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
HR_RE = re.compile(r"^---\s*$", re.MULTILINE)
FAQ_HEADING_RE = re.compile(r"^#{1,3}\s+(.*faq|frequently\s+asked\s+questions).*$", re.IGNORECASE)
QUESTION_RE = re.compile(r"^#{2,4}\s+(.+)\s*$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
ITALIC_RE = re.compile(r"\*(.+?)\*|_(.+?)_")


class RenderEngine:
    def __init__(self):
        self._document = DocumentModel()

    def render(self, content: str, metadata: dict[str, Any] | None = None) -> DocumentModel:
        self._document = DocumentModel()
        md = metadata or {}

        self._document.title = md.get("title") or self._extract_title(content)
        self._document.seo_title = md.get("seo_title") or md.get("meta_title") or self._document.title
        self._document.meta_description = md.get("meta_description") or md.get("description") or ""
        self._document.content = content
        self._document.author = md.get("author") or "AI Writing Platform"
        self._document.publish_date = md.get("publish_date") or md.get("created_at") or ""
        self._document.category = md.get("category") or md.get("primary_category") or ""
        self._document.tags = md.get("tags") or md.get("keywords", []) or []
        self._document.primary_keyword = md.get("primary_keyword") or md.get("primary_keyword", "")
        self._document.secondary_keywords = md.get("secondary_keywords") or md.get("secondary_keywords", [])
        self._document.language = md.get("language") or "en"

        self._parse_sections(content)
        self._parse_images(content)
        self._parse_tables(content)
        self._parse_code_blocks(content)
        self._parse_links(content)
        self._parse_headings(content)
        self._parse_faq(content)

        self._document.word_count = len(content.split()) if content else 0
        self._document.reading_time_minutes = max(1, self._document.word_count // 200)

        return self._document

    def _extract_title(self, content: str) -> str:
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else "Untitled Document"

    def _parse_sections(self, content: str) -> None:
        lines = content.split("\n")
        sections: list[SectionInfo] = []
        current_section: SectionInfo | None = None
        current_content: list[str] = []
        in_code_block = False

        for line in lines:
            if line.startswith("```"):
                in_code_block = not in_code_block
                current_content.append(line)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match and not in_code_block:
                if current_section and current_content:
                    current_section.content = "\n".join(current_content).strip()
                current_section = SectionInfo(
                    heading=heading_match.group(2).strip(),
                    heading_tag=f"h{len(heading_match.group(1))}",
                    order=len(sections),
                )
                sections.append(current_section)
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section and current_content:
            current_section.content = "\n".join(current_content).strip()

        self._document.sections = sections

        metadata_block = ""
        if sections:
            first_content = sections[0].content
            meta_match = re.search(r"^> \*\*SEO Title:\*\* (.+)$", first_content, re.MULTILINE)
            if meta_match and not self._document.seo_title:
                self._document.seo_title = meta_match.group(1).strip()

        has_intro = False
        has_conclusion = False
        has_cta = False
        for s in sections:
            heading_lower = s.heading.lower()
            if any(w in heading_lower for w in ["introduction", "overview", "getting started"]):
                self._document.introduction = s.content
                has_intro = True
            elif any(w in heading_lower for w in ["conclusion", "summary", "wrapping up", "final thoughts"]):
                self._document.conclusion = s.content
                has_conclusion = True
            elif any(w in heading_lower for w in ["call to action", "next steps", "get started", "try it"]):
                self._document.call_to_action = s.content
                has_cta = True

        if not has_intro and sections:
            self._document.introduction = sections[0].content

    def _parse_images(self, content: str) -> None:
        for match in IMAGE_RE.finditer(content):
            alt = match.group(1).strip()
            url = match.group(2).strip()
            filename = url.split("/")[-1].split("?")[0] if url else ""
            self._document.images.append(ImageInfo(url=url, alt=alt, filename=filename))

    def _parse_tables(self, content: str) -> None:
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            if lines[i].startswith("|") and lines[i].endswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                if len(table_lines) >= 2:
                    self._parse_table(table_lines)
            else:
                i += 1

    def _parse_table(self, lines: list[str]) -> None:
        header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
        if len(lines) >= 2 and re.match(r"^[\s|:-]+$", lines[1]):
            alignments = []
            for cell in lines[1].strip("|").split("|"):
                cell = cell.strip()
                if cell.startswith(":") and cell.endswith(":"):
                    alignments.append("center")
                elif cell.startswith(":"):
                    alignments.append("left")
                elif cell.endswith(":"):
                    alignments.append("right")
                else:
                    alignments.append("left")
            data_rows = []
            for row_line in lines[2:]:
                if row_line.startswith("|"):
                    cells = [c.strip() for c in row_line.strip("|").split("|")]
                    data_rows.append(cells)
            self._document.tables.append(TableInfo(
                headers=header_cells,
                rows=data_rows,
                alignment=alignments,
            ))

    def _parse_code_blocks(self, content: str) -> None:
        for match in CODE_BLOCK_RE.finditer(content):
            lang = match.group(1).strip()
            code = match.group(2).strip()
            self._document.code_blocks.append(CodeBlockInfo(language=lang, code=code))

    def _parse_links(self, content: str) -> None:
        for match in LINK_RE.finditer(content):
            text = match.group(1).strip()
            url = match.group(2).strip()
            is_internal = url.startswith("/") or not url.startswith("http")
            self._document.links.append(LinkInfo(text=text, url=url, is_internal=is_internal))

    def _parse_headings(self, content: str) -> None:
        for match in HEADING_RE.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()
            self._document.headings.append(HeadingInfo(text=text, tag=f"h{level}", level=level))

    def _parse_faq(self, content: str) -> None:
        lines = content.split("\n")
        in_faq = False
        current_q = ""
        current_a: list[str] = []
        in_code_block = False

        for line in lines:
            if line.startswith("```"):
                in_code_block = not in_code_block
                if in_faq:
                    current_a.append(line)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match and not in_code_block:
                heading_text = heading_match.group(2).lower()
                if any(w in heading_text for w in ["faq", "frequently asked", "questions", "q&a"]):
                    in_faq = True
                    continue
                elif in_faq:
                    in_faq = False
                    if current_q and current_a:
                        self._document.faq.append(FAQItem(
                            question=current_q,
                            answer="\n".join(current_a).strip(),
                        ))
                    current_q = ""
                    current_a = []

            if in_faq:
                q_match = re.match(r"^(?:#{2,4}|[*]*)\s*(.+)\s*$", line)
                if q_match and line.strip().startswith(("#", "*", "-")):
                    if current_q and current_a:
                        self._document.faq.append(FAQItem(
                            question=current_q,
                            answer="\n".join(current_a).strip(),
                        ))
                    current_q = q_match.group(1).strip().lstrip("?").strip()
                    current_a = []
                elif current_q:
                    current_a.append(line)

        if current_q and current_a:
            self._document.faq.append(FAQItem(
                question=current_q,
                answer="\n".join(current_a).strip(),
            ))

    def extract_metadata_section(self, content: str) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        lines = content.split("\n")
        in_meta = False

        for line in lines[:20]:
            if line.startswith("> **") and ":**" in line:
                in_meta = True
                parts = line.strip("> ").strip()
                kv_match = re.match(r"\*\*(.+?):\*\*\s*(.+)", parts)
                if kv_match:
                    key = kv_match.group(1).lower().replace(" ", "_")
                    value = kv_match.group(2).strip()
                    meta[key] = value
            elif in_meta and line.strip() == "---":
                break

        return meta

    def get_toc(self, content: str) -> list[str]:
        toc: list[str] = []
        for match in HEADING_RE.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()
            indent = "  " * (level - 1)
            toc.append(f"{indent}- [{text}](#{self._slugify(text)})")
        return toc

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text
