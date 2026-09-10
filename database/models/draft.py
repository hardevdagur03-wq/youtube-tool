from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class DraftModel(BaseModel):
    __tablename__ = "drafts"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    draft_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, index=True
    )
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    html_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reading_time_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    link_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    editor_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    toc: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<DraftModel uuid={self.uuid} draft={self.draft_number}>"
