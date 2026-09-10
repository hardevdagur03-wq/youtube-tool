from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Callable

from editor.editor_models import (
    CursorPosition, DocumentModel, DocumentStats, EditorConfig,
    EditorState, SelectionRange, ValidationResult, ValidationSeverity,
    ViewMode,
)

logger = logging.getLogger(__name__)

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MARKDOWN_TABLE_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
MARKDOWN_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
MARKDOWN_BLOCKQUOTE_RE = re.compile(r"^>\s+(.*)$", re.MULTILINE)
MARKDOWN_LIST_RE = re.compile(r"^(\s*[-*+]\s|\s*\d+\.\s)", re.MULTILINE)
MARKDOWN_HR_RE = re.compile(r"^(\s*[-*_]\s*[-*_]\s*[-*_]+\s*)$", re.MULTILINE)
MARKDOWN_FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]:\s+(.*)")
MARKDOWN_TASK_LIST_RE = re.compile(r"^\s*[-*+]\s+\[[ x]\]\s+", re.MULTILINE)


class DocumentManager:
    def __init__(self, config: EditorConfig | None = None):
        self._config = config or EditorConfig()
        self._state = EditorState()
        self._change_listeners: list[Callable] = []

    @property
    def state(self) -> EditorState:
        return self._state

    @property
    def document(self) -> DocumentModel:
        return self._state.document

    @property
    def config(self) -> EditorConfig:
        return self._config

    def set_config(self, config: EditorConfig) -> None:
        self._config = config

    def load_document(self, content: str, project_id: str = "", title: str = "") -> DocumentModel:
        doc = DocumentModel(
            project_id=project_id,
            title=title,
            content=content,
            markdown=content,
            version=1,
            checksum=hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
        )
        doc.update_stats()
        self._state.document = doc
        self._state.project_id = project_id
        self._state.is_dirty = False
        self._state.is_loading = False
        self._emit("document_loaded", {"project_id": project_id})
        return doc

    def get_content(self) -> str:
        return self._state.document.content

    def set_content(self, content: str, emit_change: bool = True) -> None:
        old_content = self._state.document.content
        self._state.document.content = content
        self._state.document.markdown = content
        self._state.document.update_stats()
        self._state.is_dirty = True
        if content != old_content and emit_change:
            self._emit("document_changed", {
                "old_content": old_content,
                "new_content": content,
            })

    def get_html(self) -> str:
        return self._state.document.html

    def set_html(self, html: str) -> None:
        self._state.document.html = html

    def get_selection(self) -> SelectionRange:
        return self._state.selection

    def set_selection(self, selection: SelectionRange) -> None:
        self._state.selection = selection
        if not selection.collapsed:
            self._emit("selection_changed", {"selection": selection.model_dump()})

    def get_cursor(self) -> CursorPosition:
        return self._state.cursor

    def set_cursor(self, cursor: CursorPosition) -> None:
        self._state.cursor = cursor
        self._state.last_cursor_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        self._emit("cursor_moved", {"cursor": cursor.model_dump()})

    def set_view_mode(self, mode: ViewMode) -> None:
        self._state.view_mode = mode
        self._state.config.view_mode = mode
        self._emit("view_mode_changed", {"mode": mode.value})

    def get_view_mode(self) -> ViewMode:
        return self._state.view_mode

    def insert_text(self, text: str, offset: int | None = None) -> str:
        content = self._state.document.content
        if offset is None:
            offset = self._state.cursor.offset
        new_content = content[:offset] + text + content[offset:]
        self.set_content(new_content)
        return new_content

    def delete_range(self, start: int, end: int) -> str:
        content = self._state.document.content
        new_content = content[:start] + content[end:]
        self.set_content(new_content)
        return new_content

    def replace_range(self, start: int, end: int, replacement: str) -> str:
        content = self._state.document.content
        new_content = content[:start] + replacement + content[end:]
        self.set_content(new_content)
        return new_content

    def apply_formatting(self, command: str, selection: SelectionRange | None = None) -> str:
        sel = selection or self._state.selection
        if sel.collapsed:
            return self._state.document.content

        text = sel.text
        start = sel.start.offset
        end = sel.end.offset
        wrapped = self._wrap_formatting(text, command)
        return self.replace_range(start, end, wrapped)

    def _wrap_formatting(self, text: str, command: str) -> str:
        fmt: dict[str, tuple[str, str]] = {
            "bold": ("**", "**"),
            "italic": ("*", "*"),
            "strikethrough": ("~~", "~~"),
            "inline_code": ("`", "`"),
            "highlight": ("==", "=="),
            "heading_1": ("# ", ""),
            "heading_2": ("## ", ""),
            "heading_3": ("### ", ""),
            "heading_4": ("#### ", ""),
        }
        if command in fmt:
            prefix, suffix = fmt[command]
            return f"{prefix}{text}{suffix}"
        return text

    def insert_heading(self, level: int, text: str) -> str:
        prefix = "#" * level
        return f"{prefix} {text}\n\n"

    def insert_table(self, rows: int, cols: int, headers: list[str] | None = None) -> str:
        if headers and len(headers) != cols:
            headers = None
        lines: list[str] = []
        header_row = "| " + " | ".join(headers or [f"Column {i+1}" for i in range(cols)]) + " |"
        sep_row = "| " + " | ".join(["---"] * cols) + " |"
        lines.append(header_row)
        lines.append(sep_row)
        for _ in range(rows - 1):
            data_row = "| " + " | ".join([""] * cols) + " |"
            lines.append(data_row)
        return "\n".join(lines) + "\n\n"

    def insert_code_block(self, language: str = "", code: str = "") -> str:
        return f"```{language}\n{code}\n```\n\n"

    def insert_blockquote(self, text: str) -> str:
        return f"> {text}\n\n"

    def insert_link(self, text: str, url: str) -> str:
        return f"[{text}]({url})"

    def insert_image(self, alt: str, url: str) -> str:
        return f"![{alt}]({url})"

    def insert_horizontal_rule(self) -> str:
        return "---\n\n"

    def insert_list(self, items: list[str], ordered: bool = False) -> str:
        lines: list[str] = []
        for i, item in enumerate(items):
            if ordered:
                lines.append(f"{i+1}. {item}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines) + "\n\n"

    def compute_statistics(self) -> DocumentStats:
        content = self._state.document.content
        stats = DocumentStats()
        if not content:
            return stats

        stats.word_count = len(content.split())
        stats.character_count = len(content)
        stats.character_count_no_spaces = len(content.replace(" ", "").replace("\n", ""))
        stats.paragraph_count = len([p for p in content.split("\n\n") if p.strip()])

        sentences = re.split(r"[.!?]+", content)
        stats.sentence_count = len([s for s in sentences if s.strip()])
        stats.heading_count = len(MARKDOWN_HEADING_RE.findall(content))
        stats.image_count = len(MARKDOWN_IMAGE_RE.findall(content))
        stats.link_count = len(MARKDOWN_LINK_RE.findall(content))
        stats.table_count = len(MARKDOWN_TABLE_RE.findall(content))
        stats.code_block_count = len(MARKDOWN_CODE_BLOCK_RE.findall(content))
        stats.blockquote_count = len(MARKDOWN_BLOCKQUOTE_RE.findall(content))
        stats.list_count = len(MARKDOWN_LIST_RE.findall(content))

        stats.reading_time_minutes = max(1, round(stats.word_count / 200))
        stats.speaking_time_minutes = max(1, round(stats.word_count / 130))

        if stats.word_count > 0:
            unique_words = set(w.lower().strip(".,!?;:'\"()[]") for w in content.split())
            stats.vocabulary_richness = round(len(unique_words) / stats.word_count, 4) if stats.word_count > 0 else 0
            total_chars = sum(len(w) for w in content.split())
            stats.avg_word_length = round(total_chars / stats.word_count, 2) if stats.word_count > 0 else 0

        if stats.sentence_count > 0:
            stats.avg_sentence_length = round(stats.word_count / stats.sentence_count, 2)

        syllable_count = 0
        difficult_words = 0
        for word in content.split():
            clean = word.strip(".,!?;:'\"()[]").lower()
            if clean:
                s = self._count_syllables(clean)
                syllable_count += s
                if s >= 3:
                    difficult_words += 1

        stats.syllable_count = syllable_count
        stats.difficult_word_count = difficult_words

        if stats.word_count > 0 and stats.sentence_count > 0:
            stats.flesch_reading_ease = round(
                206.835 - 1.015 * (stats.word_count / stats.sentence_count)
                - 84.6 * (syllable_count / stats.word_count),
                2,
            )
            stats.readability_score = min(100, max(0, stats.flesch_reading_ease))

        return stats

    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        if len(word) <= 3:
            return 1
        count = 0
        vowels = "aeiouy"
        prev_is_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel
        if word.endswith("e"):
            count -= 1
        if word.endswith("le") and len(word) > 2:
            count += 1
        return max(1, count)

    def compute_seo_score(self) -> float:
        content = self._state.document.content
        if not content:
            return 0.0

        score = 0.0
        checks = 0

        if self._state.document.title:
            score += 10
            checks += 10
        if self._state.document.seo_title:
            score += 5
            checks += 5
        if self._state.document.meta_description:
            score += 5
            checks += 5

        word_count = len(content.split())
        if 1000 <= word_count <= 2500:
            score += 15
        elif word_count >= 500:
            score += 10
        checks += 15

        headings = MARKDOWN_HEADING_RE.findall(content)
        h1_count = sum(1 for _, tag in [(m[0], m[0]) for m in [("", "")]] if False)
        h1_count = len(re.findall(r"^#\s+(.+)$", content, re.MULTILINE))
        h2_count = len(re.findall(r"^##\s+(.+)$", content, re.MULTILINE))

        if h1_count == 1:
            score += 10
        elif h1_count == 0:
            score += 0
        checks += 10

        if h2_count >= 3:
            score += 10
        elif h2_count >= 1:
            score += 5
        checks += 10

        images = MARKDOWN_IMAGE_RE.findall(content)
        if len(images) >= 1:
            score += 5
        checks += 5

        links = MARKDOWN_LINK_RE.findall(content)
        if len(links) >= 1:
            score += 5
            has_internal = False
            for _, url in links:
                if url.startswith("/") or "yourdomain" in url:
                    has_internal = True
                    break
            if has_internal:
                score += 5
            checks += 5

        if word_count >= 300:
            for keyword in ["how", "what", "why", "when", "guide", "tutorial", "best", "tips"]:
                if keyword in content.lower():
                    score += 2
                    checks += 2

        readability = self.compute_statistics().flesch_reading_ease
        if readability >= 60:
            score += 10
        elif readability >= 30:
            score += 5
        checks += 10

        return round(min(100, (score / max(1, checks)) * 100), 1)

    def validate(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        content = self._state.document.content

        if not content:
            return results

        h1_tags = re.findall(r"^#\s+(.+)$", content, re.MULTILINE)
        if len(h1_tags) == 0:
            results.append(ValidationResult(
                severity=ValidationSeverity.WARNING,
                message="Document has no H1 heading",
                rule="heading-h1",
                suggestion="Add an H1 heading at the top of the document",
            ))
        elif len(h1_tags) > 1:
            for i, tag in enumerate(h1_tags[1:], 2):
                lines = content.split("\n")
                line_num = 1
                for j, line in enumerate(lines):
                    if re.match(r"^#\s+" + re.escape(tag) + r"$", line):
                        line_num = j + 1
                        break
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message=f"Multiple H1 headings found (extra: '{tag}')",
                    line=line_num,
                    rule="heading-h1-unique",
                    suggestion="Use only one H1 heading per document",
                ))

        heading_levels = re.findall(r"^(#{1,6})\s+", content, re.MULTILINE)
        prev_level = 1
        for i, level_str in enumerate(heading_levels):
            level = len(level_str)
            if level > prev_level + 1:
                lines = content.split("\n")
                line_num = 1
                count = 0
                for j, line in enumerate(lines):
                    if re.match(r"^" + level_str + r"\s+", line):
                        count += 1
                        if count == i + 1:
                            line_num = j + 1
                            break
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message=f"Heading level jumps from h{prev_level} to h{level}",
                    line=line_num,
                    rule="heading-levels",
                    suggestion=f"Use an h{prev_level + 1} heading instead of h{level}",
                ))
            prev_level = level

        code_blocks = MARKDOWN_CODE_BLOCK_RE.findall(content)
        for block in code_blocks:
            lang_match = re.match(r"```(\w*)", block)
            if lang_match and not lang_match.group(1):
                results.append(ValidationResult(
                    severity=ValidationSeverity.INFO,
                    message="Code block without language specification",
                    rule="code-block-language",
                    suggestion="Specify a language for syntax highlighting",
                ))

        images = MARKDOWN_IMAGE_RE.findall(content)
        for alt_text, url in images:
            if not alt_text:
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message=f"Image without alt text: {url}",
                    rule="image-alt",
                    suggestion="Add descriptive alt text for accessibility and SEO",
                ))
            if not url.startswith(("http://", "https://", "/")):
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message=f"Image URL may be invalid: {url}",
                    rule="image-url",
                ))

        links = MARKDOWN_LINK_RE.findall(content)
        for link_text, url in links:
            if not url.startswith(("http://", "https://", "mailto:", "/", "#")):
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message=f"Link URL may be invalid: {url}",
                    rule="link-url",
                ))

        tables = MARKDOWN_TABLE_RE.findall(content)
        for table in tables:
            columns = table.strip("|").split("|")
            if len(columns) < 2:
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    message="Table with fewer than 2 columns",
                    rule="table-columns",
                ))

        return results

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Change listener error: {e}")
