from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from prompt_management.prompt_models import (
    ExperimentResult,
    ExperimentStatus,
    ExperimentVariant,
    PromptExperiment,
)
from prompt_management.prompt_repository import PromptRepository


class PromptExperimentManager:
    def __init__(self, repository: PromptRepository):
        self._repository = repository

    def create_experiment(
        self,
        name: str,
        target_prompt_id: str,
        variants: list[ExperimentVariant],
        description: str = "",
        created_by: str = "system",
        min_executions: int = 100,
    ) -> PromptExperiment:
        total_traffic = sum(v.traffic_percent for v in variants)
        if abs(total_traffic - 100.0) > 0.01:
            for v in variants:
                v.traffic_percent = 100.0 / len(variants)

        experiment = PromptExperiment(
            name=name,
            description=description,
            target_prompt_id=target_prompt_id,
            variants=variants,
            created_by=created_by,
            min_executions=min_executions,
            status=ExperimentStatus.draft,
        )
        return self._repository.save_experiment(experiment)

    def start_experiment(self, experiment_id: str) -> PromptExperiment | None:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            return None
        experiment.status = ExperimentStatus.running
        experiment.updated_at = datetime.now(timezone.utc).isoformat()
        return self._repository.save_experiment(experiment)

    def select_variant(self, experiment_id: str) -> ExperimentVariant | None:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None or experiment.status != ExperimentStatus.running:
            return None

        roll = random.random() * 100
        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.traffic_percent
            if roll <= cumulative:
                return variant
        return experiment.variants[-1] if experiment.variants else None

    def record_result(
        self,
        experiment_id: str,
        variant_id: str,
        success: bool,
        latency_ms: float = 0.0,
        quality_score: float = 0.0,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> PromptExperiment | None:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            return None

        if variant_id not in experiment.results:
            experiment.results[variant_id] = ExperimentResult(variant_id=variant_id)

        result = experiment.results[variant_id]
        result.executions += 1
        if success:
            result.successes += 1
        else:
            result.failures += 1

        old_total_latency = result.avg_latency_ms * (result.executions - 1)
        result.avg_latency_ms = (old_total_latency + latency_ms) / result.executions

        old_total_quality = result.avg_quality_score * (result.executions - 1)
        result.avg_quality_score = (old_total_quality + quality_score) / result.executions

        old_total_tokens = result.avg_tokens * (result.executions - 1)
        result.avg_tokens = (old_total_tokens + tokens) / result.executions

        result.total_cost += cost

        experiment.updated_at = datetime.now(timezone.utc).isoformat()
        return self._repository.save_experiment(experiment)

    def evaluate_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            return None

        total_executions = sum(r.executions for r in experiment.results.values())
        evaluation = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": experiment.status.value,
            "total_executions": total_executions,
            "min_executions_met": total_executions >= experiment.min_executions,
            "variants": [],
            "winner": None,
            "can_promote": False,
        }

        best_score = -1.0
        best_variant_id = ""

        for variant in experiment.variants:
            result = experiment.results.get(variant.variant_id)
            if result is None:
                variant_eval = {
                    "variant_id": variant.variant_id,
                    "name": variant.name,
                    "is_control": variant.is_control,
                    "traffic_percent": variant.traffic_percent,
                    "executions": 0,
                    "success_rate": 0.0,
                    "avg_quality_score": 0.0,
                    "avg_latency_ms": 0.0,
                    "composite_score": 0.0,
                }
                evaluation["variants"].append(variant_eval)
                continue

            composite = (
                result.avg_quality_score * 0.4
                + (1.0 - min(result.avg_latency_ms / 10000, 1.0)) * 0.2
                + (result.successes / max(result.executions, 1)) * 0.4
            )

            variant_eval = {
                "variant_id": variant.variant_id,
                "name": variant.name,
                "is_control": variant.is_control,
                "traffic_percent": variant.traffic_percent,
                "executions": result.executions,
                "success_rate": result.successes / max(result.executions, 1),
                "avg_quality_score": result.avg_quality_score,
                "avg_latency_ms": result.avg_latency_ms,
                "avg_tokens": result.avg_tokens,
                "total_cost": result.total_cost,
                "composite_score": round(composite, 4),
            }
            evaluation["variants"].append(variant_eval)

            if composite > best_score:
                best_score = composite
                best_variant_id = variant.variant_id

        if best_variant_id:
            evaluation["winner"] = best_variant_id
            control_variant = next((v for v in experiment.variants if v.is_control), None)
            winner_variant = next((v for v in experiment.variants if v.variant_id == best_variant_id), None)
            if control_variant and winner_variant and not winner_variant.is_control:
                control_result = experiment.results.get(control_variant.variant_id)
                winner_result = experiment.results.get(winner_variant.variant_id)
                if control_result and winner_result and winner_result.executions >= experiment.min_executions:
                    improvement = ((winner_result.avg_quality_score - control_result.avg_quality_score) / max(control_result.avg_quality_score, 0.001)) * 100
                    evaluation["improvement_percent"] = round(improvement, 2)
                    evaluation["can_promote"] = improvement > 5.0

        return evaluation

    def promote_winner(self, experiment_id: str, author: str = "system") -> PromptExperiment | None:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            return None

        evaluation = self.evaluate_experiment(experiment_id)
        if not evaluation or not evaluation.get("can_promote"):
            return None

        winner_variant_id = evaluation.get("winner")
        if not winner_variant_id:
            return None

        winner_variant = next((v for v in experiment.variants if v.variant_id == winner_variant_id), None)
        if not winner_variant:
            return None

        experiment.winner_variant_id = winner_variant_id
        experiment.status = ExperimentStatus.completed
        experiment.updated_at = datetime.now(timezone.utc).isoformat()
        return self._repository.save_experiment(experiment)

    def list_experiments(self) -> list[PromptExperiment]:
        return self._repository.list_experiments()

    def get_experiment(self, experiment_id: str) -> PromptExperiment | None:
        return self._repository.get_experiment(experiment_id)
