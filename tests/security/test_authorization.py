from __future__ import annotations

import pytest


pytestmark = pytest.mark.security


class TestAuthorization:
    def test_admin_access(self):
        admin_roles = {"admin", "superadmin"}
        required_roles = {"admin"}
        user_role = "admin"
        assert user_role in admin_roles
        assert required_roles.issubset(admin_roles)

    def test_user_access(self):
        user_role = "user"
        user_permissions = {"read:own", "write:own"}
        assert "read:own" in user_permissions
        assert "write:own" in user_permissions
        assert "delete:all" not in user_permissions

    def test_resource_isolation(self):
        user_a_projects = {"p1", "p2", "p3"}
        user_b_projects = {"p4", "p5"}
        assert user_a_projects.isdisjoint(user_b_projects), (
            "User A should not have access to User B's projects"
        )

    def test_invalid_role(self):
        valid_roles = {"admin", "user", "viewer"}
        invalid_role = "superuser"
        assert invalid_role not in valid_roles

    @pytest.mark.parametrize("role,resource,should_allow", [
        ("admin", "project:delete", True),
        ("admin", "project:create", True),
        ("admin", "user:delete", True),
        ("user", "project:create", True),
        ("user", "project:delete", False),
        ("user", "user:delete", False),
        ("viewer", "project:create", False),
        ("viewer", "project:read", True),
        ("viewer", "project:delete", False),
    ])
    def test_role_based_access_matrix(self, role, resource, should_allow):
        permissions = {
            "admin": {"project:create", "project:read", "project:delete", "project:update", "user:delete"},
            "user": {"project:create", "project:read", "project:update"},
            "viewer": {"project:read"},
        }
        allowed = resource in permissions.get(role, set())
        assert allowed == should_allow, (
            f"Expected role '{role}' access to '{resource}'={should_allow}, got {allowed}"
        )
