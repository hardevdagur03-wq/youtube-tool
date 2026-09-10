from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from security.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    def _make_app(self, config: dict[str, str] | None = None):
        async def homepage(request):
            return PlainTextResponse("OK")

        app = Starlette(routes=[Route("/", endpoint=homepage)])
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        return TestClient(app)

    def test_default_csp_header(self):
        client = self._make_app()
        resp = client.get("/")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    def test_x_content_type_options(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_deny(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_xss_protection(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("x-xss-protection") == "0"

    def test_strict_transport_security(self):
        client = self._make_app()
        resp = client.get("/")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "max-age=31536000" in hsts

    def test_referrer_policy(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self):
        client = self._make_app()
        resp = client.get("/")
        pp = resp.headers.get("permissions-policy", "")
        assert "camera=()" in pp

    def test_cross_origin_embedder_policy(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("cross-origin-embedder-policy") == "require-corp"

    def test_cross_origin_opener_policy(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("cross-origin-opener-policy") == "same-origin"

    def test_cross_origin_resource_policy(self):
        client = self._make_app()
        resp = client.get("/")
        assert resp.headers.get("cross-origin-resource-policy") == "same-origin"

    def test_custom_config_overrides_default(self):
        config = {
            "Content-Security-Policy": "default-src 'none'",
            "X-Frame-Options": "SAMEORIGIN",
        }
        client = self._make_app(config)
        resp = client.get("/")
        assert resp.headers.get("content-security-policy") == "default-src 'none'"
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_existing_header_not_overridden(self):
        async def custom_header(request):
            response = PlainTextResponse("OK")
            response.headers["X-Custom"] = "preserved"
            return response

        app = Starlette(routes=[Route("/", endpoint=custom_header)])
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.headers.get("x-custom") == "preserved"
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_all_default_headers_present(self):
        expected = {
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security",
            "referrer-policy",
            "permissions-policy",
            "cross-origin-embedder-policy",
            "cross-origin-opener-policy",
            "cross-origin-resource-policy",
        }
        client = self._make_app()
        resp = client.get("/")
        header_set = set(resp.headers.keys())
        for h in expected:
            assert h in header_set, f"Missing header: {h}"
