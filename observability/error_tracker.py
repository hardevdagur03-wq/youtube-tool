from __future__ import annotations

import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from observability.logger import get_logger


@dataclass
class ErrorEvent:
    error_type: str
    message: str
    module: str
    stack_trace: str
    fingerprint: str
    timestamp: str = ""
    count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    first_seen: str = ""
    last_seen: str = ""
    resolved: bool = False

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.timestamp:
            self.timestamp = now
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "module": self.module,
            "fingerprint": self.fingerprint,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "resolved": self.resolved,
            "metadata": self.metadata,
        }


def make_fingerprint(exc: Exception, module: str = "") -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    frames = [(f.filename, f.lineno, f.name) for f in tb[-3:]] if tb else []
    return f"{type(exc).__name__}:{module}:{frames}"


class ErrorTracker:
    def __init__(self):
        self._errors: dict[str, ErrorEvent] = {}
        self._history: list[ErrorEvent] = []
        self._logger = get_logger(__name__)

    def capture(
        self,
        exc: Exception,
        module: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        fingerprint = make_fingerprint(exc, module)
        now = datetime.now(timezone.utc).isoformat()
        if fingerprint in self._errors:
            event = self._errors[fingerprint]
            event.count += 1
            event.last_seen = now
        else:
            event = ErrorEvent(
                error_type=type(exc).__name__,
                message=str(exc)[:500],
                module=module,
                stack_trace="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                fingerprint=fingerprint,
                metadata=metadata or {},
            )
            self._errors[fingerprint] = event
        self._history.append(event)
        self._logger.error(
            str(exc)[:200],
            error_type=type(exc).__name__,
            module=module,
            fingerprint=fingerprint,
        )
        return fingerprint

    def mark_resolved(self, fingerprint: str) -> None:
        if fingerprint in self._errors:
            self._errors[fingerprint].resolved = True

    def get_grouped_errors(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._errors.values()]

    def get_recent_errors(self, limit: int = 100) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def get_error_summary(self) -> dict[str, Any]:
        total = sum(e.count for e in self._errors.values())
        by_type: dict[str, int] = defaultdict(int)
        by_module: dict[str, int] = defaultdict(int)
        for e in self._errors.values():
            by_type[e.error_type] += e.count
            by_module[e.module] += e.count
        return {
            "total_errors": total,
            "unique_fingerprints": len(self._errors),
            "unresolved": sum(1 for e in self._errors.values() if not e.resolved),
            "by_type": dict(by_type),
            "by_module": dict(by_module),
        }

    def clear(self) -> None:
        self._errors.clear()
        self._history.clear()
