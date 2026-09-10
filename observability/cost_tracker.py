from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from observability.logger import get_logger


@dataclass
class CostRecord:
    service: str
    operation: str
    cost: float
    user_id: str = ""
    project_id: str = ""
    model: str = ""
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CostSummary:
    total_cost: float = 0.0
    call_count: int = 0
    by_service: dict[str, float] = field(default_factory=dict)
    by_project: dict[str, float] = field(default_factory=dict)
    by_user: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 6),
            "call_count": self.call_count,
            "by_service": {k: round(v, 6) for k, v in self.by_service.items()},
            "by_project": {k: round(v, 6) for k, v in self.by_project.items()},
            "by_user": {k: round(v, 6) for k, v in self.by_user.items()},
            "by_model": {k: round(v, 6) for k, v in self.by_model.items()},
        }


SERVICE_COST_RATES: dict[str, float] = {
    "openai": 0.0025,
    "anthropic": 0.003,
    "gemini": 0.0001,
    "youtube_api": 0.0,
    "translation": 0.0005,
    "image_generation": 0.002,
    "whisper": 0.006,
}


class CostTracker:
    def __init__(self):
        self._records: list[CostRecord] = []
        self._logger = get_logger(__name__)

    def record(self, record: CostRecord) -> None:
        self._records.append(record)

    def record_cost(
        self,
        service: str,
        operation: str,
        cost: float,
        user_id: str = "",
        project_id: str = "",
        model: str = "",
        tokens: int = 0,
        **metadata: Any,
    ) -> None:
        record = CostRecord(
            service=service,
            operation=operation,
            cost=cost,
            user_id=user_id,
            project_id=project_id,
            model=model,
            tokens=tokens,
            metadata=metadata,
        )
        self._records.append(record)

    def get_summary(self, days: int = 30) -> CostSummary:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        records = [r for r in self._records if r.timestamp >= cutoff.isoformat()]
        by_service: dict[str, float] = defaultdict(float)
        by_project: dict[str, float] = defaultdict(float)
        by_user: dict[str, float] = defaultdict(float)
        by_model: dict[str, float] = defaultdict(float)
        total = 0.0
        for r in records:
            total += r.cost
            by_service[r.service] += r.cost
            if r.project_id:
                by_project[r.project_id] += r.cost
            if r.user_id:
                by_user[r.user_id] += r.cost
            if r.model:
                by_model[r.model] += r.cost
        return CostSummary(
            total_cost=total,
            call_count=len(records),
            by_service=dict(by_service),
            by_project=dict(by_project),
            by_user=dict(by_user),
            by_model=dict(by_model),
        )

    def get_daily_costs(self, days: int = 30) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        records = [r for r in self._records if r.timestamp >= cutoff.isoformat()]
        by_date: dict[str, float] = defaultdict(float)
        for r in records:
            d = r.timestamp[:10]
            by_date[d] += r.cost
        result = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": d, "cost": round(by_date.get(d, 0.0), 6)})
        return result

    def get_by_project(self) -> dict[str, float]:
        by_project: dict[str, float] = defaultdict(float)
        for r in self._records:
            if r.project_id:
                by_project[r.project_id] += r.cost
        return {k: round(v, 6) for k, v in by_project.items()}

    def get_cumulative_cost(self) -> float:
        return round(sum(r.cost for r in self._records), 6)

    def get_estimated_monthly_cost(self) -> float:
        if not self._records:
            return 0.0
        now = datetime.now(timezone.utc)
        first = datetime.fromisoformat(self._records[0].timestamp)
        days_span = max((now - first).days, 1)
        total = sum(r.cost for r in self._records)
        return round((total / days_span) * 30, 6)

    def clear(self) -> None:
        self._records.clear()
