from __future__ import annotations

from typing import Any

from security.security_models import AuthorizationError, Permission, User, UserRole
from security.rbac import RBACManager


class PermissionService:
    def __init__(self, rbac: RBACManager | None = None):
        self._rbac = rbac or RBACManager()

    def require(self, user: User, permission: Permission) -> None:
        self._rbac.check_permission(user, permission)

    def require_any(self, user: User, permissions: list[Permission]) -> None:
        self._rbac.check_any_permission(user, permissions)

    def can(self, user: User, permission: Permission) -> bool:
        return self._rbac.has_permission(user, permission)

    def require_role(self, user: User, role: UserRole) -> None:
        if user.role != role and user.role != UserRole.SUPER_ADMIN:
            raise AuthorizationError(
                f"Requires role '{role.value}', user has '{user.role.value}'"
            )

    def require_owner_or_admin(self, user: User, resource_owner_id: str) -> None:
        if user.id == resource_owner_id or user.role == UserRole.SUPER_ADMIN:
            return
        raise AuthorizationError("Resource access denied: not owner or admin")

    def filter_by_permission(self, user: User, items: list[Any], permission: Permission) -> list[Any]:
        if self._rbac.has_permission(user, permission):
            return items
        return []
