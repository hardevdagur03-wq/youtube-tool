"""Change Detector — detects which sections changed, what changed, and tracks modifications."""

from __future__ import annotations
import difflib
import logging
import re
from typing import Any

from optimization.optimization_models import OptimizedSection

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detects and classifies changes between original and optimized content."""

    def detect_changes(
        self,
        original: str,
        optimized: str,
        section_heading: str = "",
    ) -> dict[str, Any]:
        if original == optimized:
            return {"changed": False, "diff_ratio": 1.0, "modifications": []}

        diff_ratio = self._similarity(original, optimized)
        modifications: list[dict] = []
        changes = self._get_changes(original, optimized)

        for change_type, text in changes[:10]:
            modifications.append({
                "type": change_type,
                "text": text[:100],
                "length": len(text),
            })

        return {
            "changed": True,
            "diff_ratio": round(diff_ratio, 4),
            "modifications": modifications,
            "word_count_delta": len(optimized.split()) - len(original.split()),
            "char_count_delta": len(optimized) - len(original),
            "summary": self._summarize_changes(modifications),
        }

    def was_section_optimized(
        self,
        section: OptimizedSection,
    ) -> bool:
        return section.optimized_content != section.original_content and bool(section.optimized_content)

    def has_meaningful_change(
        self,
        original: str,
        optimized: str,
        min_diff_ratio: float = 0.05,
    ) -> bool:
        if original == optimized:
            return False
        ratio = self._similarity(original, optimized)
        return (1 - ratio) >= min_diff_ratio

    def get_affected_headings(
        self,
        original_draft: str,
        optimized_draft: str,
    ) -> list[dict]:
        orig_headings = self._extract_headings(original_draft)
        opt_headings = self._extract_headings(optimized_draft)
        affected: list[dict] = []

        for h in orig_headings:
            if h not in opt_headings:
                affected.append({"heading": h, "status": "removed"})

        for h in opt_headings:
            if h not in orig_headings:
                affected.append({"heading": h, "status": "added"})

        return affected

    def _similarity(self, a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _get_changes(self, original: str, optimized: str) -> list[tuple[str, str]]:
        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            optimized.splitlines(keepends=True),
            n=0,
        ))
        changes: list[tuple[str, str]] = []
        for line in diff:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                continue
            if line.startswith('-'):
                changes.append(("removed", line[1:].strip()))
            elif line.startswith('+'):
                changes.append(("added", line[1:].strip()))
        return changes

    def _summarize_changes(self, modifications: list[dict]) -> str:
        added = sum(1 for m in modifications if m["type"] == "added")
        removed = sum(1 for m in modifications if m["type"] == "removed")
        parts = []
        if added:
            parts.append(f"{added} addition(s)")
        if removed:
            parts.append(f"{removed} removal(s)")
        return ", ".join(parts) if parts else "minor changes"

    @staticmethod
    def _extract_headings(markdown: str) -> list[str]:
        return re.findall(r'^(#{1,6})\s+(.+)$', markdown, re.MULTILINE)
