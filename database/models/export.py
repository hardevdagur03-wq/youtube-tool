from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class ExportModel(BaseModel):
    __tablename__ = "exports"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    export_format: Mapped[str] = mapped_column(
        String(32), nullable=False, default="markdown", index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checksum: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    export_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    download_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    export_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<ExportModel uuid={self.uuid} format={self.export_format}>"
