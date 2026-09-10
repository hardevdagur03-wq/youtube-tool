from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class PipelineStateModel(BaseModel):
    __tablename__ = "pipeline_states"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    current_stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default="created"
    )
    completed_stages: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    pending_stages: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    failed_stages: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    skipped_stages: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    resume_point: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    pipeline_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_order: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<PipelineStateModel project={self.project_uuid[:8]} stage={self.current_stage}>"
