from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from observability.logger import get_logger


@dataclass
class TokenUsageRecord:
    prompt_name: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    temperature: float = 0.0
    user_id: str = ""
    project_id: str = ""
    pipeline_id: str = ""
    success: bool = True
    retry_count: int = 0
    cached: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class TokenSummary:
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    estimated_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "estimated_cost": round(self.estimated_cost, 6),
        }


MODEL_COST_PER_1K_TOKENS: dict[str, float] = {
    "gemini-2.0-flash": 0.0001,
    "gemini-2.5-pro": 0.00125,
    "gpt-4o": 0.0025,
    "gpt-4o-mini": 0.00015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "deepseek-chat": 0.0005,
    "mistral-large": 0.002,
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = MODEL_COST_PER_1K_TOKENS.get(model, 0.001)
    return ((prompt_tokens + completion_tokens) / 1000) * rate


class TokenMetricsCollector:
    def __init__(self):
        self._records: list[TokenUsageRecord] = []
        self._logger = get_logger(__name__)

    def record(self, record: TokenUsageRecord) -> None:
        self._records.append(record)

    def record_call(
        self,
        prompt_name: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float = 0.0,
        temperature: float = 0.0,
        success: bool = True,
        retry_count: int = 0,
        cached: bool = False,
        user_id: str = "",
        project_id: str = "",
        pipeline_id: str = "",
    ) -> None:
        record = TokenUsageRecord(
            prompt_name=prompt_name,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            temperature=temperature,
            success=success,
            retry_count=retry_count,
            cached=cached,
            user_id=user_id,
            project_id=project_id,
            pipeline_id=pipeline_id,
        )
        self._records.append(record)

    def get_summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> TokenSummary:
        records = self._filter(since, until)
        if not records:
            return TokenSummary()
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        success = sum(1 for r in records if r.success)
        failures = sum(1 for r in records if not r.success)
        avg_latency = sum(r.latency_ms for r in records) / len(records) if records else 0
        total_cost = sum(
            estimate_cost(r.model, r.prompt_tokens, r.completion_tokens)
            for r in records
        )
        return TokenSummary(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            call_count=len(records),
            success_count=success,
            failure_count=failures,
            avg_latency_ms=avg_latency,
            estimated_cost=total_cost,
        )

    def get_by_model(self, since: datetime | None = None, until: datetime | None = None) -> dict[str, TokenSummary]:
        records = self._filter(since, until)
        by_model: dict[str, list[TokenUsageRecord]] = defaultdict(list)
        for r in records:
            by_model[r.model].append(r)
        return {
            model: self._summarize_records(recs)
            for model, recs in by_model.items()
        }

    def get_by_prompt(self, since: datetime | None = None, until: datetime | None = None) -> dict[str, TokenSummary]:
        records = self._filter(since, until)
        by_prompt: dict[str, list[TokenUsageRecord]] = defaultdict(list)
        for r in records:
            by_prompt[r.prompt_name].append(r)
        return {
            prompt: self._summarize_records(recs)
            for prompt, recs in by_prompt.items()
        }

    def get_by_project(self, since: datetime | None = None, until: datetime | None = None) -> dict[str, TokenSummary]:
        records = self._filter(since, until)
        by_project: dict[str, list[TokenUsageRecord]] = defaultdict(list)
        for r in records:
            by_project[r.project_id].append(r)
        return {
            pid: self._summarize_records(recs)
            for pid, recs in by_project.items()
        }

    def get_daily_usage(self, days: int = 30) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        records = [r for r in self._records if r.timestamp >= cutoff.isoformat()]
        by_date: dict[str, list[TokenUsageRecord]] = defaultdict(list)
        for r in records:
            d = r.timestamp[:10]
            by_date[d].append(r)
        result = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            recs = by_date.get(d, [])
            summary = self._summarize_records(recs) if recs else TokenSummary()
            result.append({
                "date": d,
                **summary.to_dict(),
            })
        return result

    def get_cache_savings(self) -> dict[str, Any]:
        cached = [r for r in self._records if r.cached]
        total_tokens = sum(r.total_tokens for r in cached)
        total_cost = sum(estimate_cost(r.model, r.prompt_tokens, r.completion_tokens) for r in cached)
        return {
            "cached_calls": len(cached),
            "saved_tokens": total_tokens,
            "saved_cost": round(total_cost, 6),
        }

    def _filter(self, since: datetime | None, until: datetime | None) -> list[TokenUsageRecord]:
        records = self._records
        if since:
            since_str = since.isoformat()
            records = [r for r in records if r.timestamp >= since_str]
        if until:
            until_str = until.isoformat()
            records = [r for r in records if r.timestamp <= until_str]
        return records

    def _summarize_records(self, records: list[TokenUsageRecord]) -> TokenSummary:
        if not records:
            return TokenSummary()
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        success = sum(1 for r in records if r.success)
        failures = sum(1 for r in records if not r.success)
        avg_latency = sum(r.latency_ms for r in records) / len(records)
        total_cost = sum(estimate_cost(r.model, r.prompt_tokens, r.completion_tokens) for r in records)
        return TokenSummary(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            call_count=len(records),
            success_count=success,
            failure_count=failures,
            avg_latency_ms=avg_latency,
            estimated_cost=total_cost,
        )

    def get_prompt_templates(self) -> list[str]:
        return list(set(r.prompt_name for r in self._records))

    def get_models(self) -> list[str]:
        return list(set(r.model for r in self._records))
