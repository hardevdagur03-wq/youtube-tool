"""Workspace service — workspace management within organizations."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from database.base import utcnow


class WorkspaceService:
    """Manages workspaces within organizations."""

    def __init__(self, workspace_repo=None):
        self._workspace_repo = workspace_repo

    async def create_workspace(
        self,
        organization_uuid: str,
        name: str,
        created_by_uuid: str,
    ) -> Any:
        workspace = type("Workspace", (), {
            "uuid": secrets.token_hex(16),
            "organization_uuid": organization_uuid,
            "name": name,
            "slug": self._generate_slug(name),
            "is_active": True,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        })
        if self._workspace_repo:
            workspace = await self._workspace_repo.create(workspace)
        return workspace

    async def get_workspace(self, workspace_uuid: str) -> Any | None:
        if self._workspace_repo:
            return await self._workspace_repo.get_by_uuid(workspace_uuid)
        return None

    async def list_workspaces(
        self, organization_uuid: str
    ) -> list[Any]:
        if self._workspace_repo:
            return await self._workspace_repo.list_by_field(
                "organization_uuid", organization_uuid
            )
        return []

    async def update_workspace(
        self, workspace_uuid: str, updates: dict[str, Any]
    ) -> Any | None:
        ws = await self.get_workspace(workspace_uuid)
        if not ws:
            return None
        for key, value in updates.items():
            if hasattr(ws, key):
                setattr(ws, key, value)
        if self._workspace_repo:
            ws = await self._workspace_repo.update(ws)
        return ws

    async def archive_workspace(self, workspace_uuid: str) -> bool:
        ws = await self.get_workspace(workspace_uuid)
        if not ws:
            return False
        ws.is_active = False
        if self._workspace_repo:
            await self._workspace_repo.update(ws)
        return True

    async def delete_workspace(self, workspace_uuid: str) -> bool:
        if self._workspace_repo:
            await self._workspace_repo.soft_delete(workspace_uuid)
        return True

    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return f"{slug}-{secrets.token_hex(4)}"
