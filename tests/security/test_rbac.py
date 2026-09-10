from __future__ import annotations

import pytest


pytestmark = pytest.mark.security


class TestRBAC:
    def test_role_permissions(self):
        roles = {
            "admin": {"create", "read", "update", "delete", "manage_users"},
            "editor": {"create", "read", "update"},
            "viewer": {"read"},
        }
        assert "delete" in roles["admin"]
        assert "delete" not in roles["editor"]
        assert roles["viewer"] == {"read"}

    def test_permission_inheritance(self):
        role_hierarchy = {
            "viewer": {"read"},
            "editor": {"create", "read", "update"},
            "admin": {"create", "read", "update", "delete", "manage_users"},
        }
        for role, perms in role_hierarchy.items():
            if role == "admin":
                assert perms.issuperset(role_hierarchy["editor"])
            if role == "editor":
                assert perms.issuperset(role_hierarchy["viewer"])

    def test_role_assignment(self):
        user_roles = {
            "alice": "admin",
            "bob": "editor",
            "charlie": "viewer",
        }
        assert user_roles["alice"] == "admin"
        assert user_roles["bob"] == "editor"
        assert user_roles["charlie"] == "viewer"

    @pytest.mark.parametrize("role,action,expected", [
        ("admin", "manage_users", True),
        ("editor", "manage_users", False),
        ("viewer", "create", False),
        ("viewer", "read", True),
        ("editor", "update", True),
        ("admin", "delete", True),
        ("viewer", "delete", False),
        ("", "read", False),
    ])
    def test_unauthorized_action_denied(self, role, action, expected):
        role_perms = {
            "admin": {"create", "read", "update", "delete", "manage_users"},
            "editor": {"create", "read", "update"},
            "viewer": {"read"},
        }
        allowed = action in role_perms.get(role, set())
        assert allowed == expected
