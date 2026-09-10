from __future__ import annotations

from datetime import datetime, timedelta, timezone

from observability.token_metrics import TokenMetricsCollector, TokenUsageRecord, estimate_cost


class TestTokenMetrics:
    def test_record_call(self):
        collector = TokenMetricsCollector()
        collector.record_call(
            prompt_name="test_prompt",
            model="gemini-2.0-flash",
            provider="google",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=250.0,
            success=True,
        )
        summary = collector.get_summary()
        assert summary.call_count == 1
        assert summary.total_prompt_tokens == 100
        assert summary.total_completion_tokens == 50
        assert summary.total_tokens == 150

    def test_record(self):
        collector = TokenMetricsCollector()
        record = TokenUsageRecord(
            prompt_name="test",
            model="gpt-4o",
            provider="openai",
            prompt_tokens=200,
            completion_tokens=100,
        )
        collector.record(record)
        summary = collector.get_summary()
        assert summary.call_count == 1
        assert summary.total_tokens == 300

    def test_by_model(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="p1", model="gpt-4o", provider="openai", prompt_tokens=10, completion_tokens=5)
        collector.record_call(prompt_name="p2", model="claude-3-sonnet", provider="anthropic", prompt_tokens=20, completion_tokens=10)
        by_model = collector.get_by_model()
        assert "gpt-4o" in by_model
        assert "claude-3-sonnet" in by_model
        assert by_model["gpt-4o"].call_count == 1

    def test_by_prompt(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="prompt_a", model="gpt-4o", provider="openai", prompt_tokens=5, completion_tokens=5)
        collector.record_call(prompt_name="prompt_a", model="gpt-4o", provider="openai", prompt_tokens=5, completion_tokens=5)
        collector.record_call(prompt_name="prompt_b", model="gpt-4o", provider="openai", prompt_tokens=5, completion_tokens=5)
        by_prompt = collector.get_by_prompt()
        assert by_prompt["prompt_a"].call_count == 2
        assert by_prompt["prompt_b"].call_count == 1

    def test_by_project(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="p1", model="gpt-4o", provider="openai", prompt_tokens=10, completion_tokens=5, project_id="proj1")
        collector.record_call(prompt_name="p2", model="gpt-4o", provider="openai", prompt_tokens=10, completion_tokens=5, project_id="proj1")
        collector.record_call(prompt_name="p3", model="gpt-4o", provider="openai", prompt_tokens=10, completion_tokens=5, project_id="proj2")
        by_project = collector.get_by_project()
        assert by_project["proj1"].call_count == 2
        assert by_project["proj2"].call_count == 1

    def test_daily_usage(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="p1", model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50)
        daily = collector.get_daily_usage(days=7)
        assert len(daily) == 7
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_entry = [d for d in daily if d["date"] == today]
        assert len(today_entry) == 1
        assert today_entry[0]["call_count"] == 1

    def test_cache_savings(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="p1", model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50, cached=True)
        savings = collector.get_cache_savings()
        assert savings["cached_calls"] == 1
        assert savings["saved_tokens"] == 150

    def test_filter_by_time(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="old", model="gpt-4o", provider="openai", prompt_tokens=10, completion_tokens=5)
        since = datetime.now(timezone.utc) + timedelta(hours=1)
        summary = collector.get_summary(since=since)
        assert summary.call_count == 0

    def test_estimate_cost(self):
        cost = estimate_cost("gemini-2.0-flash", 1000, 500)
        expected = ((1000 + 500) / 1000) * 0.0001
        assert abs(cost - expected) < 0.0001

    def test_get_prompt_templates(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="tmpl1", model="gpt-4o", provider="openai", prompt_tokens=1, completion_tokens=1)
        collector.record_call(prompt_name="tmpl2", model="gpt-4o", provider="openai", prompt_tokens=1, completion_tokens=1)
        templates = collector.get_prompt_templates()
        assert "tmpl1" in templates
        assert "tmpl2" in templates

    def test_get_models(self):
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="p1", model="gpt-4o", provider="openai", prompt_tokens=1, completion_tokens=1)
        models = collector.get_models()
        assert "gpt-4o" in models
