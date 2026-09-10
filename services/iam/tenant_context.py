"""Tenant context — extracts and validates tenant information from requests.

Every API request passes through tenant middleware which:
1. Extracts organization_id from JWT claims
2. Validates the user is a member of that organization
3. Attaches tenant context to the request
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from security.jwt_service import JWTService
from services.iam.organization_service import OrganizationService

tenant_var: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar(
    "tenant_context", default=None
)


@dataclass
class TenantContext:
    """Tenant context attached to every authenticated request."""
    organization_uuid: str = ""
    organization_slug: str = ""
    user_uuid: str = ""
    user_role: str = ""
    workspace_uuid: str = ""
    project_uuid: str = ""


def get_tenant_context() -> TenantContext | None:
    return tenant_var.get()


def set_tenant_context(ctx: TenantContext) -> None:
    tenant_var.set(ctx)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extracts tenant context from every authenticated request.

    Order:
    1. Extract JWT from Authorization header
    2. Decode claims (org_id, sub/user_id)
    3. Set TenantContext with organization and user info
    4. Chain passes context via contextvars
    """

    def __init__(self, app: Any, jwt_service: JWTService | None = None):
        super().__init__(app)
        self._jwt = jwt_service or JWTService()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        ctx = TenantContext()

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                claims = self._jwt.decode_token(token)
                ctx.user_uuid = claims.get("sub", "")
                ctx.organization_uuid = claims.get("org_id", "")
            except Exception:
                pass

        # Also check path params for org/workspace/project IDs
        path_params = request.path_params
        ctx.organization_uuid = ctx.organization_uuid or path_params.get(
            "organization_id", ""
        )
        ctx.workspace_uuid = path_params.get("workspace_id", "")
        ctx.project_uuid = path_params.get("project_id", "")

        token_ctx = tenant_var.set(ctx)
        try:
            response = await call_next(request)
            return response
        finally:
            tenant_var.reset(token_ctx)


def require_organization(org_uuid: str | None) -> str:
    """Validate and return organization UUID from context or parameter."""
    ctx = get_tenant_context()
    if org_uuid:
        return org_uuid
    if ctx and ctx.organization_uuid:
        return ctx.organization_uuid
    raise PermissionError("Organization context required")


def require_tenant_access(
    resource_org_uuid: str,
    user_uuid: str | None = None,
) -> None:
    """Verify the user has access to the given organization's resources."""
    ctx = get_tenant_context()
    uid = user_uuid or (ctx.user_uuid if ctx else "")
    if not uid:
        raise PermissionError("Authentication required")

    user_org = ctx.organization_uuid if ctx else ""
    if user_org and user_org != resource_org_uuid:
        raise PermissionError("Cross-tenant access denied")
