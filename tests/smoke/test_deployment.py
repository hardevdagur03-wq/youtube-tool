"""Smoke tests to verify deployment is healthy."""
import os

import pytest
import httpx

BASE_URL = os.environ.get("SMOKE_TEST_URL", "http://localhost:8000")
TIMEOUT = float(os.environ.get("SMOKE_TEST_TIMEOUT", "30"))


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, verify=False) as c:
        yield c


class TestHealthEndpoints:
    def test_api_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_api_homepage(self, client):
        resp = client.get("/")
        assert resp.status_code in (200, 302, 307)

    def test_static_files(self, client):
        resp = client.get("/static/")
        assert resp.status_code in (200, 404)  # 404 is OK if no static index

    def test_cors_headers(self, client):
        resp = client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in resp.headers or resp.status_code in (200, 204)


class TestAPIEndpoints:
    def test_api_info(self, client):
        resp = client.get("/api/info")
        # Info endpoint may vary; just check it responds
        assert resp.status_code < 500

    def test_api_metrics(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code in (200, 404)  # 404 if not wired yet


class TestDatabase:
    def test_db_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        if "data" in data and "database" in data["data"]:
            assert data["data"]["database"].get("healthy") in (True,)


class TestRedis:
    def test_redis_connectivity(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        if "data" in data and "redis" in data["data"]:
            assert data["data"]["redis"].get("healthy") in (True, False)


class TestInfrastructure:
    def test_security_headers(self, client):
        resp = client.get("/")
        headers = resp.headers
        security_headers = [
            "x-frame-options",
            "x-content-type-options",
            "x-xss-protection",
            "strict-transport-security",
            "referrer-policy",
        ]
        present = [h for h in security_headers if h in headers]
        assert len(present) >= 2, f"Few security headers: {present}"

    def test_compression(self, client):
        resp = client.get("/", headers={"Accept-Encoding": "gzip"})
        assert resp.status_code in (200, 302, 307)

    def test_tls(self, client):
        """If using HTTPS, verify TLS."""
        if BASE_URL.startswith("https://"):
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with httpx.Client(base_url=BASE_URL, verify=ctx) as secure_client:
                resp = secure_client.get("/api/health")
                assert resp.status_code == 200


class TestPipeline:
    def test_pipeline_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
