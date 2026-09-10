from __future__ import annotations

import uuid

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from security.auth_manager import AuthManager
from security.security_middleware import SecurityMiddleware
from security.security_models import User, UserRole


class TestSecurityMiddleware:
    def setup_method(self):
        self.auth_manager = AuthManager()
        self.user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            role=UserRole.EDITOR,
            is_active=True,
            password_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        )
        self.auth_manager.register_user(self.user)

    def _make_app(self):
        async def protected(request):
            user = getattr(request.state, "user", None)
            if user:
                return JSONResponse({"user_id": user.id, "email": user.email})
            return JSONResponse({"error": "no user"}, status_code=401)

        async def public(request):
            return PlainTextResponse("public")

        async def admin(request):
            return JSONResponse({"role": "admin"})

        app = Starlette(routes=[
            Route("/protected", endpoint=protected),
            Route("/public", endpoint=public),
            Route("/admin", endpoint=admin),
        ])
        app.add_middleware(
            SecurityMiddleware,
            auth_manager=self.auth_manager,
        )
        return TestClient(app)

    def test_public_endpoint_no_auth_required(self):
        client = self._make_app()
        resp = client.get("/public")
        assert resp.status_code == 200
        assert resp.text == "public"

    def test_protected_endpoint_with_valid_token(self):
        client = self._make_app()
        login = self.auth_manager.authenticate(self.user.email, "test")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == self.user.id

    def test_protected_endpoint_without_token(self):
        client = self._make_app()
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_protected_endpoint_with_invalid_token(self):
        client = self._make_app()
        resp = client.get("/protected", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_protected_endpoint_expired_token_returns_401(self):
        client = self._make_app()
        resp = client.get("/protected", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNTE2MjM5MDIyfQ.7UY1sFPLiFYDrzXHqJmFv0YpE9Z1c0b3Q2a5d8g7h3k6l9p0o2i1u4y5t6r7e8w9q0"})
        assert resp.status_code in (401, 403)

    def test_health_endpoint_excluded(self):
        client = self._make_app()
        resp = client.get("/health")
        assert resp.status_code == 200 or resp.status_code == 404

    def test_api_key_authentication(self):
        client = self._make_app()
        api_key_obj, raw_key = self.auth_manager._api_key_manager.generate(
            user_id=self.user.id, name="test-key"
        )
        resp = client.get("/protected", headers={"Authorization": f"ApiKey {raw_key}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == self.user.id

    def test_rate_limiting_returns_429(self):
        from security.rate_limiter import SecurityRateLimiter, RateLimitRule
        limiter = SecurityRateLimiter()
        auth_mgr = AuthManager(rate_limiter=limiter)
        user = User(
            id=str(uuid.uuid4()), email="ratelimit@test.com", username="ratelimit",
            is_active=True, password_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        )
        auth_mgr.register_user(user)

        async def protected(request):
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/protected", endpoint=protected)])
        app.add_middleware(SecurityMiddleware, auth_manager=auth_mgr, rate_limiter=limiter)
        client = TestClient(app)

        limiter._rules.clear()
        limiter.add_rule(RateLimitRule(key_prefix="api:", max_requests=1, window_seconds=60))

        client.get("/protected")
        resp = client.get("/protected")
        assert resp.status_code == 429

    def test_middleware_sets_request_state(self):
        client = self._make_app()
        login = self.auth_manager.authenticate(self.user.email, "test")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert resp.status_code == 200
