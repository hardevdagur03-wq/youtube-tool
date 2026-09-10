from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_experiments import PromptExperimentManager
from prompt_management.prompt_models import ExperimentStatus, ExperimentVariant
from prompt_management.prompt_repository import PromptRepository


@pytest.fixture
def manager():
    with tempfile.TemporaryDirectory() as tmp:
        repo = PromptRepository(Path(tmp) / "prompts")
        yield PromptExperimentManager(repo)


def make_variants():
    return [
        ExperimentVariant(name="Control", prompt_id="p_test", version="1.0.0", traffic_percent=50.0, is_control=True),
        ExperimentVariant(name="Variant B", prompt_id="p_test", version="1.1.0", traffic_percent=50.0),
    ]


class TestPromptExperimentManager:
    def test_create_experiment(self, manager):
        exp = manager.create_experiment(
            name="Test A/B Test",
            target_prompt_id="p_test",
            variants=make_variants(),
            created_by="test",
        )
        assert exp.name == "Test A/B Test"
        assert exp.status == ExperimentStatus.draft
        assert len(exp.variants) == 2

    def test_create_experiment_auto_balance(self, manager):
        variants = [
            ExperimentVariant(name="A", prompt_id="p_test", version="1.0.0", traffic_percent=80.0),
            ExperimentVariant(name="B", prompt_id="p_test", version="1.1.0", traffic_percent=80.0),
        ]
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=variants)
        total = sum(v.traffic_percent for v in exp.variants)
        assert abs(total - 100.0) < 0.01

    def test_start_experiment(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        started = manager.start_experiment(exp.experiment_id)
        assert started is not None
        assert started.status == ExperimentStatus.running

    def test_start_nonexistent(self, manager):
        result = manager.start_experiment("nonexistent")
        assert result is None

    def test_select_variant(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        manager.start_experiment(exp.experiment_id)
        variant = manager.select_variant(exp.experiment_id)
        assert variant is not None
        assert variant.name in ("Control", "Variant B")

    def test_select_variant_not_running(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        variant = manager.select_variant(exp.experiment_id)
        assert variant is None

    def test_record_result(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        variant = exp.variants[0]
        updated = manager.record_result(
            experiment_id=exp.experiment_id,
            variant_id=variant.variant_id,
            success=True,
            latency_ms=200.0,
            quality_score=0.9,
            tokens=500,
            cost=0.01,
        )
        assert updated is not None
        result = updated.results[variant.variant_id]
        assert result.executions == 1
        assert result.successes == 1

    def test_record_result_multiple(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        v1 = exp.variants[0]
        v2 = exp.variants[1]
        manager.record_result(exp.experiment_id, v1.variant_id, success=True, quality_score=0.9)
        manager.record_result(exp.experiment_id, v1.variant_id, success=True, quality_score=0.8)
        manager.record_result(exp.experiment_id, v2.variant_id, success=False, quality_score=0.3)
        updated = manager.get_experiment(exp.experiment_id)
        assert updated is not None
        assert updated.results[v1.variant_id].executions == 2
        assert updated.results[v1.variant_id].avg_quality_score == pytest.approx(0.85, rel=1e-3)
        assert updated.results[v2.variant_id].executions == 1
        assert updated.results[v2.variant_id].failures == 1

    def test_evaluate_experiment(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants(), min_executions=1)
        manager.start_experiment(exp.experiment_id)
        manager.record_result(exp.experiment_id, exp.variants[0].variant_id, success=True, quality_score=0.9)
        manager.record_result(exp.experiment_id, exp.variants[1].variant_id, success=True, quality_score=0.95)
        evaluation = manager.evaluate_experiment(exp.experiment_id)
        assert evaluation is not None
        assert evaluation["total_executions"] == 2
        assert len(evaluation["variants"]) == 2

    def test_list_experiments(self, manager):
        manager.create_experiment(name="A", target_prompt_id="p_test", variants=make_variants())
        manager.create_experiment(name="B", target_prompt_id="p_test", variants=make_variants())
        experiments = manager.list_experiments()
        assert len(experiments) == 2

    def test_get_experiment(self, manager):
        exp = manager.create_experiment(name="Test", target_prompt_id="p_test", variants=make_variants())
        fetched = manager.get_experiment(exp.experiment_id)
        assert fetched is not None
        assert fetched.experiment_id == exp.experiment_id
