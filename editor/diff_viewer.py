from __future__ import annotations

import difflib
import logging
from typing import Callable

from editor.editor_models import DiffLine, DiffType, VersionDiff

logger = logging.getLogger(__name__)


class DiffViewer:
    def __init__(self):
        self._change_listeners: list[Callable] = []

    def compute_diff(
        self,
        old_content: str,
        new_content: str,
        old_version: int = 0,
        new_version: int = 1,
        context_lines: int = 3,
    ) -> VersionDiff:
        diff = VersionDiff(
            old_version=old_version,
            new_version=new_version,
            old_content=old_content,
            new_content=new_content,
        )

        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        opcodes = matcher.get_opcodes()

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                for idx in range(i1, i2):
                    line_idx = idx - i1
                    if line_idx >= context_lines and idx + context_lines < i2:
                        if line_idx == context_lines and (i2 - i1) > context_lines * 2 + 1:
                            diff.lines.append(DiffLine(
                                type=DiffType.UNCHANGED,
                                content="...",
                                old_line_number=idx + 1,
                                new_line_number=j1 + (idx - i1) + 1,
                            ))
                            continue
                        elif line_idx > context_lines and line_idx < i2 - i1 - context_lines:
                            continue
                    diff.lines.append(DiffLine(
                        type=DiffType.UNCHANGED,
                        content=old_lines[idx],
                        old_line_number=idx + 1,
                        new_line_number=j1 + (idx - i1) + 1,
                    ))
                    diff.unchanged_lines += 1

            elif tag == "replace":
                for idx in range(i1, i2):
                    diff.lines.append(DiffLine(
                        type=DiffType.REMOVED,
                        content=old_lines[idx],
                        old_line_number=idx + 1,
                    ))
                    diff.removed_lines += 1
                for idx in range(j1, j2):
                    diff.lines.append(DiffLine(
                        type=DiffType.ADDED,
                        content=new_lines[idx],
                        new_line_number=idx + 1,
                    ))
                    diff.added_lines += 1
                diff.modified_lines += 1

            elif tag == "delete":
                for idx in range(i1, i2):
                    diff.lines.append(DiffLine(
                        type=DiffType.REMOVED,
                        content=old_lines[idx],
                        old_line_number=idx + 1,
                    ))
                    diff.removed_lines += 1

            elif tag == "insert":
                for idx in range(j1, j2):
                    diff.lines.append(DiffLine(
                        type=DiffType.ADDED,
                        content=new_lines[idx],
                        new_line_number=idx + 1,
                    ))
                    diff.added_lines += 1

        total = max(len(old_lines), len(new_lines))
        diff.change_percentage = round(
            ((diff.added_lines + diff.removed_lines) / max(1, total)) * 100, 2
        )

        return diff

    def compute_inline_diff(self, old_text: str, new_text: str) -> list[dict]:
        matcher = difflib.SequenceMatcher(None, old_text, new_text)
        result: list[dict] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                result.append({"type": "equal", "text": old_text[i1:i2]})
            elif tag == "replace":
                result.append({"type": "removed", "text": old_text[i1:i2]})
                result.append({"type": "added", "text": new_text[j1:j2]})
            elif tag == "delete":
                result.append({"type": "removed", "text": old_text[i1:i2]})
            elif tag == "insert":
                result.append({"type": "added", "text": new_text[j1:j2]})
        return result

    def compute_word_diff(self, old_text: str, new_text: str) -> list[dict]:
        old_words = old_text.split()
        new_words = new_text.split()
        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        result: list[dict] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                result.append({"type": "equal", "text": " ".join(old_words[i1:i2])})
            elif tag == "replace":
                result.append({"type": "removed", "text": " ".join(old_words[i1:i2])})
                result.append({"type": "added", "text": " ".join(new_words[j1:j2])})
            elif tag == "delete":
                result.append({"type": "removed", "text": " ".join(old_words[i1:i2])})
            elif tag == "insert":
                result.append({"type": "added", "text": " ".join(new_words[j1:j2])})
        return result

    def render_diff_html(self, diff: VersionDiff) -> str:
        html_parts: list[str] = [
            '<div class="diff-container font-mono text-sm">',
            f'<div class="diff-header flex items-center gap-4 p-3 border-b border-gray-200 dark:border-gray-700">',
            f'<span class="diff-version text-gray-500">v{diff.old_version} → v{diff.new_version}</span>',
            f'<span class="diff-stat text-green-600">+{diff.added_lines}</span>',
            f'<span class="diff-stat text-red-600">-{diff.removed_lines}</span>',
            f'<span class="diff-stat text-gray-500">{diff.change_percentage}% changed</span>',
            '</div>',
            '<div class="diff-lines">',
        ]

        for line in diff.lines:
            line_class = {
                DiffType.ADDED: "diff-added bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200",
                DiffType.REMOVED: "diff-removed bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200",
                DiffType.UNCHANGED: "diff-unchanged text-gray-700 dark:text-gray-300",
                DiffType.MODIFIED: "diff-modified bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200",
            }.get(line.type, "diff-unchanged")

            old_num = str(line.old_line_number) if line.old_line_number else ""
            new_num = str(line.new_line_number) if line.new_line_number else ""

            prefix = {
                DiffType.ADDED: "+",
                DiffType.REMOVED: "-",
                DiffType.UNCHANGED: " ",
                DiffType.MODIFIED: "~",
            }.get(line.type, " ")

            html_parts.append(
                f'<div class="diff-line {line_class} flex">'
                f'<span class="diff-line-number w-12 text-right pr-2 text-gray-400 select-none">{old_num}</span>'
                f'<span class="diff-line-number w-12 text-right pr-2 text-gray-400 select-none">{new_num}</span>'
                f'<span class="diff-prefix w-4 text-center select-none">{prefix}</span>'
                f'<span class="diff-content flex-1 whitespace-pre-wrap">{self._escape_html(line.content)}</span>'
                f'</div>'
            )

        html_parts.append("</div></div>")
        return "\n".join(html_parts)

    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"DiffViewer listener error: {e}")
