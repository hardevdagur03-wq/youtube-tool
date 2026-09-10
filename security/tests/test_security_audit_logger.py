from __future__ import annotations

from security.audit_logger import SecurityAuditLogger
from security.security_models import AlertSeverity, SecurityEvent


class TestSecurityAuditLogger:
    def setup_method(self):
        self.logger = SecurityAuditLogger()

    def test_log_event_creates_security_event(self):
        self.logger.log_event(
            event_type="auth.login",
            actor_id="user-1",
            action="login",
        )
        events = self.logger.get_recent()
        assert len(events) == 1
        assert events[0]["event_type"] == "auth.login"
        assert events[0]["actor_id"] == "user-1"

    def test_log_event_with_details(self):
        self.logger.log_event(
            event_type="permission.denied",
            actor_id="user-1",
            action="access_denied",
            resource_type="document",
            resource_id="doc-123",
            details={"required_permission": "admin:access"},
            ip_address="192.168.1.1",
        )
        events = self.logger.get_recent()
        assert events[0]["resource_type"] == "document"
        assert events[0]["resource_id"] == "doc-123"
        assert events[0]["details"]["required_permission"] == "admin:access"

    def test_log_event_with_trace_id(self):
        self.logger.log_event(
            event_type="auth.login",
            actor_id="user-1",
            action="login",
            trace_id="trace-abc",
        )
        events = self.logger.get_recent()
        assert events[0]["trace_id"] == "trace-abc"

    def test_get_recent_returns_most_recent(self):
        for i in range(5):
            self.logger.log_event(
                event_type="auth.login",
                actor_id=f"user-{i}",
                action="login",
            )
        events = self.logger.get_recent(limit=2)
        assert len(events) == 2

    def test_get_by_actor_filters_correctly(self):
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login")
        self.logger.log_event(event_type="auth.logout", actor_id="user-2", action="logout")
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login")
        events = self.logger.get_by_actor("user-1")
        assert len(events) == 2
        assert all(e["actor_id"] == "user-1" for e in events)

    def test_get_by_type_filters_correctly(self):
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login")
        self.logger.log_event(event_type="auth.failed", actor_id="user-2", action="login_failed")
        self.logger.log_event(event_type="auth.login", actor_id="user-3", action="login")
        events = self.logger.get_by_type("auth.login")
        assert len(events) == 2

    def test_get_by_resource_filters_correctly(self):
        self.logger.log_event(
            event_type="permission.denied", actor_id="user-1", action="denied",
            resource_type="project", resource_id="proj-1",
        )
        self.logger.log_event(
            event_type="permission.denied", actor_id="user-2", action="denied",
            resource_type="project", resource_id="proj-2",
        )
        events = self.logger.get_by_resource("project", "proj-1")
        assert len(events) == 1

    def test_get_alerts_filters_by_severity(self):
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login", severity="info")
        self.logger.log_event(event_type="threat.detected", actor_id="user-2", action="brute_force", severity="high")
        alerts = self.logger.get_alerts(min_severity="medium")
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "high"

    def test_get_summary(self):
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login")
        self.logger.log_event(event_type="auth.login", actor_id="user-2", action="login")
        self.logger.log_event(event_type="auth.failed", actor_id="user-1", action="login_failed", severity="medium")
        summary = self.logger.get_summary()
        assert summary["total_events"] == 3
        assert summary["by_type"]["auth.login"] == 2
        assert summary["by_type"]["auth.failed"] == 1
        assert summary["unique_actors"] == 2

    def test_log_event_with_severity_parsing(self):
        self.logger.log_event(event_type="threat.blocked", actor_id="user-1", action="blocked", severity="critical")
        events = self.logger.get_recent()
        assert events[0]["severity"] == "critical"

    def test_log_event_invalid_severity_defaults_to_info(self):
        self.logger.log_event(event_type="test", actor_id="user-1", action="test", severity="unknown")
        events = self.logger.get_recent()
        assert events[0]["severity"] == "info"

    def test_clear_resets_all_events(self):
        self.logger.log_event(event_type="auth.login", actor_id="user-1", action="login")
        self.logger.clear()
        assert len(self.logger.get_recent()) == 0

    def test_log_event_with_user_agent(self):
        self.logger.log_event(
            event_type="auth.login", actor_id="user-1", action="login",
            user_agent="Mozilla/5.0",
        )
        events = self.logger.get_recent()
        assert events[0]["user_agent"] == "Mozilla/5.0"

    def test_event_categories_coverage(self):
        for event_type in SecurityAuditLogger.EVENT_CATEGORIES:
            self.logger.log_event(event_type=event_type, actor_id="user-1", action=event_type)
        events = self.logger.get_recent(limit=50)
        assert len(events) == len(SecurityAuditLogger.EVENT_CATEGORIES)
