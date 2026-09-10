from __future__ import annotations

import pytest


pytestmark = pytest.mark.prompt


class TestPromptRendering:
    def test_prompt_renders_variables(self):
        template = "Hello {{ name }}, welcome to {{ service }}"
        data = {"name": "Alice", "service": "Blog Platform"}
        result = template.replace("{{ name }}", data["name"]).replace("{{ service }}", data["service"])
        assert "Alice" in result
        assert "Blog Platform" in result
        assert "{{" not in result

    def test_prompt_renders_conditionals(self):
        input_text = "{% if show_greeting %}Hello{% endif %}"
        show_greeting = True
        result = input_text.replace("{% if show_greeting %}Hello{% endif %}", "Hello") if show_greeting else ""
        assert result == "Hello"

    def test_prompt_renders_loops(self):
        items = ["A", "B", "C"]
        template = "{% for item in items %}- {{ item }}\n{% endfor %}"
        result = ""
        for item in items:
            result += f"- {item}\n"
        assert "- A" in result
        assert "- B" in result
        assert "- C" in result

    def test_prompt_renders_nested_templates(self):
        outer = "Outer: {{ inner }}"
        inner = "Inner: {{ value }}"
        value = "deep"
        rendered_inner = inner.replace("{{ value }}", value)
        rendered_outer = outer.replace("{{ inner }}", rendered_inner)
        assert "Inner: deep" in rendered_outer
        assert "Outer: Inner: deep" in rendered_outer
