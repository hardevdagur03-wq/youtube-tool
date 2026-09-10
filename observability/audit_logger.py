from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from observability.logger import get_logger


class AuditEventType(Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_ACTION = "user.action"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    EXPORT_CREATED = "export.created"
    EXPORT_DOWNLOADED = "export.downloaded"
    AI_EXECUTION = "ai.execution"
    PROMPT_UPDATED = "prompt.updated"
    PROMPT_VERSION_CREATED = "prompt.version_created"
    PROMPT_DEPLOYED = "prompt.deployed"
    SETTINGS_CHANGED = "settings.changed"
    ADMIN_ACTION = "admin.action"
    SECURITY_EVENT = "security.event"


@dataclass
class AuditEvent:
    event_type: AuditEventType
    actor_id: str
    action: str
    resource_type: str = ""
    resource_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


class AuditLogger:
    def __init__(self):
        self._events: list[AuditEvent] = []
        self._logger = get_logger(__name__)

    def log(self, event: AuditEvent) -> None:
        self._events.append(event)
        self._logger.info(
            f"audit:{event.event_type.value}:{event.action}",
            actor_id=event.actor_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            trace_id=event.trace_id,
        )

    def log_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        trace_id: str = "",
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            trace_id=trace_id,
        )
        self.log(event)

    def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events[-limit:]]

    def get_by_actor(self, actor_id: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.actor_id == actor_id]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_by_resource(self, resource_type: str, resource_id: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.resource_type == resource_type and e.resource_id == resource_id]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_by_type(self, event_type: AuditEventType, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.event_type == event_type]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for e in self._events:
            key = e.event_type.value
            by_type[key] = by_type.get(key, 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": by_type,
            "unique_actors": len(set(e.actor_id for e in self._events)),
        }

    def clear(self) -> None:
        self._events.clear()
