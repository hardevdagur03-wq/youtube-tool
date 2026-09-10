from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON as SA_JSON

from database.base import BaseModel


class OptimizationModel(BaseModel):
    __tablename__ = "optimizations"

    project_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    draft_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, default="", index=True
    )
    review_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, default=""
    )
    original_draft: Mapped[str] = mapped_column(Text, nullable=False, default="")
    optimized_draft: Mapped[str] = mapped_column(Text, nullable=False, default="")
    changes_applied: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    score_improvements: Mapped[dict[str, float]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    pre_optimization_scores: Mapped[dict[str, float]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    post_optimization_scores: Mapped[dict[str, float]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    gates_passed: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    gates_failed: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    optimization_round: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<OptimizationModel uuid={self.uuid}>"
