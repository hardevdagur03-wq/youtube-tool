"""Markdown Syntax Validator — validates Markdown structure, tables, images, links, code blocks, heading hierarchy."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest
from review.review_models_ext import MarkdownReport


class MarkdownValidator(BaseValidator):
    """Validates Markdown syntax, table structure, image references, link validity, code blocks."""

    def name(self) -> str:
        return "Markdown Validation"

    def validate(self, request: BlogReviewRequest) -> MarkdownReport:
        text = request.content
        if not text:
            return MarkdownReport(score=100.0)

        issues: list[str] = []
        table_issues: list[str] = []
        image_issues: list[str] = []
        code_block_issues: list[str] = []
        heading_issues: list[str] = []
        list_issues: list[str] = []

        # Table validation
        tables = self._extract_tables(text)
        table_count = len(tables)
        for i, table in enumerate(tables):
            lines = table.strip().split('\n')
            if len(lines) < 2:
                table_issues.append(f"Table {i+1} has fewer than 2 rows")
                continue
            header_parts = [c.strip() for c in lines[0].split('|') if c.strip()]
            separator_line = lines[1]
            sep_parts = separator_line.split('|')
            sep_parts = [p.strip() for p in sep_parts if p.strip()]
            if len(sep_parts) != len(header_parts):
                table_issues.append(f"Table {i+1}: separator row column count ({len(sep_parts)}) doesn't match header ({len(header_parts)})")
            for sep in sep_parts:
                if not re.match(r'^:?-+:?$', sep.strip()):
                    table_issues.append(f"Table {i+1}: invalid alignment marker '{sep.strip()}'")
                    break
            for j, line in enumerate(lines[2:], 3):
                row_parts = [c.strip() for c in line.split('|') if c.strip()]
                if len(row_parts) != len(header_parts):
                    table_issues.append(f"Table {i+1} row {j}: column count mismatch ({len(row_parts)} vs {len(header_parts)})")

        if table_issues:
            issues.extend(table_issues)

        # Image validation
        images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
        image_count = len(images)
        images_missing_alt = sum(1 for alt, _ in images if not alt.strip())
        for alt, src in images:
            if not alt.strip():
                image_issues.append(f"Image '{src}' missing ALT text")
            if not src.strip():
                image_issues.append("Image with empty source URL found")
            elif src.startswith('http') and not re.match(r'^https?://', src):
                image_issues.append(f"Image URL '{src}' should use HTTPS")

        # Link validation
        links = re.findall(r'(?<!\!)\[([^\]]*)\]\(([^)]+)\)', text)
        link_count = len(links)
        broken_links: list[str] = []
        for link_text, url in links:
            if not url.strip():
                broken_links.append(f"Link '{link_text}' has empty URL")
            elif url.startswith('http') and not re.match(r'^https?://', url):
                broken_links.append(f"Link '{link_text}' URL '{url}' should use HTTPS")

        # Code block validation
        fenced_blocks = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
        indented_blocks = re.findall(r'(?:^|\n)( {4}.*(?:\n {4}.*)*)', text)
        code_block_count = len(fenced_blocks) + len(indented_blocks)
        for lang, code in fenced_blocks:
            if not code.strip():
                code_block_issues.append("Empty code block found")

        # Heading validation
        headings = re.findall(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE)
        prev_level = 0
        for i, (level_str, title) in enumerate(headings):
            level = len(level_str)
            if level > prev_level + 1 and prev_level > 0:
                heading_issues.append(f"Heading level skipped from H{prev_level} to H{level} ('{title}')")
            prev_level = level

        h1_count = sum(1 for lvl, _ in headings if len(lvl) == 1)
        if h1_count > 1:
            heading_issues.append(f"Multiple H1 headings found ({h1_count})")

        # List validation
        lines = text.split('\n')
        in_list = False
        list_type = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^[-*+]\s', stripped):
                if in_list and list_type == 'ordered':
                    list_issues.append(f"Mixed list types at line {i+1}: unordered item in ordered list")
                in_list = True
                list_type = 'unordered'
            elif re.match(r'^\d+[.)]\s', stripped):
                if in_list and list_type == 'unordered':
                    list_issues.append(f"Mixed list types at line {i+1}: ordered item in unordered list")
                in_list = True
                list_type = 'ordered'
            elif stripped and not stripped.startswith(' ') and not stripped.startswith('\t'):
                in_list = False
                list_type = None

        # HTML usage detection
        html_usage = bool(re.search(r'<[a-z]+[\s>]', text))

        # Score calculation
        total_issues = len(table_issues) + len(image_issues) + len(code_block_issues) + len(heading_issues) + len(list_issues) + len(broken_links)
        score = max(0, 100 - total_issues * 5)
        if html_usage:
            score -= 5
        score = max(0, min(100, score))

        return MarkdownReport(
            score=round(score, 1),
            table_count=table_count,
            table_issues=table_issues,
            image_count=image_count,
            images_missing_alt=images_missing_alt,
            image_issues=image_issues,
            link_count=link_count,
            broken_links=broken_links,
            code_block_count=code_block_count,
            code_block_issues=code_block_issues,
            heading_issues=heading_issues,
            list_issues=list_issues,
            html_usage_detected=html_usage,
            issues=issues,
        )

    def _extract_tables(self, text: str) -> list[str]:
        tables: list[str] = []
        lines = text.split('\n')
        in_table = False
        current_table: list[str] = []
        for line in lines:
            if '|' in line and '---' not in line.split('|')[1] if len(line.split('|')) > 1 else False:
                pass
            is_table_row = bool(re.match(r'^\s*\|', line)) or bool(re.match(r'^\s*[\w\s]+\|', line))
            is_separator = bool(re.match(r'^\s*\|[\s:-]+\|', line))
            if is_table_row or is_separator:
                if not in_table:
                    in_table = True
                    current_table = [line]
                else:
                    current_table.append(line)
            else:
                if in_table and len(current_table) >= 2:
                    tables.append('\n'.join(current_table))
                in_table = False
                current_table = []
        if in_table and len(current_table) >= 2:
            tables.append('\n'.join(current_table))
        return tables
