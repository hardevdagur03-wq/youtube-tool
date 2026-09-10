from __future__ import annotations

import logging
import re
from typing import Callable

from editor.editor_models import HeadingInfo, TableOfContentsEntry

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class HeadingNavigator:
    def __init__(self):
        self._headings: list[HeadingInfo] = []
        self._toc: list[TableOfContentsEntry] = []
        self._change_listeners: list[Callable] = []

    def parse(self, content: str) -> list[HeadingInfo]:
        self._headings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            match = HEADING_RE.match(line)
            if match:
                tag = match.group(1)
                text = match.group(2).strip()
                level = len(tag)
                anchor_id = self._generate_anchor_id(text)
                self._headings.append(HeadingInfo(
                    text=text,
                    tag=f"h{level}",
                    level=level,
                    line=line_num,
                    anchor_id=anchor_id,
                ))

        self._build_tree()
        return self._headings

    def get_headings(self) -> list[HeadingInfo]:
        return self._headings

    def get_toc(self) -> list[TableOfContentsEntry]:
        return self._toc

    def get_nested_toc(self) -> list[TableOfContentsEntry]:
        return self._toc

    def get_headings_by_level(self, level: int) -> list[HeadingInfo]:
        return [h for h in self._headings if h.level == level]

    def get_heading_count(self) -> int:
        return len(self._headings)

    def get_heading_at_line(self, line: int) -> HeadingInfo | None:
        for heading in self._headings:
            if heading.line == line:
                return heading
        return None

    def get_section_content(self, content: str, heading_line: int) -> str:
        lines = content.split("\n")
        if heading_line < 1 or heading_line > len(lines):
            return ""

        start_line = heading_line - 1
        heading_level = len(re.match(r"^(#+)", lines[start_line]).group(1)) if re.match(r"^(#+)", lines[start_line]) else 2

        end_line = len(lines)
        for i in range(start_line + 1, len(lines)):
            match = HEADING_RE.match(lines[i])
            if match and len(match.group(1)) <= heading_level:
                end_line = i
                break

        return "\n".join(lines[start_line:end_line])

    def navigate_to_heading(self, content: str, heading_text: str) -> int | None:
        for heading in self._headings:
            if heading.text.lower() == heading_text.lower():
                return heading.line
        return None

    def get_heading_hierarchy(self) -> list[dict]:
        hierarchy: list[dict] = []
        stack: list[dict] = []

        for heading in self._headings:
            node = {
                "heading": heading,
                "children": [],
            }
            while stack and stack[-1]["heading"].level >= heading.level:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                hierarchy.append(node)
            stack.append(node)

        return hierarchy

    def collapse_headings(self, content: str, level: int) -> str:
        lines = content.split("\n")
        result: list[str] = []
        skip = False
        skip_level = 0

        for line in lines:
            match = HEADING_RE.match(line)
            if match:
                heading_level = len(match.group(1))
                if heading_level <= level:
                    skip = False
                elif heading_level > level:
                    if not skip:
                        skip = True
                        skip_level = heading_level
            if not skip:
                result.append(line)

        return "\n".join(result)

    def _build_tree(self) -> None:
        self._toc = []
        stack: list[TableOfContentsEntry] = []

        for heading in self._headings:
            entry = TableOfContentsEntry(
                title=heading.text,
                anchor_id=heading.anchor_id,
                level=heading.level,
                line=heading.line,
            )

            while stack and stack[-1].level >= heading.level:
                stack.pop()

            if stack:
                stack[-1].children.append(entry)
            else:
                self._toc.append(entry)

            stack.append(entry)

    def _generate_anchor_id(self, text: str) -> str:
        anchor = text.lower().strip()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s_]+", "-", anchor)
        anchor = re.sub(r"-+", "-", anchor)
        return anchor

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"HeadingNavigator listener error: {e}")
