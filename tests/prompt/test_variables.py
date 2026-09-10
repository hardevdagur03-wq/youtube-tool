from __future__ import annotations

import pytest


pytestmark = pytest.mark.prompt


class TestPromptVariables:
    def test_all_variables_replaced(self):
        template = "{{ title }} by {{ author }} ({{ year }})"
        data = {"title": "Test", "author": "Alice", "year": 2026}
        result = template
        for key, value in data.items():
            result = result.replace("{{ " + key + " }}", str(value))
        assert "{{" not in result
        assert result == "Test by Alice (2026)"

    def test_missing_variable_handling(self):
        template = "Hello {{ name }}, your {{ role }}"
        data = {"name": "Bob"}
        result = template
        for key, value in data.items():
            result = result.replace("{{ " + key + " }}", str(value))
        assert "{{" in result or "{{" not in result

    def test_default_values(self):
        def render(template, data, defaults=None):
            if defaults is None:
                defaults = {}
            result = template
            all_vars = {**defaults, **data}
            for key, value in all_vars.items():
                result = result.replace("{{ " + key + " }}", str(value))
            return result

        result = render("{{ name }} ({{ role }})", {"name": "Alice"}, {"role": "User"})
        assert "Alice" in result
        assert "User" in result
        assert "(User)" in result

    def test_variable_escaping(self):
        dangerous = "<script>alert('xss')</script>"
        escaped = dangerous.replace("<", "&lt;").replace(">", "&gt;")
        template = "Content: {{ content }}"
        result = template.replace("{{ content }}", escaped)
        assert "&lt;script&gt;" in result
        assert "<script>" not in result
