from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[], bool]
    cooldown_seconds: int = 300
    last_fired: float = 0.0

    def check(self) -> bool:
        now = time.time()
        if now - self.last_fired < self.cooldown_seconds:
            return False
        try:
            triggered = self.condition()
            if triggered:
                self.last_fired = now
            return triggered
        except Exception:
            return False


@dataclass
class AlertEvent:
    rule_name: str
    severity: AlertSeverity
    description: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp,
        }


class AlertManager:
    def __init__(self):
        self._rules: dict[str, AlertRule] = {}
        self._history: list[AlertEvent] = []

    def register(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def unregister(self, name: str) -> None:
        self._rules.pop(name, None)

    def evaluate(self) -> list[AlertEvent]:
        events: list[AlertEvent] = []
        for rule in self._rules.values():
            if rule.check():
                event = AlertEvent(
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                )
                events.append(event)
                self._history.append(event)
        return events

    def get_history(self, limit: int = 100) -> list[dict[str, str]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def clear_history(self) -> None:
        self._history.clear()

    def get_rules(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
                "cooldown_seconds": rule.cooldown_seconds,
            }
            for name, rule in self._rules.items()
        }
