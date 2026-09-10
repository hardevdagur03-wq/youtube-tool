from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.audit_log import AuditLogModel
from database.models.version import VersionModel
from database.repositories.base import BaseRepository


class HistoryRepository(BaseRepository[AuditLogModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLogModel)

    async def log_event(
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
    ) -> AuditLogModel:
        return await self.create(
            project_uuid=project_uuid,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            changes=changes or {},
            extra_data=extra_data or {},
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )

    async def list_by_project(
        self, project_uuid: str, limit: int = 100
    ) -> Sequence[AuditLogModel]:
        filters = [AuditLogModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="created_at", descending=True,
            filters=filters,
        )
        return result.items

    async def list_by_entity(
        self, entity_type: str, entity_uuid: str, limit: int = 50
    ) -> Sequence[AuditLogModel]:
        filters = [
            AuditLogModel.entity_type == entity_type,
            AuditLogModel.entity_uuid == entity_uuid,
        ]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="created_at", descending=True,
            filters=filters,
        )
        return result.items

    async def list_by_action(
        self, action: str, limit: int = 50
    ) -> Sequence[AuditLogModel]:
        filters = [AuditLogModel.action == action]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="created_at", descending=True,
            filters=filters,
        )
        return result.items

    async def get_project_timeline(
        self, project_uuid: str
    ) -> list[dict[str, Any]]:
        events = await self.list_by_project(project_uuid)
        return [
            {
                "timestamp": e.created_at.isoformat() if hasattr(e.created_at, 'isoformat') else str(e.created_at),
                "action": e.action,
                "actor": e.actor_id,
                "entity_type": e.entity_type,
                "changes": e.changes,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ]

    async def get_recent_activity(
        self, limit: int = 50
    ) -> Sequence[AuditLogModel]:
        return await self.list_all(
            order_by="created_at", descending=True, limit=limit
        )

    async def count_by_action(
        self, action: str
    ) -> int:
        return await self.count(
            filters=[AuditLogModel.action == action]
        )

    async def get_action_summary(
        self, since_days: int = 7
    ) -> list[dict[str, Any]]:
        from sqlalchemy import func, text
        rows = await self.list_all(order_by="created_at", descending=True, limit=1000)
        action_counts: dict[str, int] = {}
        for r in rows:
            action_counts[r.action] = action_counts.get(r.action, 0) + 1
        return [
            {"action": action, "count": count}
            for action, count in sorted(
                action_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]


class VersionHistoryRepository(BaseRepository[VersionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, VersionModel)

    async def list_by_entity(
        self, entity_type: str, entity_uuid: str, limit: int = 50
    ) -> Sequence[VersionModel]:
        filters = [
            VersionModel.entity_type == entity_type,
            VersionModel.entity_uuid == entity_uuid,
        ]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="version_number", descending=True,
            filters=filters,
        )
        return result.items

    async def get_version(
        self, entity_type: str, entity_uuid: str, version_number: int
    ) -> VersionModel | None:
        from sqlalchemy import and_
        filters = [
            VersionModel.entity_type == entity_type,
            VersionModel.entity_uuid == entity_uuid,
            VersionModel.version_number == version_number,
        ]
        result = await self.paginate(page=1, page_size=1, filters=filters)
        return result.items[0] if result.items else None

    async def get_latest_version(
        self, entity_type: str, entity_uuid: str
    ) -> VersionModel | None:
        filters = [
            VersionModel.entity_type == entity_type,
            VersionModel.entity_uuid == entity_uuid,
        ]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="version_number", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None

    async def get_next_version_number(
        self, entity_type: str, entity_uuid: str
    ) -> int:
        latest = await self.get_latest_version(entity_type, entity_uuid)
        return (latest.version_number + 1) if latest else 1


__all__ = ["HistoryRepository", "VersionHistoryRepository"]
