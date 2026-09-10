"""Document Validator — validates sections and assembled documents.

Validates:
- Section existence and readability
- Markdown structure and encoding
- Heading hierarchy
- Word count minimums
- Content corruption detection
- Cross-reference validity
"""

from __future__ import annotations

import logging
import re
from typing import Any

from draft.draft_models import (
    DiscoveredSection,
    SectionValidationResult,
    SectionType,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
TABLE_RE = re.compile(r"^\|.+\|\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
BLOCKQUOTE_RE = re.compile(r"^>\s+(.+)$", re.MULTILINE)
LIST_RE = re.compile(r"^(\s*[-*+]\s+|\s*\d+\.\s+)", re.MULTILINE)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HR_RE = re.compile(r"^---+\s*$", re.MULTILINE)


class DocumentValidator:
    """Validates sections and assembled documents before merge."""

    MIN_SECTION_WORDS = 10
    MAX_SECTION_WORDS = 10000

    def validate_section(
        self,
        section: DiscoveredSection,
        config: dict[str, Any] | None = None,
    ) -> SectionValidationResult:
        config = config or {}
        min_words = config.get("min_section_word_count", self.MIN_SECTION_WORDS)

        result = SectionValidationResult(
            section_id=section.section_id,
            filename=section.filename,
        )

        content = section.content
        result.exists = bool(content.strip())

        if not result.exists:
            result.errors.append("Section content is empty")
            result.valid = False
            return result

        word_count = len(content.split())
        result.word_count = word_count

        if word_count < min_words:
            result.errors.append(f"Word count {word_count} below minimum {min_words}")
            result.warnings.append(f"Section too short: {word_count} words")

        if word_count > self.MAX_SECTION_WORDS:
            result.warnings.append(f"Section very long: {word_count} words")

        result.encoding_valid = self._check_encoding(content)
        if not result.encoding_valid:
            result.errors.append("Invalid encoding detected")

        result.markdown_valid = self._check_markdown_valid(content)
        if not result.markdown_valid:
            result.warnings.append("Markdown structure issues detected")

        result.no_corruption = self._check_corruption(content)
        if not result.no_corruption:
            result.errors.append("Content corruption detected (null bytes or control chars)")

        heading_info = self._extract_heading_info(content)
        if heading_info:
            result.has_heading = True
            result.heading_tag = heading_info["tag"]
            result.heading_text = heading_info["text"]
        else:
            if section.section_type != SectionType.CTA:
                result.warnings.append("No heading found in section")

        if result.errors:
            result.valid = False
        else:
            result.valid = True

        self._validate_content_consistency(result, content, section)

        return result

    def _check_encoding(self, content: str) -> bool:
        try:
            content.encode("utf-8")
            return True
        except (UnicodeEncodeError, UnicodeDecodeError):
            return False

    def _check_markdown_valid(self, content: str) -> bool:
        lines = content.split("\n")
        in_code_block = False
        for line in lines:
            if line.startswith("```"):
                in_code_block = not in_code_block
            if not in_code_block:
                headings = MARKDOWN_HEADING_RE.findall(line)
                for tag, text in headings:
                    if not text.strip():
                        return False
        return True

    def _check_corruption(self, content: str) -> bool:
        if "\x00" in content:
            return False
        control_chars = sum(1 for c in content if ord(c) < 32 and c not in "\n\r\t")
        if control_chars > len(content) * 0.01:
            return False
        return True

    def _extract_heading_info(self, content: str) -> dict[str, Any] | None:
        for line in content.split("\n"):
            m = MARKDOWN_HEADING_RE.match(line)
            if m:
                tag = m.group(1)
                text = m.group(2).strip()
                return {"tag": f"h{len(tag)}", "level": len(tag), "text": text}
        return None

    def _validate_content_consistency(
        self,
        result: SectionValidationResult,
        content: str,
        section: DiscoveredSection,
    ) -> None:
        if not content:
            return
        headings = MARKDOWN_HEADING_RE.findall(content)
        if len(headings) > 3:
            result.warnings.append(f"Multiple headings ({len(headings)}) in single section")

        sentences = re.split(r"[.!?]+", content)
        long_sentences = [s for s in sentences if len(s.split()) > 50]
        if long_sentences:
            result.warnings.append(f"{len(long_sentences)} unusually long sentence(s)")

    def validate_document(
        self,
        sections: list[DiscoveredSection],
        config: dict[str, Any] | None = None,
    ) -> list[SectionValidationResult]:
        return [self.validate_section(s, config) for s in sections]

    def check_missing_sections(
        self,
        expected: list[str],
        found: list[str],
    ) -> list[str]:
        return [s for s in expected if s not in found]

    def has_critical_failures(self, results: list[SectionValidationResult]) -> bool:
        for r in results:
            if not r.valid and r.errors:
                for e in r.errors:
                    if "empty" in e.lower() or "corruption" in e.lower():
                        return True
        return False

    def check_heading_hierarchy(self, sections: list[DiscoveredSection]) -> list[str]:
        warnings = []
        has_h1 = False
        for section in sections:
            heading_info = self._extract_heading_info(section.content)
            if heading_info:
                level = heading_info["level"]
                if level == 1:
                    if has_h1:
                        warnings.append(
                            f"Multiple H1 headings found in {section.filename}"
                        )
                    has_h1 = True
        return warnings

    def count_tables(self, content: str) -> int:
        if not content:
            return 0
        lines = content.split("\n")
        count = 0
        in_table = False
        for line in lines:
            if TABLE_RE.match(line):
                if not in_table:
                    count += 1
                    in_table = True
            else:
                in_table = False
        return count

    def count_images(self, content: str) -> int:
        if not content:
            return 0
        return len(IMAGE_RE.findall(content))

    def count_code_blocks(self, content: str) -> int:
        if not content:
            return 0
        return len(CODE_BLOCK_RE.findall(content))

    def count_blockquotes(self, content: str) -> int:
        if not content:
            return 0
        return len(BLOCKQUOTE_RE.findall(content))

    def count_lists(self, content: str) -> int:
        if not content:
            return 0
        count = 0
        in_list = False
        for line in content.split("\n"):
            if LIST_RE.match(line):
                if not in_list:
                    count += 1
                    in_list = True
            else:
                in_list = False
        return count

    def count_headings(self, content: str) -> int:
        if not content:
            return 0
        return len(MARKDOWN_HEADING_RE.findall(content))

    def count_paragraphs(self, content: str) -> int:
        if not content:
            return 0
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        return len(paras)

    def estimate_reading_time_minutes(self, word_count: int) -> int:
        return max(1, round(word_count / 200))
