from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

STANDARD_EVENTS = {
    "project.created",
    "project.updated",
    "project.deleted",
    "project.restored",
    "pipeline.started",
    "pipeline.stage_completed",
    "pipeline.stage_failed",
    "pipeline.paused",
    "pipeline.resumed",
    "pipeline.cancelled",
    "pipeline.completed",
    "metadata.fetched",
    "transcript.generated",
    "analysis.completed",
    "knowledge_graph.generated",
    "seo.updated",
    "outline.generated",
    "sections.generated",
    "draft.assembled",
    "draft.saved",
    "draft.edited",
    "review.completed",
    "optimization.completed",
    "export.created",
    "export.downloaded",
    "rollback.performed",
    "version.created",
    "settings.updated",
    "error.occurred",
}


class AuditService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_uuid: str,
        project_uuid: str | None = None,
        actor_type: str = "system",
        actor_id: str = "system",
        changes: dict[str, Any] | None = None,
        extra_data: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        duration_ms: int = 0,
    ) -> None:
        await self.uow.history.log_event(
            action=action,
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            project_uuid=project_uuid,
            actor_type=actor_type,
            actor_id=actor_id,
            changes=changes,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )

    async def log_project_event(
        self,
        project_uuid: str,
        action: str,
        changes: dict[str, Any] | None = None,
        actor_id: str = "system",
    ) -> None:
        await self.log(
            action=action,
            entity_type="project",
            entity_uuid=project_uuid,
            project_uuid=project_uuid,
            actor_id=actor_id,
            changes=changes,
        )

    async def log_pipeline_event(
        self,
        project_uuid: str,
        action: str,
        stage: str,
        changes: dict[str, Any] | None = None,
    ) -> None:
        await self.log(
            action=action,
            entity_type="pipeline",
            entity_uuid=project_uuid,
            project_uuid=project_uuid,
            changes={"stage": stage, **(changes or {})},
        )

    async def log_error(
        self,
        project_uuid: str | None,
        entity_type: str,
        entity_uuid: str,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.log(
            action="error.occurred",
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            project_uuid=project_uuid,
            changes={"error": error, "details": details or {}},
        )

    async def get_project_history(
        self, project_uuid: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self.uow.history.get_project_timeline(project_uuid)

    async def get_entity_history(
        self, entity_type: str, entity_uuid: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        events = await self.uow.history.list_by_entity(
            entity_type, entity_uuid, limit
        )
        return [
            {
                "timestamp": e.created_at.isoformat() if hasattr(e.created_at, 'isoformat') else str(e.created_at),
                "action": e.action,
                "actor": e.actor_id,
                "changes": e.changes,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ]

    async def get_recent_activity(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        events = await self.uow.history.get_recent_activity(limit)
        return [
            {
                "timestamp": e.created_at.isoformat() if hasattr(e.created_at, 'isoformat') else str(e.created_at),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_uuid": e.entity_uuid[:8],
                "project_uuid": e.project_uuid[:8] if e.project_uuid else None,
                "actor": e.actor_id,
            }
            for e in events
        ]

    async def get_action_summary(
        self, since_days: int = 7
    ) -> list[dict[str, Any]]:
        return await self.uow.history.get_action_summary(since_days)
