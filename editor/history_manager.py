from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Callable

from editor.editor_models import (
    CursorPosition, HistoryEntry, HistoryAction, SelectionRange,
)

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self, max_history: int = 1000):
        self._undo_stack: list[HistoryAction] = []
        self._redo_stack: list[HistoryAction] = []
        self._max_history = max_history
        self._current_index = -1
        self._change_listeners: list[Callable] = []
        self._group_depth = 0
        self._group_actions: list[HistoryAction] = []
        self._can_undo = False
        self._can_redo = False

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def record(
        self,
        content_before: str,
        content_after: str,
        cursor_before: CursorPosition | None = None,
        cursor_after: CursorPosition | None = None,
        description: str = "edit",
        action_type: str = "edit",
    ) -> str:
        entry_id = uuid.uuid4().hex[:12]
        action = HistoryAction(
            entry_id=entry_id,
            content_before=content_before,
            content_after=content_after,
            cursor_before=cursor_before or CursorPosition(),
            cursor_after=cursor_after or CursorPosition(),
            description=description,
            action_type=action_type,
        )

        if self._group_depth > 0:
            self._group_actions.append(action)
        else:
            self._push(action)

        if description != "autosave":
            self._emit("history_recorded", {
                "entry_id": entry_id,
                "action_type": action_type,
                "description": description,
            })

        return entry_id

    def _push(self, action: HistoryAction) -> None:
        self._undo_stack.append(action)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._can_undo = True
        self._can_redo = False

    def undo(self) -> HistoryAction | None:
        if not self._undo_stack:
            return None
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        self._can_undo = len(self._undo_stack) > 0
        self._can_redo = True
        self._emit("undo", {
            "entry_id": action.entry_id,
            "description": action.description,
        })
        return action

    def redo(self) -> HistoryAction | None:
        if not self._redo_stack:
            return None
        action = self._redo_stack.pop()
        self._undo_stack.append(action)
        self._can_undo = True
        self._can_redo = len(self._redo_stack) > 0
        self._emit("redo", {
            "entry_id": action.entry_id,
            "description": action.description,
        })
        return action

    def peek_undo(self) -> HistoryAction | None:
        if self._undo_stack:
            return self._undo_stack[-1]
        return None

    def peek_redo(self) -> HistoryAction | None:
        if self._redo_stack:
            return self._redo_stack[-1]
        return None

    def begin_group(self) -> None:
        self._group_depth += 1

    def end_group(self, description: str = "group") -> None:
        if self._group_depth > 0:
            self._group_depth -= 1
            if self._group_depth == 0 and self._group_actions:
                first = self._group_actions[0]
                last = self._group_actions[-1]
                group_action = HistoryAction(
                    entry_id=uuid.uuid4().hex[:12],
                    content_before=first.content_before,
                    content_after=last.content_after,
                    cursor_before=first.cursor_before,
                    cursor_after=last.cursor_after,
                    description=description,
                    action_type="group",
                )
                self._group_actions.clear()
                self._push(group_action)

    def clear_history(self, preserve_current: bool = True) -> None:
        if preserve_current and self._undo_stack:
            current = self._undo_stack[-1]
            self._undo_stack.clear()
            self._undo_stack.append(current)
        else:
            self._undo_stack.clear()
        self._redo_stack.clear()
        self._can_undo = False
        self._can_redo = False
        self._emit("history_cleared", {})

    def get_undo_history(self, limit: int = 50) -> list[HistoryAction]:
        return list(reversed(self._undo_stack[-limit:]))

    def get_redo_history(self, limit: int = 50) -> list[HistoryAction]:
        return list(reversed(self._redo_stack[-limit:]))

    def get_all_history(self, limit: int = 100) -> list[HistoryAction]:
        all_actions = list(self._undo_stack) + list(reversed(self._redo_stack))
        return all_actions[-limit:]

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"History listener error: {e}")
