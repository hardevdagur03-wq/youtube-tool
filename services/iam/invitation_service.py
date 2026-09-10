"""Invitation service — invite users to organizations and workspaces."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from database.base import utcnow


class InvitationService:
    """Manages user invitations to organizations and workspaces."""

    def __init__(self, invitation_repo=None):
        self._invitation_repo = invitation_repo

    async def create_invitation(
        self,
        organization_uuid: str,
        inviter_uuid: str,
        email: str,
        role: str = "member",
        message: str = "",
    ) -> Any:
        token = secrets.token_urlsafe(48)
        invitation = type("Invitation", (), {
            "uuid": secrets.token_hex(16),
            "organization_uuid": organization_uuid,
            "inviter_uuid": inviter_uuid,
            "email": email.lower().strip(),
            "role": role,
            "token": token,
            "message": message,
            "status": "pending",
            "expires_at": utcnow() + timedelta(days=7),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        })
        if self._invitation_repo:
            invitation = await self._invitation_repo.create(invitation)
        return invitation

    async def accept_invitation(self, token: str, user_uuid: str) -> tuple[bool, str]:
        if not self._invitation_repo:
            return False, "Invitation system not configured"

        invitations = await self._invitation_repo.list_by_field("token", token)
        if not invitations:
            return False, "Invalid or expired invitation"

        invitation = invitations[0]
        if invitation.status != "pending":
            return False, "Invitation already processed"
        if invitation.expires_at and invitation.expires_at < utcnow():
            invitation.status = "expired"
            await self._invitation_repo.update(invitation)
            return False, "Invitation has expired"

        from database.models import OrganizationMemberModel
        member = OrganizationMemberModel(
            organization_uuid=invitation.organization_uuid,
            user_uuid=user_uuid,
            role=invitation.role,
        )
        await self._invitation_repo.create(member)

        invitation.status = "accepted"
        await self._invitation_repo.update(invitation)
        return True, "Invitation accepted"

    async def decline_invitation(self, token: str) -> bool:
        if not self._invitation_repo:
            return False
        invitations = await self._invitation_repo.list_by_field("token", token)
        if not invitations:
            return False
        inv = invitations[0]
        inv.status = "declined"
        await self._invitation_repo.update(inv)
        return True

    async def revoke_invitation(self, invitation_uuid: str) -> bool:
        if not self._invitation_repo:
            return False
        inv = await self._invitation_repo.get_by_uuid(invitation_uuid)
        if not inv:
            return False
        inv.status = "revoked"
        await self._invitation_repo.update(inv)
        return True

    async def list_pending(self, organization_uuid: str) -> list[Any]:
        if not self._invitation_repo:
            return []
        return await self._invitation_repo.list_by_field(
            "organization_uuid", organization_uuid
        )
