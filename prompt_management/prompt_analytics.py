from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from prompt_management.prompt_models import PromptAnalytics
from prompt_management.prompt_repository import PromptRepository


class PromptAnalyticsCollector:
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

    def __init__(self, repository: PromptRepository):
        self._repository = repository
        self._batch: list[PromptAnalytics] = []

    def record_execution(
        self,
        prompt_id: str,
        version: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        quality_score: float = 0.0,
        model_used: str = "",
        cost: float | None = None,
    ) -> PromptAnalytics:
        total_tokens = prompt_tokens + completion_tokens
        if cost is None:
            cost = self._estimate_cost(total_tokens, model_used)

        record = PromptAnalytics(
            prompt_id=prompt_id,
            version=version,
            execution_count=1,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=cost,
            total_latency_ms=latency_ms,
            avg_latency_ms=latency_ms,
            failure_count=0 if success else 1,
            success_count=1 if success else 0,
            success_rate=1.0 if success else 0.0,
            avg_quality_score=quality_score,
            model_used=model_used,
            last_executed=datetime.now(timezone.utc).isoformat(),
        )

        self._repository.save_analytics(record)
        self._batch.append(record)
        return record

    def get_summary(self, prompt_id: str) -> dict[str, Any]:
        records = self._repository.get_analytics(prompt_id)
        if not records:
            return {
                "prompt_id": prompt_id,
                "total_executions": 0,
                "success_rate": 1.0,
                "avg_latency_ms": 0.0,
                "avg_quality_score": 0.0,
                "total_tokens": 0,
                "total_cost": 0.0,
            }

        total_exec = sum(r.execution_count for r in records)
        total_success = sum(r.success_count for r in records)
        total_latency = sum(r.total_latency_ms for r in records)
        total_cost = sum(r.total_cost for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        quality_scores = [r.avg_quality_score for r in records if r.avg_quality_score > 0]

        return {
            "prompt_id": prompt_id,
            "total_executions": total_exec,
            "success_rate": total_success / total_exec if total_exec > 0 else 1.0,
            "avg_latency_ms": total_latency / total_exec if total_exec > 0 else 0.0,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "cost_per_execution": round(total_cost / total_exec, 6) if total_exec > 0 else 0.0,
            "tokens_per_execution": total_tokens / total_exec if total_exec > 0 else 0,
            "models_used": list(set(r.model_used for r in records if r.model_used)),
        }

    def get_model_performance(self, model: str) -> dict[str, Any]:
        all_records: list[PromptAnalytics] = []
        for meta in self._repository.list_metadata():
            all_records.extend(self._repository.get_analytics(meta.prompt_id))

        model_records = [r for r in all_records if r.model_used == model]
        if not model_records:
            return {"model": model, "total_executions": 0}

        total_exec = sum(r.execution_count for r in model_records)
        total_success = sum(r.success_count for r in model_records)
        total_latency = sum(r.total_latency_ms for r in model_records)
        total_cost = sum(r.total_cost for r in model_records)
        total_tokens = sum(r.total_tokens for r in model_records)

        return {
            "model": model,
            "total_executions": total_exec,
            "success_rate": total_success / total_exec if total_exec > 0 else 1.0,
            "avg_latency_ms": total_latency / total_exec if total_exec > 0 else 0.0,
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "cost_per_1k_tokens": self.MODEL_COST_PER_1K_TOKENS.get(model, 0),
        }

    def get_global_stats(self) -> dict[str, Any]:
        all_prompts = self._repository.list_metadata()
        total_exec = 0
        total_success = 0
        total_cost = 0.0
        total_tokens = 0
        prompt_stats = []

        for meta in all_prompts:
            summary = self.get_summary(meta.prompt_id)
            prompt_stats.append(summary)
            total_exec += summary["total_executions"]
            total_success += int(summary["success_rate"] * summary["total_executions"]) if summary["total_executions"] > 0 else 0
            total_cost += summary["total_cost"]
            total_tokens += summary["total_tokens"]

        return {
            "total_prompts": len(all_prompts),
            "total_executions": total_exec,
            "global_success_rate": total_success / total_exec if total_exec > 0 else 1.0,
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "avg_cost_per_execution": round(total_cost / total_exec, 6) if total_exec > 0 else 0.0,
            "prompts": prompt_stats,
        }

    def _estimate_cost(self, tokens: int, model: str) -> float:
        cost_per_1k = self.MODEL_COST_PER_1K_TOKENS.get(model, 0.001)
        return (tokens / 1000) * cost_per_1k
