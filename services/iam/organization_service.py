"""Organization service — multi-tenant organization management."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from database.base import utcnow
from database.models import (
    OrganizationMemberModel,
    OrganizationModel,
    UserModel,
)
from security.security_models import AuthorizationError


class OrganizationService:
    """Manages organization lifecycle and membership."""

    def __init__(self, org_repo=None, member_repo=None, user_repo=None):
        self._org_repo = org_repo
        self._member_repo = member_repo
        self._user_repo = user_repo

    async def create_organization(
        self,
        name: str,
        owner_uuid: str,
        slug: str = "",
    ) -> OrganizationModel:
        if not slug:
            slug = self._generate_slug(name)
        org = OrganizationModel(
            name=name,
            slug=slug,
            owner_uuid=owner_uuid,
            tier="free",
            max_members=10,
            max_projects=5,
        )
        if self._org_repo:
            org = await self._org_repo.create(org)

        await self.add_member(
            organization_uuid=org.uuid,
            user_uuid=owner_uuid,
            role="owner",
        )
        return org

    async def get_organization(self, org_uuid: str) -> OrganizationModel | None:
        if self._org_repo:
            return await self._org_repo.get_by_uuid(org_uuid)
        return None

    async def update_organization(
        self, org_uuid: str, updates: dict[str, Any]
    ) -> OrganizationModel | None:
        org = await self.get_organization(org_uuid)
        if not org:
            return None
        for key, value in updates.items():
            if hasattr(org, key):
                setattr(org, key, value)
        if self._org_repo:
            org = await self._org_repo.update(org)
        return org

    async def delete_organization(self, org_uuid: str) -> bool:
        org = await self.get_organization(org_uuid)
        if not org:
            return False
        if self._org_repo:
            await self._org_repo.soft_delete(org_uuid)
        return True

    async def list_organizations(self, limit: int = 100) -> list[OrganizationModel]:
        if self._org_repo:
            return await self._org_repo.list_all(limit=limit)
        return []

    # --- Membership Management ---

    async def add_member(
        self,
        organization_uuid: str,
        user_uuid: str,
        role: str = "member",
    ) -> OrganizationMemberModel:
        member = OrganizationMemberModel(
            organization_uuid=organization_uuid,
            user_uuid=user_uuid,
            role=role,
            is_active=True,
        )
        if self._member_repo:
            member = await self._member_repo.create(member)
        return member

    async def remove_member(
        self, organization_uuid: str, user_uuid: str
    ) -> bool:
        if self._member_repo:
            members = await self._member_repo.list_by_field(
                "organization_uuid", organization_uuid
            )
            for m in members:
                if m.user_uuid == user_uuid:
                    await self._member_repo.soft_delete(m.uuid)
                    return True
        return False

    async def get_members(
        self, organization_uuid: str
    ) -> list[OrganizationMemberModel]:
        if self._member_repo:
            return await self._member_repo.list_by_field(
                "organization_uuid", organization_uuid
            )
        return []

    async def get_user_organizations(
        self, user_uuid: str
    ) -> list[OrganizationModel]:
        if not self._member_repo or not self._org_repo:
            return []
        members = await self._member_repo.list_by_field("user_uuid", user_uuid)
        orgs = []
        for m in members:
            org = await self._org_repo.get_by_uuid(m.organization_uuid)
            if org and not org.is_deleted:
                orgs.append(org)
        return orgs

    async def is_member(
        self, organization_uuid: str, user_uuid: str
    ) -> bool:
        members = await self.get_members(organization_uuid)
        return any(m.user_uuid == user_uuid and m.is_active for m in members)

    async def update_member_role(
        self, organization_uuid: str, user_uuid: str, new_role: str
    ) -> bool:
        members = await self.get_members(organization_uuid)
        for m in members:
            if m.user_uuid == user_uuid:
                m.role = new_role
                if self._member_repo:
                    await self._member_repo.update(m)
                return True
        return False

    def _generate_slug(self, name: str) -> str:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        suffix = secrets.token_hex(4)
        return f"{slug}-{suffix}"
