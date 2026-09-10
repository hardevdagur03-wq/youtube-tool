"""Incident Manager — tracks incidents, calculates MTTD and MTTR.

Provides incident lifecycle management with timeline tracking,
severity classification, and recovery time metrics.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class Incident:
    """Represents a single incident."""

    def __init__(
        self,
        incident_id: str,
        alert_name: str,
        severity: str,
        description: str,
        source: str = "",
    ) -> None:
        self.incident_id = incident_id
        self.alert_name = alert_name
        self.severity = severity
        self.description = description
        self.source = source
        self.created_at = time.time()
        self.detected_at = time.time()
        self.acknowledged_at: float | None = None
        self.resolved_at: float | None = None
        self.status = "open"
        self.events: list[dict[str, Any]] = []
        self._add_event("created", f"Incident created: {description}")

    def _add_event(self, action: str, message: str) -> None:
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "message": message,
        })

    def acknowledge(self) -> None:
        self.acknowledged_at = time.time()
        self.status = "acknowledged"
        self._add_event("acknowledged", "Incident acknowledged")

    def resolve(self, resolution: str = "") -> None:
        self.resolved_at = time.time()
        self.status = "resolved"
        self._add_event("resolved", resolution or "Incident resolved")

    @property
    def mttd_seconds(self) -> float:
        """Mean Time To Detect (creation to detection)."""
        return 0.0  # Detection is instantaneous in this system

    @property
    def mttr_seconds(self) -> float:
        """Mean Time To Recovery (creation to resolution)."""
        if self.resolved_at is None:
            return time.time() - self.created_at
        return self.resolved_at - self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "alert_name": self.alert_name,
            "severity": self.severity,
            "description": self.description,
            "source": self.source,
            "status": self.status,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "detected_at": datetime.fromtimestamp(self.detected_at, tz=timezone.utc).isoformat(),
            "acknowledged_at": datetime.fromtimestamp(self.acknowledged_at, tz=timezone.utc).isoformat() if self.acknowledged_at else None,
            "resolved_at": datetime.fromtimestamp(self.resolved_at, tz=timezone.utc).isoformat() if self.resolved_at else None,
            "mttd_seconds": self.mttd_seconds,
            "mttr_seconds": round(self.mttr_seconds, 1),
            "events": self.events,
        }


class IncidentManager:
    """Tracks and manages incidents with MTTD/MTTR calculation.

    Usage::

        mgr = IncidentManager()
        incident = mgr.create_incident("ApplicationDown", "critical", "API is down")
        mgr.acknowledge(incident.incident_id)
        mgr.resolve(incident.incident_id)
        mttr = mgr.calculate_mttr()
    """

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def create_incident(
        self, alert_name: str, severity: str,
        description: str, source: str = "",
    ) -> Incident:
        """Create a new incident.

        Args:
            alert_name: Alert rule name.
            severity: Severity level.
            description: Human-readable description.
            source: Source system.

        Returns:
            The created Incident.
        """
        incident_id = str(uuid.uuid4())
        incident = Incident(incident_id, alert_name, severity, description, source)
        self._incidents[incident_id] = incident
        logger.info(
            "Incident created: %s (%s) — %s",
            incident_id[:8], severity, description[:80],
        )
        return incident

    def acknowledge(self, incident_id: str) -> bool:
        """Acknowledge an incident.

        Args:
            incident_id: Incident ID.

        Returns:
            True if acknowledged, False if not found.
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            return False
        incident.acknowledge()
        return True

    def resolve(self, incident_id: str, resolution: str = "") -> bool:
        """Resolve an incident.

        Args:
            incident_id: Incident ID.
            resolution: Resolution description.

        Returns:
            True if resolved, False if not found.
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            return False
        incident.resolve(resolution)
        logger.info("Incident resolved: %s — %s", incident_id[:8], resolution or "resolved")
        return True

    def get_incident(self, incident_id: str) -> Incident | None:
        """Get an incident by ID.

        Args:
            incident_id: Incident ID.

        Returns:
            Incident or None.
        """
        return self._incidents.get(incident_id)

    def get_open_incidents(self, severity: str | None = None) -> list[Incident]:
        """Get all open incidents, optionally filtered by severity.

        Args:
            severity: Optional severity filter.

        Returns:
            List of open incidents.
        """
        incidents = [
            i for i in self._incidents.values()
            if i.status in ("open", "acknowledged")
        ]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        return incidents

    def get_incident_timeline(
        self, incident_id: str,
    ) -> list[dict[str, Any]]:
        """Get the full event timeline for an incident.

        Args:
            incident_id: Incident ID.

        Returns:
            List of event dicts.
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            return []
        return incident.events

    def calculate_mttr(
        self, severity: str | None = None,
    ) -> float:
        """Calculate Mean Time To Recovery for resolved incidents.

        Args:
            severity: Optional severity filter.

        Returns:
            Average MTTR in seconds.
        """
        resolved = [
            i for i in self._incidents.values()
            if i.status == "resolved"
        ]
        if severity:
            resolved = [i for i in resolved if i.severity == severity]
        if not resolved:
            return 0.0
        total_mttr = sum(i.mttr_seconds for i in resolved)
        return round(total_mttr / len(resolved), 1)

    def calculate_mttd(self) -> float:
        """Calculate Mean Time To Detect.

        Returns:
            Average MTTD in seconds (always 0 in this system).
        """
        return 0.0

    def get_summary(self) -> dict[str, Any]:
        """Get incident management summary.

        Returns:
            Dict with open/resolved counts and MTTR.
        """
        all_incidents = list(self._incidents.values())
        open_count = len(self.get_open_incidents())
        resolved_count = sum(1 for i in all_incidents if i.status == "resolved")
        return {
            "total_incidents": len(all_incidents),
            "open": open_count,
            "resolved": resolved_count,
            "critical_open": len(self.get_open_incidents("critical")),
            "high_open": len(self.get_open_incidents("high")),
            "mttr_seconds": self.calculate_mttr(),
            "mttd_seconds": self.calculate_mttd(),
        }
