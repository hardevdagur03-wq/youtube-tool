from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class KnowledgeGraphModel(BaseModel):
    __tablename__ = "knowledge_graphs"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    entities: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    relationships: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    facts: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    topics: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    keywords: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    pain_points: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    solutions: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    quotes: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    definitions: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    clusters: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    statistics: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<KnowledgeGraphModel uuid={self.uuid}>"
