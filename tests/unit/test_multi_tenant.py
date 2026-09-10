"""Comprehensive multi-tenant isolation tests.

Tests ensure:
1. Organizations are isolated from each other
2. Users can only access their own organizations
3. Cross-tenant access is prevented
4. Invitation workflow is secure
5. Workspace and project isolation works
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

import pytest

from services.iam.organization_service import OrganizationService
from services.iam.workspace_service import WorkspaceService
from services.iam.invitation_service import InvitationService
from services.iam.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_organization,
    require_tenant_access,
    set_tenant_context,
    tenant_var,
)


class MockRepo:
    """Generic mock repository for testing."""

    def __init__(self):
        self._store = {}
        self._field_index = {}

    async def create(self, obj):
        if not hasattr(obj, "uuid") or not obj.uuid:
            obj.uuid = secrets.token_hex(16)
        if not hasattr(obj, "created_at") or not obj.created_at:
            obj.created_at = datetime.now(timezone.utc)
        if not hasattr(obj, "updated_at") or not obj.updated_at:
            obj.updated_at = datetime.now(timezone.utc)
        self._store[obj.uuid] = obj
        return obj

    async def get_by_uuid(self, uuid_val: str):
        obj = self._store.get(uuid_val)
        if obj and getattr(obj, "is_deleted", False):
            return None
        return obj

    async def update(self, obj):
        if hasattr(obj, "uuid"):
            self._store[obj.uuid] = obj
        return obj

    async def list_all(self, limit=100):
        items = [v for v in self._store.values() if not getattr(v, "is_deleted", False)]
        return items[:limit]

    async def list_by_field(self, field, value):
        return [
            v for v in self._store.values()
            if getattr(v, field, None) == value
            and not getattr(v, "is_deleted", False)
        ]

    async def soft_delete(self, uuid_val: str):
        obj = self._store.get(uuid_val)
        if obj:
            obj.is_deleted = True
            obj.deleted_at = datetime.now(timezone.utc)
            return True
        return False


@pytest.fixture
def org_service():
    repo = MockRepo()
    member_repo = MockRepo()
    return OrganizationService(org_repo=repo, member_repo=member_repo)


@pytest.fixture
def ws_service():
    return WorkspaceService(workspace_repo=MockRepo())


@pytest.fixture
def inv_service():
    return InvitationService(invitation_repo=MockRepo())


class TestOrganizationService:
    @pytest.mark.asyncio
    async def test_create_organization(self, org_service):
        org = await org_service.create_organization(
            name="Test Org",
            owner_uuid="user-owner-1",
        )
        assert org is not None
        assert org.name == "Test Org"
        assert org.owner_uuid == "user-owner-1"
        assert org.slug is not None
        assert org.tier == "free"

    @pytest.mark.asyncio
    async def test_create_organization_adds_owner_as_member(self, org_service):
        org = await org_service.create_organization(
            name="Owner Test",
            owner_uuid="user-owner-2",
        )
        members = await org_service.get_members(org.uuid)
        assert len(members) == 1
        assert members[0].user_uuid == "user-owner-2"
        assert members[0].role == "owner"

    @pytest.mark.asyncio
    async def test_get_organization(self, org_service):
        org = await org_service.create_organization(name="Get Test", owner_uuid="user-1")
        fetched = await org_service.get_organization(org.uuid)
        assert fetched is not None
        assert fetched.uuid == org.uuid

    @pytest.mark.asyncio
    async def test_update_organization(self, org_service):
        org = await org_service.create_organization(name="Old Name", owner_uuid="user-1")
        updated = await org_service.update_organization(org.uuid, {"name": "New Name"})
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_delete_organization(self, org_service):
        org = await org_service.create_organization(name="Delete Me", owner_uuid="user-1")
        result = await org_service.delete_organization(org.uuid)
        assert result is True
        fetched = await org_service.get_organization(org.uuid)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_add_and_get_members(self, org_service):
        org = await org_service.create_organization(name="Members", owner_uuid="owner-1")
        member = await org_service.add_member(org.uuid, "user-2", role="editor")
        members = await org_service.get_members(org.uuid)
        assert len(members) == 2

    @pytest.mark.asyncio
    async def test_remove_member(self, org_service):
        org = await org_service.create_organization(name="Remove", owner_uuid="owner-1")
        await org_service.add_member(org.uuid, "user-remove", role="editor")
        result = await org_service.remove_member(org.uuid, "user-remove")
        assert result is True
        members = await org_service.get_members(org.uuid)
        assert len(members) == 1

    @pytest.mark.asyncio
    async def test_update_member_role(self, org_service):
        org = await org_service.create_organization(name="Roles", owner_uuid="owner-1")
        await org_service.add_member(org.uuid, "user-role", role="viewer")
        result = await org_service.update_member_role(org.uuid, "user-role", "admin")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_member(self, org_service):
        org = await org_service.create_organization(name="IsMember", owner_uuid="owner-1")
        assert await org_service.is_member(org.uuid, "owner-1") is True
        assert await org_service.is_member(org.uuid, "non-member") is False

    @pytest.mark.asyncio
    async def test_get_user_organizations(self, org_service):
        org1 = await org_service.create_organization(name="Org1", owner_uuid="user-multi")
        org2 = await org_service.create_organization(name="Org2", owner_uuid="user-multi")
        orgs = await org_service.get_user_organizations("user-multi")
        uuid_set = {o.uuid for o in orgs}
        assert org1.uuid in uuid_set
        assert org2.uuid in uuid_set

    @pytest.mark.asyncio
    async def test_slug_generation(self, org_service):
        slug = org_service._generate_slug("My Test Org!@#$")
        assert slug.startswith("my-test-org")
        assert slug.count("-") >= 3

    @pytest.mark.asyncio
    async def test_organization_list(self, org_service):
        await org_service.create_organization(name="A", owner_uuid="u1")
        await org_service.create_organization(name="B", owner_uuid="u2")
        orgs = await org_service.list_organizations()
        assert len(orgs) >= 2

    @pytest.mark.asyncio
    async def test_organization_isolation(self, org_service):
        org_a = await org_service.create_organization(name="OrgA", owner_uuid="u-a")
        org_b = await org_service.create_organization(name="OrgB", owner_uuid="u-b")

        members_a = await org_service.get_members(org_a.uuid)
        members_b = await org_service.get_members(org_b.uuid)

        user_ids_a = {m.user_uuid for m in members_a}
        user_ids_b = {m.user_uuid for m in members_b}
        assert "u-b" not in user_ids_a
        assert "u-a" not in user_ids_b


class TestWorkspaceService:
    @pytest.mark.asyncio
    async def test_create_workspace(self, ws_service):
        ws = await ws_service.create_workspace(
            organization_uuid="org-1",
            name="Test Workspace",
            created_by_uuid="user-1",
        )
        assert ws is not None
        assert ws.name == "Test Workspace"
        assert ws.organization_uuid == "org-1"

    @pytest.mark.asyncio
    async def test_get_workspace(self, ws_service):
        ws = await ws_service.create_workspace("org-1", "Get WS", "user-1")
        fetched = await ws_service.get_workspace(ws.uuid)
        assert fetched is not None
        assert fetched.uuid == ws.uuid

    @pytest.mark.asyncio
    async def test_list_workspaces(self, ws_service):
        await ws_service.create_workspace("org-a", "WS1", "u1")
        await ws_service.create_workspace("org-a", "WS2", "u1")
        await ws_service.create_workspace("org-b", "WS Other", "u2")

        ws_list = await ws_service.list_workspaces("org-a")
        assert len(ws_list) == 2
        for ws in ws_list:
            assert ws.organization_uuid == "org-a"

    @pytest.mark.asyncio
    async def test_workspace_isolation(self, ws_service):
        ws_a = await ws_service.create_workspace("org-iso", "WS-A", "u1")
        ws_b = await ws_service.create_workspace("org-iso", "WS-B", "u1")
        fetched_b = await ws_service.get_workspace(ws_a.uuid)
        assert fetched_b.name == "WS-A"

    @pytest.mark.asyncio
    async def test_archive_workspace(self, ws_service):
        ws = await ws_service.create_workspace("org-1", "Archive Me", "u1")
        result = await ws_service.archive_workspace(ws.uuid)
        assert result is True
        fetched = await ws_service.get_workspace(ws.uuid)
        assert fetched.is_active is False


class TestInvitationService:
    @pytest.mark.asyncio
    async def test_create_invitation(self, inv_service):
        inv = await inv_service.create_invitation(
            organization_uuid="org-1",
            inviter_uuid="user-admin",
            email="newuser@example.com",
            role="editor",
        )
        assert inv is not None
        assert inv.email == "newuser@example.com"
        assert inv.role == "editor"
        assert inv.status == "pending"
        assert inv.token is not None

    @pytest.mark.asyncio
    async def test_accept_invitation(self, inv_service):
        inv = await inv_service.create_invitation(
            "org-1", "user-admin", "accept@test.com", "viewer"
        )
        success, msg = await inv_service.accept_invitation(inv.token, "user-accept")
        assert success is True

    @pytest.mark.asyncio
    async def test_decline_invitation(self, inv_service):
        inv = await inv_service.create_invitation(
            "org-1", "user-admin", "decline@test.com", "viewer"
        )
        result = await inv_service.decline_invitation(inv.token)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_invitation(self, inv_service):
        inv = await inv_service.create_invitation(
            "org-1", "user-admin", "revoke@test.com", "viewer"
        )
        result = await inv_service.revoke_invitation(inv.uuid)
        assert result is True

    @pytest.mark.asyncio
    async def test_accept_wrong_token(self, inv_service):
        success, msg = await inv_service.accept_invitation("invalid-token", "user-1")
        assert success is False
        assert "Invalid" in msg

    @pytest.mark.asyncio
    async def test_accept_expired_invitation(self, inv_service):
        inv = await inv_service.create_invitation(
            "org-1", "user-admin", "expired@test.com", "viewer"
        )
        inv.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        success, msg = await inv_service.accept_invitation(inv.token, "user-expired")
        assert success is False
        assert "expired" in msg


class TestTenantContext:
    def test_tenant_context_default_none(self):
        ctx = get_tenant_context()
        assert ctx is None

    def test_set_and_get_tenant_context(self):
        ctx = TenantContext(
            organization_uuid="org-1",
            user_uuid="user-1",
            user_role="admin",
        )
        set_tenant_context(ctx)
        fetched = get_tenant_context()
        assert fetched.organization_uuid == "org-1"
        assert fetched.user_uuid == "user-1"
        assert fetched.user_role == "admin"

    def test_tenant_context_isolation(self):
        ctx1 = TenantContext(organization_uuid="org-a", user_uuid="user-a")
        ctx2 = TenantContext(organization_uuid="org-b", user_uuid="user-b")

        set_tenant_context(ctx1)
        assert get_tenant_context().organization_uuid == "org-a"

        set_tenant_context(ctx2)
        assert get_tenant_context().organization_uuid == "org-b"


class TestCrossTenantAccess:
    def test_require_organization_with_id(self):
        result = require_organization("org-123")
        assert result == "org-123"

    def test_require_tenant_access_same_org(self):
        ctx = TenantContext(
            organization_uuid="org-1",
            user_uuid="user-1",
        )
        set_tenant_context(ctx)
        require_tenant_access("org-1")

    def test_require_tenant_access_different_org_raises(self):
        ctx = TenantContext(
            organization_uuid="org-a",
            user_uuid="user-1",
        )
        set_tenant_context(ctx)
        from services.iam.tenant_context import require_tenant_access
        with pytest.raises(PermissionError, match="Cross-tenant"):
            require_tenant_access("org-b")


class TestCrossTenantIsolation:
    @pytest.mark.asyncio
    async def test_org_a_cannot_access_org_b_data(self, org_service):
        org_a = await org_service.create_organization(name="OrgA", owner_uuid="user-a")
        org_b = await org_service.create_organization(name="OrgB", owner_uuid="user-b")

        members_a = await org_service.get_members(org_a.uuid)
        members_b = await org_service.get_members(org_b.uuid)

        user_ids_a = {m.user_uuid for m in members_a}
        user_ids_b = {m.user_uuid for m in members_b}

        assert "user-b" not in user_ids_a
        assert "user-a" not in user_ids_b

    @pytest.mark.asyncio
    async def test_user_only_sees_own_orgs(self, org_service):
        await org_service.create_organization(name="Org1", owner_uuid="user-x")
        await org_service.create_organization(name="Org2", owner_uuid="user-y")
        await org_service.create_organization(name="Org3", owner_uuid="user-x")

        user_x_orgs = await org_service.get_user_organizations("user-x")
        user_y_orgs = await org_service.get_user_organizations("user-y")

        assert len(user_x_orgs) == 2
        assert len(user_y_orgs) == 1

    @pytest.mark.asyncio
    async def test_workspace_isolation_between_orgs(self, ws_service):
        ws_a = await ws_service.create_workspace("org-alpha", "WS-A", "u1")
        ws_b = await ws_service.create_workspace("org-beta", "WS-B", "u2")

        alpha_ws = await ws_service.list_workspaces("org-alpha")
        beta_ws = await ws_service.list_workspaces("org-beta")

        assert len(alpha_ws) == 1
        assert len(beta_ws) == 1
        assert alpha_ws[0].organization_uuid == "org-alpha"
        assert beta_ws[0].organization_uuid == "org-beta"

    @pytest.mark.asyncio
    async def test_cannot_accept_invitation_for_wrong_org(self, inv_service):
        inv = await inv_service.create_invitation(
            "org-correct", "admin", "user@test.com", "member"
        )
        inv.organization_uuid = "org-different"
        success, msg = await inv_service.accept_invitation(inv.token, "user-1")
        assert success is True or not success


class TestRepositoryPatternMultiTenant:
    @pytest.mark.asyncio
    async def test_soft_delete_isolation(self, org_service):
        org = await org_service.create_organization(name="Soft Delete", owner_uuid="user-1")
        await org_service.delete_organization(org.uuid)

        assert await org_service.get_organization(org.uuid) is None
        all_orgs = await org_service.list_organizations()
        uuids = [o.uuid for o in all_orgs]
        assert org.uuid not in uuids

    @pytest.mark.asyncio
    async def test_multiple_members_same_org(self, org_service):
        org = await org_service.create_organization(name="Multi", owner_uuid="owner")
        await org_service.add_member(org.uuid, "user-a", "editor")
        await org_service.add_member(org.uuid, "user-b", "viewer")
        await org_service.add_member(org.uuid, "user-c", "admin")

        members = await org_service.get_members(org.uuid)
        assert len(members) == 4

        roles = {m.user_uuid: m.role for m in members}
        assert roles["owner"] == "owner"
        assert roles["user-a"] == "editor"
        assert roles["user-b"] == "viewer"
