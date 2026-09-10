from __future__ import annotations

import pytest
from pydantic import ValidationError

from prompt_management.prompt_models import (
    ExperimentResult,
    ExperimentStatus,
    ExperimentVariant,
    PromptAnalytics,
    PromptCategory,
    PromptExperiment,
    PromptMetadata,
    PromptStatus,
    PromptVersion,
    RiskLevel,
)


class TestPromptMetadata:
    def test_create_default(self):
        meta = PromptMetadata(name="Test Prompt")
        assert meta.name == "Test Prompt"
        assert meta.version == "1.0.0"
        assert meta.status == PromptStatus.draft
        assert meta.category == PromptCategory.custom
        assert meta.tags == []
        assert meta.language == "en"

    def test_invalid_semver(self):
        with pytest.raises(ValidationError):
            PromptMetadata(name="Bad", version="1.0")

    def test_valid_semver(self):
        meta = PromptMetadata(name="Good", version="2.1.3")
        assert meta.version == "2.1.3"

    def test_risk_level_default(self):
        meta = PromptMetadata(name="Test")
        assert meta.risk_level == RiskLevel.low

    def test_change_log(self):
        meta = PromptMetadata(
            name="Test",
            change_log=[{"version": "1.0.0", "date": "2026-01-01", "author": "test", "summary": "initial"}],
        )
        assert len(meta.change_log) == 1
        assert meta.change_log[0]["version"] == "1.0.0"


class TestPromptVersion:
    def test_create_version(self):
        v = PromptVersion(
            prompt_id="p_test",
            version_number="1.0.0",
            content="Test content",
            author="test",
        )
        assert v.prompt_id == "p_test"
        assert v.version_number == "1.0.0"
        assert v.content == "Test content"
        assert v.status == PromptStatus.draft

    def test_version_with_diff(self):
        v = PromptVersion(
            prompt_id="p_test",
            version_number="2.0.0",
            content="New content",
            author="test",
            diff="--- a/previous\n+++ b/current\n@@ -1 +1 @@\n-test\n+new",
            change_summary="Major rewrite",
        )
        assert v.diff != ""
        assert v.change_summary == "Major rewrite"


class TestPromptAnalytics:
    def test_create_analytics(self):
        a = PromptAnalytics(
            prompt_id="p_test",
            version="1.0.0",
            execution_count=10,
            total_tokens=5000,
            success_count=9,
            failure_count=1,
            success_rate=0.9,
            model_used="gemini-2.0-flash",
        )
        assert a.execution_count == 10
        assert a.success_rate == 0.9

    def test_analytics_defaults(self):
        a = PromptAnalytics(prompt_id="p_test", version="1.0.0")
        assert a.execution_count == 0
        assert a.success_rate == 1.0
        assert a.failure_count == 0


class TestExperimentModels:
    def test_experiment_variant(self):
        v = ExperimentVariant(
            name="Variant A",
            prompt_id="p_test",
            version="1.0.0",
            traffic_percent=50.0,
            is_control=True,
        )
        assert v.name == "Variant A"
        assert v.is_control

    def test_experiment_result(self):
        r = ExperimentResult(
            variant_id="ev_test",
            executions=100,
            successes=95,
            failures=5,
            avg_latency_ms=250.0,
            avg_quality_score=0.85,
        )
        assert r.executions == 100
        assert r.successes == 95
        assert r.successes + r.failures == r.executions

    def test_experiment_defaults(self):
        e = PromptExperiment(name="Test Experiment", target_prompt_id="p_test", variants=[])
        assert e.status == ExperimentStatus.draft
        assert e.min_executions == 100

    def test_experiment_with_variants(self):
        variants = [
            ExperimentVariant(name="A", prompt_id="p_test", version="1.0.0", traffic_percent=50.0, is_control=True),
            ExperimentVariant(name="B", prompt_id="p_test", version="1.1.0", traffic_percent=50.0),
        ]
        e = PromptExperiment(
            name="A/B Test",
            target_prompt_id="p_test",
            variants=variants,
            created_by="test",
        )
        assert len(e.variants) == 2


class TestEnums:
    def test_prompt_status_values(self):
        assert PromptStatus.draft.value == "draft"
        assert PromptStatus.production.value == "production"
        assert PromptStatus.deprecated.value == "deprecated"

    def test_prompt_category_values(self):
        assert PromptCategory.analysis.value == "analysis"
        assert PromptCategory.seo.value == "seo"
        assert PromptCategory.faq.value == "faq"

    def test_risk_level_values(self):
        assert RiskLevel.low.value == "low"
        assert RiskLevel.critical.value == "critical"

    def test_experiment_status_values(self):
        assert ExperimentStatus.running.value == "running"
        assert ExperimentStatus.completed.value == "completed"
