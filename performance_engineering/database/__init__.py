"""Database model for performance metrics tracking."""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, Integer, String, Text
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.base import BaseModel


class PerformanceMetricModel(BaseModel):
    """Stores performance metric snapshots for trending."""

    __tablename__ = "performance_metrics"

    metric_name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metric_unit: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ms"
    )
    labels: Mapped[dict] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    endpoint: Mapped[str] = mapped_column(
        String(128), nullable=False, default=""
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    def __repr__(self) -> str:
        return (
            f"<PerformanceMetricModel name={self.metric_name} "
            f"value={self.metric_value} {self.metric_unit}>"
        )
