from __future__ import annotations

from typing import Any

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class SEOModel(BaseModel):
    __tablename__ = "seo"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    primary_keyword: Mapped[str] = mapped_column(
        String(512), nullable=False, default="", index=True
    )
    secondary_keywords: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    lsi_keywords: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    search_intent: Mapped[str] = mapped_column(
        String(64), nullable=False, default="informational"
    )
    meta_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url_slug: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    target_audience: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_structure: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    faq_schema: Mapped[list[dict[str, str]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    schema_markup: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    featured_snippet_target: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    internal_links: Mapped[list[dict[str, str]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    external_links: Mapped[list[dict[str, str]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    competitor_keywords: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    seo_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    readability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    keyword_difficulty: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<SEOModel uuid={self.uuid} keyword={self.primary_keyword}>"
