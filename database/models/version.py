from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class VersionModel(BaseModel):
    __tablename__ = "versions"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    entity_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, index=True
    )
    previous_version_uuid: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    previous_version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    changed_fields: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    changed_by: Mapped[str] = mapped_column(
        String(128), nullable=False, default="system"
    )
    pipeline_stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    checksum: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return (
            f"<VersionModel uuid={self.uuid} "
            f"entity={self.entity_type}:{self.entity_uuid[:8]} "
            f"v{self.version_number}>"
        )
