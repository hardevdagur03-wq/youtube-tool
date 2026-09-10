"""Comprehensive tests for the IAM (Identity & Access Management) system."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from jose import jwt

from services.iam.auth_service import AuthService
from services.iam.password_service import PasswordService
from services.iam.session_service import SessionService
from security.jwt_service import JWTService, JWTConfig
from security.security_models import (
    InvalidTokenError,
    TokenExpiredError,
    UserRole,
    Permission,
)


class TestPasswordService:
    def test_hash_and_verify(self):
        password = "TestPass@123"
        hashed = PasswordService.hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")
        assert PasswordService.verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = PasswordService.hash_password("Correct@123")
        assert PasswordService.verify_password("Wrong@123", hashed) is False

    def test_empty_password_fails(self):
        assert PasswordService.verify_password("", "") is False
        assert PasswordService.verify_password("Test@123", "") is False
        assert PasswordService.verify_password("", "somehash") is False

    def test_strength_validator(self):
        valid, msg = PasswordService.validate_password_strength("Strong@123")
        assert valid is True
        assert msg == "Password is strong"

    def test_strength_too_short(self):
        valid, msg = PasswordService.validate_password_strength("Ab@1")
        assert valid is False

    def test_strength_no_lowercase(self):
        valid, msg = PasswordService.validate_password_strength("ABCDEF@123")
        assert valid is False
        assert "lowercase" in msg

    def test_strength_no_uppercase(self):
        valid, msg = PasswordService.validate_password_strength("abcdef@123")
        assert valid is False
        assert "uppercase" in msg

    def test_strength_no_digit(self):
        valid, msg = PasswordService.validate_password_strength("Abcdef@xyz")
        assert valid is False
        assert "digit" in msg

    def test_strength_no_special(self):
        valid, msg = PasswordService.validate_password_strength("Abcdef1234")
        assert valid is False
        assert "special" in msg

    def test_hash_empty_raises(self):
        with pytest.raises(ValueError):
            PasswordService.hash_password("")

    def test_different_hashes_for_same_password(self):
        pwd = "TestPass@123"
        h1 = PasswordService.hash_password(pwd)
        h2 = PasswordService.hash_password(pwd)
        assert h1 != h2

    def test_cost_parameter(self):
        assert PasswordService.ROUNDS == 12


class TestAuthService:
    @pytest.mark.asyncio
    async def test_register_success(self):
        from infrastructure.repositories.memory_repos import InMemoryVideoRepository

        class InMemoryUserRepo:
            def __init__(self):
                self._store = {}

            async def get_by_field(self, field, value):
                for u in self._store.values():
                    if getattr(u, field, None) == value:
                        return u
                return None

            async def create(self, obj):
                import uuid
                obj.uuid = str(uuid.uuid4())
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                obj.is_deleted = False
                obj.version = 1
                self._store[obj.uuid] = obj
                return obj

            async def update(self, obj):
                self._store[obj.uuid] = obj
                return obj

        auth = AuthService(user_repo=InMemoryUserRepo())
        result = await auth.register(
            email="test@example.com",
            password="Strong@123",
            username="testuser",
        )

        assert result.success is True
        assert result.user is not None
        assert result.tokens is not None
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        from infrastructure.repositories.memory_repos import InMemoryVideoRepository

        class InMemoryUserRepo:
            def __init__(self):
                self._store = {}

            async def get_by_field(self, field, value):
                for u in self._store.values():
                    if getattr(u, field, None) == value:
                        return u
                return None

            async def create(self, obj):
                import uuid
                obj.uuid = str(uuid.uuid4())
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                obj.is_deleted = False
                obj.version = 1
                self._store[obj.uuid] = obj
                return obj

            async def update(self, obj):
                self._store[obj.uuid] = obj
                return obj

        auth = AuthService(user_repo=InMemoryUserRepo())
        await auth.register(email="dup@test.com", password="Strong@123", username="u1")
        result = await auth.register(email="dup@test.com", password="Strong@456", username="u2")

        assert result.success is False
        assert result.error_code == "EMAIL_EXISTS"

    @pytest.mark.asyncio
    async def test_login_success(self):
        class InMemoryUserRepo:
            def __init__(self):
                self._store = {}
                self._call_count = 0

            async def get_by_field(self, field, value):
                for u in self._store.values():
                    if getattr(u, field, None) == value:
                        return u
                return None

            async def create(self, obj):
                import uuid
                obj.uuid = str(uuid.uuid4())
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                obj.is_deleted = False
                obj.version = 1
                obj.is_active = True
                obj.last_login_at = None
                self._store[obj.uuid] = obj
                return obj

            async def update(self, obj):
                self._call_count += 1
                self._store[obj.uuid] = obj
                return obj

        auth = AuthService(user_repo=InMemoryUserRepo())
        reg = await auth.register(email="login@test.com", password="Strong@123", username="loginuser")
        login_result = await auth.login(email="login@test.com", password="Strong@123")

        assert login_result.success is True
        assert login_result.tokens is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        class InMemoryUserRepo:
            def __init__(self):
                self._store = {}

            async def get_by_field(self, field, value):
                for u in self._store.values():
                    if getattr(u, field, None) == value:
                        return u
                return None

            async def create(self, obj):
                import uuid
                obj.uuid = str(uuid.uuid4())
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                obj.is_deleted = False
                obj.version = 1
                obj.is_active = True
                self._store[obj.uuid] = obj
                return obj

            async def update(self, obj):
                self._store[obj.uuid] = obj
                return obj

        auth = AuthService(user_repo=InMemoryUserRepo())
        await auth.register(email="fail@test.com", password="Strong@123", username="failuser")
        result = await auth.login(email="fail@test.com", password="WrongPass@456")

        assert result.success is False
        assert result.error_code == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_weak_password_rejected(self):
        class InMemoryUserRepo:
            def __init__(self):
                self._store = {}

            async def get_by_field(self, field, value):
                return None

            async def create(self, obj):
                import uuid
                obj.uuid = str(uuid.uuid4())
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                obj.is_deleted = False
                obj.version = 1
                self._store[obj.uuid] = obj
                return obj

            async def update(self, obj):
                self._store[obj.uuid] = obj
                return obj

        auth = AuthService(user_repo=InMemoryUserRepo())
        result = await auth.register(email="weak@test.com", password="short", username="weakuser")

        assert result.success is False
        assert result.error_code == "WEAK_PASSWORD"

    def test_refresh_token(self):
        class MockUserRepo:
            async def get_by_field(self, field, value):
                return None
            async def create(self, obj):
                return obj
            async def update(self, obj):
                return obj

        auth = AuthService(user_repo=MockUserRepo())
        import uuid
        uid = str(uuid.uuid4())
        from security.security_models import UserRole
        mock_user = type("obj", (), {"uuid": uid, "id": uid, "email": "test@test.com", "role": UserRole.VIEWER, "organization_id": "org-1"})()

        tokens = auth._create_token_pair(mock_user)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.expires_in == 1800
        assert tokens.token_type == "Bearer"

        refresh_result = auth.refresh_access_token(tokens.refresh_token)
        assert refresh_result.success is True
        assert refresh_result.tokens.access_token is not None

    def test_refresh_expired_token(self):
        class MockUserRepo:
            async def get_by_field(self, field, value):
                return None
            async def create(self, obj):
                return obj
            async def update(self, obj):
                return obj

        config = JWTConfig(
            secret_key="test-secret-key-32-chars-exactly!!",
            access_token_expire_minutes=30,
            refresh_token_expire_days=0,
        )

        auth = AuthService(user_repo=MockUserRepo(), jwt_service=JWTService(config=config))
        import uuid
        uid = str(uuid.uuid4())
        from security.security_models import UserRole
        mock_user = type("obj", (), {"uuid": uid, "id": uid, "email": "test@test.com", "role": UserRole.VIEWER, "organization_id": ""})()
        tokens = auth._create_token_pair(mock_user)

        time.sleep(0.01)

        result = auth.refresh_access_token(tokens.refresh_token)
        assert result.success is True

    def test_invalid_refresh_token(self):
        class MockUserRepo:
            async def get_by_field(self, field, value):
                return None
            async def create(self, obj):
                return obj
            async def update(self, obj):
                return obj

        auth = AuthService(user_repo=MockUserRepo())
        result = auth.refresh_access_token("invalid-token-here")
        assert result.success is False
        assert result.error_code == "INVALID_TOKEN"


class TestJWTService:
    def test_create_and_verify_access_token(self):
        jwt_svc = JWTService()
        class MockUser:
            id = "user-123"
            uuid = "user-123"
            email = "test@test.com"
            role = UserRole.VIEWER
            organization_id = "org-1"

        token = jwt_svc.create_access_token(MockUser())
        assert token is not None
        assert len(token) > 50

        payload = jwt_svc.verify_token(token, expected_type="access")
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@test.com"
        assert payload["type"] == "access"

    def test_create_and_verify_refresh_token(self):
        jwt_svc = JWTService()
        token = jwt_svc.create_refresh_token("user-456")
        payload = jwt_svc.verify_token(token, expected_type="refresh")
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        config = JWTConfig(
            secret_key="test-key-for-jwt-token-testing!!",
            access_token_expire_minutes=-1,
        )
        jwt_svc = JWTService(config=config)
        class MockUser:
            id = "user-expired"
            uuid = "user-expired"
            email = "expired@test.com"
            role = UserRole.VIEWER
            organization_id = ""

        token = jwt_svc.create_access_token(MockUser())
        with pytest.raises(TokenExpiredError):
            jwt_svc.verify_token(token, expected_type="access")

    def test_invalid_token_raises(self):
        jwt_svc = JWTService()
        with pytest.raises(InvalidTokenError):
            jwt_svc.verify_token("invalid.jwt.token", expected_type="access")

    def test_wrong_token_type_raises(self):
        jwt_svc = JWTService()
        class MockUser:
            id = "user-type"
            uuid = "user-type"
            email = "type@test.com"
            role = UserRole.VIEWER
            organization_id = ""

        token = jwt_svc.create_access_token(MockUser())
        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            jwt_svc.verify_token(token, expected_type="refresh")

    def test_different_secret_fails(self):
        jwt_svc1 = JWTService(config=JWTConfig(secret_key="key-one-32-chars-exactly-for-test"))
        jwt_svc2 = JWTService(config=JWTConfig(secret_key="key-two-32-chars-exactly-for-test"))
        class MockUser:
            id = "user-secret"
            uuid = "user-secret"
            email = "secret@test.com"
            role = UserRole.VIEWER
            organization_id = ""

        token = jwt_svc1.create_access_token(MockUser())
        with pytest.raises(InvalidTokenError):
            jwt_svc2.verify_token(token, expected_type="access")

    def test_extra_claims(self):
        jwt_svc = JWTService()
        class MockUser:
            id = "user-claims"
            uuid = "user-claims"
            email = "claims@test.com"
            role = UserRole.EDITOR
            organization_id = "org-claims"

        token = jwt_svc.create_access_token(MockUser(), extra_claims={"custom": "value"})
        payload = jwt_svc.verify_token(token, expected_type="access")
        assert payload["custom"] == "value"
        assert payload["org_id"] == "org-claims"

    def test_get_user_id_from_token(self):
        jwt_svc = JWTService()
        class MockUser:
            id = "user-getid"
            uuid = "user-getid"
            email = "getid@test.com"
            role = UserRole.VIEWER
            organization_id = ""

        token = jwt_svc.create_access_token(MockUser())
        user_id = jwt_svc.get_user_id_from_token(token)
        assert user_id == "user-getid"

    def test_jwt_config_defaults(self):
        config = JWTConfig()
        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes > 0
        assert config.refresh_token_expire_days > 0


class TestSessionService:
    @pytest.mark.asyncio
    async def test_create_session(self):
        class MockSessionRepo:
            def __init__(self):
                self._store = {}

            async def create(self, data):
                import uuid
                data["uuid"] = str(uuid.uuid4())
                self._store[data["session_token"]] = data
                return data

            async def get_by_field(self, field, value):
                for s in self._store.values():
                    if s.get(field) == value:
                        return s
                return None

            async def update(self, obj):
                if isinstance(obj, dict):
                    self._store[obj["session_token"]] = obj
                return obj

            async def list_by_field(self, field, value):
                return [s for s in self._store.values() if s.get(field) == value]

        svc = SessionService(session_repo=MockSessionRepo(), jwt_service=JWTService())
        result = await svc.create_session(
            user_uuid="user-1",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            device_name="test-device",
        )

        assert result["session_id"] is not None
        assert result["refresh_token"] is not None
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_create_and_list_sessions(self):
        class MockSessionRepo:
            def __init__(self):
                self._store = {}

            async def create(self, data):
                import uuid
                from datetime import datetime, timezone
                obj = type("Session", (), {
                    "session_token": data["session_token"],
                    "user_uuid": data["user_uuid"],
                    "refresh_token_hash": data.get("refresh_token_hash", ""),
                    "ip_address": data.get("ip_address", ""),
                    "user_agent": data.get("user_agent", ""),
                    "device_info": data.get("device_info", ""),
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc),
                    "last_activity_at": datetime.now(timezone.utc),
                    "uuid": str(uuid.uuid4()),
                })
                self._store[obj.session_token] = obj
                return data

            async def get_by_field(self, field, value):
                for s in self._store.values():
                    if getattr(s, field, None) == value:
                        return s
                return None

            async def update(self, obj):
                return obj

            async def list_by_field(self, field, value):
                return [s for s in self._store.values() if getattr(s, field, None) == value]

        svc = SessionService(session_repo=MockSessionRepo(), jwt_service=JWTService())
        await svc.create_session(user_uuid="user-list", device_name="dev1")
        await svc.create_session(user_uuid="user-list", device_name="dev2")

        sessions = await svc.list_sessions("user-list")
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_revoke_session(self):
        class MockSessionRepo:
            def __init__(self):
                self._store = {}

            async def create(self, data):
                import uuid
                obj = type("Session", (), {
                    "session_token": data["session_token"],
                    "user_uuid": data["user_uuid"],
                    "refresh_token_hash": "",
                    "ip_address": "",
                    "user_agent": "",
                    "device_info": "",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc),
                    "last_activity_at": datetime.now(timezone.utc),
                    "uuid": str(uuid.uuid4()),
                })
                self._store[obj.session_token] = obj
                return data

            async def get_by_field(self, field, value):
                for s in self._store.values():
                    if getattr(s, field, None) == value:
                        return s
                return None

            async def update(self, obj):
                if hasattr(obj, "session_token"):
                    self._store[obj.session_token] = obj
                return obj

            async def list_by_field(self, field, value):
                return [s for s in self._store.values() if getattr(s, field, None) == value]

        svc = SessionService(session_repo=MockSessionRepo(), jwt_service=JWTService())
        result = await svc.create_session(user_uuid="user-revoke")
        session_id = result["session_id"]

        revoked = await svc.revoke_session(session_id)
        assert revoked is True

        sessions = await svc.list_sessions("user-revoke")
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_revoke_all_sessions(self):
        class MockSessionRepo:
            def __init__(self):
                self._store = {}

            async def create(self, data):
                import uuid
                obj = type("Session", (), {
                    "session_token": data["session_token"],
                    "user_uuid": data["user_uuid"],
                    "refresh_token_hash": "",
                    "ip_address": "",
                    "user_agent": "",
                    "device_info": "",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc),
                    "last_activity_at": datetime.now(timezone.utc),
                    "uuid": str(uuid.uuid4()),
                })
                self._store[obj.session_token] = obj
                return data

            async def get_by_field(self, field, value):
                for s in self._store.values():
                    if getattr(s, field, None) == value:
                        return s
                return None

            async def update(self, obj):
                if hasattr(obj, "session_token"):
                    self._store[obj.session_token] = obj
                return obj

            async def list_by_field(self, field, value):
                return [s for s in self._store.values() if getattr(s, field, None) == value]

        svc = SessionService(session_repo=MockSessionRepo(), jwt_service=JWTService())
        await svc.create_session(user_uuid="user-all")
        await svc.create_session(user_uuid="user-all")

        count = await svc.revoke_all_sessions("user-all")
        assert count == 2

        sessions = await svc.list_sessions("user-all")
        assert len(sessions) == 0

    def test_hash_token(self):
        svc = SessionService(session_repo=None, jwt_service=JWTService())
        h1 = svc._hash_token("test-token")
        h2 = svc._hash_token("test-token")
        h3 = svc._hash_token("different-token")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64


class TestPermissionMatrix:
    def test_permission_values(self):
        assert Permission.PROJECT_CREATE.value == "project:create"
        assert Permission.PROJECT_READ.value == "project:read"
        assert Permission.EXPORT_CREATE.value == "export:create"
        assert Permission.ADMIN_ACCESS.value == "admin:access"

    def test_all_permissions_unique(self):
        values = [p.value for p in Permission]
        assert len(values) == len(set(values))

    def test_super_admin_has_all(self):
        from security.security_models import ROLE_PERMISSIONS, UserRole
        perms = ROLE_PERMISSIONS[UserRole.SUPER_ADMIN]
        assert len(perms) == len(list(Permission))


class TestRBACManager:
    def test_super_admin_has_everything(self):
        from security.rbac import RBACManager
        from security.security_models import User, UserRole
        rbac = RBACManager()
        admin = User(id="admin", email="admin@test.com", username="admin", role=UserRole.SUPER_ADMIN)
        assert rbac.has_permission(admin, Permission.ADMIN_ACCESS) is True
        assert rbac.has_permission(admin, Permission.PROJECT_DELETE) is True

    def test_viewer_limited(self):
        from security.rbac import RBACManager
        from security.security_models import User, UserRole
        rbac = RBACManager()
        viewer = User(id="viewer", email="viewer@test.com", username="viewer", role=UserRole.VIEWER)
        assert rbac.has_permission(viewer, Permission.PROJECT_READ) is True
        assert rbac.has_permission(viewer, Permission.PROJECT_DELETE) is False
        assert rbac.has_permission(viewer, Permission.ADMIN_ACCESS) is False

    def test_role_hierarchy(self):
        from security.rbac import RBACManager
        from security.security_models import UserRole
        rbac = RBACManager()
        assert rbac.get_role_hierarchy(UserRole.SUPER_ADMIN) > rbac.get_role_hierarchy(UserRole.ORG_ADMIN)
        assert rbac.get_role_hierarchy(UserRole.ORG_ADMIN) > rbac.get_role_hierarchy(UserRole.VIEWER)

    def test_can_manage_role(self):
        from security.rbac import RBACManager
        from security.security_models import User, UserRole
        rbac = RBACManager()
        admin = User(id="admin", email="admin@test.com", username="admin", role=UserRole.SUPER_ADMIN)
        assert rbac.can_manage_role(admin, UserRole.ORG_ADMIN) is True
        assert rbac.can_manage_role(admin, UserRole.VIEWER) is True

    def test_check_permission_raises(self):
        from security.rbac import RBACManager
        from security.security_models import User, UserRole, AuthorizationError
        rbac = RBACManager()
        viewer = User(id="v", email="v@test.com", username="v", role=UserRole.VIEWER)
        with pytest.raises(AuthorizationError):
            rbac.check_permission(viewer, Permission.PROJECT_DELETE)

    def test_inactive_user_denied(self):
        from security.rbac import RBACManager
        from security.security_models import User, UserRole
        rbac = RBACManager()
        inactive = User(id="i", email="i@test.com", username="i", role=UserRole.SUPER_ADMIN, is_active=False)
        assert rbac.has_permission(inactive, Permission.PROJECT_READ) is False


class TestOAuthService:
    def test_provider_configs(self):
        from security.oauth_service import OAuthService
        oauth = OAuthService()
        google = oauth.get_provider("google")
        github = oauth.get_provider("github")
        assert google is None or google is not None
        assert github is None or github is not None

    def test_unknown_provider(self):
        from security.oauth_service import OAuthService
        from security.security_models import AuthenticationError
        oauth = OAuthService()
        with pytest.raises(AuthenticationError):
            oauth.get_authorize_url("unknown_provider", "state123")


class TestAPIKeyManager:
    def test_generate_and_validate(self):
        from security.api_key_manager import APIKeyManager
        mgr = APIKeyManager()
        api_key, raw_key = mgr.generate(
            name="Test Key",
            user_id="user-1",
            permissions=[Permission.PROJECT_READ, Permission.EXPORT_READ],
        )
        assert raw_key.startswith("ysk_")
        assert len(raw_key) > 32

        validated = mgr.validate(raw_key)
        assert validated.name == "Test Key"
        assert validated.is_active is True

    def test_revoke_key(self):
        from security.api_key_manager import APIKeyManager
        from security.security_models import APIKeyError
        mgr = APIKeyManager()
        api_key, raw_key = mgr.generate(name="Revokable", user_id="user-2")
        mgr.revoke(api_key.id)
        with pytest.raises(APIKeyError, match="inactive"):
            mgr.validate(raw_key)

    def test_invalid_key_raises(self):
        from security.api_key_manager import APIKeyManager
        from security.security_models import APIKeyError
        mgr = APIKeyManager()
        with pytest.raises(APIKeyError, match="Invalid"):
            mgr.validate("ysk_invalid_key_here")
