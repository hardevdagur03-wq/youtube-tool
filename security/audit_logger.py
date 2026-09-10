from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from security.security_models import SecurityEvent


class SecurityAuditLogger:
    EVENT_CATEGORIES = {
        "auth.login": "Authentication",
        "auth.logout": "Authentication",
        "auth.failed": "Authentication",
        "auth.mfa": "Authentication",
        "auth.password_change": "Authentication",
        "session.created": "Session",
        "session.expired": "Session",
        "session.revoked": "Session",
        "permission.denied": "Authorization",
        "permission.granted": "Authorization",
        "permission.revoked": "Authorization",
        "api_key.created": "API Key",
        "api_key.revoked": "API Key",
        "api_key.used": "API Key",
        "rate_limit.exceeded": "Rate Limit",
        "threat.detected": "Threat",
        "threat.blocked": "Threat",
        "prompt.injection": "Prompt Security",
        "prompt.leakage": "Prompt Security",
        "security.header_set": "Security",
        "admin.action": "Admin",
        "user.created": "User",
        "user.updated": "User",
        "user.deleted": "User",
        "export.downloaded": "Export",
    }

    def __init__(self):
        self._events: list[SecurityEvent] = []

    def log(self, event: SecurityEvent) -> None:
        self._events.append(event)

    def log_event(
        self,
        event_type: str,
        actor_id: str,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        trace_id: str = "",
        severity: str = "info",
    ) -> None:
        event = SecurityEvent(
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=self._parse_severity(severity),
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            trace_id=trace_id,
        )
        self._events.append(event)

    def _parse_severity(self, severity: str) -> Any:
        from security.security_models import AlertSeverity
        try:
            return AlertSeverity(severity)
        except ValueError:
            return AlertSeverity.INFO

    def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events[-limit:]]

    def get_by_actor(self, actor_id: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.actor_id == actor_id]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_by_type(self, event_type: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.event_type == event_type]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_by_resource(self, resource_type: str, resource_id: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._events if e.resource_type == resource_type and e.resource_id == resource_id]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_alerts(self, min_severity: str = "medium", limit: int = 50) -> list[dict[str, Any]]:
        from security.security_models import AlertSeverity
        min_sev = AlertSeverity(min_severity)
        sev_order = {s: i for i, s in enumerate(AlertSeverity)}
        filtered = [e for e in self._events if sev_order.get(e.severity, 0) >= sev_order.get(min_sev, 0)]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for e in self._events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": by_type,
            "by_severity": by_severity,
            "unique_actors": len(set(e.actor_id for e in self._events)),
        }

    def clear(self) -> None:
        self._events.clear()
