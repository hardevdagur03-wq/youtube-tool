from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class TranscriptModel(BaseModel):
    __tablename__ = "transcripts"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    language: Mapped[str] = mapped_column(
        String(16), nullable=False, default="en", index=True
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="youtube"
    )
    plain_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<TranscriptModel uuid={self.uuid} video_id={self.video_id}>"
