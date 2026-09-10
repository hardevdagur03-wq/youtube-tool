"""Table Validator — validates table alignment, headers, and row consistency."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest
from review.review_models_ext import MarkdownReport


class TableValidator(BaseValidator):
    """Validates Markdown table structure, alignment, and consistency."""

    def name(self) -> str:
        return "Table Validation"

    def validate(self, request: BlogReviewRequest) -> MarkdownReport:
        text = request.content
        if not text:
            return MarkdownReport(score=100.0)

        table_issues: list[str] = []
        tables = self._extract_tables(text)

        for i, table in enumerate(tables):
            lines = table.strip().split('\n')
            if len(lines) < 2:
                table_issues.append(f"Table {i+1}: fewer than 2 lines (no separator row)")
                continue

            header_cells = [c.strip() for c in lines[0].split('|')]
            header_cells = [c for c in header_cells if c]
            header_count = len(header_cells)

            if header_count == 0:
                table_issues.append(f"Table {i+1}: empty header row")
                continue

            # Validate separator row
            sep_line = lines[1]
            sep_cells = sep_line.split('|')
            sep_cells = [c.strip() for c in sep_cells if c.strip()]

            if len(sep_cells) != header_count:
                table_issues.append(f"Table {i+1}: separator row has {len(sep_cells)} columns, header has {header_count}")

            valid_sep = all(re.match(r'^:?-+:?$', cell) for cell in sep_cells if cell)
            if not valid_sep:
                invalid_seps = [cell for cell in sep_cells if cell and not re.match(r'^:?-+:?$', cell)]
                for inv in invalid_seps[:3]:
                    table_issues.append(f"Table {i+1}: invalid alignment marker '{inv}'")

            # Validate alignment consistency
            alignments = []
            for cell in sep_cells:
                if cell.startswith(':') and cell.endswith(':'):
                    alignments.append('center')
                elif cell.endswith(':'):
                    alignments.append('right')
                else:
                    alignments.append('left')

            # Validate data rows
            for j, line in enumerate(lines[2:], 3):
                row_cells = [c.strip() for c in line.split('|')]
                row_cells = [c for c in row_cells if c]
                if len(row_cells) != header_count:
                    table_issues.append(f"Table {i+1} row {j}: {len(row_cells)} cells, expected {header_count}")

            # Check for empty header names
            empty_headers = [h for h in header_cells if not h.strip()]
            if empty_headers:
                table_issues.append(f"Table {i+1}: {len(empty_headers)} empty header(s)")

        # Score calculation
        score = max(0, 100 - len(table_issues) * 8)
        score = max(0, min(100, score))

        return MarkdownReport(
            score=round(score, 1),
            table_count=len(tables),
            table_issues=table_issues,
            issues=table_issues,
        )

    def _extract_tables(self, text: str) -> list[str]:
        tables: list[str] = []
        lines = text.split('\n')
        in_table = False
        current: list[str] = []
        for line in lines:
            if '|' in line and ('---' in line or re.match(r'^\s*\|', line) or re.match(r'^[^|]+\|', line)):
                if not in_table:
                    in_table = True
                    current = [line]
                else:
                    current.append(line)
            else:
                if in_table and len(current) >= 2:
                    tables.append('\n'.join(current))
                in_table = False
                current = []
        if in_table and len(current) >= 2:
            tables.append('\n'.join(current))
        return tables
