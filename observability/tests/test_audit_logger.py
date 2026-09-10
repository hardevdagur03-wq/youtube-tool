from __future__ import annotations

from observability.audit_logger import AuditLogger, AuditEvent, AuditEventType


class TestAuditLogger:
    def setup_method(self):
        self.logger = AuditLogger()

    def test_log_event(self):
        self.logger.log_event(
            event_type=AuditEventType.PROJECT_CREATED,
            actor_id="user1",
            action="create_project",
            resource_type="project",
            resource_id="proj_123",
        )
        recent = self.logger.get_recent()
        assert len(recent) == 1
        assert recent[0]["event_type"] == "project.created"
        assert recent[0]["actor_id"] == "user1"

    def test_log(self):
        event = AuditEvent(
            event_type=AuditEventType.PIPELINE_STARTED,
            actor_id="user2",
            action="start_pipeline",
            resource_type="pipeline",
            resource_id="pipe_456",
            details={"stage": "transcript"},
        )
        self.logger.log(event)
        recent = self.logger.get_recent()
        assert len(recent) == 1

    def test_get_by_actor(self):
        self.logger.log_event(event_type=AuditEventType.USER_LOGIN, actor_id="alice", action="login")
        self.logger.log_event(event_type=AuditEventType.USER_LOGOUT, actor_id="alice", action="logout")
        self.logger.log_event(event_type=AuditEventType.USER_LOGIN, actor_id="bob", action="login")
        alice_events = self.logger.get_by_actor("alice")
        assert len(alice_events) == 2
        bob_events = self.logger.get_by_actor("bob")
        assert len(bob_events) == 1

    def test_get_by_resource(self):
        self.logger.log_event(
            event_type=AuditEventType.PROJECT_UPDATED, actor_id="u1",
            action="update", resource_type="project", resource_id="proj_1",
        )
        self.logger.log_event(
            event_type=AuditEventType.PROJECT_DELETED, actor_id="u1",
            action="delete", resource_type="project", resource_id="proj_1",
        )
        self.logger.log_event(
            event_type=AuditEventType.EXPORT_CREATED, actor_id="u1",
            action="export", resource_type="export", resource_id="exp_1",
        )
        proj_events = self.logger.get_by_resource("project", "proj_1")
        assert len(proj_events) == 2

    def test_get_by_type(self):
        self.logger.log_event(event_type=AuditEventType.SECURITY_EVENT, actor_id="u1", action="alert")
        self.logger.log_event(event_type=AuditEventType.SECURITY_EVENT, actor_id="u2", action="blocked")
        security = self.logger.get_by_type(AuditEventType.SECURITY_EVENT)
        assert len(security) == 2

    def test_get_summary(self):
        self.logger.log_event(event_type=AuditEventType.USER_LOGIN, actor_id="u1", action="login")
        self.logger.log_event(event_type=AuditEventType.USER_LOGIN, actor_id="u2", action="login")
        self.logger.log_event(event_type=AuditEventType.PROJECT_CREATED, actor_id="u1", action="create")
        summary = self.logger.get_summary()
        assert summary["total_events"] == 3
        assert summary["unique_actors"] == 2
        assert summary["by_type"]["user.login"] == 2

    def test_clear(self):
        self.logger.log_event(event_type=AuditEventType.USER_LOGIN, actor_id="u1", action="login")
        self.logger.clear()
        assert len(self.logger.get_recent()) == 0

    def test_all_event_types_present(self):
        types = [e.value for e in AuditEventType]
        assert "user.login" in types
        assert "project.created" in types
        assert "pipeline.started" in types
        assert "ai.execution" in types
        assert "security.event" in types
        assert len(types) == 18
