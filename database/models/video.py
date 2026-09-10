from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class VideoModel(BaseModel):
    __tablename__ = "videos"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    channel_title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    channel_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    view_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    category: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<VideoModel uuid={self.uuid} video_id={self.video_id}>"
