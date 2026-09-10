from __future__ import annotations

import logging
import re
from typing import Callable

from editor.editor_models import (
    FindReplaceMatch, FindReplaceRequest, FindReplaceResult,
)

logger = logging.getLogger(__name__)


class FindReplaceEngine:
    def __init__(self):
        self._last_query: str = ""
        self._last_result: FindReplaceResult | None = None
        self._current_match_index: int = -1
        self._change_listeners: list[Callable] = []

    def find_all(self, content: str, request: FindReplaceRequest) -> FindReplaceResult:
        result = FindReplaceResult()

        if not request.query:
            return result

        query = request.query
        flags = re.MULTILINE
        if not request.case_sensitive:
            flags |= re.IGNORECASE

        try:
            if request.use_regex:
                pattern = re.compile(query, flags)
            else:
                pattern = re.compile(re.escape(query), flags)
        except re.error as e:
            result.error = f"Invalid regex: {e}"
            return result

        lines = content.split("\n")
        offset = 0

        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                match_start = match.start()
                match_end = match.end()
                matched_text = line[match_start:match_end]

                if request.whole_word:
                    if not self._is_whole_word(line, match_start, match_end):
                        continue

                abs_start = offset + match_start
                abs_end = offset + match_end

                context_start = max(0, match_start - 30)
                context_end = min(len(line), match_end + 30)

                result.matches.append(FindReplaceMatch(
                    line=line_num,
                    column=match_start + 1,
                    start_offset=abs_start,
                    end_offset=abs_end,
                    text=matched_text,
                    context_before=line[context_start:match_start].strip(),
                    context_after=line[match_end:context_end].strip(),
                ))

            offset += len(line) + 1

        result.total_matches = len(result.matches)
        self._last_query = request.query
        self._last_result = result
        self._current_match_index = -1 if result.total_matches == 0 else 0

        return result

    def replace_one(self, content: str, request: FindReplaceRequest) -> FindReplaceResult:
        if self._current_match_index < 0:
            return self.find_all(content, request)

        all_matches = self.find_all(content, request)
        if self._current_match_index >= len(all_matches.matches):
            return all_matches

        match = all_matches.matches[self._current_match_index]
        new_content = (
            content[: match.start_offset]
            + request.replacement
            + content[match.end_offset :]
        )

        result = all_matches
        result.replacements_made = 1
        result.replaced_text = new_content

        self._emit("find_replace_executed", {
            "action": "replace_one",
            "query": request.query,
            "replacement": request.replacement,
        })

        return result

    def replace_all(self, content: str, request: FindReplaceRequest) -> FindReplaceResult:
        query = request.query
        replacement = request.replacement
        flags = re.MULTILINE
        if not request.case_sensitive:
            flags |= re.IGNORECASE

        try:
            if request.use_regex:
                pattern = re.compile(query, flags)
            else:
                pattern = re.compile(re.escape(query), flags)
        except re.error as e:
            result = FindReplaceResult()
            result.error = f"Invalid regex: {e}"
            return result

        def _replacement(m: re.Match) -> str:
            return re.sub(r"\\(\d+)", lambda x: m.group(int(x.group(1))), replacement)

        if request.whole_word:
            old_content = content
            new_content_list = list(content)
            replacements = 0
            lines = content.split("\n")
            offset = 0
            for line_num, line in enumerate(lines, 1):
                for match in pattern.finditer(line):
                    if self._is_whole_word(line, match.start(), match.end()):
                        abs_start = offset + match.start()
                        abs_end = offset + match.end()
                        for k in range(abs_start, abs_end):
                            pass
                        repl = replacement
                        new_content_list[abs_start:abs_end] = list(repl)
                        offset_adj = len(repl) - (abs_end - abs_start)
                        replacements += 1
                        break
                offset += len(line) + 1

            if replacements > 0:
                content = "".join(new_content_list)
        else:
            content = pattern.sub(replacement, content)

        result = FindReplaceResult()
        lines = content.split("\n")
        offset = 0
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                result.matches.append(FindReplaceMatch(
                    line=line_num,
                    column=match.start() + 1,
                    start_offset=offset + match.start(),
                    end_offset=offset + match.end(),
                    text=match.group(),
                ))
            offset += len(line) + 1

        result.total_matches = len(result.matches)
        result.replacements_made = len(re.findall(pattern, content))
        result.replaced_text = content

        self._emit("find_replace_executed", {
            "action": "replace_all",
            "query": request.query,
            "replacements": result.replacements_made,
        })

        return result

    def highlight_matches(self, content: str, request: FindReplaceRequest) -> list[FindReplaceMatch]:
        result = self.find_all(content, request)
        return result.matches

    def go_to_next_match(self) -> int:
        if self._last_result and self._last_result.total_matches > 0:
            self._current_match_index = (self._current_match_index + 1) % self._last_result.total_matches
        return self._current_match_index

    def go_to_previous_match(self) -> int:
        if self._last_result and self._last_result.total_matches > 0:
            self._current_match_index = (self._current_match_index - 1 + self._last_result.total_matches) % self._last_result.total_matches
        return self._current_match_index

    @property
    def current_match(self) -> int:
        return self._current_match_index + 1 if self._current_match_index >= 0 else 0

    @property
    def total_matches(self) -> int:
        return self._last_result.total_matches if self._last_result else 0

    def _is_whole_word(self, text: str, start: int, end: int) -> bool:
        if start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
            return False
        if end < len(text) and (text[end].isalnum() or text[end] == "_"):
            return False
        return True

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"FindReplace listener error: {e}")
