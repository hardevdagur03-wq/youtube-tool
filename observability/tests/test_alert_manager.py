from __future__ import annotations

import time

from observability.alert_manager import AlertManager, AlertRule, AlertSeverity, AlertEvent


class TestAlertManager:
    def test_register_and_evaluate(self):
        manager = AlertManager()
        triggered = False

        def condition() -> bool:
            nonlocal triggered
            return triggered

        rule = AlertRule(
            name="test_rule",
            description="test description",
            severity=AlertSeverity.WARNING,
            condition=condition,
            cooldown_seconds=0,
        )
        manager.register(rule)
        events = manager.evaluate()
        assert len(events) == 0
        triggered = True
        events = manager.evaluate()
        assert len(events) == 1
        assert events[0].rule_name == "test_rule"
        assert events[0].severity == AlertSeverity.WARNING

    def test_cooldown(self):
        manager = AlertManager()
        call_count = 0

        def condition() -> bool:
            nonlocal call_count
            call_count += 1
            return True

        rule = AlertRule(
            name="cooldown_rule",
            description="cool",
            severity=AlertSeverity.INFO,
            condition=condition,
            cooldown_seconds=3600,
        )
        manager.register(rule)
        events1 = manager.evaluate()
        assert len(events1) == 1
        events2 = manager.evaluate()
        assert len(events2) == 0

    def test_unregister(self):
        manager = AlertManager()
        rule = AlertRule(
            name="temp", description="temp", severity=AlertSeverity.INFO,
            condition=lambda: True, cooldown_seconds=0,
        )
        manager.register(rule)
        manager.unregister("temp")
        assert len(manager._rules) == 0

    def test_get_history(self):
        manager = AlertManager()
        rule = AlertRule(
            name="hist", description="hist", severity=AlertSeverity.CRITICAL,
            condition=lambda: True, cooldown_seconds=0,
        )
        manager.register(rule)
        manager.evaluate()
        history = manager.get_history()
        assert len(history) >= 1

    def test_clear_history(self):
        manager = AlertManager()
        rule = AlertRule(
            name="clear_hist", description="ch", severity=AlertSeverity.WARNING,
            condition=lambda: True, cooldown_seconds=0,
        )
        manager.register(rule)
        manager.evaluate()
        manager.clear_history()
        assert len(manager.get_history()) == 0

    def test_alert_event_to_dict(self):
        event = AlertEvent(rule_name="r1", severity=AlertSeverity.CRITICAL, description="desc")
        d = event.to_dict()
        assert d["rule_name"] == "r1"
        assert d["severity"] == "critical"
