"""Database model for export templates."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.base import BaseModel


class ExportTemplateModel(BaseModel):
    """Stores named export template configurations."""

    __tablename__ = "export_templates"

    name: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    brand_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#059669")
    secondary_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#1f2937")
    accent_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#7c3aed")
    font_family: Mapped[str] = mapped_column(String(128), nullable=False, default="Inter, sans-serif")
    font_family_heading: Mapped[str] = mapped_column(String(128), nullable=False, default="Inter, sans-serif")
    font_family_mono: Mapped[str] = mapped_column(String(128), nullable=False, default="JetBrains Mono, monospace")
    font_size_base: Mapped[int] = mapped_column(default=16)
    page_size: Mapped[str] = mapped_column(String(16), nullable=False, default="A4")
    cover_page: Mapped[bool] = mapped_column(default=True)
    toc_enabled: Mapped[bool] = mapped_column(default=True)
    css_variables: Mapped[dict] = mapped_column(SA_JSON, nullable=False, default=dict)
    template_metadata: Mapped[dict] = mapped_column(SA_JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<ExportTemplateModel name={self.name}>"
