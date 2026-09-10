from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class AuditLogModel(BaseModel):
    __tablename__ = "audit_logs"

    project_uuid: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="system", index=True
    )
    actor_id: Mapped[str] = mapped_column(
        String(128), nullable=False, default="system"
    )
    action: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    entity_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, default=""
    )
    changes: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    ip_address: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    user_agent: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    def __repr__(self) -> str:
        return f"<AuditLogModel action={self.action} entity={self.entity_type}>"
