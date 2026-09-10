"""Session management service with refresh token rotation.

Implements:
- Multiple concurrent sessions per user
- Refresh token rotation (each refresh invalidates the old token)
- Reuse detection (if a rotated token is reused, revoke all sessions)
- Session listing and revocation
- Device fingerprinting
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from database.base import utcnow
from security.jwt_service import JWTService


@dataclass
class SessionInfo:
    session_id: str
    created_at: str
    expires_at: str
    last_activity: str
    ip_address: str
    user_agent: str
    device_name: str
    is_current: bool = False


class SessionService:
    """Manages user sessions with refresh token rotation."""

    def __init__(self, session_repo: Any, jwt_service: JWTService):
        self._session_repo = session_repo
        self._jwt = jwt_service

    async def create_session(
        self,
        user_uuid: str,
        ip_address: str = "",
        user_agent: str = "",
        device_name: str = "",
    ) -> dict[str, str]:
        now = utcnow()
        refresh_token = secrets.token_urlsafe(48)
        refresh_hash = self._hash_token(refresh_token)
        session_id = secrets.token_hex(16)

        session = await self._session_repo.create({
            "user_uuid": user_uuid,
            "session_token": session_id,
            "refresh_token_hash": refresh_hash,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_info": device_name,
            "is_active": True,
            "expires_at": now + timedelta(days=30),
            "last_activity_at": now,
        })

        return {
            "session_id": session_id,
            "refresh_token": refresh_token,
            "expires_at": (now + timedelta(days=30)).isoformat(),
        }

    async def rotate_refresh_token(
        self, refresh_token: str, old_session_id: str
    ) -> dict[str, str] | None:
        refresh_hash = self._hash_token(refresh_token)
        session = await self._session_repo.get_by_field("session_token", old_session_id)

        if not session or not session.is_active:
            return None

        if session.refresh_token_hash != refresh_hash:
            await self._revoke_all_sessions(session.user_uuid)
            return None

        new_refresh_token = secrets.token_urlsafe(48)
        new_refresh_hash = self._hash_token(new_refresh_token)

        session.refresh_token_hash = new_refresh_hash
        session.last_activity_at = utcnow()
        await self._session_repo.update(session)

        return {
            "session_id": session.session_token,
            "refresh_token": new_refresh_token,
        }

    async def revoke_session(self, session_id: str) -> bool:
        session = await self._session_repo.get_by_field("session_token", session_id)
        if not session:
            return False
        session.is_active = False
        await self._session_repo.update(session)
        return True

    async def revoke_all_sessions(self, user_uuid: str) -> int:
        sessions = await self._session_repo.list_by_field("user_uuid", user_uuid)
        count = 0
        for session in sessions:
            if session.is_active:
                session.is_active = False
                await self._session_repo.update(session)
                count += 1
        return count

    async def list_sessions(self, user_uuid: str) -> list[SessionInfo]:
        sessions = await self._session_repo.list_by_field("user_uuid", user_uuid)
        return [
            SessionInfo(
                session_id=s.session_token,
                created_at=s.created_at.isoformat() if s.created_at else "",
                expires_at=s.expires_at.isoformat() if s.expires_at else "",
                last_activity=s.last_activity_at.isoformat() if s.last_activity_at else "",
                ip_address=s.ip_address or "",
                user_agent=s.user_agent or "",
                device_name=s.device_info or "",
            )
            for s in sessions if s.is_active
        ]

    async def validate_session(self, session_id: str) -> bool:
        session = await self._session_repo.get_by_field("session_token", session_id)
        if not session or not session.is_active:
            return False
        if session.expires_at and session.expires_at < utcnow():
            session.is_active = False
            await self._session_repo.update(session)
            return False
        session.last_activity_at = utcnow()
        await self._session_repo.update(session)
        return True

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def _revoke_all_sessions(self, user_uuid: str) -> None:
        await self.revoke_all_sessions(user_uuid)
