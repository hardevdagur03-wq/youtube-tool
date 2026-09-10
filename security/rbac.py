from __future__ import annotations

from security.security_models import (
    Permission, ROLE_PERMISSIONS, AuthorizationError, User, UserRole,
)


class RBACManager:
    def __init__(self):
        self._role_permissions: dict[UserRole, list[Permission]] = dict(ROLE_PERMISSIONS)

    def get_permissions(self, role: UserRole) -> list[Permission]:
        return list(self._role_permissions.get(role, []))

    def has_permission(self, user: User, permission: Permission) -> bool:
        if not user.is_active:
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return permission in self._role_permissions.get(user.role, [])

    def has_any_permission(self, user: User, permissions: list[Permission]) -> bool:
        return any(self.has_permission(user, p) for p in permissions)

    def has_all_permissions(self, user: User, permissions: list[Permission]) -> bool:
        return all(self.has_permission(user, p) for p in permissions)

    def check_permission(self, user: User, permission: Permission) -> None:
        if not self.has_permission(user, permission):
            raise AuthorizationError(
                f"User '{user.id}' with role '{user.role.value}' "
                f"lacks required permission: {permission.value}"
            )

    def check_any_permission(self, user: User, permissions: list[Permission]) -> None:
        if not self.has_any_permission(user, permissions):
            raise AuthorizationError(
                f"User '{user.id}' with role '{user.role.value}' "
                f"lacks any of required permissions: {[p.value for p in permissions]}"
            )

    def get_role_hierarchy(self, role: UserRole) -> int:
        hierarchy = {
            UserRole.SUPER_ADMIN: 100,
            UserRole.ORG_ADMIN: 80,
            UserRole.EDITOR: 60,
            UserRole.WRITER: 50,
            UserRole.REVIEWER: 40,
            UserRole.VIEWER: 30,
            UserRole.API_CLIENT: 20,
        }
        return hierarchy.get(role, 0)

    def can_manage_role(self, actor: User, target_role: UserRole) -> bool:
        if actor.role == UserRole.SUPER_ADMIN:
            return True
        if actor.role == UserRole.ORG_ADMIN and target_role in (
            UserRole.EDITOR, UserRole.WRITER, UserRole.REVIEWER, UserRole.VIEWER, UserRole.API_CLIENT,
        ):
            return True
        return False
