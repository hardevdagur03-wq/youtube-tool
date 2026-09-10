from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import BaseModel
from sqlalchemy import JSON as SA_JSON


class ProjectModel(BaseModel):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    short_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    video_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    thumbnail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    channel_title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    channel_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="CREATED", index=True
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    folder_path: Mapped[str] = mapped_column(Text, nullable=False, default="")

    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    warnings: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    pipeline_state: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    statistics: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    checkpoints: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    artifacts: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    stage_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    sections_rel = relationship(
        "SectionModel", back_populates="project_rel",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProjectModel uuid={self.uuid} name={self.name} status={self.status}>"
