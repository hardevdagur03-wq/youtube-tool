from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class OutlineModel(BaseModel):
    __tablename__ = "outlines"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    title_variants: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    sections: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    hierarchy: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    planned_word_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    introduction_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    conclusion_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cta_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    faq_plan: Mapped[list[dict[str, str]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    image_placeholders: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    table_plans: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    example_plans: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    keywords_per_section: Mapped[dict[str, list[str]]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<OutlineModel uuid={self.uuid} title={self.title[:60]}>"
