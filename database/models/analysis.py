from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class AnalysisModel(BaseModel):
    __tablename__ = "analyses"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_points: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    topics: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    entities: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False, default="neutral")
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, default="informational")
    complexity: Mapped[str] = mapped_column(String(32), nullable=False, default="intermediate")
    readability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    keywords: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    categories: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pain_points: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    questions: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<AnalysisModel uuid={self.uuid}>"
