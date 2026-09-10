from __future__ import annotations

from typing import Any

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class ReviewModel(BaseModel):
    __tablename__ = "reviews"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    draft_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, default="", index=True
    )
    grammar_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    seo_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    readability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hallucination_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    eeat_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    accessibility_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    duplication_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    recommendations: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    strengths: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    publication_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<ReviewModel uuid={self.uuid} overall={self.overall_score:.1f}>"
