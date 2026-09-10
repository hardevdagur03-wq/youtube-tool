from __future__ import annotations

from datetime import datetime, timedelta, timezone

from observability.cost_tracker import CostTracker, CostRecord


class TestCostTracker:
    def test_record_cost(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.025, model="gpt-4o")
        summary = tracker.get_summary(days=30)
        assert summary.call_count == 1
        assert abs(summary.total_cost - 0.025) < 0.0001

    def test_record(self):
        tracker = CostTracker()
        record = CostRecord(service="gemini", operation="generate", cost=0.005, model="gemini-2.0-flash")
        tracker.record(record)
        summary = tracker.get_summary()
        assert summary.call_count == 1

    def test_by_service(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.05)
        tracker.record_cost(service="anthropic", operation="chat", cost=0.03)
        summary = tracker.get_summary()
        assert "openai" in summary.by_service
        assert "anthropic" in summary.by_service

    def test_by_project(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01, project_id="proj_a")
        tracker.record_cost(service="openai", operation="chat", cost=0.02, project_id="proj_b")
        by_project = tracker.get_by_project()
        assert abs(by_project["proj_a"] - 0.01) < 0.0001
        assert abs(by_project["proj_b"] - 0.02) < 0.0001

    def test_daily_costs(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01)
        daily = tracker.get_daily_costs(days=7)
        assert len(daily) == 7
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_entry = [d for d in daily if d["date"] == today]
        assert len(today_entry) == 1
        assert today_entry[0]["cost"] > 0

    def test_cumulative_cost(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01)
        tracker.record_cost(service="openai", operation="chat", cost=0.02)
        cumulative = tracker.get_cumulative_cost()
        assert abs(cumulative - 0.03) < 0.0001

    def test_estimated_monthly(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01)
        estimated = tracker.get_estimated_monthly_cost()
        assert estimated > 0

    def test_clear(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01)
        tracker.clear()
        assert tracker.get_cumulative_cost() == 0.0

    def test_summary_to_dict(self):
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="chat", cost=0.01)
        summary = tracker.get_summary()
        d = summary.to_dict()
        assert "total_cost" in d
        assert "by_service" in d
