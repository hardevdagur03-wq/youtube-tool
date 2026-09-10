from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class SectionModel(BaseModel):
    __tablename__ = "sections"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    project_uuid_fk: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.uuid", ondelete="CASCADE"), nullable=True
    )
    heading: Mapped[str] = mapped_column(Text, nullable=False, default="")
    heading_tag: Mapped[str] = mapped_column(
        String(4), nullable=False, default="h2"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_plain: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    validation_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    generated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    subsections: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )

    project_rel = relationship("ProjectModel", back_populates="sections_rel")

    def __repr__(self) -> str:
        return f"<SectionModel uuid={self.uuid} heading={self.heading[:60]}>"
