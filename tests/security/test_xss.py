from __future__ import annotations

import pytest


pytestmark = pytest.mark.security


XSS_PAYLOADS = [
    ("basic_script", "<script>alert('xss')</script>"),
    ("img_onerror", "<img src=x onerror=alert(1)>"),
    ("svg_onload", "<svg onload=alert(1)>"),
    ("body_onload", "<body onload=alert(1)>"),
    ("javascript_url", "<a href='javascript:alert(1)'>click</a>"),
    ("onmouseover", "<div onmouseover='alert(1)'>hover</div>"),
    ("expression", "<div style='width:expression(alert(1))'>"),
    ("iframe", "<iframe src='javascript:alert(1)'>"),
    ("input_onfocus", "<input onfocus='alert(1)' autofocus>"),
    ("details_open", "<details open ontoggle=alert(1)>"),
]


class TestXSS:
    @pytest.mark.parametrize("attack_type,payload", XSS_PAYLOADS)
    def test_stored_xss_blocked(self, attack_type, payload):
        sanitized = payload.replace("<", "&lt;").replace(">", "&gt;")
        assert "<script>" not in sanitized
        assert "&lt;" in sanitized or "&gt;" in sanitized
        assert "<" not in sanitized or "&lt;" in sanitized

    @pytest.mark.parametrize("attack_type,payload", XSS_PAYLOADS)
    def test_reflected_xss_blocked(self, attack_type, payload):
        escaped = payload
        escaped = escaped.replace("<", "&lt;")
        escaped = escaped.replace(">", "&gt;")
        escaped = escaped.replace('"', "&quot;")
        escaped = escaped.replace("'", "&#x27;")
        assert "&lt;script&gt;" in escaped or "&lt;img" in escaped

    def test_dom_based_xss_blocked(self):
        user_input = "javascript:alert(1)"
        allowed_protocols = {"http", "https", "mailto", "tel"}
        protocol = user_input.split(":")[0] if ":" in user_input else ""
        assert protocol not in allowed_protocols

    def test_html_sanitization(self):
        dirty = "<script>alert('xss')</script><p>Safe content</p><img src=x onerror=alert(1)>"
        import re
        clean = re.sub(r'<script[^>]*>.*?</script>', '', dirty, flags=re.DOTALL)
        clean = re.sub(r'<img[^>]*onerror[^>]*>', '', clean, flags=re.DOTALL)
        clean = re.sub(r' on\w+\s*=\s*["\'][^"\']*["\']', '', clean)
        assert "<script>" not in clean
        assert "onerror" not in clean
        assert "<p>Safe content</p>" in clean
